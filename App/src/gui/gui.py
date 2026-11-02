from PyQt6.QtCore import QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QAction, QDesktopServices
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QWidget

from analysis import AnalysisPipeline
from languages import LANGUAGES
from .gui_factory import GUIFactory
from .layouts import HLayout, VLayout
from .text_highlighting import TextHighlight

DETECTION_DELAY_MS = 250

class MainWindow(QMainWindow):
    _detected = pyqtSignal(int, object)
    _finished = pyqtSignal(int, object, object)

    def __init__(self, processor, spellchecker=None, thesaurus=None):
        super().__init__()
        self.setWindowTitle("Multi-Language Detection Tool")
        self.set_centered_geometry(1200, 780)
        self.processor = processor
        self.spellchecker = spellchecker
        self.thesaurus = thesaurus

        central = QWidget()
        self.setCentralWidget(central)
        main = VLayout(central)

        # Header
        header, self.title_label = GUIFactory.create_header(
            "Type some text; each sentence is colour-coded by its language"
        )
        main.addLayout(header)

        # Input + font controls
        input_layout = HLayout()

        self.text_input = GUIFactory.create_text_edit("Enter text...")
        input_layout.addWidget(self.text_input, stretch=1)

        self.font_slider, self.font_size_label = GUIFactory.create_font_slider()
        font_controls = VLayout()
        font_controls.addWidget(self.font_slider, stretch=1)
        font_controls.addWidget(self.font_size_label)
        input_layout.addLayout(font_controls)

        main.addLayout(input_layout, stretch=1)

        # Status line: language of the sentence under the cursor
        self.status_label = QLabel("")
        main.addWidget(self.status_label)

        # Legend
        main.addLayout(GUIFactory.create_language_legend())

        # Detection is debounced so we don't run the model on every keystroke.
        self._detect_timer = QTimer(self)
        self._detect_timer.setSingleShot(True)
        self._detect_timer.setInterval(DETECTION_DELAY_MS)
        self._detect_timer.timeout.connect(self.detect_language)

        self.segments = []
        self.misspellings = []

        # Language detection and spellchecking run on background threads.
        self._pipeline = AnalysisPipeline(processor, spellchecker)
        self._detected.connect(self._on_detected)
        self._finished.connect(self._on_finished)

        if self.spellchecker:
            self.text_input.suggestion_provider = lambda m: self.spellchecker.suggest(
                m.language, m.word
            )
            self.text_input.ignore_requested.connect(self.ignore_word)
            self.text_input.add_to_dictionary_requested.connect(self.add_to_dictionary)
            self.text_input.suggestion_applied.connect(self.learn_correction)

        if self.thesaurus:
            self.text_input.thesaurus_provider = self.thesaurus.lookup
            self.text_input.language_at = self.language_at

        user_dictionary = (
            self.spellchecker.user_dictionary if self.spellchecker
            else self.thesaurus.user_dictionary if self.thesaurus
            else None
        )
        self._user_dictionary = user_dictionary
        if user_dictionary and user_dictionary.path:
            menu = self.menuBar().addMenu("Dictionary")
            open_action = QAction("Open personal dictionary file...", self)
            open_action.triggered.connect(self.open_dictionary_file)
            menu.addAction(open_action)

        self.text_input.textChanged.connect(self._on_text_changed)
        self.text_input.cursorPositionChanged.connect(self.update_status)
        self.font_slider.valueChanged.connect(self.change_font_size)
        self.change_font_size(self.font_slider.value())

    # -- detection ---------------------------------------------------------

    def _on_text_changed(self):
        self._pipeline.invalidate()
        self._detect_timer.start()

    def detect_language(self):
        self._pipeline.submit(
            self.text_input.text(),
            on_detected=self._detected.emit,
            on_finished=self._finished.emit,
        )

    def _on_detected(self, generation: int, segments):
        if not self._pipeline.is_current(generation):
            return
        self.segments = segments
        self.misspellings = []
        self._render()

    def _on_finished(self, generation: int, segments, misspellings):
        if not self._pipeline.is_current(generation):
            return
        self.segments = segments
        self.misspellings = misspellings
        self._render()

    def _render(self):
        highlights = []
        for seg in self.segments:
            lang = LANGUAGES.get(seg.language)
            if lang:
                highlights.append(
                    TextHighlight(seg.start, seg.end - seg.start, lang.color)
                )

        self.text_input.set_annotations(highlights, self.misspellings)
        self.update_status()

    def language_at(self, index: int):
        for seg in self.segments:
            if seg.start <= index <= seg.end:
                return seg.language if seg.language in LANGUAGES else None
        return None

    def ignore_word(self, word: str):
        self.spellchecker.ignore(word)
        self.detect_language()

    def open_dictionary_file(self):
        dictionary = self._user_dictionary
        dictionary.ensure_file()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(dictionary.path)))

    def add_to_dictionary(self, misspelling):
        self.spellchecker.add_to_dictionary(misspelling.language, misspelling.word)
        self.detect_language()

    def learn_correction(self, misspelling, replacement: str):
        self.spellchecker.learn(misspelling.language, misspelling.word, replacement)

    def update_status(self):
        parts = []

        pos = self.text_input.textCursor().position()
        for seg in self.segments:
            if seg.start <= pos <= seg.end:
                lang = LANGUAGES.get(seg.language)
                name = lang.name if lang else (seg.language or "unknown")
                note = " (inherited from previous sentence)" if seg.inherited else ""
                parts.append(
                    f"Sentence under cursor: {name}{note}, "
                    f"confidence {seg.confidence:.0%}"
                )
                break

        if self.misspellings:
            count = len(self.misspellings)
            parts.append(
                f"{count} possible spelling error{'s' if count != 1 else ''} "
                "(right-click an underlined word)"
            )

        self.status_label.setText("   |   ".join(parts))

    # -- window helpers ----------------------------------------------------

    def set_centered_geometry(self, w: int, h: int):
        screen = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(
            (screen.width() - w) // 2, (screen.height() - h) // 2, w, h
        )

    def change_font_size(self, size: int):
        self.font_size_label.setText(str(size))
        font = self.text_input.font()
        font.setPointSize(size)
        self.text_input.setFont(font)
