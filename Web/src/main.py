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