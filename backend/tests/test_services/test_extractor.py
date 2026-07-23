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
