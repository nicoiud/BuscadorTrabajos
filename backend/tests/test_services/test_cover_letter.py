import pytest

from app.services.enrichment.cover_letter import CoverLetterError, generate_cover_letter
from tests.conftest import empty_response, tool_call_response


async def test_generate_cover_letter_parses_tool_call_response(patch_llm):
    patch_llm(
        tool_call_response(
            {
                "cover_letter": "Estimados, me postulo para el puesto de Backend Engineer...",
                "key_points": ["5 años con Python", "Experiencia en equipos remotos"],
            }
        )
    )

    result = await generate_cover_letter(
        "Backend Engineer", "Acme", "Buscamos un backend engineer...", "Soy dev Python senior"
    )

    assert "me postulo" in result.cover_letter
    assert result.key_points == ["5 años con Python", "Experiencia en equipos remotos"]


async def test_generate_cover_letter_raises_when_no_tool_call(patch_llm):
    patch_llm(empty_response())

    with pytest.raises(CoverLetterError):
        await generate_cover_letter("Title", "Company", "Description", "Profile")


async def test_generate_cover_letter_raises_on_missing_field(patch_llm):
    patch_llm(tool_call_response({"cover_letter": "X"}))

    with pytest.raises(CoverLetterError):
        await generate_cover_letter("Title", "Company", "Description", "Profile")
