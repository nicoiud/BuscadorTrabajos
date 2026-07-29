import re

from langdetect import DetectorFactory, LangDetectException, detect

from app.models.job_posting import JobLanguage

# langdetect es no-determinístico por defecto (usa un sampling aleatorio interno);
# fijar la seed hace que el mismo texto siempre devuelva el mismo idioma.
DetectorFactory.seed = 0

_LANG_MAP = {
    "es": JobLanguage.ES,
    "en": JobLanguage.EN,
    "pt": JobLanguage.PT,
}

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def detect_job_language(*texts: str) -> JobLanguage:
    """Detecta el idioma real de un aviso a partir de su título/descripción.

    No es una llamada a un proveedor de IA (Claude/Voyage) — es una heurística
    estadística local y determinística, así que vive en el adapter de ingestion
    sin violar la regla de "nunca escribir campos derivados de IA" de CLAUDE.md.
    """
    combined = " ".join(texts)
    cleaned = _HTML_TAG_RE.sub(" ", combined).strip()
    if not cleaned:
        return JobLanguage.OTHER

    try:
        code = detect(cleaned)
    except LangDetectException:
        return JobLanguage.OTHER

    return _LANG_MAP.get(code, JobLanguage.OTHER)
