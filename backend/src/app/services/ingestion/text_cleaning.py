import html
import re

import ftfy

_BLOCK_BREAK_RE = re.compile(r"(?i)<(br\s*/?|/p|/li|/div|/h[1-6]|/tr)\s*>")
_TAG_RE = re.compile(r"<[^>]+>")
_BLANK_LINES_RE = re.compile(r"\n{3,}")


def fix_mojibake(value: str) -> str:
    """Repara texto que quedó corrupto por un mal manejo de encoding aguas arriba
    (ej. UTF-8 interpretado como Latin-1 y reencodeado) usando `ftfy`. Best-effort:
    corrupciones de varias vueltas no siempre se pueden reconstruir del todo.
    """
    return ftfy.fix_text(value) if value else value


def strip_html(value: str) -> str:
    """Convierte HTML crudo (como el que devuelve la API de RemoteOK) a texto plano.

    No es sanitización contra XSS — el resultado nunca se inyecta como HTML en el
    frontend, siempre se muestra como texto — es solo limpieza para que no aparezcan
    tags ni entidades (`&amp;`, `<br>`, `<p>`) literales en la UI.
    """
    if not value:
        return value
    with_breaks = _BLOCK_BREAK_RE.sub("\n", value)
    without_tags = _TAG_RE.sub("", with_breaks)
    unescaped = html.unescape(without_tags)
    collapsed = _BLANK_LINES_RE.sub("\n\n", unescaped)
    return "\n".join(line.rstrip() for line in collapsed.split("\n")).strip()


def strip_html_inline(value: str) -> str:
    """Como `strip_html` pero para campos de una sola línea (título, empresa)."""
    return " ".join(strip_html(value).split())


def clean_raw_text(value: str) -> str:
    """Pipeline completo para un campo multi-línea (ej. descripción): repara
    mojibake y después limpia el HTML."""
    return strip_html(fix_mojibake(value))


def clean_raw_text_inline(value: str) -> str:
    """Pipeline completo para un campo de una sola línea (ej. título, empresa)."""
    return strip_html_inline(fix_mojibake(value))
