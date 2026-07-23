from dataclasses import dataclass

import anthropic

from app.core.config import settings

DRAFT_TOOL_NAME = "record_cover_letter_draft"

_DRAFT_TOOL = {
    "name": DRAFT_TOOL_NAME,
    "description": "Registra el borrador de carta de presentación y puntos clave para un aviso.",
    "input_schema": {
        "type": "object",
        "properties": {
            "cover_letter": {
                "type": "string",
                "description": (
                    "Carta de presentación breve (3-4 párrafos), en el mismo idioma del "
                    "aviso, personalizada con el perfil del candidato y el puesto."
                ),
            },
            "key_points": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "3 a 5 frases cortas que el candidato puede reusar para responder "
                    "preguntas típicas del formulario (por qué le interesa, fortalezas "
                    "relevantes, disponibilidad)."
                ),
            },
        },
        "required": ["cover_letter", "key_points"],
    },
}

_SYSTEM_PROMPT = (
    "Sos un asistente que ayuda a candidatos a postular a empleos. Te paso el perfil/CV "
    "de una persona y un aviso de empleo, y llamás a la herramienta "
    f"'{DRAFT_TOOL_NAME}' con un borrador de carta de presentación honesto (no inventes "
    "experiencia que no está en el perfil) y puntos clave reusables. Escribí en el mismo "
    "idioma del aviso."
)


@dataclass(frozen=True)
class CoverLetterDraft:
    cover_letter: str
    key_points: list[str]


class CoverLetterError(Exception):
    pass


def get_client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


def _build_user_message(
    job_title: str, job_company: str, job_description: str, profile_text: str
) -> str:
    return (
        f"Perfil/CV del candidato:\n{profile_text[:4000]}\n\n"
        f"Puesto: {job_title}\n"
        f"Empresa: {job_company}\n"
        f"Descripción del aviso:\n{job_description[:4000]}"
    )


async def generate_cover_letter(
    job_title: str, job_company: str, job_description: str, profile_text: str
) -> CoverLetterDraft:
    client = get_client()
    response = await client.messages.create(
        model=settings.claude_model,
        max_tokens=1024,
        system=_SYSTEM_PROMPT,
        tools=[_DRAFT_TOOL],
        tool_choice={"type": "tool", "name": DRAFT_TOOL_NAME},
        messages=[
            {
                "role": "user",
                "content": _build_user_message(
                    job_title, job_company, job_description, profile_text
                ),
            }
        ],
    )

    tool_use = next(
        (block for block in response.content if getattr(block, "type", None) == "tool_use"),
        None,
    )
    if tool_use is None:
        raise CoverLetterError("Claude no devolvió un tool_use block con el borrador.")

    data = tool_use.input
    try:
        return CoverLetterDraft(
            cover_letter=data["cover_letter"],
            key_points=list(data["key_points"]),
        )
    except KeyError as exc:
        raise CoverLetterError(f"Respuesta de Claude incompleta, falta el campo {exc}") from exc
