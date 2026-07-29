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
async def test_fetch_strips_html_tags_and_entities_from_raw_fields():
    # RemoteOK devuelve texto con HTML crudo — el frontend lo muestra como texto
    # plano (React escapa `<`/`>`), así que sin esto se ven tags y entidades
    # literales como "<br>" y "&amp;" en la UI.
    payload = [
        {"legal": "notice"},
        {
            "id": "7",
            "position": "Backend Engineer",
            "company": "Adams &amp; Martin Group",
            "description": "<p>Build our <strong>Python</strong> backend.</p><br><br>"
            "<ul><li>Item one</li><li>Item two</li></ul>",
        },
    ]
    respx.get(REMOTEOK_API_URL).mock(return_value=Response(200, json=payload))

    postings = await RemoteOkAdapter().fetch()

    assert postings[0].company == "Adams & Martin Group"
    assert "<" not in postings[0].description
    assert "Build our Python backend." in postings[0].description
    assert "Item one" in postings[0].description


@respx.mock
async def test_fetch_repairs_mojibake_already_present_in_the_source_payload():
    # Distinto del bug de decodificación de httpx (ver test de arriba): a veces el
    # texto que sirve RemoteOK ya viene corrupto de origen (mojibake generado aguas
    # arriba, no por cómo nosotros leemos la respuesta). Estos bytes, decodificados
    # como UTF-8 tal cual llegan, ya contienen la secuencia mojibake clásica.
    mojibake_title = "Bolsa de IniciaÃ§Ã£o CientÃ­fica"
    payload = [
        {"legal": "notice"},
        {"id": "8", "position": mojibake_title, "company": "PUCRS", "description": "desc"},
    ]
    respx.get(REMOTEOK_API_URL).mock(return_value=Response(200, json=payload))

    postings = await RemoteOkAdapter().fetch()

    assert postings[0].title == "Bolsa de Iniciação Científica"


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
