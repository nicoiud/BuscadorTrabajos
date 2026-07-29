import json

import respx
from httpx import Response

from app.models.job_posting import JobLanguage, JobRegion
from app.services.ingestion.remoteok import REMOTEOK_API_URL, RemoteOkAdapter


@respx.mock
async def test_fetch_parses_postings_and_skips_legal_notice(remoteok_api_fixture):
    respx.get(REMOTEOK_API_URL).mock(return_value=Response(200, json=remoteok_api_fixture))

    postings = await RemoteOkAdapter().fetch()

    assert len(postings) == 2
    first = postings[0]
    assert first.external_id == "1000001"
    assert first.title == "Senior Backend Engineer"
    assert first.company == "Acme Remote"
    assert first.language == JobLanguage.EN
    assert first.region == JobRegion.REMOTE_INTL
    assert first.posted_at is not None


@respx.mock
async def test_fetch_decodes_utf8_body_without_explicit_charset_header():
    # RemoteOK responde con Content-Type: application/json sin `charset=utf-8`.
    # Si se confía en la detección automática de httpx, esto puede terminar
    # decodificando los bytes UTF-8 como Latin-1 (mojibake: "Ã©" en vez de "é").
    payload = [
        {"legal": "notice"},
        {
            "id": "42",
            "position": "Ingeniero de Operación",
            "company": "Compañía Ñu",
            "description": "Descrição da vaga com acentuação",
        },
    ]
    body = json.dumps(payload).encode("utf-8")
    respx.get(REMOTEOK_API_URL).mock(
        return_value=Response(200, content=body, headers={"Content-Type": "application/json"})
    )

    postings = await RemoteOkAdapter().fetch()

    assert len(postings) == 1
    assert postings[0].title == "Ingeniero de Operación"
    assert postings[0].company == "Compañía Ñu"
    assert postings[0].description == "Descrição da vaga com acentuação"


@respx.mock
async def test_fetch_detects_real_language_instead_of_hardcoding_english():
    # Regresión: RemoteOK trae avisos en varios idiomas (predominantemente inglés,
    # pero también portugués de empresas brasileñas); el adapter mandaba "en" fijo
    # sin mirar el contenido real.
    payload = [
        {"legal": "notice"},
        {
            "id": "1",
            "position": "Engenheiro de Software",
            "company": "Empresa Brasileira",
            "description": "Vaga para desenvolvedor backend com experiência em Python.",
        },
    ]
    respx.get(REMOTEOK_API_URL).mock(return_value=Response(200, json=payload))

    postings = await RemoteOkAdapter().fetch()

    assert postings[0].language == JobLanguage.PT


@respx.mock
async def test_fetch_handles_malformed_entries_gracefully():
    payload = [
        {"legal": "notice"},
        {"id": "1", "position": "OK Job", "company": "Co", "description": "d"},
        {"company": "Missing position and id"},
    ]
    respx.get(REMOTEOK_API_URL).mock(return_value=Response(200, json=payload))

    postings = await RemoteOkAdapter().fetch()

    assert len(postings) == 1
    assert postings[0].external_id == "1"
