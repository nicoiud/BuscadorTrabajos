import respx
from httpx import Response

from app.models.job_posting import JobLanguage
from app.services.ingestion.jooble import JOOBLE_API_URL, JoobleAdapter


@respx.mock
async def test_fetch_parses_postings(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "jooble_api_key", "test-key")
    monkeypatch.setattr(settings, "jooble_keywords", "sistemas")
    monkeypatch.setattr(settings, "jooble_location", "Argentina")

    url = JOOBLE_API_URL.format(key="test-key")
    payload = {
        "totalCount": 1,
        "jobs": [
            {
                "id": 987654321,
                "title": "Analista Funcional",
                "location": "Buenos Aires",
                "snippet": "Buscamos analista funcional con experiencia...",
                "salary": "",
                "company": "Acme SRL",
                "updated": "2026-07-20T10:00:00.0000000",
                "link": "https://ar.jooble.org/jdp/987654321",
                "type": "Full-time",
            }
        ],
    }
    respx.post(url).mock(return_value=Response(200, json=payload))

    postings = await JoobleAdapter().fetch()

    assert len(postings) == 1
    posting = postings[0]
    assert posting.external_id == "987654321"
    assert posting.title == "Analista Funcional"
    assert posting.company == "Acme SRL"
    assert posting.description == "Buscamos analista funcional con experiencia..."
    assert posting.location == "Buenos Aires"
    assert posting.url == "https://ar.jooble.org/jdp/987654321"
    assert posting.language == JobLanguage.ES
    assert posting.posted_at is not None


@respx.mock
async def test_fetch_sends_keywords_and_location_from_settings(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "jooble_api_key", "test-key")
    monkeypatch.setattr(settings, "jooble_keywords", "programador")
    monkeypatch.setattr(settings, "jooble_location", "Cordoba")

    url = JOOBLE_API_URL.format(key="test-key")
    route = respx.post(url).mock(return_value=Response(200, json={"jobs": []}))

    await JoobleAdapter().fetch()

    sent_body = route.calls.last.request.content
    assert b"programador" in sent_body
    assert b"Cordoba" in sent_body


@respx.mock
async def test_fetch_defaults_missing_company_and_id(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "jooble_api_key", "test-key")

    url = JOOBLE_API_URL.format(key="test-key")
    payload = {"jobs": [{"title": "Soporte IT", "snippet": "", "link": "https://ar.jooble.org/jdp/1"}]}
    respx.post(url).mock(return_value=Response(200, json=payload))

    postings = await JoobleAdapter().fetch()

    assert postings[0].company == "Empresa sin especificar"
    assert postings[0].external_id == "https://ar.jooble.org/jdp/1"
