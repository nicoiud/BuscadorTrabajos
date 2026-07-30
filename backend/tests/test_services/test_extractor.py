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


async def test_extract_job_fields_falls_back_to_raw_values_on_missing_fields(patch_llm):
    # Regresión: antes, si al modelo le faltaba cualquiera de los campos
    # "requeridos" del schema, se perdía el aviso entero con ExtractionError — un
    # solo campo mal devuelto no debería tirar abajo el aviso cuando ya tenemos el
    # título/empresa crudos para usar como fallback.
    patch_llm(tool_call_response({"title_normalized": "X"}))

    result = await extract_job_fields("Title", "Company", "Description")

    assert result.title_normalized == "X"
    assert result.company_normalized == "Company"  # fallback al crudo
    assert result.requirements == []
    assert result.summary == ""


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


async def test_extract_job_fields_sanitizes_invalid_enum_values(patch_llm):
    # Regresión: un modelo local (Ollama) no valida el schema tan estricto como Groq
    # y puede mandar una descripción larga en vez de un valor exacto del enum — eso
    # rompía el insert en Postgres más adelante. Ahora se descarta a None en vez de
    # dejarlo pasar.
    patch_llm(
        tool_call_response(
            {
                "title_normalized": "Speculative CV",
                "company_normalized": "ETL Systems",
                "modality": "hybrid/onsite (implied by 'free on-site Employee Gym')",
                "seniority": "somewhere between mid and senior",
                "requirements": ["RF design"],
                "summary": "ETL Systems is hiring.",
            }
        )
    )

    result = await extract_job_fields("Speculative CV", "ETL Systems", "Some description")

    assert result.modality is None
    assert result.seniority is None


async def test_extract_job_fields_recovers_from_schema_echo_in_text_fields(patch_llm):
    # Bug real encontrado en producción con un modelo local (Ollama) débil: en vez
    # de devolver el texto esperado, el modelo devolvió el propio JSON del schema
    # de la tool como si fuera el valor del campo. Guardarlo tal cual contamina el
    # texto que se usa para generar el embedding (búsqueda semántica) con basura.
    patch_llm(
        tool_call_response(
            {
                "title_normalized": (
                    '{"type":"string","description":"Título del puesto, limpio y '
                    'sin ruido.", "value":"ACT Application Form"}'
                ),
                "company_normalized": '{"type":"string","description":"Nombre de la empresa.","value":"Yo-Bar"}',
                "requirements": ["Loving the company's products"],
                "summary": "Some summary.",
            }
        )
    )

    result = await extract_job_fields("ACT Application Form", "Yo-Bar", "Some description")

    assert result.title_normalized == "ACT Application Form"
    assert result.company_normalized == "Yo-Bar"


async def test_extract_job_fields_recovers_requirements_sent_as_stringified_array(patch_llm):
    # Bug real: el modelo mandó requirements como un string con forma de array en
    # vez de un array real. `list(esa_string)` la explotaba en caracteres sueltos
    # ("[", "\"", "l", "o", "v", "i", "n", "g", ...) en vez de items reales.
    patch_llm(
        tool_call_response(
            {
                "title_normalized": "Web Publisher",
                "company_normalized": "eStoreLabs",
                "requirements": '["Availability 2 years", "English C1 level"]',
                "summary": "Some summary.",
            }
        )
    )

    result = await extract_job_fields("Web Publisher", "eStoreLabs", "Some description")

    assert result.requirements == ["Availability 2 years", "English C1 level"]


async def test_extract_job_fields_discards_unparseable_requirements_string(patch_llm):
    patch_llm(
        tool_call_response(
            {
                "title_normalized": "Web Publisher",
                "company_normalized": "eStoreLabs",
                "requirements": "not a list at all",
                "summary": "Some summary.",
            }
        )
    )

    result = await extract_job_fields("Web Publisher", "eStoreLabs", "Some description")

    assert result.requirements == []


async def test_extract_job_fields_coerces_stringified_salary_and_truncates_currency(patch_llm):
    patch_llm(
        tool_call_response(
            {
                "title_normalized": "Backend Engineer",
                "company_normalized": "Acme",
                "requirements": ["Python"],
                "summary": "Backend role.",
                "salary_min": "50000",
                "salary_max": "not specified",
                "currency": "US Dollars per year",
            }
        )
    )

    result = await extract_job_fields("Backend Engineer", "Acme", "Some description")

    assert result.salary_min == 50000
    assert result.salary_max is None
    assert result.currency == "US Dolla"  # truncado a 8 caracteres, columna VARCHAR(8)
