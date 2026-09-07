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
from .text_highlighting import HighlightLineEdit, TextHighlight

LANGUAGE_COLORS = {
    "en": "#FFF59D",  # yellow
    "de": "#A5D6A7",  # green
    "fr": "#90CAF9",  # blue
    "es": "#FFCC80",  # orange
    "it": "#CE93D8",  # purple
}

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

        self.input_layout = HLayout().left()

        # Input Field
        self.text_input = HighlightLineEdit()
        self.text_input.setPlaceholderText("Enter text...")
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

        # Language Legend
        self.language_legend = self.create_language_legend()
        main.addLayout(self.language_legend)

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
            self.text_input.clear_highlights()
            self.result_label.setText("Enter some text.")
            return

        words = input_text.split()
        detections = map(
            self.processor.detect_language,
            words
        )

        highlights = []

        position = 0

        for word, result in zip(words, detections):
            if result.detections:
                language = result.detections[0].language_code

                color = LANGUAGE_COLORS.get(language)

                if color:
                    start = input_text.find(word, position)

                    highlights.append(
                        TextHighlight(
                            start=start,
                            length=len(word),
                            color=color,
                        )
                    )

                    position = start + len(word)

        self.text_input.set_highlights(highlights)

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


    def create_language_legend(self):
        legend = HLayout().left()
        legend.setSpacing(20)

        languages = {
            "en": "English",
            "de": "German",
            "fr": "French",
            "es": "Spanish",
            "it": "Italian",
        }

        for code, name in languages.items():
            swatch = QLabel()
            swatch.setFixedSize(18, 18)
            swatch.setStyleSheet(
                f"""
                background-color: {LANGUAGE_COLORS[code]};
                border-radius: 3px;
                """
            )

            label = QLabel(name)

            legend.addWidget(swatch)
            legend.addWidget(label)

        return legend