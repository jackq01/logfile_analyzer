from PyQt6.QtWidgets import (QStyledItemDelegate, QApplication, QStyle, QStyleOptionViewItem)
from PyQt6.QtGui import QColor, QFontMetrics, QPalette
from PyQt6.QtCore import Qt, QRect

class HighlightDelegate(QStyledItemDelegate):
    
    def paint(self, painter, option, index):
        painter.save()
        
        style = self.parent().style() if self.parent() else QApplication.style()
        check_rect = style.subElementRect(QStyle.SubElement.SE_ItemViewItemCheckIndicator, option, self.parent())
        text_rect = option.rect
        
        text_rect.setRight(text_rect.right() - check_rect.width() - 10)
        
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        else:
            bg = index.data(Qt.ItemDataRole.BackgroundRole)
            if bg is None:
                bg = QColor("#FFFFFF")
            painter.fillRect(option.rect, bg)
        
        text = index.data(Qt.ItemDataRole.DisplayRole)
        highlight_data = index.data(Qt.ItemDataRole.UserRole + 1)
        lines = text.splitlines() if text else []
        y = text_rect.top()
        line_height = QFontMetrics(option.font).height()
        for line_idx, line in enumerate(lines):
            line_rect = QRect(text_rect.left(), y, text_rect.width(), line_height)
            x_cursor = line_rect.left()
            if highlight_data:
                line_start = sum(len(l)+1 for l in lines[:line_idx])
                line_end = line_start + len(line)
                line_highlights = [(start, end, fmt) for start, end, fmt in highlight_data if start >= line_start and end <= line_end]
                cursor = 0
                for h_start, h_end, fmt in line_highlights:
                    rel_start = h_start - line_start
                    rel_end = h_end - line_start
                    normal_text = line[cursor:rel_start]
                    if normal_text:
                        painter.setPen(option.palette.color(QPalette.ColorRole.Text))
                        painter.setFont(option.font)
                        rect_left = x_cursor
                        seg_rect = QRect(rect_left, line_rect.top(), line_rect.width() - (rect_left - line_rect.left()), line_rect.height())
                        painter.drawText(seg_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, normal_text)
                        fm = QFontMetrics(painter.font())
                        try:
                            advance = fm.horizontalAdvance(normal_text)
                        except AttributeError:
                            advance = fm.width(normal_text)
                        x_cursor += advance
                    highlight_text = line[rel_start:rel_end]
                    if highlight_text:
                        painter.setPen(fmt.foreground().color())
                        painter.setFont(fmt.font() if fmt.font() else option.font)
                        rect_left = x_cursor
                        seg_rect = QRect(rect_left, line_rect.top(), line_rect.width() - (rect_left - line_rect.left()), line_rect.height())
                        painter.drawText(seg_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, highlight_text)
                        fm_h = QFontMetrics(painter.font())
                        try:
                            advance_h = fm_h.horizontalAdvance(highlight_text)
                        except AttributeError:
                            advance_h = fm_h.width(highlight_text)
                        x_cursor += advance_h
                    cursor = rel_end
                if cursor < len(line):
                    painter.setPen(option.palette.color(QPalette.ColorRole.Text))
                    painter.setFont(option.font)
                    remaining_text = line[cursor:]
                    rect_left = x_cursor
                    seg_rect = QRect(rect_left, line_rect.top(), line_rect.width() - (rect_left - line_rect.left()), line_rect.height())
                    painter.drawText(seg_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, remaining_text)
            else:
                painter.setPen(option.palette.color(QPalette.ColorRole.Text))
                painter.setFont(option.font)
                painter.drawText(line_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, line)
            y += line_height
        
        if option.features & QStyleOptionViewItem.ViewItemFeature.HasCheckIndicator:
            checkbox_option = QStyleOptionViewItem(option)
            checkbox_option.rect = check_rect
            checkbox_option.state = checkbox_option.state & ~QStyle.StateFlag.State_HasFocus
            
            if index.data(Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked:
                checkbox_option.state |= QStyle.StateFlag.State_On
            else:
                checkbox_option.state |= QStyle.StateFlag.State_Off
            
            style.drawPrimitive(QStyle.PrimitiveElement.PE_IndicatorViewItemCheck, checkbox_option, painter)
        
        painter.restore()
