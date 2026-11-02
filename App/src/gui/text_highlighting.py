from dataclasses import dataclass
from typing import Callable
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction, QColor, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import QMenu, QPlainTextEdit, QTextEdit
from correction.spellcheck import WORD
from languages import LANGUAGES


@dataclass
class TextHighlight:
    start: int
    length: int
    color: QColor | str

    def __post_init__(self):
        if isinstance(self.color, str):
            self.color = QColor(self.color)


def _utf16_offset(text: str, index: int) -> int: return len(text[:index].encode("utf-16-le")) // 2

def _py_index(text: str, utf16_offset: int) -> int:
    raw = text.encode("utf-16-le")[: utf16_offset * 2]
    return len(raw.decode("utf-16-le", errors="ignore"))


class HighlightTextEdit(QPlainTextEdit):
    HIGHLIGHT_ALPHA = 110
    ignore_requested = pyqtSignal(str)
    add_to_dictionary_requested = pyqtSignal(object)
    suggestion_applied = pyqtSignal(object, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlights: list[TextHighlight] = []
        self.misspellings: list = []
        self.suggestion_provider: Callable[[object], list[str]] | None = None
        self.thesaurus_provider: Callable[[str, str], object] | None = None
        self.language_at: Callable[[int], str | None] | None = None

    def text(self) -> str: return self.toPlainText()

    # -- annotations -------------------------------------------------------

    def set_annotations(self, highlights: list[TextHighlight], misspellings: list):
        self.highlights = highlights
        self.misspellings = misspellings
        self._apply_selections()

    def set_highlights(self, highlights: list[TextHighlight]):
        self.set_annotations(highlights, self.misspellings)

    def clear_highlights(self):
        self.set_annotations([], [])

    def _make_selection(self, text: str, start: int, end: int, fmt: QTextCharFormat):
        start = max(0, start)
        end = min(len(text), end)
        if start >= end:
            return None
        cursor = QTextCursor(self.document())
        cursor.setPosition(_utf16_offset(text, start))
        cursor.setPosition(_utf16_offset(text, end), QTextCursor.MoveMode.KeepAnchor)

        selection = QTextEdit.ExtraSelection()
        selection.cursor = cursor
        selection.format = fmt
        return selection

    def _background_at(self, index: int) -> QColor | None:
        for h in self.highlights:
            if h.start <= index < h.start + h.length:
                color = QColor(h.color)
                color.setAlpha(self.HIGHLIGHT_ALPHA)
                return color
        return None

    def _apply_selections(self):
        text = self.toPlainText()
        selections = []

        for h in self.highlights:
            color = QColor(h.color)
            color.setAlpha(self.HIGHLIGHT_ALPHA)
            fmt = QTextCharFormat()
            fmt.setBackground(color)
            sel = self._make_selection(text, h.start, h.start + h.length, fmt)
            if sel:
                selections.append(sel)

        for m in self.misspellings:
            fmt = QTextCharFormat()
            fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
            fmt.setUnderlineColor(QColor("#D32F2F"))
            background = self._background_at(m.start)
            if background:
                fmt.setBackground(background)
            sel = self._make_selection(text, m.start, m.end, fmt)
            if sel:
                selections.append(sel)

        self.setExtraSelections(selections)

    # -- right-click menu --------------------------------------------------

    def _index_at(self, event_pos) -> int:
        text = self.toPlainText()
        return _py_index(text, self.cursorForPosition(event_pos).position())

    def _misspelling_at(self, index: int):
        for m in self.misspellings:
            if m.start <= index <= m.end:
                return m
        return None

    def _word_at(self, index: int):
        for m in WORD.finditer(self.toPlainText()):
            if m.start() <= index <= m.end():
                return m.start(), m.end(), m.group()
        return None

    def _replace_span(self, start: int, end: int, replacement: str):
        text = self.toPlainText()
        cursor = QTextCursor(self.document())
        cursor.setPosition(_utf16_offset(text, start))
        cursor.setPosition(_utf16_offset(text, end), QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(replacement)   # triggers textChanged -> re-check

    def _replace(self, misspelling, replacement: str):
        self._replace_span(misspelling.start, misspelling.end, replacement)
        self.suggestion_applied.emit(misspelling, replacement)

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        first = menu.actions()[0] if menu.actions() else None
        index = self._index_at(event.pos())
        misspelling = self._misspelling_at(index)

        def add(action: QAction):
            menu.insertAction(first, action)

        if misspelling is not None:
            if misspelling.valid_in:
                names = ", ".join(
                    LANGUAGES[c].name for c in misspelling.valid_in if c in LANGUAGES
                )
                note = QAction(f"'{misspelling.word}' seems to be in: {names}", menu)
                note.setEnabled(False)
                add(note)

            suggestions = (
                self.suggestion_provider(misspelling) if self.suggestion_provider else []
            )
            for suggestion in suggestions:
                action = QAction(suggestion, menu)
                action.triggered.connect(
                    lambda _checked=False, s=suggestion, m=misspelling: self._replace(m, s)
                )
                add(action)

            if not suggestions and not misspelling.valid_in:
                none = QAction("No suggestions", menu)
                none.setEnabled(False)
                add(none)

            add_word = QAction("Add to dictionary", menu)
            add_word.triggered.connect(
                lambda _checked=False, m=misspelling: self.add_to_dictionary_requested.emit(m)
            )
            add(add_word)

            ignore = QAction("Ignore", menu)
            ignore.triggered.connect(
                lambda _checked=False, w=misspelling.word: self.ignore_requested.emit(w)
            )
            add(ignore)
            menu.insertSeparator(first)

        elif self.thesaurus_provider and self.language_at:
            found = self._word_at(index)
            language = self.language_at(found[0]) if found else None
            result = self.thesaurus_provider(language, found[2]) if language else None

            if result and (result.synonyms or result.antonyms):
                start, end, word = found
                for title, items in (
                    ("Synonyms", result.synonyms),
                    ("Antonyms", result.antonyms),
                ):
                    if not items:
                        continue
                    submenu = QMenu(f"{title} of '{word}'", menu)
                    for item in items:
                        action = QAction(item, submenu)
                        action.triggered.connect(
                            lambda _checked=False, s=start, e=end, t=item: self._replace_span(s, e, t)
                        )
                        submenu.addAction(action)
                    menu.insertMenu(first, submenu)
                menu.insertSeparator(first)

        menu.exec(event.globalPos())
        menu.deleteLater()
