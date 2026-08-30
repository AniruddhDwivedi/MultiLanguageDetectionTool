from PyQt6.QtWidgets import QLabel, QPushButton
from .layouts import HLayout

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
