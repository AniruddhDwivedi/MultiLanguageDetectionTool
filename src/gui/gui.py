from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QLabel,
    QPushButton,
    QLineEdit,
)
from .layouts import VLayout, HLayout
from .gui_factory import GUIFactory

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("APP NAME")
        self.set_centered_geometry(1200, 780)

        # Main layout
        central = QWidget()
        self.setCentralWidget(central)
        main = VLayout(central)

        # Header
        header = HLayout().center()
        title = QLabel("APP NAME")
        header.addWidget(title)
        main.addLayout(header)

        # Input Field
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Enter text...")
        main.addWidget(self.text_input)

        # Button Area
        self.detect_button = QPushButton("Detect Language")
        main.addWidget(self.detect_button)

        # Result Field
        self.result_label = QLabel("Result will appear here")
        self.result_label.setWordWrap(True)
        main.addWidget(self.result_label)
        main.addStretch()

        # Connect button processing
        self.detect_button.clicked.connect(
            self.detect_language
        )

    def detect_language(self):
        input_text = self.text_input.text()

        if not input_text:
            self.result_label.setText("Enter some text.")
            return

        result = self.processor.detect_language(input_text)

        if not result.detections:
            self.result_label.setText(
                "No language detected."
            )
            return

        lines = []

        for detection in result.detections:
            lines.append(
                f"{detection.language_code}: "
                f"{detection.probability:.2%}"
            )

        self.result_label.setText(
            "\n".join(lines)
        )

    def set_centered_geometry(self, w: int, h: int):
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - w) // 2
        y = (screen.height() - h) // 2
        self.setGeometry(x, y, w, h)

