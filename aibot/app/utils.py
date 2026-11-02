import hashlib
import re
from urllib.parse import urldefrag


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def news_fingerprint(title: str, url: str | None, content: str = "") -> str:
    clean_url = urldefrag(url)[0].rstrip("/") if url else ""
    basis = "|".join((normalize_text(title), clean_url.lower(), normalize_text(content)[:1000]))
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()
