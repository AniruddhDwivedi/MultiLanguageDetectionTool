"""Split text into sentence-like segments while remembering where each one sits.

The pitch calls for breaking a paragraph up "at each punctuation mark" so that
mixed-language sentences (e.g. an English lead-in followed by a German quote)
are not detected as one blob. Splitting on *every* comma and apostrophe would
leave fragments far too short for the detector, so the rules are:

  split on    . ! ? …   (when they end a sentence, not inside "3.14" or "e.g.x")
              ; :        (colon only when followed by whitespace/end, not "10:30")
              " “ ” « »  quotation marks
              ( )        brackets
              newlines
  never split on  , ' ’ -   (so "We're" and "well-known" stay whole)

Every Segment carries its character span in the original string, which is what
the highlighter needs.
"""

import re
from dataclasses import dataclass

# A delimiter is one of:
#   - a run of sentence-ending punctuation followed by space/end/closing quote
#   - a semicolon
#   - a colon followed by space/end
#   - a quotation mark, bracket or newline
_DELIMITER = re.compile(
    r"""
    [.!?…]+(?=\s|$|["”»)])      # sentence end, not a decimal point
  | ;
  | :(?=\s|$)
  | ["“”«»()\n]
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class Segment:
    start: int  # inclusive character index in the original text
    end: int    # exclusive
    text: str


def split_segments(text: str) -> list[Segment]:
    """Return the non-empty segments of ``text`` in order.

    Delimiters and surrounding whitespace are excluded from the segment spans,
    so a highlight covers only the words themselves.
    """
    segments: list[Segment] = []
    cursor = 0

    def add(start: int, end: int) -> None:
        # Trim whitespace, then keep the span only if it holds a letter or digit.
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        chunk = text[start:end]
        if any(ch.isalnum() for ch in chunk):
            segments.append(Segment(start, end, chunk))

    for match in _DELIMITER.finditer(text):
        add(cursor, match.start())
        cursor = match.end()
    add(cursor, len(text))

    return segments
