from dataclasses import dataclass

import anthropic

from app.core.config import settings

EXTRACTION_TOOL_NAME = "record_job_extraction"

_EXTRACTION_TOOL = {
    "name": EXTRACTION_TOOL_NAME,
    "description": "Registra los campos normalizados de un aviso de empleo.",
    "input_schema": {
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
            },
            "modality": {
                "type": "string",
                "enum": ["remote", "hybrid", "onsite"],
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
            "seniority",
            "modality",
            "requirements",
            "summary",
        ],
    },
}

_SYSTEM_PROMPT = (
    "Sos un extractor de datos estructurados para avisos de empleo. Analizás el "
    "título, empresa y descripción de un aviso (puede estar en español o inglés, y "
    "puede tener HTML/formato desprolijo) y llamás a la herramienta "
    f"'{EXTRACTION_TOOL_NAME}' con los campos normalizados. No inventes salario si no "
    "está explícito en el texto — usá null."
)


@dataclass(frozen=True)
class JobExtraction:
    title_normalized: str
    company_normalized: str
    seniority: str
    modality: str
    requirements: list[str]
    summary: str
    salary_min: int | None = None
    salary_max: int | None = None
    currency: str | None = None


class ExtractionError(Exception):
    pass


def get_client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


def _build_user_message(title_raw: str, company_raw: str, description_raw: str) -> str:
    return (
        f"Título: {title_raw}\n"
        f"Empresa: {company_raw}\n"
        f"Descripción:\n{description_raw[:6000]}"
    )


async def extract_job_fields(
    title_raw: str, company_raw: str, description_raw: str
) -> JobExtraction:
    client = get_client()
    response = await client.messages.create(
        model=settings.claude_model,
        max_tokens=1024,
        system=_SYSTEM_PROMPT,
        tools=[_EXTRACTION_TOOL],
        tool_choice={"type": "tool", "name": EXTRACTION_TOOL_NAME},
        messages=[
            {"role": "user", "content": _build_user_message(title_raw, company_raw, description_raw)}
        ],
    )

    tool_use = next(
        (block for block in response.content if getattr(block, "type", None) == "tool_use"),
        None,
    )
    if tool_use is None:
        raise ExtractionError("Claude no devolvió un tool_use block con la extracción.")

    data = tool_use.input
    try:
        return JobExtraction(
            title_normalized=data["title_normalized"],
            company_normalized=data["company_normalized"],
            seniority=data["seniority"],
            modality=data["modality"],
            requirements=list(data["requirements"]),
            summary=data["summary"],
            salary_min=data.get("salary_min"),
            salary_max=data.get("salary_max"),
            currency=data.get("currency"),
        )
    except KeyError as exc:
        raise ExtractionError(f"Respuesta de Claude incompleta, falta el campo {exc}") from exc
