from dataclasses import dataclass

from app.services.enrichment.llm_client import LLMError, call_with_tool

DRAFT_TOOL_NAME = "record_cover_letter_draft"

_DRAFT_SCHEMA = {
    "description": "Registra el borrador de carta de presentación y puntos clave para un aviso.",
    "parameters": {
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
    "de una persona y un aviso de empleo, y llamás a la función "
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
    try:
        data = await call_with_tool(
            _SYSTEM_PROMPT,
            _build_user_message(job_title, job_company, job_description, profile_text),
            DRAFT_TOOL_NAME,
            _DRAFT_SCHEMA,
        )
    except LLMError as exc:
        raise CoverLetterError(str(exc)) from exc

    try:
        return CoverLetterDraft(
            cover_letter=data["cover_letter"],
            key_points=list(data["key_points"]),
        )
    except KeyError as exc:
        raise CoverLetterError(f"Respuesta del modelo incompleta, falta el campo {exc}") from exc
