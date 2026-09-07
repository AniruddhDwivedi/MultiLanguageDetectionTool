from PyQt6.QtWidgets import QLabel, QPushButton
from .layouts import HLayout
from .text_highlighting import HighlightLineEdit

class GUIFactory:
    @staticmethod
    def create_header():
        layout = HLayout()

        title = QLabel("APP NAME")

        layout.addStretch()
        layout.addWidget(title)
        layout.addStretch()

        return layout, {
            "title": title,
        }

    @staticmethod
    def create_line_edit(
        placeholder: str = "",
    ):
        line_edit = HighlightLineEdit()
        line_edit.setPlaceholderText(placeholder)

        return line_edit, {
            "line_edit": line_edit,
        }
