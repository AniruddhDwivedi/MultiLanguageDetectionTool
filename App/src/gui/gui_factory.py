from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QSlider
from languages import LANGUAGES
from .layouts import HLayout
from .text_highlighting import HighlightTextEdit


class GUIFactory:
    @staticmethod
    def create_header(text: str):
        layout = HLayout().center()
        title = QLabel(text)
        layout.addWidget(title)
        return layout, title

    @staticmethod
    def create_text_edit(placeholder: str = ""):
        edit = HighlightTextEdit()
        edit.setPlaceholderText(placeholder)
        return edit

    @staticmethod
    def create_font_slider(minimum: int = 8, maximum: int = 72, value: int = 16):
        slider = QSlider(Qt.Orientation.Vertical)
        slider.setMinimum(minimum)
        slider.setMaximum(maximum)
        slider.setValue(value)

        label = QLabel(str(value))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return slider, label

    @staticmethod
    def create_language_legend():
        legend = HLayout().left()
        legend.setSpacing(20)

        for lang in LANGUAGES.values():
            swatch = QLabel()
            swatch.setFixedSize(18, 18)
            swatch.setStyleSheet(
                f"background-color: {lang.color}; border-radius: 3px;"
            )
            legend.addWidget(swatch)
            legend.addWidget(QLabel(lang.name))

        return legend
