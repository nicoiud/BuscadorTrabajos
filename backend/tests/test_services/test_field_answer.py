from app.services.enrichment.field_answer import generate_field_answer
from tests.conftest import empty_response, text_response


async def test_generate_field_answer_returns_trimmed_text(patch_llm):
    patch_llm(text_response("  Disponibilidad inmediata.  "))

    result = await generate_field_answer("¿Cuál es tu disponibilidad?", "Perfil de prueba")

    assert result == "Disponibilidad inmediata."


async def test_generate_field_answer_returns_empty_string_without_content(patch_llm):
    patch_llm(empty_response())

    result = await generate_field_answer("Campo", "Perfil")

    assert result == ""
