#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QRadioButton, QGroupBox,
                             QMessageBox, QApplication, QGraphicsOpacityEffect,
                             QStackedWidget, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QVariantAnimation
from PyQt6.QtGui import QFont, QColor, QPalette

from .style_manager import style_manager, responsive_font_manager

_auth_manager = None


def _get_auth_manager():
    global _auth_manager
    if _auth_manager is None:
        from .auth_manager import get_auth_manager
        _auth_manager = get_auth_manager()
    return _auth_manager


class ButtonStateAnimator(QVariantAnimation):
    def __init__(self, button, start_color, end_color, duration=200, parent=None):
        super().__init__(parent)
        self.button = button
        self.start_color = start_color
        self.end_color = end_color
        self.setDuration(duration)
        self.setStartValue(start_color)
        self.setEndValue(end_color)
        self.valueChanged.connect(self._update_button_color)
    
    def _update_button_color(self, color):
        if isinstance(color, QColor):
            r, g, b = color.red(), color.green(), color.blue()
            self.button.setStyleSheet(self.button.styleSheet().replace(
                f"background-color: #{self.start_color.name()[1:]};",
                f"background-color: rgb({r}, {g}, {b});"
            ))


class AuthTab(QWidget):
    auth_status_changed = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self._button_original_styles = {}
        self._auth_manager = _get_auth_manager()
        self.init_ui()
        self.update_status_display(self._auth_manager.is_valid, self._auth_manager.last_validation_message or "未认证")
        QTimer.singleShot(100, self._delayed_auth_check)
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(style_manager.spacing['xl'])
        main_layout.setContentsMargins(
            style_manager.spacing['xxl'], 
            style_manager.spacing['xxl'], 
            style_manager.spacing['xxl'], 
            style_manager.spacing['xxl']
        )
        
        title_label = QLabel("认证授权管理")
        title_label.setFont(responsive_font_manager.get_font('page_title'))
        title_label.setStyleSheet(style_manager.get_page_title_style())
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        auth_type_group = QGroupBox("认证方式")
        auth_type_group.setFont(responsive_font_manager.get_font('group_title'))
        auth_type_group.setStyleSheet(style_manager.get_group_title_style())
        auth_type_layout = QVBoxLayout()
        auth_type_layout.setSpacing(style_manager.spacing['md'])
        auth_type_layout.setContentsMargins(
            style_manager.spacing['xl'], 
            style_manager.spacing['xl'], 
            style_manager.spacing['xl'], 
            style_manager.spacing['xl']
        )
        
        type_layout = QHBoxLayout()
        type_layout.setSpacing(30)
        
        self.authkey_radio = QRadioButton("密钥认证")
        self.authkey_radio.setFont(responsive_font_manager.get_font('content'))
        self.authkey_radio.setStyleSheet(style_manager.get_radio_button_style())
        self.authkey_radio.setChecked(self._auth_manager.get_auth_type() == "authkey")
        
        self.domain_radio = QRadioButton("域名认证")
        self.domain_radio.setFont(responsive_font_manager.get_font('content'))
        self.domain_radio.setStyleSheet(style_manager.get_radio_button_style())
        self.domain_radio.setChecked(self._auth_manager.get_auth_type() == "domain")
        
        type_layout.addWidget(self.authkey_radio)
        type_layout.addWidget(self.domain_radio)
        type_layout.addStretch()
        auth_type_layout.addLayout(type_layout)
        
        self.authkey_radio.toggled.connect(self.on_auth_type_changed)
        self.domain_radio.toggled.connect(self.on_auth_type_changed)
        
        self.content_stack = QStackedWidget()
        self.content_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self.authkey_widget = QWidget()
        authkey_container_layout = QVBoxLayout(self.authkey_widget)
        authkey_container_layout.setContentsMargins(0, 0, 0, 0)
        authkey_container_layout.setSpacing(0)
        
        authkey_input_layout = QHBoxLayout()
        authkey_label = QLabel("认证密钥：")
        authkey_label.setFont(responsive_font_manager.get_font('label'))
        authkey_label.setStyleSheet(style_manager.get_label_style())
        authkey_label.setFixedWidth(70)
        
        self.authkey_input = QLineEdit()
        self.authkey_input.setFont(responsive_font_manager.get_font('input'))
        self.authkey_input.setPlaceholderText("请输入授权码")
        self.authkey_input.setText(self._auth_manager.authkey)
        self.authkey_input.setEchoMode(QLineEdit.EchoMode.Normal)
        self.authkey_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.authkey_input.setStyleSheet(style_manager.get_input_style())
        
        authkey_input_layout.addWidget(authkey_label)
        authkey_input_layout.addWidget(self.authkey_input)
        authkey_container_layout.addLayout(authkey_input_layout)
        
        self.domain_widget = QWidget()
        domain_container_layout = QVBoxLayout(self.domain_widget)
        domain_container_layout.setContentsMargins(0, 0, 0, 0)
        domain_container_layout.setSpacing(0)
        
        domain_info_layout = QHBoxLayout()
        domain_label = QLabel("当前域名：")
        domain_label.setFont(responsive_font_manager.get_font('label'))
        domain_label.setStyleSheet(style_manager.get_label_style())
        domain_label.setFixedWidth(70)
        
        self.domain_display = QLabel()
        self.domain_display.setFont(responsive_font_manager.get_font('content'))
        self.domain_display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.domain_display.setStyleSheet(f"""
            QLabel {{
                padding: 8px 12px;
                border: 1px solid {style_manager.colors['border']};
                border-radius: {style_manager.border_radius['sm']}px;
                background-color: {style_manager.colors['background_secondary']};
                color: {style_manager.colors['text_secondary']};
            }}
        """)
        self.domain_display.setText(self._auth_manager.get_pc_domain() or "无法获取")
        domain_info_layout.addWidget(domain_label)
        domain_info_layout.addWidget(self.domain_display)
        domain_container_layout.addLayout(domain_info_layout)
        
        self.content_stack.addWidget(self.authkey_widget)
        self.content_stack.addWidget(self.domain_widget)
        
        self.authkey_widget_opacity = QGraphicsOpacityEffect(self.authkey_widget)
        self.authkey_widget.setGraphicsEffect(self.authkey_widget_opacity)
        self.authkey_widget_opacity.setOpacity(1.0)
        
        self.domain_widget_opacity = QGraphicsOpacityEffect(self.domain_widget)
        self.domain_widget.setGraphicsEffect(self.domain_widget_opacity)
        self.domain_widget_opacity.setOpacity(1.0)
        
        auth_type_layout.addWidget(self.content_stack)
        
        auth_type_group.setLayout(auth_type_layout)
        main_layout.addWidget(auth_type_group)
        
        status_group = QGroupBox("认证状态")
        status_group.setFont(responsive_font_manager.get_font('group_title'))
        status_group.setStyleSheet(style_manager.get_group_title_style())
        status_layout = QVBoxLayout()
        status_layout.setSpacing(style_manager.spacing['md'])
        status_layout.setContentsMargins(
            style_manager.spacing['xl'], 
            style_manager.spacing['xl'], 
            style_manager.spacing['xl'], 
            style_manager.spacing['xl']
        )
        
        status_display_layout = QHBoxLayout()
        self.status_icon = QLabel("●")
        self.status_icon.setFont(responsive_font_manager.get_font('page_title'))
        self.status_icon.setStyleSheet(f"color: {style_manager.colors['danger']};")
        
        self.status_label = QLabel("未认证")
        self.status_label.setFont(responsive_font_manager.get_font('content'))
        self.status_label.setStyleSheet(style_manager.get_label_style('secondary'))
        
        status_display_layout.addWidget(self.status_icon)
        status_display_layout.addWidget(self.status_label)
        status_display_layout.addStretch()
        status_layout.addLayout(status_display_layout)
        
        self.status_detail = QLabel()
        self.status_detail.setFont(responsive_font_manager.get_font('content'))
        self.status_detail.setStyleSheet(style_manager.get_label_style('hint'))
        self.status_detail.setWordWrap(True)
        status_layout.addWidget(self.status_detail)
        
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)
        
        button_layout = QHBoxLayout()
        button_layout.setSpacing(style_manager.spacing['xl'])
        
        self.save_btn = QPushButton("保存设置")
        self.save_btn.setFont(responsive_font_manager.get_font('button'))
        self.save_btn.setFixedHeight(style_manager.button_height['lg'])
        self.save_btn.setFixedWidth(120)
        self.save_btn.setStyleSheet(style_manager.get_button_style('secondary'))
        self.save_btn.clicked.connect(self.save_settings)
        
        self.auth_btn = QPushButton("立即认证")
        self.auth_btn.setFont(responsive_font_manager.get_font('button'))
        self.auth_btn.setFixedHeight(style_manager.button_height['lg'])
        self.auth_btn.setFixedWidth(120)
        self.auth_btn.setStyleSheet(style_manager.get_button_style('primary'))
        self.auth_btn.clicked.connect(self.do_auth)
        
        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.auth_btn)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        help_group = QGroupBox("使用说明")
        help_group.setFont(responsive_font_manager.get_font('group_title'))
        help_group.setStyleSheet(style_manager.get_group_title_style())
        help_layout = QVBoxLayout()
        help_layout.setContentsMargins(
            style_manager.spacing['xl'], 
            style_manager.spacing['xl'], 
            style_manager.spacing['xl'], 
            style_manager.spacing['xl']
        )
        
        help_text = QLabel(
            "1. 密钥认证：输入管理员提供的密钥进行认证；\n"
            "2. 域名认证：系统自动获取本机域名进行认证；\n"
            "3. 认证成功，日志导出功能自动解锁。\n"
        )
        help_text.setFont(responsive_font_manager.get_font('content'))
        help_text.setStyleSheet(style_manager.get_label_style('secondary'))
        help_text.setWordWrap(True)
        help_layout.addWidget(help_text)
        help_group.setLayout(help_layout)
        main_layout.addWidget(help_group)
        
        main_layout.addStretch()
        self.setLayout(main_layout)
        
        self.update_auth_type_ui()
    
    def on_auth_type_changed(self):
        self._animate_switch()
    
    def _animate_switch(self):
        is_authkey = self.authkey_radio.isChecked()
        target_index = 0 if is_authkey else 1
        
        if self.content_stack.currentIndex() == target_index:
            return
        
        self._fade_out_animation = QPropertyAnimation(
            self.authkey_widget_opacity if self.content_stack.currentIndex() == 0 else self.domain_widget_opacity,
            b"opacity"
        )
        self._fade_out_animation.setDuration(100)
        self._fade_out_animation.setStartValue(1.0)
        self._fade_out_animation.setEndValue(0.0)
        self._fade_out_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        self._fade_out_animation.finished.connect(lambda: self._complete_switch(target_index))
        self._fade_out_animation.start()
    
    def _complete_switch(self, target_index):
        self.content_stack.setCurrentIndex(target_index)
        
        target_opacity = self.authkey_widget_opacity if target_index == 0 else self.domain_widget_opacity
        target_opacity.setOpacity(0.0)
        
        self._fade_in_animation = QPropertyAnimation(target_opacity, b"opacity")
        self._fade_in_animation.setDuration(100)
        self._fade_in_animation.setStartValue(0.0)
        self._fade_in_animation.setEndValue(1.0)
        self._fade_in_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._fade_in_animation.start()
    
    def update_auth_type_ui(self):
        is_authkey = self.authkey_radio.isChecked()
        target_index = 0 if is_authkey else 1
        self.content_stack.setCurrentIndex(target_index)
        self.authkey_input.setEnabled(is_authkey)
    
    def _show_button_status(self, button, success: bool, success_text: str, fail_text: str, original_text: str, original_style: str, duration: int = 1000):
        button.setEnabled(False)
        
        if button not in self._button_original_styles:
            self._button_original_styles[button] = original_style
        
        fixed_width = button.width()
        fixed_height = button.height()
        
        if success:
            display_text = f"✓ {success_text}"
            bg_color = "#4CAF50"
            hover_color = "#45a049"
        else:
            display_text = f"✗ {fail_text}"
            bg_color = "#e53935"
            hover_color = "#c62828"
        
        new_style = f"""
            QPushButton {{
                padding: 4px 16px;
                background-color: {bg_color};
                color: white;
                border-radius: 4px;
                font-family: "Microsoft YaHei";
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
        """
        
        self._apply_style_with_animation(button, new_style, fixed_width, fixed_height)
        button.setText(display_text)
        
        QTimer.singleShot(duration, lambda: self._restore_button(button, original_text, fixed_width, fixed_height))
    
    def _apply_style_with_animation(self, button, new_style, fixed_width=None, fixed_height=None):
        button.setStyleSheet(new_style)
        
        if fixed_width is not None:
            button.setFixedWidth(fixed_width)
        if fixed_height is not None:
            button.setFixedHeight(fixed_height)
        
        if button.graphicsEffect():
            button.setGraphicsEffect(None)
    
    def _restore_button(self, button, original_text: str, fixed_width=None, fixed_height=None):
        button.setText(original_text)
        
        original_style = self._button_original_styles.get(button, "")
        button.setStyleSheet(original_style)
        
        if fixed_width is not None:
            button.setFixedWidth(fixed_width)
        if fixed_height is not None:
            button.setFixedHeight(fixed_height)
        
        if button.graphicsEffect():
            button.setGraphicsEffect(None)
        
        button.setEnabled(True)
    
    def save_settings(self):
        original_style = self.save_btn.styleSheet()
        original_text = self.save_btn.text()
        
        try:
            auth_type = "authkey" if self.authkey_radio.isChecked() else "domain"
            self._auth_manager.set_auth_type(auth_type)
            
            if auth_type == "authkey":
                self._auth_manager.authkey = self.authkey_input.text().strip()
                self._auth_manager.save_config()
            
            self._show_button_status(
                self.save_btn, 
                success=True,
                success_text="保存成功",
                fail_text="保存失败",
                original_text=original_text,
                original_style=original_style
            )
        except Exception as e:
            self._show_button_status(
                self.save_btn, 
                success=False,
                success_text="保存成功",
                fail_text="保存失败",
                original_text=original_text,
                original_style=original_style
            )
    
    def do_auth(self):
        original_style = self.auth_btn.styleSheet()
        original_text = self.auth_btn.text()
        
        self.save_settings()
        
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            is_valid, message = self._auth_manager.validate_auth(force_refresh=True)
            self.update_status_display(is_valid, message)
            self.auth_status_changed.emit(is_valid)
            
            self._show_button_status(
                self.auth_btn,
                success=is_valid,
                success_text="认证成功",
                fail_text="认证失败",
                original_text=original_text,
                original_style=original_style
            )
        except Exception as e:
            self.update_status_display(False, "认证过程发生错误")
            self.auth_status_changed.emit(False)
            
            self._show_button_status(
                self.auth_btn,
                success=False,
                success_text="认证成功",
                fail_text="认证失败",
                original_text=original_text,
                original_style=original_style
            )
        finally:
            QApplication.restoreOverrideCursor()
    
    def _delayed_auth_check(self):
        try:
            is_valid, message = self._auth_manager.validate_auth(force_refresh=False)
            self.update_status_display(is_valid, message)
            self.auth_status_changed.emit(is_valid)
        except Exception:
            self.update_status_display(False, "网络连接失败，请检查网络后重试")
            self.auth_status_changed.emit(False)
    
    def refresh_auth_status(self):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            is_valid, message = self._auth_manager.validate_auth(force_refresh=False)
            self.update_status_display(is_valid, message)
            self.auth_status_changed.emit(is_valid)
        except Exception:
            self.update_status_display(False, "获取认证状态失败，请检查网络连接")
            self.auth_status_changed.emit(False)
        finally:
            QApplication.restoreOverrideCursor()
    
    def update_status_display(self, is_valid, message):
        if is_valid:
            self.status_icon.setStyleSheet(f"color: {style_manager.colors['success']};")
            self.status_label.setText("认证成功")
            self.status_label.setStyleSheet(f"color: {style_manager.colors['success']}; font-weight: bold;")
        else:
            self.status_icon.setStyleSheet(f"color: {style_manager.colors['danger']};")
            self.status_label.setText("认证失败")
            self.status_label.setStyleSheet(f"color: {style_manager.colors['danger']};")
        
        self.status_detail.setText(message)
    
    def get_auth_status(self):
        return self._auth_manager.is_valid
