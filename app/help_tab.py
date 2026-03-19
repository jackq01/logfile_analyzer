#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from .style_manager import style_manager, responsive_font_manager


HELP_MARKDOWN = """

### 一、核心功能

#### 1. 多文件上传
- 支持 `.txt`、`.log` 等文本格式日志文件
- 可同时上传多个文件，系统自动分配不同背景色区分来源
- 支持单独删除已上传文件

#### 2. 正则解析
- **日志匹配正则**：用于切分单条日志（默认已配置）
- **时间匹配正则**：用于提取日志时间戳（默认已配置）
- 支持自定义正则表达式，无效时自动回退默认值

#### 3. 时间范围过滤
- 可启用/关闭时间范围筛选
- 支持精确到毫秒的时间设置
- 仅显示指定时间范围内的日志

#### 4. 关键词搜索
- **过滤模式**：仅显示包含任一关键词的日志
- **高亮模式**：显示所有日志，匹配关键词以红色高亮
- 支持多关键词（每行一个），支持正则表达式语法

#### 5. 关注日志
- 勾选日志条目可添加至关注列表
- 关注列表保持原始时间顺序
- 支持导出关注日志

#### 6. 日志导出
- 导出当前显示日志或关注日志
- 可选附带来源文件名信息

---

### 二、操作流程

1. **上传文件** → 点击「上传日志文件」选择日志文件
2. **配置参数** → 设置正则表达式、时间范围、关键词
3. **开始分析** → 点击「开始分析」按钮
4. **查看结果** → 在日志显示区浏览分析结果
5. **标记关注** → 勾选需要关注的日志条目
6. **导出日志** → 导出当前显示或关注日志

---

### 三、快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl + D` | 添加/删除关注 |
| `Ctrl + C` | 复制选中日志 |
| `Ctrl + +` | 放大字号 |
| `Ctrl + -` | 缩小字号 |
| `Delete / Backspace` | 删除关注列表选中项 |

---

### 四、常见问题

#### Q1: 上传文件后无日志显示？
- 检查日志匹配正则是否正确
- 确认文件编码是否支持（支持 UTF-8、GBK、GB2312 等）

#### Q2: 时间过滤不生效？
- 确认已勾选「启用」时间范围
- 检查时间匹配正则是否与日志格式匹配

#### Q3: 关键词搜索无结果？
- 过滤模式下需至少一个关键词匹配
- 检查关键词是否包含正则特殊字符（需转义）

#### Q4: 导出功能不可用？
- 需先完成认证授权
- 在「认证授权」页签完成认证后即可使用

#### Q5: 如何处理大日志文件？
- 系统采用分页虚拟滚动，自动优化内存
- 建议使用时间范围缩小数据量

---

### 五、技术支持

- **软件授权**：联系微信aigc-service获取授权

- **定制开发**：邮件jackq01@126.com，主题: 定制日志分析工具
"""


class HelpTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(
            style_manager.spacing['xl'], 
            style_manager.spacing['xl'], 
            style_manager.spacing['xl'], 
            style_manager.spacing['xl']
        )
        main_layout.setSpacing(style_manager.spacing['md'])
        
        self.help_text = QTextEdit()
        self.help_text.setReadOnly(True)
        self.help_text.setMarkdown(HELP_MARKDOWN)
        self.help_text.setFont(responsive_font_manager.get_font('content'))
        self.help_text.setStyleSheet(f"""
            QTextEdit {{
                border: 1px solid {style_manager.colors['border']};
                border-radius: {style_manager.border_radius['md']}px;
                background-color: {style_manager.colors['background_tertiary']};
                padding: 15px;
            }}
        """)
        
        main_layout.addWidget(self.help_text)
        
        self.setLayout(main_layout)
