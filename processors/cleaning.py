import re

HTML_TAG_RE = re.compile(r"<[^>]+>")
URL_RE = re.compile(r"https?://\S+|www\.\S+")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
NON_WORD_HEAVY_RE = re.compile(r"^[\W_]+$")


def clean_text(text: str) -> str:
    text = HTML_TAG_RE.sub(" ", text)
    text = URL_RE.sub(" ", text)
    text = EMAIL_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def is_valid_text(text: str, min_chars: int = 200) -> bool:
    if len(text) < min_chars:
        return False
    if NON_WORD_HEAVY_RE.match(text):
        return False
    alpha_ratio = sum(ch.isalpha() for ch in text) / max(1, len(text))
    return alpha_ratio > 0.2
