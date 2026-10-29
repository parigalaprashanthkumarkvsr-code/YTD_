import os
import re

_WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
_ALLOWED_PUNCTUATION = set(" ._-()[]")
_MAX_STEM_BYTES = 180


def sanitize_filename(name: str, fallback: str = "download") -> str:
    """Return a safe basename that cannot escape its directory."""
    base = os.path.basename(name.replace("\\", "/"))
    stem, extension = os.path.splitext(base)

    cleaned_chars = [
        char if (char.isalnum() or char in _ALLOWED_PUNCTUATION) else "_" for char in stem
    ]
    stem = "".join(cleaned_chars)
    stem = re.sub(r"\s+", " ", stem)
    stem = re.sub(r"_+", "_", stem).strip(" ._")

    if not stem:
        stem = fallback
    if stem.upper() in _WINDOWS_RESERVED:
        stem = f"_{stem}"

    encoded = stem.encode("utf-8")
    if len(encoded) > _MAX_STEM_BYTES:
        stem = encoded[:_MAX_STEM_BYTES].decode("utf-8", errors="ignore").rstrip(" ._")

    safe_extension = ""
    if extension:
        suffix = re.sub(r"[^A-Za-z0-9]", "", extension.lstrip("."))[:10]
        if suffix:
            safe_extension = f".{suffix}"

    return f"{stem}{safe_extension}"
