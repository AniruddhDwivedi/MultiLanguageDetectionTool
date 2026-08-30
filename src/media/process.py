import os
from mediapipe.tasks import python
from mediapipe.tasks.python import text

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(HERE, "models", "detector.tflite")

class LanguageProcessor:
    def __init__(self):
        base_options = python.BaseOptions(
            model_asset_path=MODEL_PATH
        )

        options = text.LanguageDetectorOptions(
            base_options=base_options
        )

        self.detector = text.LanguageDetector.create_from_options(
            options
        )

    def detect_language(self, input_text: str):
        return self.detector.detect(input_text)

    def get_detector_details(self):
        return {
            "type": type(self.detector).__name__,
            "model_path": MODEL_PATH,
        }