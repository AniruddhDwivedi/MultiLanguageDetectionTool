from dataclasses import dataclass
from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtCore import Qt

@dataclass
class TextHighlight:
    start: int
    length: int
    color: QColor | str

    def __post_init__(self):
        if isinstance(self.color, str):
            self.color = QColor(self.color)

class HighlightLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.highlights: list[TextHighlight] = []

    def set_highlights(self, highlights: list[TextHighlight]):
        self.highlights = highlights
        self.update()

    def clear_highlights(self):
        self.highlights.clear()
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)

        if not self.highlights or not self.text():
            return

        painter = QPainter(self)
        painter.setPen(Qt.PenStyle.NoPen)

        text = self.text()
        font_metrics = self.fontMetrics()

        cursor_position = self.cursorPosition()
        cursor_rect = self.cursorRect()

        cursor_x = cursor_rect.left()

        # The cursor rect gives us the actual vertical position
        # of the text inside the QLineEdit.
        y = cursor_rect.top()
        height = cursor_rect.height()

        for highlight in self.highlights:
            start = max(0, highlight.start)
            end = min(
                len(text),
                start + highlight.length
            )

            if start >= end:
                continue

            # Calculate horizontal position relative to the cursor.
            if start < cursor_position:
                x = (
                    cursor_x
                    - font_metrics.horizontalAdvance(
                        text[start:cursor_position]
                    )
                )
            else:
                x = (
                    cursor_x
                    + font_metrics.horizontalAdvance(
                        text[cursor_position:start]
                    )
                )

            width = font_metrics.horizontalAdvance(
                text[start:end]
            )

            color = QColor(highlight.color)
            color.setAlpha(70)

            painter.fillRect(
                QRectF(
                    x,
                    y,
                    width,
                    height,
                ),
                color,
            )

        painter.end()