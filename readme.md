# PolyWrite AI: Multi Language Detection and Correction Tool

A desktop writing tool for **code-mixed text**. As you type, it works out the language of each sentence, colours it, and spellchecks every word against the dictionary of *that* language, so a German sentence in the middle of an English paragraph is no longer one long red squiggle.

Everything runs **locally and offline**: no server, no account, no internet connection once installed.

## Screenshots

<img width="1189" height="810" alt="Screenshot 2026-11-15 154621" src="https://github.com/user-attachments/assets/2f84b942-dd52-4ef2-8243-25a389eccb1e" />

<img width="1192" height="810" alt="Screenshot 2026-11-17 174904" src="https://github.com/user-attachments/assets/bb2870da-1417-441b-a152-57cdcb66ac39" />

## Features

- **Sentence-level language detection** for English, French, German, Italian and Spanish, shown as a coloured background per sentence (legend at the bottom of the window).
- **Per-language spellchecking** with wavy underlines under misspelled words.
- **Right-click suggestions**, ranked by how common each word is, so the word you meant (e.g. "are" for "ane") comes before rare near-matches.
- **Words can overrule the detector:** if a sentence has many errors in its detected language but fits another one better, it is relabelled, and a word that is valid in another language is flagged as such ("seems to be in: German").
- **Personal dictionary** stored as an editable JSON file: "Add to dictionary" keeps a word, and corrections you choose are remembered and offered first next time.
- **Basic thesaurus:** right-click a correctly spelled word for synonyms and antonyms, from your personal dictionary and from MyThes files (an English one is included).
- **Responsive:** language detection and spellchecking run on background threads, so typing never waits for them.

## Usage

1. Install **Python 3.13**.
2. Download the source code and create a virtual environment.
3. Install the requirements:
   ```
   pip install -r requirements.txt
   ```
4. Run the program:
   ```
   python3 src/main.py
   ```

To check that the language model, dictionaries, word lists and thesaurus are all found, run `python3 src/main.py --selftest`. The result is written to a `selftest.txt` file in the application's data folder (`%LOCALAPPDATA%\MultiLanguageAutocorrect` on Windows).

Your personal dictionary is saved as `user_dictionary.json` in the application-data folder; the **Dictionary** menu opens it for editing.

## Project layout

```
src/
  main.py             start-up
  analysis.py         the two background threads (detect, then spellcheck)
  languages.py        supported languages and their colours
  gui/                window, text editor with highlights and right-click menu
  media/              sentence splitter and the language detector (+ model)
  correction/         spellchecker, personal dictionary, thesaurus
  data/thesaurus/     MyThes thesaurus files
packaging/            Windows build files
```

## Dependencies

| Used for | Library |
| --- | --- |
| Language detection | [MediaPipe](https://ai.google.dev/edge/mediapipe) Language Detector (Google AI Edge), a pre-built TensorFlow Lite model (`language_detector.tflite`) |
| Interface | PyQt6 (Qt 6) |
| Spellchecking | Hunspell dictionaries through [phunspell](https://pypi.org/project/phunspell/) / [spylls](https://pypi.org/project/spylls/) (pure Python, no native Hunspell needed) |
| Suggestion ranking | [wordfreq](https://pypi.org/project/wordfreq/) |
| Thesaurus | MyThes data files |

## Known limitations

- Very short text (one to three words) and sentences that mix several languages are identified unreliably; sentences of four or more words are identified correctly in nearly every test.
- A very short sentence (or one the detector is unsure of) takes the language of the sentence before it. This keeps colouring stable, but it is wrong when a short reply switches language.
- Grammar checking is not implemented.
- The thesaurus matches exact words only ("eagles" will not find "eagle").

## Windows executable

Build files are in `packaging/` (PyInstaller, a PowerShell script and a GitHub Actions workflow). They build `PolyWrite.exe` and run the self-test on the finished program. **These have not yet been run on Windows**, so treat the Windows build as experimental. To build it, either run `packaging\build_windows.ps1` in PowerShell on a Windows PC (64-bit Python 3.13), or use the **Build Windows executable** workflow under the repository's *Actions* tab; both produce `dist\PolyWrite\PolyWrite.exe` and a zip of it.

## Next steps

- Grammar checking (offline, lightweight, e.g. singular and plural agreement)
- A better rule for short sentences that switch language, and a tuned confidence threshold
- Thesaurus data for every supported language
- More languages (e.g. Latin)
- Faster handling of long documents (separate processes instead of threads)
- A web version
- A Linux AppImage
