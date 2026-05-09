import re
import urllib.parse

LANG_MARKER = re.compile(r'Abstract in (\w+)', re.IGNORECASE)

def split_abstract_by_language(raw: str) -> dict[str, str]:
    """Split a concatenated multi-language abstract blob into {lang: text}."""
    parts = LANG_MARKER.split(raw)          # ['', 'portuguese', 'RESUMO...', 'english', 'ABSTRACT...']
    out = {}
    it = iter(parts[1:])                    # skip leading empty string
    for lang, body in zip(it, it):
        out[lang.lower()] = body.strip()
    return out if out else {"default": raw.strip()}

def extract_pid(url: str) -> str:
    pid = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("pid", [None])[0]
    return pid or url