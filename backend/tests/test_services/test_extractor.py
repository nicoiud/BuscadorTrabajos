import pytest

from app.services.enrichment.extractor import ExtractionError, extract_job_fields
from tests.conftest import empty_response, tool_call_response


async def test_extract_job_fields_parses_tool_call_response(patch_llm):
    patch_llm(
        tool_call_response(
            {
                "title_normalized": "Senior Backend Engineer",
                "company_normalized": "Acme Remote",
                "seniority": "senior",
                "modality": "remote",
                "salary_min": 80000,
                "salary_max": 110000,
                "currency": "USD",
                "requirements": ["Python", "PostgreSQL", "AWS"],
                "summary": "Build and scale Acme's backend platform.",
            }
        )
    )

    result = await extract_job_fields("Senior Backend Eng", "Acme", "We need a backend eng...")

    assert result.title_normalized == "Senior Backend Engineer"
    assert result.seniority == "senior"
    assert result.modality == "remote"
    assert result.requirements == ["Python", "PostgreSQL", "AWS"]
    assert result.salary_min == 80000


async def test_extract_job_fields_raises_when_no_tool_call(patch_llm):
    patch_llm(empty_response())

    with pytest.raises(ExtractionError):
        await extract_job_fields("Title", "Company", "Description")


async def test_extract_job_fields_raises_on_missing_field(patch_llm):
    patch_llm(tool_call_response({"title_normalized": "X"}))  # missing required fields

    with pytest.raises(ExtractionError):
        await extract_job_fields("Title", "Company", "Description")


async def test_extract_job_fields_allows_missing_seniority_and_modality(patch_llm):
    # Muchos avisos no dicen seniority/modalidad explícitamente — el modelo puede
    # omitir esos campos del todo en vez de inventarlos, y no debería fallar.
    patch_llm(
        tool_call_response(
            {
                "title_normalized": "Community Manager",
                "company_normalized": "Acme",
                "requirements": ["Social media"],
                "summary": "Manage Acme's social media presence.",
            }
        )
    )

    result = await extract_job_fields("Community Manager", "Acme", "Some description")

    assert result.seniority is None
    assert result.modality is None


async def test_extract_job_fields_raises_extraction_error_on_provider_rejection(patch_llm_error):
    # Regresión: Groq puede devolver 400 (ej. el modelo mandó "null" como string en
    # vez de omitir un campo) — esto tiene que traducirse a ExtractionError, no a una
    # excepción cruda de openai que tire abajo el lote entero en pipeline.py.
    patch_llm_error()

    with pytest.raises(ExtractionError):
        await extract_job_fields("Title", "Company", "Description")
