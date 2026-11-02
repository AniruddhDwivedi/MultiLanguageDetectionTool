import re
import sys
import time
from itertools import islice

from languages import LANGUAGES
from media.process import LanguageProcessor

DICTIONARIES = {
    "en": "en_GB",
    "fr": "fr_FR",
    "de": "de_DE",
    "it": "it_IT",
    "es": "es_ES",
}

MAX_SUGGESTIONS = 5
WORD = re.compile(r"[^\W\d_]+(?:['’\-][^\W\d_]+)*")


class SpellCheckers:
    def __init__(self):
        try:
            import phunspell
        except ImportError:
            sys.exit("phunspell is not installed. Run:  pip install phunspell")
        self._phunspell = phunspell
        self._cache = {}

    def get(self, code):
        if code not in DICTIONARIES:
            return None
        if code not in self._cache:
            start = time.perf_counter()
            self._cache[code] = self._phunspell.Phunspell(DICTIONARIES[code])
            print(f"   (loaded {DICTIONARIES[code]} in "
                  f"{time.perf_counter() - start:.1f}s)")
        return self._cache[code]

    def is_valid(self, code, word):
        return self.get(code).lookup(word)

    def suggestions(self, code, word):
        return list(islice(self.get(code).suggest(word), MAX_SUGGESTIONS))

    def other_languages_accepting(self, word, exclude):
        """Languages (other than ``exclude``) in which ``word`` is spelled correctly."""
        return [c for c in DICTIONARIES if c != exclude and self.is_valid(c, word)]


def check_segment(checkers, text, language):
    if language not in DICTIONARIES:
        print("      (no dictionary for this language, skipping spellcheck)")
        return

    problems = 0
    for match in WORD.finditer(text):
        word = match.group()
        if checkers.is_valid(language, word):
            continue

        problems += 1
        others = checkers.other_languages_accepting(word, exclude=language)
        if others:
            names = ", ".join(LANGUAGES[c].name for c in others)
            print(f"      '{word}' is not {LANGUAGES[language].name}, "
                  f"but is valid in: {names}")
        else:
            suggestions = checkers.suggestions(language, word)
            hint = ", ".join(suggestions) if suggestions else "no suggestions"
            print(f"      '{word}' looks misspelled -> {hint}")

    if not problems:
        print("      no spelling problems")

def main():
    processor = LanguageProcessor()
    checkers = SpellCheckers()

    print("Spellcheck sandbox. Empty line to quit. Prefix /xx to force a language.")
    while True:
        try:
            line = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            break

        forced = None
        if re.match(r"/[a-z]{2}\s", line):
            forced, line = line[1:3], line[4:].strip()
            if forced not in LANGUAGES:
                print(f"   unknown language '{forced}', options: {', '.join(LANGUAGES)}")
                continue

        for seg in processor.analyze(line):
            language = forced or seg.language
            name = LANGUAGES[language].name if language in LANGUAGES else language
            if forced:
                how = "forced"
            else:
                how = f"{seg.confidence:.0%}" + (", inherited" if seg.inherited else "")
            print(f"   [{name} ({how})] {seg.text}")
            check_segment(checkers, seg.text, language)

if __name__ == "__main__":
    main()
