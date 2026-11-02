import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterator

from languages import LANGUAGES, normalize_code
from .segmenter import split_segments

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(HERE, "models", "language_detector.tflite")

MIN_CONFIDENCE = 0.55
MIN_LETTERS = 4


@dataclass(frozen=True)
class AnalyzedSegment:
    start: int
    end: int
    text: str
    language: str | None  
    confidence: float
    inherited: bool = False
    candidates: tuple[tuple[str, float], ...] = ()

    @property
    def supported(self) -> bool:
        return self.language in LANGUAGES


class LanguageProcessor:
    def __init__(self, detector=None):
        if detector is None:
            from mediapipe.tasks import python
            from mediapipe.tasks.python import text

            options = text.LanguageDetectorOptions(
                base_options=python.BaseOptions(model_asset_path=MODEL_PATH)
            )
            detector = text.LanguageDetector.create_from_options(options)

        self.detector = detector
        self._detect_cached = lru_cache(maxsize=2048)(self._detect_raw)

    # -- low level ---------------------------------------------------------

    def detect_language(self, input_text: str): return self.detector.detect(input_text)

    def _detect_raw(self, segment_text: str):
        result = self.detector.detect(segment_text)
        if not result.detections:
            return None, 0.0, ()

        top = max(result.detections, key=lambda d: d.probability)

        best: dict[str, float] = {}
        for d in result.detections:
            code = normalize_code(d.language_code)
            if code in LANGUAGES:
                best[code] = max(best.get(code, 0.0), float(d.probability))
        candidates = tuple(sorted(best.items(), key=lambda kv: -kv[1]))

        return normalize_code(top.language_code), float(top.probability), candidates

    # -- sentence level ----------------------------------------------------

    def iter_analyze(self, text: str) -> Iterator[AnalyzedSegment]:
        previous_language: str | None = None

        for seg in split_segments(text):
            letters = sum(ch.isalpha() for ch in seg.text)
            language, confidence, candidates = (None, 0.0, ())
            if letters:
                language, confidence, candidates = self._detect_cached(seg.text)

            unsure = (
                language is None
                or confidence < MIN_CONFIDENCE
                or letters < MIN_LETTERS
            )
            inherited = False
            if unsure and previous_language is not None:
                language, inherited = previous_language, True
            elif unsure:
                if letters < MIN_LETTERS:
                    language = None

            if language is not None:
                previous_language = language

            yield AnalyzedSegment(
                seg.start, seg.end, seg.text, language, confidence, inherited, candidates
            )

    def analyze(self, text: str) -> list[AnalyzedSegment]:
        return list(self.iter_analyze(text))

    def get_detector_details(self):
        return {
            "type": type(self.detector).__name__,
            "model_path": MODEL_PATH,
        }
