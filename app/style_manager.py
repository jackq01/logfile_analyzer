#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtGui import QFont, QFontMetrics, QScreen
from PyQt6.QtCore import Qt


class ResponsiveFontManager:
    _instance = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if ResponsiveFontManager._initialized:
            return
        ResponsiveFontManager._initialized = True
        
        self._base_resolution = 1920
        self._current_scale = 1.0
        self._screen = None
        self._app = None
        
        self._resolution_ranges = [
            (3840, 1.4),
            (2560, 1.2),
            (1920, 1.0),
            (1600, 0.95),
            (1366, 0.9),
            (1280, 0.85),
            (1024, 0.8),
            (800, 0.75),
            (0, 0.7),
        ]
        
        self._font_configs = {
            'page_title': {'base_size': 16, 'weight': QFont.Weight.Bold, 'family': 'Microsoft YaHei'},
            'group_title': {'base_size': 12, 'weight': QFont.Weight.Bold, 'family': 'Microsoft YaHei'},
            'button': {'base_size': 11, 'weight': QFont.Weight.Normal, 'family': 'Microsoft YaHei'},
            'button_large': {'base_size': 12, 'weight': QFont.Weight.Bold, 'family': 'Microsoft YaHei'},
            'content': {'base_size': 10, 'weight': QFont.Weight.Normal, 'family': 'Microsoft YaHei'},
            'label': {'base_size': 10, 'weight': QFont.Weight.Normal, 'family': 'Microsoft YaHei'},
            'hint': {'base_size': 9, 'weight': QFont.Weight.Normal, 'family': 'Microsoft YaHei'},
            'log_display': {'base_size': 12, 'weight': QFont.Weight.Normal, 'family': 'Microsoft YaHei'},
            'input': {'base_size': 10, 'weight': QFont.Weight.Normal, 'family': 'Microsoft YaHei'},
        }
        
        self._cached_fonts = {}
    
    def initialize(self, app: QApplication):
        self._app = app
        self._screen = app.primaryScreen()
        self._update_scale()
    
    def _update_scale(self):
        if not self._screen:
            if self._app:
                self._screen = self._app.primaryScreen()
            if not self._screen:
                self._current_scale = 1.0
                return
        
        screen_width = self._screen.geometry().width()
        logical_dpi = self._screen.logicalDotsPerInch()
        base_dpi = 96
        dpi_scale = logical_dpi / base_dpi
        
        resolution_scale = 1.0
        for min_width, scale in self._resolution_ranges:
            if screen_width >= min_width:
                resolution_scale = scale
                break
        
        self._current_scale = resolution_scale * (dpi_scale ** 0.3)
        self._cached_fonts.clear()
    
    def get_font(self, font_type: str) -> QFont:
        cache_key = font_type
        if cache_key in self._cached_fonts:
            return QFont(self._cached_fonts[cache_key])
        
        config = self._font_configs.get(font_type, self._font_configs['content'])
        
        scaled_size = max(8, int(config['base_size'] * self._current_scale))
        
        font = QFont(config['family'], scaled_size, config['weight'])
        
        self._cached_fonts[cache_key] = font
        return font
    
    def get_scaled_size(self, base_size: int) -> int:
        return max(1, int(base_size * self._current_scale))
    
    def get_current_scale(self) -> float:
        return self._current_scale



class StyleManager:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.colors = {
            'primary': '#4CAF50',
            'primary_hover': '#45a049',
            'primary_pressed': '#3d8b40',
            'secondary': '#2196F3',
            'secondary_hover': '#1976D2',
            'accent': '#FF9800',
            'accent_hover': '#F57C00',
            'danger': '#e53935',
            'danger_hover': '#c62828',
            'success': '#4CAF50',
            'warning': '#FF9800',
            'info': '#008CBA',
            'info_hover': '#007B9E',
            
            'text_primary': '#333333',
            'text_secondary': '#666666',
            'text_hint': '#888888',
            'text_disabled': '#999999',
            'text_white': '#ffffff',
            
            'background': '#ffffff',
            'background_secondary': '#f5f5f5',
            'background_tertiary': '#fafafa',
            'border': '#dddddd',
            'border_focus': '#4CAF50',
            
            'input_bg': '#f5f5f5',
            'input_bg_focus': '#ffffff',
        }
        
        self.spacing = {
            'xs': 4,
            'sm': 6,
            'md': 8,
            'lg': 12,
            'xl': 15,
            'xxl': 20,
        }
        
        self.border_radius = {
            'sm': 4,
            'md': 6,
            'lg': 8,
        }
        
        self.button_height = {
            'sm': 24,
            'md': 30,
            'lg': 36,
        }
        
        self._style_cache = {}
    
    def get_page_title_style(self) -> str:
        return f"""
            QLabel {{
                color: {self.colors['text_primary']};
                font-family: "Microsoft YaHei";
                font-weight: bold;
            }}
        """
    
    def get_group_title_style(self) -> str:
        return f"""
            QGroupBox {{
                font-family: "Microsoft YaHei";
                font-weight: bold;
                color: {self.colors['text_primary']};
                border: 1px solid {self.colors['border']};
                border-radius: {self.border_radius['md']}px;
                margin-top: 12px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                left: 10px;
            }}
        """
    
    def get_button_style(self, button_type: str = 'primary', size: str = 'md') -> str:
        cache_key = f'button_{button_type}_{size}'
        if cache_key in self._style_cache:
            return self._style_cache[cache_key]
        
        height = self.button_height.get(size, self.button_height['md'])
        
        if button_type == 'primary':
            style = f"""
                QPushButton {{
                    padding: 4px 16px;
                    min-height: {height}px;
                    background-color: {self.colors['primary']};
                    color: {self.colors['text_white']};
                    border: none;
                    border-radius: {self.border_radius['sm']}px;
                    font-family: "Microsoft YaHei";
                }}
                QPushButton:hover {{
                    background-color: {self.colors['primary_hover']};
                }}
                QPushButton:pressed {{
                    background-color: {self.colors['primary_pressed']};
                }}
                QPushButton:disabled {{
                    background-color: #cccccc;
                    color: {self.colors['text_disabled']};
                }}
            """
        elif button_type == 'secondary':
            style = f"""
                QPushButton {{
                    padding: 4px 16px;
                    min-height: {height}px;
                    background-color: {self.colors['secondary']};
                    color: {self.colors['text_white']};
                    border: none;
                    border-radius: {self.border_radius['sm']}px;
                    font-family: "Microsoft YaHei";
                }}
                QPushButton:hover {{
                    background-color: {self.colors['secondary_hover']};
                }}
                QPushButton:disabled {{
                    background-color: #cccccc;
                    color: {self.colors['text_disabled']};
                }}
            """
        elif button_type == 'accent':
            style = f"""
                QPushButton {{
                    padding: 4px 16px;
                    min-height: {height}px;
                    background-color: {self.colors['accent']};
                    color: {self.colors['text_white']};
                    border: none;
                    border-radius: {self.border_radius['sm']}px;
                    font-family: "Microsoft YaHei";
                }}
                QPushButton:hover {{
                    background-color: {self.colors['accent_hover']};
                }}
                QPushButton:disabled {{
                    background-color: #cccccc;
                    color: {self.colors['text_disabled']};
                }}
            """
        elif button_type == 'info':
            style = f"""
                QPushButton {{
                    padding: 4px 16px;
                    min-height: {height}px;
                    background-color: {self.colors['info']};
                    color: {self.colors['text_white']};
                    border: none;
                    border-radius: {self.border_radius['sm']}px;
                    font-family: "Microsoft YaHei";
                }}
                QPushButton:hover {{
                    background-color: {self.colors['info_hover']};
                }}
                QPushButton:disabled {{
                    background-color: #cccccc;
                    color: {self.colors['text_disabled']};
                }}
            """
        elif button_type == 'danger':
            style = f"""
                QPushButton {{
                    padding: 2px 10px;
                    min-height: {height}px;
                    background-color: {self.colors['background']};
                    color: {self.colors['danger']};
                    border: 1px solid {self.colors['border']};
                    border-radius: {self.border_radius['sm']}px;
                    font-family: "Microsoft YaHei";
                }}
                QPushButton:hover {{
                    background-color: #ffecec;
                    border-color: {self.colors['danger']};
                }}
            """
        elif button_type == 'outline':
            style = f"""
                QPushButton {{
                    padding: 4px 16px;
                    min-height: {height}px;
                    background-color: transparent;
                    color: {self.colors['primary']};
                    border: 1px solid {self.colors['primary']};
                    border-radius: {self.border_radius['sm']}px;
                    font-family: "Microsoft YaHei";
                }}
                QPushButton:hover {{
                    background-color: {self.colors['primary']};
                    color: {self.colors['text_white']};
                }}
            """
        else:
            style = ""
        
        self._style_cache[cache_key] = style
        return style
    
    def get_input_style(self) -> str:
        if 'input' in self._style_cache:
            return self._style_cache['input']
        style = f"""
            QLineEdit, QTextEdit, QPlainTextEdit {{
                padding: 6px 10px;
                border: 1px solid {self.colors['border']};
                border-radius: {self.border_radius['sm']}px;
                background-color: {self.colors['input_bg']};
                font-family: "Microsoft YaHei";
                color: {self.colors['text_primary']};
            }}
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
                border-color: {self.colors['border_focus']};
                background-color: {self.colors['input_bg_focus']};
            }}
            QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
                background-color: {self.colors['background_secondary']};
                color: {self.colors['text_disabled']};
            }}
        """
        self._style_cache['input'] = style
        return style
    
    def get_date_time_edit_style(self) -> str:
        if 'date_time_edit' in self._style_cache:
            return self._style_cache['date_time_edit']
        style = f"""
            QDateEdit, QTimeEdit {{
                padding: 2px 4px;
                border: 1px solid {self.colors['border']};
                border-radius: {self.border_radius['sm']}px;
                background-color: {self.colors['background']};
                font-family: "Microsoft YaHei";
                color: {self.colors['text_primary']};
            }}
            QDateEdit:focus, QTimeEdit:focus {{
                border-color: {self.colors['border_focus']};
            }}
            QDateEdit::drop-down, QTimeEdit::drop-down {{
                border: none;
                width: 20px;
            }}
            QDateEdit::down-arrow, QTimeEdit::down-arrow {{
                image: none;
            }}
        """
        self._style_cache['date_time_edit'] = style
        return style
    
    def get_list_widget_style(self) -> str:
        if 'list_widget' in self._style_cache:
            return self._style_cache['list_widget']
        style = f"""
            QListWidget {{
                background-color: {self.colors['background_secondary']};
                border: 1px solid {self.colors['border']};
                border-radius: {self.border_radius['sm']}px;
                font-family: "Microsoft YaHei";
                outline: none;
            }}
            QListWidget::item {{
                margin: 2px 0px;
                padding: 6px 5px;
            }}
            QListWidget::item:hover {{
                background-color: #e8e8e8;
            }}
            QListWidget::item:selected {{
                background-color: #d0d0d0;
            }}
        """
        self._style_cache['list_widget'] = style
        return style
    
    def get_log_display_style(self) -> str:
        if 'log_display' in self._style_cache:
            return self._style_cache['log_display']
        style = f"""
            QListWidget {{
                border: 1px solid {self.colors['border']};
                border-radius: {self.border_radius['sm']}px;
                background-color: {self.colors['background']};
                font-family: "Microsoft YaHei";
                outline: none;
            }}
            QListWidget::item {{
                padding: 8px 5px;
                margin: 2px 0px;
            }}
        """
        self._style_cache['log_display'] = style
        return style
    
    def get_checkbox_style(self) -> str:
        if 'checkbox' in self._style_cache:
            return self._style_cache['checkbox']
        style = f"""
            QCheckBox {{
                font-family: "Microsoft YaHei";
                color: {self.colors['text_primary']};
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {self.colors['border']};
                border-radius: 3px;
                background-color: {self.colors['background']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.colors['primary']};
                border-color: {self.colors['primary']};
            }}
            QCheckBox::indicator:hover {{
                border-color: {self.colors['primary']};
            }}
        """
        self._style_cache['checkbox'] = style
        return style
    
    def get_radio_button_style(self) -> str:
        if 'radio_button' in self._style_cache:
            return self._style_cache['radio_button']
        style = f"""
            QRadioButton {{
                font-family: "Microsoft YaHei";
                color: {self.colors['text_primary']};
                spacing: 6px;
            }}
            QRadioButton::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
                background-color: {self.colors['background']};
            }}
            QRadioButton::indicator:checked {{
                background-color: {self.colors['primary']};
                border-color: {self.colors['primary']};
            }}
            QRadioButton::indicator:hover {{
                border-color: {self.colors['primary']};
            }}
        """
        self._style_cache['radio_button'] = style
        return style
    
    def get_progress_bar_style(self) -> str:
        if 'progress_bar' in self._style_cache:
            return self._style_cache['progress_bar']
        style = f"""
            QProgressBar {{
                border: 1px solid {self.colors['border']};
                border-radius: {self.border_radius['sm']}px;
                text-align: center;
                background-color: {self.colors['background_secondary']};
                font-family: "Microsoft YaHei";
                color: {self.colors['text_primary']};
            }}
            QProgressBar::chunk {{
                background-color: {self.colors['primary']};
                border-radius: 3px;
            }}
        """
        self._style_cache['progress_bar'] = style
        return style
    
    def get_splitter_style(self) -> str:
        if 'splitter' in self._style_cache:
            return self._style_cache['splitter']
        style = f"""
            QSplitter::handle {{
                height: 6px;
                background: transparent;
                background-repeat: no-repeat;
                background-position: center;
            }}
            QSplitter::handle:hover {{
                background-color: rgba(0, 0, 0, 0.05);
            }}
            QSplitter::handle:pressed {{
                background-color: rgba(0, 0, 0, 0.1);
            }}
        """
        self._style_cache['splitter'] = style
        return style
    
    def get_label_style(self, label_type: str = 'normal') -> str:
        cache_key = f'label_{label_type}'
        if cache_key in self._style_cache:
            return self._style_cache[cache_key]
        
        if label_type == 'hint':
            style = f"""
                QLabel {{
                    color: {self.colors['text_hint']};
                    font-family: "Microsoft YaHei";
                }}
            """
        elif label_type == 'secondary':
            style = f"""
                QLabel {{
                    color: {self.colors['text_secondary']};
                    font-family: "Microsoft YaHei";
                }}
            """
        elif label_type == 'success':
            style = f"""
                QLabel {{
                    color: {self.colors['success']};
                    font-family: "Microsoft YaHei";
                }}
            """
        elif label_type == 'danger':
            style = f"""
                QLabel {{
                    color: {self.colors['danger']};
                    font-family: "Microsoft YaHei";
                }}
            """
        else:
            style = f"""
                QLabel {{
                    color: {self.colors['text_primary']};
                    font-family: "Microsoft YaHei";
                }}
            """
        self._style_cache[cache_key] = style
        return style
    
    def get_tab_widget_style(self) -> str:
        if 'tab_widget' in self._style_cache:
            return self._style_cache['tab_widget']
        style = f"""
            QTabWidget::pane {{
                border: 1px solid {self.colors['border']};
                border-radius: {self.border_radius['sm']}px;
                background-color: {self.colors['background']};
            }}
            QTabBar::tab {{
                background-color: {self.colors['background_secondary']};
                color: {self.colors['text_secondary']};
                padding: 8px 20px;
                margin-right: 2px;
                border-top-left-radius: {self.border_radius['sm']}px;
                border-top-right-radius: {self.border_radius['sm']}px;
                font-family: "Microsoft YaHei";
            }}
            QTabBar::tab:selected {{
                background-color: {self.colors['background']};
                color: {self.colors['text_primary']};
                font-weight: bold;
            }}
            QTabBar::tab:hover {{
                background-color: #e8e8e8;
            }}
        """
        self._style_cache['tab_widget'] = style
        return style
    
    def get_scroll_area_style(self) -> str:
        if 'scroll_area' in self._style_cache:
            return self._style_cache['scroll_area']
        style = f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                border: none;
                background-color: {self.colors['background_secondary']};
                width: 10px;
                margin: 0;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background-color: #c0c0c0;
                min-height: 30px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: #a0a0a0;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar:horizontal {{
                border: none;
                background-color: {self.colors['background_secondary']};
                height: 10px;
                margin: 0;
                border-radius: 5px;
            }}
            QScrollBar::handle:horizontal {{
                background-color: #c0c0c0;
                min-width: 30px;
                border-radius: 5px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: #a0a0a0;
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0;
            }}
        """
        self._style_cache['scroll_area'] = style
        return style


style_manager = StyleManager()
responsive_font_manager = ResponsiveFontManager()
_font_manager_instance = None


def get_font_manager():
    global _font_manager_instance
    if _font_manager_instance is None:
        _font_manager_instance = ResponsiveFontManager()
    return _font_manager_instance


def apply_global_styles(app: QApplication):
    font_manager = get_font_manager()
    font_manager.initialize(app)
    
    app.setStyleSheet(f"""
        * {{
            font-family: "Microsoft YaHei";
        }}
        
        QWidget {{
            font-family: "Microsoft YaHei";
        }}
        
        QToolTip {{
            background-color: {style_manager.colors['text_primary']};
            color: {style_manager.colors['text_white']};
            border: none;
            padding: 4px 8px;
            border-radius: {style_manager.border_radius['sm']}px;
        }}
        
        QMessageBox {{
            font-family: "Microsoft YaHei";
        }}
        
        QMessageBox QLabel {{
            font-family: "Microsoft YaHei";
            color: {style_manager.colors['text_primary']};
        }}
        
        QFileDialog {{
            font-family: "Microsoft YaHei";
        }}
    """)
    
    return font_manager
