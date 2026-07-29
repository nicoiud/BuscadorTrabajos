from dataclasses import dataclass

from app.services.enrichment.llm_client import LLMError, call_with_tool

EXTRACTION_TOOL_NAME = "record_job_extraction"

_EXTRACTION_SCHEMA = {
    "description": "Registra los campos normalizados de un aviso de empleo.",
    "parameters": {
        "type": "object",
        "properties": {
            "title_normalized": {
                "type": "string",
                "description": "Título del puesto, limpio y sin ruido (sin emojis, sin 'URGENTE', etc).",
            },
            "company_normalized": {"type": "string", "description": "Nombre de la empresa, limpio."},
            "seniority": {
                "type": "string",
                "enum": ["junior", "mid", "senior", "lead", "exec"],
                "description": "Omitir este campo por completo si el aviso no da para inferirlo con confianza.",
            },
            "modality": {
                "type": "string",
                "enum": ["remote", "hybrid", "onsite"],
                "description": "Omitir este campo por completo si el aviso no da para inferirlo con confianza.",
            },
            "salary_min": {"type": ["integer", "null"], "description": "Salario mínimo si se menciona, sino null."},
            "salary_max": {"type": ["integer", "null"], "description": "Salario máximo si se menciona, sino null."},
            "currency": {"type": ["string", "null"], "description": "Código de moneda (USD, ARS, EUR), sino null."},
            "requirements": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Lista corta de requisitos/skills clave, 3 a 8 items.",
            },
            "summary": {
                "type": "string",
                "description": "Resumen de 2-3 oraciones del puesto, en el idioma original del aviso.",
            },
        },
        "required": [
            "title_normalized",
            "company_normalized",
            "requirements",
            "summary",
        ],
    },
}

_SYSTEM_PROMPT = (
    "Sos un extractor de datos estructurados para avisos de empleo. Analizás el "
    "título, empresa y descripción de un aviso (puede estar en español o inglés, y "
    "puede tener HTML/formato desprolijo) y llamás a la función "
    f"'{EXTRACTION_TOOL_NAME}' con los campos normalizados. No inventes salario, "
    "seniority ni modalidad si no están explícitos o claramente implícitos en el "
    "texto — omití esos campos del todo en ese caso. Nunca uses la palabra 'null' "
    "como texto; o mandás el valor real, o no incluís el campo."
)


@dataclass(frozen=True)
class JobExtraction:
    title_normalized: str
    company_normalized: str
    requirements: list[str]
    summary: str
    seniority: str | None = None
    modality: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    currency: str | None = None


class ExtractionError(Exception):
    pass


def _build_user_message(title_raw: str, company_raw: str, description_raw: str) -> str:
    return (
        f"Título: {title_raw}\n"
        f"Empresa: {company_raw}\n"
        f"Descripción:\n{description_raw[:6000]}"
    )


async def extract_job_fields(
    title_raw: str, company_raw: str, description_raw: str
) -> JobExtraction:
    try:
        data = await call_with_tool(
            _SYSTEM_PROMPT,
            _build_user_message(title_raw, company_raw, description_raw),
            EXTRACTION_TOOL_NAME,
            _EXTRACTION_SCHEMA,
        )
    except LLMError as exc:
        raise ExtractionError(str(exc)) from exc

    try:
        return JobExtraction(
            title_normalized=data["title_normalized"],
            company_normalized=data["company_normalized"],
            requirements=list(data["requirements"]),
            summary=data["summary"],
            seniority=data.get("seniority"),
            modality=data.get("modality"),
            salary_min=data.get("salary_min"),
            salary_max=data.get("salary_max"),
            currency=data.get("currency"),
        )
    except KeyError as exc:
        raise ExtractionError(f"Respuesta del modelo incompleta, falta el campo {exc}") from exc
