import queue
import threading
import traceback

_DONE = object() 
_FAILED = object()


class AnalysisPipeline:
    def __init__(self, processor, spellchecker=None):
        self.processor = processor
        self.spellchecker = spellchecker
        self._generation = 0
        self._lock = threading.Lock()

    # -- generation handling -------------------------------------------------

    def invalidate(self) -> int:
        with self._lock:
            self._generation += 1
            return self._generation

    def is_current(self, generation: int) -> bool:
        return generation == self._generation

    # -- public API ----------------------------------------------------------

    def submit(self, text: str, on_detected, on_finished) -> int:
        generation = self.invalidate()
        segments_queue: queue.Queue = queue.Queue()

        threading.Thread(
            target=self._detect_stage,
            args=(generation, text, segments_queue, on_detected),
            daemon=True,
        ).start()
        threading.Thread(
            target=self._spell_stage,
            args=(generation, segments_queue, on_finished),
            daemon=True,
        ).start()
        return generation

    # -- stages --------------------------------------------------------------

    def _detect_stage(self, generation, text, out_queue, on_detected):
        segments = []
        marker = _DONE
        try:
            for segment in self.processor.iter_analyze(text):
                if not self.is_current(generation):
                    return
                segments.append(segment)
                out_queue.put(segment)
            if self.is_current(generation):
                on_detected(generation, segments)
        except Exception:
            traceback.print_exc()
            marker = _FAILED
        finally:
            out_queue.put(marker)   # always release the spellcheck stage

    def _spell_stage(self, generation, in_queue, on_finished):
        segments, misspellings = [], []
        try:
            while True:
                segment = in_queue.get()
                if segment is _DONE:
                    break
                if segment is _FAILED:
                    return
                if not self.is_current(generation):
                    return
                if self.spellchecker:
                    checked, found = self.spellchecker.check([segment])
                    segments += checked
                    misspellings += found
                else:
                    segments.append(segment)
            if self.is_current(generation):
                on_finished(generation, segments, misspellings)
        except Exception:
            traceback.print_exc()
