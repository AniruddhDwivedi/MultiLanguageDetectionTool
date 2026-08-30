from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QPushButton,
    QLineEdit,
    QSlider
)
from PyQt6.QtCore import Qt
from .layouts import VLayout, HLayout
from .gui_factory import GUIFactory

class MainWindow(QMainWindow):
    def __init__(self, processor):
        super().__init__()
        self.setWindowTitle("Multi-Language Detection Tool")
        self.set_centered_geometry(1200, 780)
        self.processor = processor

        # Main layout
        central = QWidget()
        self.setCentralWidget(central)
        main = VLayout(central)

        # Header
        header = HLayout().center()
        title = QLabel("Enter some text and click the button to know the language it's from")
        header.addWidget(title)
        main.addLayout(header)

        # Input Region
        self.input_layout = HLayout().left()

        # Input Field
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Enter text...")
        self.text_input.setFixedSize(1200, 400)
        self.text_input.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.input_layout.addWidget(self.text_input)

        # Font Controls
        self.font_slider = QSlider(Qt.Orientation.Vertical)
        self.font_slider.setMinimum(8)
        self.font_slider.setMaximum(72)
        self.font_slider.setValue(16)

        # Font size label
        self.font_size_label = QLabel("16")
        self.font_size_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.font_controls = VLayout()
        self.font_controls.addWidget(self.font_slider)
        self.font_controls.addWidget(self.font_size_label)

        self.input_layout.addLayout(self.font_controls)
        main.addLayout(self.input_layout)

        # Result Field
        self.result_label = QLabel("Result will appear here")
        self.result_label.setWordWrap(True)
        resFont = self.result_label.font()
        resFont.setPointSize(48)
        self.result_label.setFont(resFont)
        main.addWidget(self.result_label)
        main.addStretch()

        self.text_input.textChanged.connect(
            self.detect_language
        )

        self.font_slider.valueChanged.connect(
            self.change_font_size
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

        langs = {'en': 'English', 'de': 'German', 'fr': 'French', 'es': 'Spanish', 'it': 'Italian'}

        restext = lines[0].split(":")

        if restext[0] not in langs: return

        res = f"Detected Language: {langs[restext[0]]} \nLikelihood: {restext[1]}"

        self.result_label.setText(
            res
        )

    def set_centered_geometry(self, w: int, h: int):
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - w) // 2
        y = (screen.height() - h) // 2
        self.setGeometry(x, y, w, h)

    def change_font_size(self, size):
        self.font_size_label.setText(str(size))
        
        font = self.text_input.font()
        font.setPointSize(size)
        self.text_input.setFont(font)
