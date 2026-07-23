from app.services.enrichment.llm_client import call_text

_SYSTEM_PROMPT = (
    "Sos un asistente que ayuda a completar formularios de postulación laboral. Te paso "
    "el perfil/CV de una persona y la pregunta o el campo de un formulario (puede estar "
    "en español o inglés), y respondés SOLO con el texto que debería ir en ese campo — "
    "sin saludos, sin explicaciones, sin comillas. Respuesta breve (1-3 oraciones salvo "
    "que el campo pida explícitamente algo más largo). No inventes datos que no están en "
    "el perfil."
)


async def generate_field_answer(field_label: str, profile_text: str) -> str:
    user_message = (
        f"Perfil/CV:\n{profile_text[:4000]}\n\n"
        f"Campo del formulario a completar: {field_label}"
    )
    return await call_text(_SYSTEM_PROMPT, user_message, max_tokens=300)
