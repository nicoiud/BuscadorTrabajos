import anthropic

from app.core.config import settings

_SYSTEM_PROMPT = (
    "Sos un asistente que ayuda a completar formularios de postulación laboral. Te paso "
    "el perfil/CV de una persona y la pregunta o el campo de un formulario (puede estar "
    "en español o inglés), y respondés SOLO con el texto que debería ir en ese campo — "
    "sin saludos, sin explicaciones, sin comillas. Respuesta breve (1-3 oraciones salvo "
    "que el campo pida explícitamente algo más largo). No inventes datos que no están en "
    "el perfil."
)


def get_client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


async def generate_field_answer(field_label: str, profile_text: str) -> str:
    client = get_client()
    response = await client.messages.create(
        model=settings.claude_model,
        max_tokens=300,
        system=_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Perfil/CV:\n{profile_text[:4000]}\n\n"
                    f"Campo del formulario a completar: {field_label}"
                ),
            }
        ],
    )

    text_block = next(
        (block for block in response.content if getattr(block, "type", None) == "text"),
        None,
    )
    return text_block.text.strip() if text_block is not None else ""
