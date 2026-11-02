import sys
from pathlib import Path
from PyQt6.QtCore import QStandardPaths
from PyQt6.QtWidgets import QApplication
from correction.spellcheck import SpellChecker
from correction.thesaurus import Thesaurus
from correction.user_dictionary import UserDictionary
from gui.gui import MainWindow
from media.process import LanguageProcessor

HERE = Path(__file__).resolve().parent

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MultiLanguageAutocorrect")
    processor = LanguageProcessor()
    data_dir = Path(
        QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    )
    user_dictionary = UserDictionary(data_dir / "user_dictionary.json")

    thesaurus = Thesaurus(
        user_dictionary,
        search_dirs=[HERE / "data" / "thesaurus", data_dir / "thesaurus"],
    )

    try:
        spellchecker = SpellChecker(user_dictionary)
        spellchecker.preload()
    except ImportError as error:
        print(f"Spellchecking disabled: {error}")
        spellchecker = None

    window = MainWindow(processor, spellchecker, thesaurus)
    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
