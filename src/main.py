import sys
import os
from PyQt6.QtWidgets import QApplication
from gui.gui import MainWindow
from media.process import LanguageProcessor

HERE = os.path.dirname(os.path.abspath(__file__))

def main():
    app = QApplication(sys.argv)

    processor = LanguageProcessor()

    window = MainWindow(processor)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())


# #UI Factories
# class HLayout(QHBoxLayout):

#     def center(self):
#         self.setAlignment(
#             Qt.AlignmentFlag.AlignCenter
#         )

#         return self


# class VLayout(QVBoxLayout):

#     def center(self):
#         self.setAlignment(
#             Qt.AlignmentFlag.AlignCenter
#         )

#         return self

# #UI Creation
# class MainWindow(QMainWindow):
#     def __init__(self):
#         #Basic window creation
#         super().__init__()
#         self.setWindowTitle("APP NAME")
#         self.set_centered_geometry(1200, 780)

#         # Centralizing the layout
#         central = QWidget()
#         self.setCentralWidget(central)

#         # Main layout
#         main = VLayout(central)

#         # Header creation
#         header = HLayout()
#         title = QLabel("APP NAME")

#         header.addStretch()
#         header.addWidget(title)
#         header.addStretch()

#         #UI Finalization
#         main.addLayout(header)
#         main.addStretch()

#     def set_centered_geometry(self, w: int, h: int):
#         screen = QApplication.primaryScreen().availableGeometry()
#         x = (screen.width() - w) // 2
#         y = (screen.height() - h) // 2
#         self.setGeometry(x, y, w, h)

# app = QApplication(sys.argv)
# window = MainWindow()
# window.show()
# sys.exit(app.exec())