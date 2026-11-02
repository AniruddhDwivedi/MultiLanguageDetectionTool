"""Persistent, hand-editable personal dictionary stored as JSON.

Example ``user_dictionary.json``:

    {
      "version": 2,
      "languages": {
        "en": {
          "words": {
            "anthropic": {},
            "happy": {
              "synonyms": ["glad", "cheerful"],
              "antonyms": ["sad"]
            }
          },
          "corrections": {
            "ane": {"are": 3}
          }
        }
      }
    }

* ``words``       - every key is an accepted word that is never flagged as a
                    spelling error. Its value holds optional thesaurus fields
                    (``synonyms``, ``antonyms``, ``related`` - any list of
                    strings; ``{}`` is fine).
* ``corrections`` - "typo -> replacement" counts learned when the user picks a
                    suggestion; higher counts are offered first.

Synonym and antonym links work both ways: listing "sad" as an antonym of
"happy" also makes "happy" an antonym of "sad".

Language keys are the two-letter codes (en, fr, de, it, es, la). Matching
ignores capitalisation. Edits made to the file while the app is running are
picked up at the next spellcheck. Pass ``path=None`` for an in-memory
dictionary (tests).
"""

import csv
import json
import os
import threading
from pathlib import Path

VERSION = 2
SYMMETRIC_KINDS = ("synonyms", "antonyms")


def _norm(word: str) -> str:
    return word.strip().replace("’", "'").lower()


def _empty_language() -> dict:
    return {"words": {}, "corrections": {}}


class UserDictionary:
    def __init__(self, path: str | os.PathLike | None = None):
        self.path = Path(path) if path else None
        self._lock = threading.RLock()
        self._data: dict[str, dict] = {}
        self._reverse: dict[str, dict[str, dict[str, list[str]]]] = {}
        self._mtime: float | None = None

        if self.path and not self.path.exists():
            self._import_legacy()
        else:
            self._load()

    # -- queries -----------------------------------------------------------

    def has_word(self, language: str, word: str) -> bool:
        return _norm(word) in self._data.get(language, {}).get("words", ())

    def corrections_for(self, language: str, typo: str) -> list[str]:
        """Replacements recorded for ``typo``, most used first."""
        counts = self._data.get(language, {}).get("corrections", {}).get(_norm(typo), {})
        return [w for w, _ in sorted(counts.items(), key=lambda kv: -kv[1])]

    def relations(self, language: str, word: str, kind: str) -> list[str]:
        """Entries of ``kind`` ("synonyms", "antonyms", ...) for ``word``,
        including links created from the other side."""
        word = _norm(word)
        own = self._data.get(language, {}).get("words", {}).get(word, {}).get(kind, [])
        back = self._reverse.get(language, {}).get(word, {}).get(kind, [])
        merged = []
        for item in [*own, *back]:
            if item not in merged:
                merged.append(item)
        return merged

    # -- updates -----------------------------------------------------------

    def add_word(self, language: str, word: str) -> None:
        with self._lock:
            self.refresh()
            self._words(language).setdefault(_norm(word), {})
            self._save()

    def remove_word(self, language: str, word: str) -> None:
        with self._lock:
            self.refresh()
            self._words(language).pop(_norm(word), None)
            self._save()

    def add_relation(self, language: str, word: str, kind: str, value: str) -> None:
        """Record e.g. ``add_relation("en", "happy", "synonyms", "glad")``."""
        with self._lock:
            self.refresh()
            entry = self._words(language).setdefault(_norm(word), {})
            values = entry.setdefault(kind, [])
            if _norm(value) not in values:
                values.append(_norm(value))
            self._save()

    def remember_correction(self, language: str, typo: str, chosen: str) -> None:
        typo, chosen = _norm(typo), _norm(chosen)
        if not typo or typo == chosen:
            return
        with self._lock:
            self.refresh()
            counts = self._corrections(language).setdefault(typo, {})
            counts[chosen] = counts.get(chosen, 0) + 1
            self._save()

    def _lang(self, language: str) -> dict:
        return self._data.setdefault(language, _empty_language())

    def _words(self, language: str) -> dict:
        return self._lang(language).setdefault("words", {})

    def _corrections(self, language: str) -> dict:
        return self._lang(language).setdefault("corrections", {})

    # -- persistence -------------------------------------------------------

    def ensure_file(self) -> None:
        """Make sure the file exists so it can be opened for editing."""
        with self._lock:
            if self.path and not self.path.exists():
                self._save()

    def refresh(self) -> None:
        """Reload from disk if the file was edited since we last touched it."""
        if not self.path:
            return
        try:
            mtime = self.path.stat().st_mtime
        except OSError:
            return
        if mtime != self._mtime:
            with self._lock:
                self._load()

    def _load(self) -> None:
        if not self.path or not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8-sig"))
            if not isinstance(data, dict):
                raise ValueError("top level must be an object")
            if data.get("version", 1) == 1:
                languages = self._convert_v1(data)
            else:
                languages = self._clean(data.get("languages", {}))
            self._mtime = self.path.stat().st_mtime
        except (OSError, ValueError, AttributeError, TypeError):
            # Unreadable file: keep a copy instead of silently overwriting it.
            try:
                self.path.replace(self.path.with_suffix(".corrupt.json"))
            except OSError:
                pass
            return
        self._data = languages
        self._rebuild_reverse()
        if data.get("version", 1) == 1:
            self._merge_csv()   # the CSV version came after v1 JSON: keep its data too
            self._save()        # upgrade the file to the current layout

    @staticmethod
    def _clean(languages: dict) -> dict:
        """Normalise hand-edited data (lower-case keys, drop bad shapes)."""
        cleaned: dict[str, dict] = {}
        for language, block in languages.items():
            out = cleaned.setdefault(str(language).lower(), _empty_language())
            for word, entry in (block.get("words") or {}).items():
                fields = {}
                for kind, values in (entry or {}).items():
                    if isinstance(values, list):
                        fields[kind] = [_norm(v) for v in values if str(v).strip()]
                out["words"][_norm(word)] = fields
            for typo, counts in (block.get("corrections") or {}).items():
                out["corrections"][_norm(typo)] = {
                    _norm(c): int(n) for c, n in counts.items()
                }
        return cleaned

    @staticmethod
    def _convert_v1(data: dict) -> dict:
        """Version 1 kept ``words`` as lists and ``corrections`` at top level."""
        languages: dict[str, dict] = {}
        for language, words in data.get("words", {}).items():
            block = languages.setdefault(language, _empty_language())
            for word in words:
                block["words"][_norm(word)] = {}
        for language, corrections in data.get("corrections", {}).items():
            block = languages.setdefault(language, _empty_language())
            block["corrections"] = {
                _norm(t): {_norm(c): int(n) for c, n in counts.items()}
                for t, counts in corrections.items()
            }
        return languages

    def _rebuild_reverse(self) -> None:
        reverse: dict[str, dict[str, dict[str, list[str]]]] = {}
        for language, block in self._data.items():
            for word, entry in block.get("words", {}).items():
                for kind in SYMMETRIC_KINDS:
                    for other in entry.get(kind, []):
                        bucket = reverse.setdefault(language, {}).setdefault(other, {})
                        bucket.setdefault(kind, [])
                        if word not in bucket[kind]:
                            bucket[kind].append(word)
        self._reverse = reverse

    def _save(self) -> None:
        if not self.path:
            return
        languages = {}
        for language in sorted(self._data):
            block = self._data[language]
            languages[language] = {
                "words": dict(sorted(block.get("words", {}).items())),
                "corrections": dict(sorted(block.get("corrections", {}).items())),
            }
        payload = {"version": VERSION, "languages": languages}
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            os.replace(tmp, self.path)   # atomic: never leaves a half-written file
            self._mtime = self.path.stat().st_mtime
        except OSError as error:
            print(f"Could not save personal dictionary: {error}")
        self._rebuild_reverse()

    def _import_legacy(self) -> None:
        """No JSON yet: carry over the earlier CSV-based dictionary, if any."""
        self._merge_csv()
        if self._data:
            self._save()

    def _merge_csv(self) -> None:
        """Merge ``user_dictionary.csv`` (previous format) into the data."""
        legacy = self.path.with_suffix(".csv")
        if not legacy.exists():
            return
        try:
            with open(legacy, newline="", encoding="utf-8-sig") as handle:
                for row in csv.reader(handle):
                    if len(row) < 2 or row[0].strip().startswith("#"):
                        continue
                    language, word = row[0].strip().lower(), _norm(row[1])
                    if language == "language" or not language or not word:
                        continue
                    correction = _norm(row[2]) if len(row) > 2 else ""
                    if not correction:
                        self._words(language).setdefault(word, {})
                        continue
                    count = int(row[3]) if len(row) > 3 and row[3].strip().isdigit() else 1
                    counts = self._corrections(language).setdefault(word, {})
                    counts[correction] = counts.get(correction, 0) + count
        except (OSError, ValueError, csv.Error):
            return
