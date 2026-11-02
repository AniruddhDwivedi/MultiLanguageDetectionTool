"""Basic thesaurus: synonyms, antonyms and related words for a word.

Two sources, merged in this order:

1. The user's own entries in the personal dictionary JSON (always available).
2. MyThes files (the format LibreOffice uses), if installed, one pair of
   ``th_<lang>_*.dat`` / ``.idx`` files per language. See data/thesaurus/README.txt.

Lookups are exact (case-insensitive): "eagles" will not find "eagle". Reducing
inflected forms to their base form is left for the grammar/inflection work.
"""

import re
import threading
from dataclasses import dataclass, field
from pathlib import Path

from .spellcheck import match_case
from .user_dictionary import UserDictionary

MAX_PER_KIND = 12

# Markers MyThes data files may append to a term, mapped to our categories.
_MARKERS = {
    "antonym": "antonyms",
    "similar term": "synonyms",
    "related term": "related",
    "generic term": "related",
    "specific term": "related",
}
_MARKER = re.compile(r"^(.*?)\s*\(([^()]+)\)$")

SYSTEM_DIRS = [Path("/usr/share/mythes"), Path("/usr/share/myspell/dicts")]


@dataclass
class ThesaurusResult:
    synonyms: list[str] = field(default_factory=list)
    antonyms: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.synonyms or self.antonyms)


class MyThesFile:
    """Reader for one MyThes ``.dat`` / ``.idx`` pair (loaded on first use)."""

    def __init__(self, dat_path: Path, idx_path: Path):
        self.dat_path = dat_path
        self.idx_path = idx_path
        self._offsets: dict[str, int] | None = None
        self._encoding = "utf-8"
        self._lock = threading.Lock()

    def _load_index(self) -> dict[str, int]:
        with self._lock:
            if self._offsets is None:
                offsets: dict[str, int] = {}
                with open(self.dat_path, "rb") as dat:
                    self._encoding = self._codec(dat.readline())
                with open(self.idx_path, "rb") as idx:
                    idx.readline()   # encoding line
                    idx.readline()   # entry count
                    for raw in idx:
                        word, _, offset = raw.decode(self._encoding, "replace").rstrip("\r\n").rpartition("|")
                        if word and offset.isdigit():
                            offsets.setdefault(word.lower(), int(offset))
                self._offsets = offsets
            return self._offsets

    @staticmethod
    def _codec(first_line: bytes) -> str:
        name = first_line.decode("ascii", "ignore").strip() or "utf-8"
        try:
            "".encode(name)
            return name
        except LookupError:
            return "utf-8"

    def lookup(self, word: str) -> ThesaurusResult:
        offsets = self._load_index()
        offset = offsets.get(word.lower())
        result = ThesaurusResult()
        if offset is None:
            return result

        with open(self.dat_path, "rb") as dat:
            dat.seek(offset)
            header = dat.readline().decode(self._encoding, "replace").rstrip("\r\n")
            _, _, count = header.rpartition("|")
            meanings = int(count) if count.isdigit() else 0
            for _ in range(meanings):
                line = dat.readline().decode(self._encoding, "replace").rstrip("\r\n")
                terms = line.split("|")[1:]   # first field is the part of speech
                for term in terms:
                    category = "synonyms"
                    match = _MARKER.match(term)
                    if match and match.group(2).lower() in _MARKERS:
                        term, category = match.group(1), _MARKERS[match.group(2).lower()]
                    term = term.strip()
                    if term and term.lower() != word.lower():
                        getattr(result, category).append(term)
        return result


class Thesaurus:
    def __init__(self, user_dictionary: UserDictionary | None = None, search_dirs=()):
        self.user_dictionary = user_dictionary or UserDictionary(None)
        self.search_dirs = [Path(d) for d in search_dirs] + SYSTEM_DIRS
        self._files: dict[str, MyThesFile | None] = {}
        self._lock = threading.Lock()

    def _file_for(self, language: str) -> MyThesFile | None:
        with self._lock:
            if language not in self._files:
                self._files[language] = self._find_file(language)
            return self._files[language]

    def _find_file(self, language: str) -> MyThesFile | None:
        for directory in self.search_dirs:
            if not directory.is_dir():
                continue
            # Prefer the "_v2" files; names look like th_en_US_v2.dat.
            candidates = sorted(
                directory.glob(f"th_{language}_*.dat"),
                key=lambda p: ("_v2" not in p.name, p.name),
            )
            for dat in candidates:
                idx = dat.with_suffix(".idx")
                if idx.exists():
                    return MyThesFile(dat, idx)
        return None

    def available_languages(self, languages) -> list[str]:
        """Languages that have MyThes data installed (user entries not counted)."""
        return [code for code in languages if self._file_for(code)]

    def lookup(self, language: str, word: str) -> ThesaurusResult:
        result = ThesaurusResult()
        ud = self.user_dictionary
        ud.refresh()

        result.synonyms += ud.relations(language, word, "synonyms")
        result.antonyms += ud.relations(language, word, "antonyms")
        result.related += ud.relations(language, word, "related")

        source = self._file_for(language)
        if source:
            try:
                found = source.lookup(word)
            except (OSError, ValueError) as error:
                print(f"Thesaurus file for '{language}' could not be read: {error}")
                found = ThesaurusResult()
            result.synonyms += found.synonyms
            result.antonyms += found.antonyms
            result.related += found.related

        # De-duplicate, cap, and match the capitalisation of the original word.
        for kind in ("synonyms", "antonyms", "related"):
            seen, items = set(), []
            for term in getattr(result, kind):
                key = term.lower()
                if key not in seen and key != word.lower():
                    seen.add(key)
                    items.append(match_case(word, term))
            setattr(result, kind, items[:MAX_PER_KIND])
        return result
