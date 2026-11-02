from dataclasses import dataclass

@dataclass(frozen=True)
class Language:
    code: str 
    name: str
    color: str


LANGUAGES: dict[str, Language] = {
    lang.code: lang
    for lang in (
        Language("en", "English", "#FFF59D"),  # yellow
        Language("fr", "French",  "#90CAF9"),  # blue
        Language("de", "German",  "#A5D6A7"),  # green
        Language("it", "Italian", "#CE93D8"),  # purple
        Language("es", "Spanish", "#FFCC80"),  # orange
    )
}


def normalize_code(code: str) -> str: return code.lower().replace("_", "-").split("-")[0]
