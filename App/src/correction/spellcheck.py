"""Per-language spellchecking on top of the segment-level language detection.

Pipeline position:  text -> split_segments -> detector -> SpellChecker.check

For every segment the checker looks each word up in the dictionary of the
segment's language. A word that fails is reported as a ``Misspelling``; if the
word *is* valid in another supported language, that is recorded too, so the UI
can say "this word seems to be in: French" instead of offering bad corrections.

Suggestions are NOT computed here (they're slow); ask ``suggest()`` for them
when the user actually opens the menu.
"""

import re
import threading
from functools import lru_cache
from dataclasses import dataclass, field, replace
from itertools import islice

from media.process import AnalyzedSegment

from .user_dictionary import UserDictionary

# Our language code -> Hunspell dictionary shipped with phunspell.
# Latin is deliberately absent: it is detected but not spellchecked.
DICTIONARIES = {
    "en": "en_GB",
    "fr": "fr_FR",
    "de": "de_DE",
    "it": "it_IT",
    "es": "es_ES",
}

MAX_SUGGESTIONS = 5

# Optional frequency re-ranking (needs `pip install wordfreq`): fetch more
# Hunspell candidates, then prefer common words. Each step down Hunspell's own
# ordering costs RANK_PENALTY points of Zipf frequency (roughly 0-8), so a much
# more common word can overtake a slightly closer but rare one ("are" over
# "sane" for "ane"), without letting very distant words jump the queue.
CANDIDATES = 15
RANK_PENALTY = 0.25

# When a segment has spelling errors in the detected language, the other
# languages are tried in order of the detector's own probability. The segment is
# relabelled to the language with the fewest errors, but only if that is strictly
# fewer than the original and no more than this share of the words are wrong
# (so we never swap one mostly-wrong language for another).
MAX_ALTERNATIVE_ERROR_RATE = 0.5

# A word: letters (any script), optionally joined by an apostrophe or hyphen,
# so "We're", "l'homme" and "well-known" are single tokens. The lookarounds make
# sure we don't pick letters out of things like "abc123" or "snake_case".
WORD = re.compile(
    r"(?<![\w'’\-])[^\W\d_]+(?:['’\-][^\W\d_]+)*(?![\w])"
)


def match_case(typo: str, suggestion: str) -> str:
    """Give a learned (lower-cased) replacement the capitalisation of the typo."""
    if typo.isupper() and len(typo) > 1:
        return suggestion.upper()
    if typo[:1].isupper():
        return suggestion[:1].upper() + suggestion[1:]
    return suggestion


@dataclass(frozen=True)
class Misspelling:
    start: int                 # absolute character span in the full text
    end: int
    word: str
    language: str              # language the word was checked against
    valid_in: tuple[str, ...] = field(default_factory=tuple)  # other languages accepting it


class SpellChecker:
    def __init__(self, user_dictionary: UserDictionary | None = None):
        try:
            import phunspell
        except ImportError as exc:
            raise ImportError(
                "phunspell is not installed. Run: pip install phunspell"
            ) from exc

        self._phunspell = phunspell
        try:
            from wordfreq import zipf_frequency
            self._zipf = zipf_frequency
        except ImportError:
            self._zipf = None   # suggestions keep Hunspell's own order
        self._spellers: dict[str, object] = {}
        # Hunspell's dictionaries never change at runtime, so remember answers:
        # repeated words and unchanged sentences cost a dict lookup, not a parse.
        self._lookup = lru_cache(maxsize=200_000)(self._hunspell_lookup)
        self._load_lock = threading.Lock()
        self.ignored: set[str] = set()   # lower-cased words ignored this session
        self.user_dictionary = user_dictionary or UserDictionary(None)

    # -- dictionaries ------------------------------------------------------

    def supports(self, language: str | None) -> bool:
        return language in DICTIONARIES

    def preload(self) -> threading.Thread:
        """Load every dictionary in the background so the first check is fast.
        If a check needs a dictionary that isn't ready yet, it simply waits."""
        thread = threading.Thread(
            target=self._load_everything,
            daemon=True,
        )
        thread.start()
        return thread

    def _load_everything(self) -> None:
        for code in DICTIONARIES:
            self._speller(code)
            if self._zipf:
                self._zipf("the", code)   # forces wordfreq to load that list

    def _speller(self, code: str):
        with self._load_lock:
            if code not in self._spellers:
                self._spellers[code] = self._phunspell.Phunspell(DICTIONARIES[code])
            return self._spellers[code]

    # -- lookups -----------------------------------------------------------

    def _hunspell_lookup(self, language: str, word: str) -> bool:
        return bool(self._speller(language).lookup(word))

    def is_valid(self, language: str, word: str) -> bool:
        # The personal dictionary is checked every time (it can change); only
        # the Hunspell answer is cached.
        if self.user_dictionary.has_word(language, word):
            return True
        return self._lookup(language, word.replace("’", "'"))  # dictionaries use '

    def suggest(self, language: str, word: str) -> list[str]:
        """Replacement candidates: ones the user picked before come first,
        then Hunspell's own suggestions."""
        word = word.replace("’", "'")
        learned = [
            match_case(word, w)
            for w in self.user_dictionary.corrections_for(language, word)
        ]
        suggestions = list(learned)

        candidates = list(islice(self._speller(language).suggest(word), CANDIDATES))
        if self._zipf:
            ranked = sorted(
                enumerate(candidates),
                key=lambda pair: -(
                    self._zipf(pair[1], language) - RANK_PENALTY * pair[0]
                ),
            )
            candidates = [c for _, c in ranked]

        for candidate in candidates:
            if len(suggestions) >= MAX_SUGGESTIONS:
                break
            if candidate not in suggestions:
                suggestions.append(candidate)
        return suggestions[:MAX_SUGGESTIONS]

    def add_to_dictionary(self, language: str, word: str) -> None:
        self.user_dictionary.add_word(language, word)

    def learn(self, language: str, typo: str, chosen: str) -> None:
        """Remember that the user fixed ``typo`` with ``chosen``."""
        self.user_dictionary.remember_correction(language, typo, chosen)

    def ignore(self, word: str) -> None:
        self.ignored.add(word.lower())

    # -- main entry point --------------------------------------------------

    def _words(self, segment: AnalyzedSegment):
        """Yield (start, end, text) for each word worth checking in a segment."""
        for m in WORD.finditer(segment.text):
            word = m.group()
            if word.lower() in self.ignored:
                continue
            if len(word) > 1 and word.isupper():   # acronyms: NASA, PDF
                continue
            yield m.start(), m.end(), word

    def _errors(self, language: str, words: list) -> list:
        return [w for w in words if not self.is_valid(language, w[2])]

    def _alternatives(self, seg: AnalyzedSegment, current: str) -> list[str]:
        """Other dictionary languages, most likely first (per the detector)."""
        ordered = [code for code, _ in seg.candidates if code in DICTIONARIES]
        ordered += [code for code in DICTIONARIES if code not in ordered]
        return [code for code in ordered if code != current]

    def check(
        self, segments: list[AnalyzedSegment]
    ) -> tuple[list[AnalyzedSegment], list[Misspelling]]:
        """Spellcheck every segment, and let the words overrule the detector.

        If the detected language leaves errors, every other language is tried
        in the detector's order of preference. The one with the fewest errors
        wins (ties keep the more likely language), provided it is strictly
        better than the original and not itself mostly wrong. For
        "Rauchend is verboten here." detected as German: German leaves 2 errors
        ("is", "here"), English only 1 ("Rauchend"), so the sentence becomes
        English with a single flagged word.

        Returns the segments (some possibly relabelled) plus all misspellings
        with absolute positions in the original text.
        """
        self.user_dictionary.refresh()   # pick up hand edits to the dictionary

        result_segments: list[AnalyzedSegment] = []
        misspellings: list[Misspelling] = []

        for seg in segments:
            language = seg.language
            if not self.supports(language):
                result_segments.append(seg)
                continue

            words = list(self._words(seg))
            bad = self._errors(language, words)

            if bad:
                best_language, best_bad = language, bad
                for code in self._alternatives(seg, language):
                    alt_bad = self._errors(code, words)
                    if (
                        len(alt_bad) < len(best_bad)
                        and len(alt_bad) <= MAX_ALTERNATIVE_ERROR_RATE * len(words)
                    ):
                        best_language, best_bad = code, alt_bad
                if best_language != language:
                    seg = replace(seg, language=best_language, inherited=False)
                    language, bad = best_language, best_bad

            for start, end, word in bad:
                valid_in = tuple(
                    code for code in DICTIONARIES
                    if code != language and self.is_valid(code, word)
                )
                misspellings.append(
                    Misspelling(seg.start + start, seg.start + end, word, language, valid_in)
                )

            result_segments.append(seg)

        return result_segments, misspellings
