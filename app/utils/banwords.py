import re

from app.enums.base import Language
from app.enums.open_ai import banwords


def case_like(template: str, repl: str) -> str:
    """Return word for replacement adjusted to the same capitalization pattern as initial banword

    Args:
        template (str): captures banword (upper, title, or lower cased)
        repl (str): lowercase replacement word

    Returns:
        str: replacement word formatted in the same way as a banword
    """
    if template.isupper():
        return repl.upper()
    if template[0].isupper():
        return repl.capitalize()

    return repl


def get_assets(language: Language) -> tuple[re.Pattern, dict[str, str]]:
    """Build regex pattern and lookup table for given language

    Args:
        lang (Language): language of text (Language.FR or Language.US)

    Returns:
        tuple[re.Pattern, dict[str, str]]: tuple with pattern object and word mapping
    """
    table = getattr(banwords, f"REPLACEMENTS_{language.name}")
    pattern_src = "|".join(map(re.escape, sorted(table, key=len, reverse=True)))
    pattern = re.compile(rf"(?<!\w)({pattern_src})(?!\w)", re.IGNORECASE)

    return pattern, table


def remove_banwords(texts: str | list[str], language: Language = Language.US) -> str | list[str]:
    """Replace banned words in texts with appropriate words

    Args:
        texts (list[str]): List of strings to remove banwords from
        lang (Language, optional): Language of texts, defaults to English (US)

    Returns:
        list[str]: List of cleaned texts
    """
    pattern, table = get_assets(language)

    def _repl(m: re.Match) -> str:
        original = m.group(0)
        return case_like(original, table[original.lower()])

    if isinstance(texts, str):
        return pattern.sub(_repl, texts)
    else:
        return [pattern.sub(_repl, t) for t in texts]
