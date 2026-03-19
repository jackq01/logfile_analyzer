import sys
import os
import io
import logging
import traceback
import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QTextEdit, QFileDialog, QCheckBox, 
                             QDateEdit, QTimeEdit, QListWidget, QListWidgetItem, 
                             QSplitter, QMessageBox, QRadioButton, QGroupBox, QProgressBar, QAbstractItemView,
                             QTabWidget, QAbstractSpinBox, QSizePolicy)
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QPalette, QIcon
from PyQt6.QtCore import Qt, QTimer

from .utils import generate_light_colors
from .log_processor import LogProcessor
from .highlight_delegate import HighlightDelegate
from .style_manager import style_manager, responsive_font_manager


def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

_auth_manager = None
_AuthTab = None
_HelpTab = None


def _get_auth_manager():
    global _auth_manager
    if _auth_manager is None:
        from .auth_manager import get_auth_manager
        _auth_manager = get_auth_manager()
    return _auth_manager


def _get_auth_tab_class():
    global _AuthTab
    if _AuthTab is None:
        from .auth_tab import AuthTab
        _AuthTab = AuthTab
    return _AuthTab


def _get_help_tab_class():
    global _HelpTab
    if _HelpTab is None:
        from .help_tab import HelpTab
        _HelpTab = HelpTab
    return _HelpTab

class LogAnalyzerApp(QMainWindow):
    LOG_REGEX_PATTERN = r'(%@\d+%[\s\S]*?(?=%@\d+%|\Z))'
    TIME_REGEX_PATTERN = r'(\w+)\s+(\d{1,2})\s+(\d{1,2}):(\d{1,2}):(\d{1,2}):(\d{1,3})\s+(\d{4})'

    def __init__(self):
        super().__init__()
        sys.excepthook = self.handle_uncaught_exception
        
        self.cache = {}
        self.page_size = 1000
        self.current_page = 0
        self.total_pages = 0
        
        self.log_display = QListWidget()
        self.log_display.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.log_display.setItemDelegate(HighlightDelegate(self.log_display))
        self.log_display.itemChanged.connect(self.on_log_item_changed)
        self.log_display.verticalScrollBar().valueChanged.connect(self.handle_scroll)
        
        self.log_display.setFont(responsive_font_manager.get_font('log_display'))
        self.log_display.setStyleSheet(style_manager.get_log_display_style())
        self.log_display.installEventFilter(self)
        
        self.setWindowTitle("日志分析工具v1.0")
        icon_path = get_resource_path("icon.ico")
        if not os.path.exists(icon_path):
            icon_path = get_resource_path("icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.resize(1200, 800)
        screen = QApplication.primaryScreen().geometry()
        window_geometry = self.frameGeometry()
        center_point = screen.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())
        
        self.uploaded_files = []
        self.file_names = []
        self.all_logs = []
        self.current_logs = []
        self.watched_logs = []
        self.colors_by_file = {}
        self.analysis_started = False
        self.log_id_map = {}
        self.entry_to_id_map = {}
        
        self.auth_tab = None
        self.help_tab = None
        
        self.log_processor = LogProcessor(self.LOG_REGEX_PATTERN, self.TIME_REGEX_PATTERN, self)
        
        self.init_ui()
        
        QTimer.singleShot(50, self._delayed_init_tabs)

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        left_panel = QWidget()
        left_panel.setMinimumWidth(280)
        left_layout = QVBoxLayout()
        left_layout.setSpacing(style_manager.spacing['lg'])
        left_layout.setContentsMargins(
            style_manager.spacing['md'], 
            style_manager.spacing['lg'], 
            style_manager.spacing['md'], 
            style_manager.spacing['lg']
        )
        
        file_group = QGroupBox("文件操作")
        file_group.setFont(responsive_font_manager.get_font('group_title'))
        file_group.setStyleSheet(style_manager.get_group_title_style())
        file_layout = QVBoxLayout()
        file_layout.setSpacing(style_manager.spacing['sm'])
        file_layout.setContentsMargins(
            style_manager.spacing['md'], 
            style_manager.spacing['sm'], 
            style_manager.spacing['md'], 
            style_manager.spacing['sm']
        )
        
        self.upload_btn = QPushButton("上传日志文件")
        self.upload_btn.setFont(responsive_font_manager.get_font('button'))
        self.upload_btn.setFixedHeight(style_manager.button_height['md'])
        self.upload_btn.setStyleSheet(style_manager.get_button_style('primary'))
        self.upload_btn.clicked.connect(self.handle_file_upload)
        file_layout.addWidget(self.upload_btn)
        
        self.file_list = QListWidget()
        self.file_list.setFont(responsive_font_manager.get_font('content'))
        self.file_list.setStyleSheet(style_manager.get_list_widget_style())
        self.file_list.setMinimumHeight(80)
        file_layout.addWidget(self.file_list)
        file_group.setLayout(file_layout)
        left_layout.addWidget(file_group, 40)
        
        time_group = QGroupBox("时间范围")
        time_group.setFont(responsive_font_manager.get_font('group_title'))
        time_group.setStyleSheet(style_manager.get_group_title_style())
        time_layout = QVBoxLayout()
        time_layout.setSpacing(style_manager.spacing['md'])
        time_layout.setContentsMargins(
            style_manager.spacing['md'], 
            style_manager.spacing['sm'], 
            style_manager.spacing['md'], 
            style_manager.spacing['sm']
        )
        
        self.time_range_check = QCheckBox("启用")
        self.time_range_check.setFont(responsive_font_manager.get_font('content'))
        self.time_range_check.setStyleSheet(style_manager.get_checkbox_style())
        time_layout.addWidget(self.time_range_check)
        
        start_time_group = QWidget()
        start_layout = QHBoxLayout()
        start_time_group.setLayout(start_layout)
        start_layout.setContentsMargins(0, 0, 0, 0)
        start_layout.setSpacing(style_manager.spacing['sm'])
        
        label_start = QLabel("开始:")
        label_start.setFont(responsive_font_manager.get_font('label'))
        label_start.setStyleSheet(style_manager.get_label_style())
        start_layout.addWidget(label_start)
        
        self.start_date = QDateEdit()
        self.start_date.setFont(responsive_font_manager.get_font('input'))
        self.start_date.setFixedHeight(26)
        self.start_date.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.start_date.setCalendarPopup(True)
        self.start_date.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.start_date.setStyleSheet(style_manager.get_date_time_edit_style())
        self.start_date.setDate(datetime.date(2026, 1, 1))
        start_layout.addWidget(self.start_date, 1)
        
        self.start_time = QTimeEdit()
        self.start_time.setFont(responsive_font_manager.get_font('input'))
        self.start_time.setFixedHeight(26)
        self.start_time.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.start_time.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.start_time.setStyleSheet(style_manager.get_date_time_edit_style())
        self.start_time.setTime(datetime.time(0, 0))
        start_layout.addWidget(self.start_time, 1)
        
        time_layout.addWidget(start_time_group)
        
        end_time_group = QWidget()
        end_layout = QHBoxLayout()
        end_time_group.setLayout(end_layout)
        end_layout.setContentsMargins(0, 0, 0, 0)
        end_layout.setSpacing(style_manager.spacing['sm'])
        
        label_end = QLabel("结束:")
        label_end.setFont(responsive_font_manager.get_font('label'))
        label_end.setStyleSheet(style_manager.get_label_style())
        end_layout.addWidget(label_end)
        
        self.end_date = QDateEdit()
        self.end_date.setFont(responsive_font_manager.get_font('input'))
        self.end_date.setFixedHeight(26)
        self.end_date.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.end_date.setCalendarPopup(True)
        self.end_date.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.end_date.setStyleSheet(style_manager.get_date_time_edit_style())
        self.end_date.setDate(datetime.date(2026, 12, 31))
        end_layout.addWidget(self.end_date, 1)
        
        self.end_time = QTimeEdit()
        self.end_time.setFont(responsive_font_manager.get_font('input'))
        self.end_time.setFixedHeight(26)
        self.end_time.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.end_time.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.end_time.setStyleSheet(style_manager.get_date_time_edit_style())
        self.end_time.setTime(datetime.time(23, 59))
        end_layout.addWidget(self.end_time, 1)
        
        time_layout.addWidget(end_time_group)
        time_group.setLayout(time_layout)
        left_layout.addWidget(time_group, 23)
        
        search_group = QGroupBox("搜索设置")
        search_group.setFont(responsive_font_manager.get_font('group_title'))
        search_group.setStyleSheet(style_manager.get_group_title_style())
        search_layout = QVBoxLayout()
        search_layout.setSpacing(style_manager.spacing['md'])
        search_layout.setContentsMargins(
            style_manager.spacing['md'], 
            style_manager.spacing['sm'], 
            style_manager.spacing['md'], 
            style_manager.spacing['sm']
        )
        
        self.search_edit = QTextEdit()
        self.search_edit.setFont(responsive_font_manager.get_font('input'))
        self.search_edit.setPlaceholderText("输入关键词（每行一个）")
        self.search_edit.setStyleSheet(style_manager.get_input_style())
        search_layout.addWidget(self.search_edit)
        
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(20)
        mode_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.filter_mode_radio = QRadioButton("过滤模式")
        self.filter_mode_radio.setFont(responsive_font_manager.get_font('content'))
        self.filter_mode_radio.setStyleSheet(style_manager.get_radio_button_style())
        self.filter_mode_radio.setChecked(True)
        self.highlight_mode_radio = QRadioButton("高亮模式")
        self.highlight_mode_radio.setFont(responsive_font_manager.get_font('content'))
        self.highlight_mode_radio.setStyleSheet(style_manager.get_radio_button_style())
        mode_layout.addWidget(self.filter_mode_radio)
        mode_layout.addWidget(self.highlight_mode_radio)
        search_layout.addLayout(mode_layout)
        
        search_group.setLayout(search_layout)
        left_layout.addWidget(search_group, 22)
        
        regex_group = QGroupBox("正则设置")
        regex_group.setFont(responsive_font_manager.get_font('group_title'))
        regex_group.setStyleSheet(style_manager.get_group_title_style())
        regex_layout = QVBoxLayout()
        regex_layout.setSpacing(style_manager.spacing['sm'])
        regex_layout.setContentsMargins(
            style_manager.spacing['md'], 
            style_manager.spacing['sm'], 
            style_manager.spacing['md'], 
            style_manager.spacing['sm']
        )
        
        label = QLabel("日志匹配正则表达式：")
        label.setFont(responsive_font_manager.get_font('label'))
        label.setStyleSheet(style_manager.get_label_style())
        regex_layout.addWidget(label)
        self.log_regex_edit = QTextEdit()
        self.log_regex_edit.setFont(responsive_font_manager.get_font('input'))
        self.log_regex_edit.setPlaceholderText("用于匹配单条日志的正则表达式")
        self.log_regex_edit.setText(self.LOG_REGEX_PATTERN)
        self.log_regex_edit.setStyleSheet(style_manager.get_input_style())
        regex_layout.addWidget(self.log_regex_edit)
        
        label_time = QLabel("时间匹配正则表达式：")
        label_time.setFont(responsive_font_manager.get_font('label'))
        label_time.setStyleSheet(style_manager.get_label_style())
        regex_layout.addWidget(label_time)
        self.time_regex_edit = QTextEdit()
        self.time_regex_edit.setFont(responsive_font_manager.get_font('input'))
        self.time_regex_edit.setPlaceholderText("用于匹配日志中时间的正则表达式")
        self.time_regex_edit.setText(self.TIME_REGEX_PATTERN)
        self.time_regex_edit.setStyleSheet(style_manager.get_input_style())
        regex_layout.addWidget(self.time_regex_edit)
        
        regex_group.setLayout(regex_layout)
        left_layout.addWidget(regex_group, 25)
        
        button_container = QWidget()
        button_layout = QVBoxLayout()
        button_layout.setContentsMargins(0, style_manager.spacing['sm'], 0, style_manager.spacing['sm'])
        button_layout.setSpacing(style_manager.spacing['sm'])
        
        self.analyze_btn = QPushButton("开始分析")
        self.analyze_btn.clicked.connect(self.process_files)
        self.analyze_btn.setFont(responsive_font_manager.get_font('button_large'))
        self.analyze_btn.setFixedHeight(style_manager.button_height['md'])
        self.analyze_btn.setStyleSheet(style_manager.get_button_style('primary', 'md'))
        button_layout.addWidget(self.analyze_btn)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(24)
        self.progress_bar.setStyleSheet(style_manager.get_progress_bar_style())
        button_layout.addWidget(self.progress_bar)
        button_container.setLayout(button_layout)
        left_layout.addWidget(button_container, 10)
        
        left_panel.setLayout(left_layout)

        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.setStyleSheet(style_manager.get_splitter_style())
        
        upper_widget = QWidget()
        upper_layout = QVBoxLayout()
        display_title_layout = QHBoxLayout()
        display_label = QLabel("日志显示")
        display_label.setFont(responsive_font_manager.get_font('group_title'))
        display_label.setStyleSheet(style_manager.get_label_style())
        self.display_count_label = QLabel()
        self.display_count_label.setFont(responsive_font_manager.get_font('label'))
        self.display_count_label.setStyleSheet(style_manager.get_label_style('hint'))
        self.display_count_label.setText("")
        self.log_export_btn = QPushButton("导出当前日志")
        self.log_export_btn.setFont(responsive_font_manager.get_font('button'))
        self.log_export_btn.setMinimumWidth(120)
        self.log_export_btn.setStyleSheet(style_manager.get_button_style('accent'))
        self.log_export_btn.clicked.connect(self.export_displayed_logs)
        display_title_layout.addWidget(display_label)
        display_title_layout.addWidget(self.display_count_label)
        display_title_layout.addStretch()
        self.display_source_check = QCheckBox("附带来源")
        self.display_source_check.setFont(responsive_font_manager.get_font('content'))
        self.display_source_check.setStyleSheet(style_manager.get_checkbox_style())
        self.display_source_check.setChecked(False)
        display_title_layout.addWidget(self.display_source_check)
        display_title_layout.addWidget(self.log_export_btn)
        upper_layout.addLayout(display_title_layout)
        upper_layout.addWidget(self.log_display)
        upper_widget.setLayout(upper_layout)

        lower_widget = QWidget()
        lower_layout = QVBoxLayout()
        watched_title_layout = QHBoxLayout()
        watched_label = QLabel("关注日志")
        watched_label.setFont(responsive_font_manager.get_font('group_title'))
        watched_label.setStyleSheet(style_manager.get_label_style())
        self.watched_count_label = QLabel()
        self.watched_count_label.setFont(responsive_font_manager.get_font('label'))
        self.watched_count_label.setStyleSheet(style_manager.get_label_style('hint'))
        self.watched_count_label.setText("")
        self.export_btn = QPushButton("导出关注日志")
        self.export_btn.clicked.connect(self.export_logs)
        self.export_btn.setFont(responsive_font_manager.get_font('button'))
        self.export_btn.setMinimumWidth(120)
        self.export_btn.setStyleSheet(style_manager.get_button_style('info'))
        watched_title_layout.addWidget(watched_label)
        watched_title_layout.addWidget(self.watched_count_label)
        watched_title_layout.addStretch()
        self.watched_source_check = QCheckBox("附带来源")
        self.watched_source_check.setFont(responsive_font_manager.get_font('content'))
        self.watched_source_check.setStyleSheet(style_manager.get_checkbox_style())
        self.watched_source_check.setChecked(False)
        watched_title_layout.addWidget(self.watched_source_check)
        watched_title_layout.addWidget(self.export_btn)
        lower_layout.addLayout(watched_title_layout)
        
        self.watched_logs_display = QListWidget()
        self.watched_logs_display.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.watched_logs_display.installEventFilter(self)
        self.watched_logs_display.setFont(responsive_font_manager.get_font('log_display'))
        self.watched_logs_display.setStyleSheet(style_manager.get_log_display_style())
        lower_layout.addWidget(self.watched_logs_display)
        
        shortcut_label = QLabel("说明：CTRL D添加/删除，CTRL C复制，CTRL +放大，CTRL -缩小")
        shortcut_label.setFont(responsive_font_manager.get_font('hint'))
        shortcut_label.setStyleSheet(style_manager.get_label_style('hint'))
        lower_layout.addWidget(shortcut_label, alignment=Qt.AlignmentFlag.AlignLeft)
        
        lower_widget.setLayout(lower_layout)

        right_splitter.addWidget(upper_widget)
        right_splitter.addWidget(lower_widget)
        right_splitter.setSizes([500, 300])

        right_layout.addWidget(right_splitter)
        right_panel.setLayout(right_layout)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 900])

        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(responsive_font_manager.get_font('content'))
        self.tab_widget.setStyleSheet(style_manager.get_tab_widget_style())
        
        log_analysis_widget = QWidget()
        log_analysis_layout = QVBoxLayout()
        log_analysis_layout.setContentsMargins(0, 0, 0, 0)
        log_analysis_layout.addWidget(splitter)
        log_analysis_widget.setLayout(log_analysis_layout)
        
        self.tab_widget.addTab(log_analysis_widget, "日志分析")
        
        self.tab_widget.addTab(QWidget(), "认证授权")
        self.tab_widget.addTab(QWidget(), "使用说明")
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(
            style_manager.spacing['xs'], 
            style_manager.spacing['xs'], 
            style_manager.spacing['xs'], 
            style_manager.spacing['xs']
        )
        main_layout.addWidget(self.tab_widget)
        main_widget.setLayout(main_layout)
        
        self.statusBar().showMessage("如需授权或定制，请联系开发者（微信：aigc-service）")
    
    def _delayed_init_tabs(self):
        AuthTabClass = _get_auth_tab_class()
        self.auth_tab = AuthTabClass(self)
        self.auth_tab.auth_status_changed.connect(self.on_auth_status_changed)
        self.tab_widget.removeTab(1)
        self.tab_widget.insertTab(1, self.auth_tab, "认证授权")
        
        HelpTabClass = _get_help_tab_class()
        self.help_tab = HelpTabClass(self)
        self.tab_widget.removeTab(2)
        self.tab_widget.insertTab(2, self.help_tab, "使用说明")
        
        self.update_export_buttons_state(_get_auth_manager().is_valid)

    def handle_uncaught_exception(self, exc_type, exc_value, exc_traceback):
        error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logging.error(f"未捕获的异常:\n{error_msg}")
        
        error_dialog = QMessageBox(self)
        error_dialog.setIcon(QMessageBox.Icon.Critical)
        error_dialog.setWindowTitle("程序错误")
        error_dialog.setText("程序发生未处理的异常")
        error_dialog.setDetailedText(error_msg)
        error_dialog.exec()
        
        QApplication.quit()

    def export_logs(self):
        if not self.check_auth_and_prompt():
            return
        if not self.watched_logs:
            QMessageBox.warning(self, "导出失败", "没有关注的日志可导出")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存日志文件", "", "文本文件 (*.txt);;所有文件 (*)")
            
        if not file_path:
            return
            
        try:
            logs_with_id = [(self.entry_to_id_map.get(log), log) for log in self.watched_logs if self.entry_to_id_map.get(log) is not None]
            logs_with_id.sort(key=lambda x: int(x[0]))
            with open(file_path, 'w', encoding='utf-8') as f:
                for log_id, log in logs_with_id:
                    if self.watched_source_check.isChecked():
                        file_name = log.source_file.split('/')[-1]
                        source_info = f"来源: {file_name}\n"
                        f.write(source_info)
                    f.write(log.content)
                    f.write("\n\n")
            QMessageBox.information(self, "导出成功", f"日志已成功导出到 {file_path}")
        except Exception as e:
            logging.error(f"导出日志失败: {str(e)}")
            QMessageBox.critical(self, "导出错误", f"导出日志时发生错误: {str(e)}")

    def export_displayed_logs(self):
        if not self.check_auth_and_prompt():
            return
        if not self.current_logs:
            QMessageBox.warning(self, "导出失败", "没有可导出的日志")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存日志文件", "", "文本文件 (*.txt);;所有文件 (*)")
        if not file_path:
            return
        try:
            logs_with_id = [(self.entry_to_id_map.get(log), log) for log in self.current_logs if self.entry_to_id_map.get(log) is not None]
            logs_with_id.sort(key=lambda x: int(x[0]))
            with open(file_path, 'w', encoding='utf-8') as f:
                for log_id, log in logs_with_id:
                    if self.display_source_check.isChecked():
                        file_name = log.source_file.split('/')[-1]
                        source_info = f"来源: {file_name}\n"
                        f.write(source_info)
                    f.write(log.content)
                    f.write("\n\n")
            QMessageBox.information(self, "导出成功", f"日志已成功导出到 {file_path}")
        except Exception as e:
            logging.error(f"导出日志失败: {str(e)}")
            QMessageBox.critical(self, "导出错误", f"导出日志时发生错误: {str(e)}")

    def handle_file_upload(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择日志文件", "", "日志文件 (*.txt *.log)")
        if not files:
            return

        if not hasattr(self, 'file_names'):
            self.file_names = []
        if not hasattr(self, 'uploaded_files'):
            self.uploaded_files = []
        if not hasattr(self, 'colors_by_file'):
            self.colors_by_file = {}

        new_files = [f for f in files if f not in self.file_names]
        self.file_names.extend(new_files)

        for f in self.file_names:
            try:
                size = os.path.getsize(f)
            except Exception:
                size = -1
            logging.debug(f"[上传] 文件: {f}, 大小: {size}")

        color_count = len(self.file_names)
        self.colors_by_file.update(generate_light_colors(color_count, self.file_names))

        for file_path in new_files:
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                    self.uploaded_files.append(io.BytesIO(content))
                    logging.debug(f"[上传] 读取文件: {file_path}, 字节数: {len(content)}")
            except Exception as e:
                logging.error(f"读取文件 {file_path} 失败: {str(e)}")
                QMessageBox.warning(self, "文件错误", f"读取文件失败：\n{file_path}\n错误信息：{str(e)}")

        self.refresh_file_list()

        self.watched_logs = []
        self.update_watched_logs_display()
        self.analysis_started = False

    def refresh_file_list(self):
        self.file_list.clear()
        for idx, file_path in enumerate(self.file_names):
            file_name = file_path.split('/')[-1]
            item_widget = QWidget()
            layout = QHBoxLayout(item_widget)
            layout.setContentsMargins(style_manager.spacing['md'], 0, style_manager.spacing['md'], 0)
            layout.setSpacing(style_manager.spacing['md'])
            label = QLabel(file_name)
            label.setToolTip(file_path)
            label.setFont(responsive_font_manager.get_font('content'))
            label.setStyleSheet(style_manager.get_label_style())
            layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignVCenter)
            btn = QPushButton("×")
            btn.setFixedSize(18, 18)
            btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #e53935;
                    border: none;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #ffcdd2;
                    border-radius: 12px;
                }
            """)
            # btn.setToolTip("删除该文件")
            btn.clicked.connect(lambda _, idx=idx: self.delete_file_item(idx))
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            
            list_item = QListWidgetItem()
            bg_color = self.colors_by_file.get(file_path, QColor("#EEEEEE"))
            list_item.setBackground(bg_color)
            self.file_list.addItem(list_item)
            self.file_list.setItemWidget(list_item, item_widget)

        self.watched_logs = []
        self.update_watched_logs_display()
        self.analysis_started = False

    def delete_file_item(self, idx):
        try:
            if idx < 0 or idx >= len(self.file_names):
                return
            file_path = self.file_names[idx]
            del self.file_names[idx]
            del self.uploaded_files[idx]
            if file_path in self.colors_by_file:
                del self.colors_by_file[file_path]
            self.refresh_file_list()
        except Exception as e:
            logging.error(f"删除文件项时出错: {str(e)}")
            QMessageBox.warning(self, "删除错误", f"删除文件时发生错误: {str(e)}")

    def process_files(self):
        if not self.uploaded_files:
            QMessageBox.information(self, "提示", "请先上传日志文件")
            return
        
        if self.time_range_check.isChecked():
            start_datetime = datetime.datetime.combine(
                self.start_date.date().toPyDate(),
                self.start_time.time().toPyTime()
            )
            end_datetime = datetime.datetime.combine(
                self.end_date.date().toPyDate(),
                self.end_time.time().toPyTime()
            )
        else:
            start_datetime = None
            end_datetime = None
            
        keywords = [kw.strip() for kw in self.search_edit.toPlainText().split("\n") if kw.strip()]
        logging.debug(f"[分析] 启用时间范围: {self.time_range_check.isChecked()}, start: {start_datetime}, end: {end_datetime}")
        logging.debug(f"[分析] 关键词列表: {keywords}")
        
        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            QApplication.processEvents()
            
            def progress_callback(percent):
                self.progress_bar.setValue(percent)
                QApplication.processEvents()
            
            self.all_logs, failed_files = self.log_processor.process_log_files(self.uploaded_files, self.file_names, self.log_regex_edit, self.time_regex_edit, progress_callback=progress_callback)
            
            self.page_size = self.log_processor.get_dynamic_page_size()
            logging.info(f"[动态参数] 更新page_size为: {self.page_size}")
            
            if failed_files:
                self.file_names = [f for f in self.file_names if f not in failed_files]
                self.uploaded_files = [self.uploaded_files[i] for i, f in enumerate(self.file_names) if f not in failed_files]
                self.refresh_file_list()
                QMessageBox.warning(self, "解析提示", f"以下文件未能解析到任何日志，已从列表中移除：\n\n" + "\n".join(failed_files))

            self.progress_bar.setValue(60)
            QApplication.processEvents()
            
            filtered_logs = self.log_processor.filter_logs_by_time_range(self.all_logs, start_datetime, end_datetime)
            self.progress_bar.setValue(80)
            QApplication.processEvents()
            
            if self.filter_mode_radio.isChecked():
                filtered_logs2 = self.log_processor.filter_logs_by_keywords(filtered_logs, keywords)
                self.progress_bar.setValue(90)
                QApplication.processEvents()
                self.display_logs(filtered_logs2)
            else:
                self.display_logs(filtered_logs, highlight_keywords=keywords)
                
            self.progress_bar.setValue(100)
            QApplication.processEvents()
            QTimer.singleShot(800, lambda: self.progress_bar.setVisible(False))
            self.analysis_started = True
        except Exception as e:
            self.progress_bar.setVisible(False)
            logging.error(f"处理文件时出错: {str(e)}")
            traceback.print_exc()
            QMessageBox.critical(self, "处理错误", f"处理文件时发生错误: {str(e)}")

    def _load_page(self, page_number, highlight_keywords=None):
        if not self.current_logs:
            if hasattr(self, 'display_count_label'):
                self.display_count_label.setText("(0)")
            return

        self.current_page = page_number
        start_idx = page_number * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.current_logs))

        self.log_display.clear()

        for idx in range(start_idx, end_idx):
            log = self.current_logs[idx]
            is_watched = log in self.watched_logs
            display_text = log.content
            
            item = QListWidgetItem(display_text)

            log_id = str(idx)
            item.setData(Qt.ItemDataRole.UserRole, log_id)

            bg_color = self.colors_by_file.get(log.source_file, QColor("#FFFFFF"))
            item.setBackground(bg_color)

            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if is_watched else Qt.CheckState.Unchecked)

            if highlight_keywords:
                highlight_data = []
                content_lower = log.content.lower()
                for keyword in highlight_keywords:
                    if not keyword:
                        continue
                    fmt = QTextCharFormat()
                    fmt.setForeground(QColor("#e53935"))
                    keyword_lower = keyword.lower()
                    start_pos = 0
                    while True:
                        pos = content_lower.find(keyword_lower, start_pos)
                        if pos == -1:
                            break
                        highlight_data.append((pos, pos + len(keyword), fmt))
                        start_pos = pos + len(keyword)
                if highlight_data:
                    highlight_data.sort(key=lambda x: x[0])
                    item.setData(Qt.ItemDataRole.UserRole + 1, highlight_data)

            self.log_display.addItem(item)
        if hasattr(self, 'display_count_label'):
            self.display_count_label.setText(f"({len(self.current_logs)})")

    def display_logs(self, logs, highlight_keywords=None):
        try:
            self.log_display.clear()
            self.log_id_map = {}
            self.entry_to_id_map = {}

            sorted_logs = sorted(logs, key=lambda x: x.timestamp if x.timestamp else datetime.datetime.min)
            self.current_logs = sorted_logs
            logging.debug(f"[显示] 当前要显示的日志数量: {len(self.current_logs)}")
            if len(self.current_logs) == 0:
                logging.warning("[显示] 没有任何日志可显示！")
            
            self.total_pages = (len(self.current_logs) + self.page_size - 1) // self.page_size
            self.current_page = 0
            
            for idx, log in enumerate(sorted_logs):
                log_id = str(idx)
                self.log_id_map[log_id] = log
                self.entry_to_id_map[log] = log_id
            
            self._load_page(0, highlight_keywords)
            if hasattr(self, 'display_count_label'):
                self.display_count_label.setText(f"({len(self.current_logs)})")
        except Exception as e:
            logging.error(f"显示日志时出错: {str(e)}")
            traceback.print_exc()
            QMessageBox.critical(self, "显示错误", f"显示日志时发生错误: {str(e)}")

    def on_log_item_changed(self, item):
        try:
            log_id = item.data(Qt.ItemDataRole.UserRole)
            log_data = self.log_id_map.get(log_id)

            if not log_data:
                return

            self.watched_logs_display.blockSignals(True)

            if item.checkState() == Qt.CheckState.Checked:
                if log_data not in self.watched_logs:
                    self.watched_logs.append(log_data)
            else:
                if log_data in self.watched_logs:
                    self.watched_logs.remove(log_data)

            self.update_watched_logs_display()
            
            highlight_keywords = None
            if self.highlight_mode_radio.isChecked():
                highlight_keywords = [kw.strip() for kw in self.search_edit.toPlainText().split("\n") if kw.strip()]
            self._load_page(self.current_page, highlight_keywords)
        except Exception as e:
            logging.error(f"处理日志勾选变化时出错: {str(e)}")
            traceback.print_exc()
            QMessageBox.warning(self, "操作错误", f"更新关注列表时发生错误: {str(e)}")
        finally:
            self.watched_logs_display.blockSignals(False)

    def update_watched_logs_display(self):
        try:
            self.watched_logs_display.blockSignals(True)
            self.watched_logs_display.clear()

            id_order = [str(i) for i in range(len(self.current_logs))]
            id_to_log = {self.entry_to_id_map.get(log): log for log in self.watched_logs}
            watched_logs_sorted = [id_to_log[log_id] for log_id in id_order if log_id in id_to_log]

            for log in watched_logs_sorted:
                log_id = self.entry_to_id_map.get(log)
                if log_id is None:
                    continue
                item = QListWidgetItem(log.content)
                item.setData(Qt.ItemDataRole.UserRole, log_id)
                bg_color = self.colors_by_file.get(log.source_file)
                if not bg_color:
                    bg_color = QColor("#EEEEEE")
                elif bg_color.lightness() < 200:
                    bg_color = bg_color.lighter(150)
                item.setBackground(bg_color)
                self.watched_logs_display.addItem(item)
            if hasattr(self, 'watched_count_label'):
                self.watched_count_label.setText(f"({len(watched_logs_sorted)})")
        except Exception as e:
            logging.error(f"更新关注日志显示时出错: {str(e)}")
            traceback.print_exc()
            QMessageBox.warning(self, "显示错误", f"更新关注日志显示时出错: {str(e)}")
        finally:
            self.watched_logs_display.blockSignals(False)

    def handle_scroll(self, value):
        if not hasattr(self, 'current_logs') or not self.current_logs:
            return
            
        viewport_height = self.log_display.viewport().height()
        item_height = 40
        visible_items = viewport_height // item_height
        total_height = len(self.current_logs) * item_height
        scroll_percentage = value / (self.log_display.verticalScrollBar().maximum() or 1)
        current_page = int(scroll_percentage * (len(self.current_logs) / self.page_size))
        
        if current_page != self.current_page:
            self._load_page(current_page)

    def adjust_font_size(self, increase=True):
        try:
            current_size = self.log_display.font().pointSize()
            new_size = current_size + (2 if increase else -2)
            new_size = max(8, min(20, new_size))
            
            new_font = QFont("Microsoft YaHei", new_size)
            
            self.log_display.setFont(new_font)
            self.watched_logs_display.setFont(new_font)
            
        except Exception as e:
            logging.error(f"调整字体大小时出错: {str(e)}")
            traceback.print_exc()

    def eventFilter(self, obj, event):
        if event.type() == event.Type.KeyPress:
            if obj in [self.log_display, self.watched_logs_display]:
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_C:
                    selected_items = obj.selectedItems()
                    if selected_items:
                        clipboard = QApplication.clipboard()
                        clipboard.setText(selected_items[0].text())
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    if event.key() == Qt.Key.Key_Plus or event.key() == Qt.Key.Key_Equal:
                        self.adjust_font_size(True)
                    elif event.key() == Qt.Key.Key_Minus:
                        self.adjust_font_size(False)
                if obj == self.log_display:
                    if event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_D:
                        selected_items = self.log_display.selectedItems()
                        if selected_items:
                            item = selected_items[0]
                            item.setCheckState(Qt.CheckState.Unchecked if item.checkState() == Qt.CheckState.Checked else Qt.CheckState.Checked)
                elif obj == self.watched_logs_display:
                    if event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_D:
                        selected_items = self.watched_logs_display.selectedItems()
                        if selected_items:
                            self.delete_watched_item(selected_items[0])
                    elif event.key() in [Qt.Key.Key_Delete, Qt.Key.Key_Backspace]:
                        selected_items = self.watched_logs_display.selectedItems()
                        if selected_items:
                            self.delete_watched_item(selected_items[0])
        return super().eventFilter(obj, event)

    def delete_watched_item(self, item=None):
        if item is None:
            item = self.watched_logs_display.currentItem()
            if not item:
                return
        try:
            if self.log_display:
                self.log_display.blockSignals(True)
            if self.watched_logs_display:
                self.watched_logs_display.blockSignals(True)

            log_id = item.data(Qt.ItemDataRole.UserRole)
            if log_id is None:
                return

            self.watched_logs = [log for log in self.watched_logs if self.entry_to_id_map.get(log) != log_id]
            self.update_watched_logs_display()

            for i in range(self.log_display.count()):
                log_item = self.log_display.item(i)
                if log_item and log_item.data(Qt.ItemDataRole.UserRole) == log_id:
                    log_item.setCheckState(Qt.CheckState.Unchecked)

        except Exception as e:
            logging.error(f"删除关注日志项时出错: {str(e)}")
            traceback.print_exc()
            QMessageBox.warning(self, "操作错误", f"删除关注日志项时发生错误: {str(e)}")
        finally:
            if self.log_display:
                self.log_display.blockSignals(False)
            if self.watched_logs_display:
                self.watched_logs_display.blockSignals(False)
    
    def check_auth_and_prompt(self):
        auth_mgr = _get_auth_manager()
        if auth_mgr.is_valid:
            return True
        
        is_valid, message = auth_mgr.validate_auth(force_refresh=False)
        
        if is_valid:
            self.update_export_buttons_state(True)
            return True
        
        if "过期" in message:
            QMessageBox.warning(self, "授权已过期", "授权已过期，请重新认证")
        elif "无效" in message or "未授权" in message:
            QMessageBox.warning(self, "认证失败", "认证失败，请重新尝试")
        elif "无法获取" in message or "请先" in message:
            QMessageBox.warning(self, "未认证", "请先完成认证授权后再使用导出功能")
        else:
            QMessageBox.warning(self, "认证异常", message)
        
        self.tab_widget.setCurrentIndex(1)
        return False
    
    def on_auth_status_changed(self, is_valid):
        self.update_export_buttons_state(is_valid)
    
    def update_export_buttons_state(self, enabled):
        if enabled:
            self.log_export_btn.setEnabled(True)
            self.export_btn.setEnabled(True)
            self.log_export_btn.setStyleSheet("""
                QPushButton {
                    padding: 5px 20px;
                    background-color: #FF9800;
                    color: white;
                    border-radius: 4px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #F57C00;
                }
            """)
            self.export_btn.setStyleSheet("""
                QPushButton {
                    padding: 5px 20px;
                    background-color: #008CBA;
                    color: white;
                    border-radius: 4px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #007B9E;
                }
            """)
        else:
            self.log_export_btn.setEnabled(False)
            self.export_btn.setEnabled(False)
            self.log_export_btn.setStyleSheet("""
                QPushButton {
                    padding: 5px 20px;
                    background-color: #ccc;
                    color: #666;
                    border-radius: 4px;
                    font-size: 12px;
                }
            """)
            self.export_btn.setStyleSheet("""
                QPushButton {
                    padding: 5px 20px;
                    background-color: #ccc;
                    color: #666;
                    border-radius: 4px;
                    font-size: 12px;
                }
            """)
