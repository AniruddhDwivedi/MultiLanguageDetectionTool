from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout

class HLayout(QHBoxLayout):

    def center(self):
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return self

    def left(self):
        self.setAlignment(Qt.AlignmentFlag.AlignLeft)
        return self

    def right(self):
        self.setAlignment(Qt.AlignmentFlag.AlignRight)
        return self

class VLayout(QVBoxLayout):

    def center(self):
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return self

    def top(self):
        self.setAlignment(Qt.AlignmentFlag.AlignTop)
        return self

    def bottom(self):
        self.setAlignment(Qt.AlignmentFlag.AlignBottom)
        return self

