import respx
from httpx import Response

from app.models.job_posting import JobLanguage
from app.services.ingestion.adzuna import ADZUNA_API_URL, AdzunaAdapter


@respx.mock
async def test_fetch_parses_postings(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "adzuna_app_id", "app-id")
    monkeypatch.setattr(settings, "adzuna_app_key", "app-key")
    monkeypatch.setattr(settings, "adzuna_query", "software developer")

    url = ADZUNA_API_URL.format(country="gb")
    payload = {
        "results": [
            {
                "id": "111222",
                "title": "Software Developer",
                "company": {"display_name": "Acme Inc"},
                "location": {"display_name": "London, UK"},
                "description": "Build our Python backend.",
                "redirect_url": "https://www.adzuna.co.uk/jobs/111222",
                "created": "2026-07-20T10:00:00Z",
            }
        ]
    }
    respx.get(url).mock(return_value=Response(200, json=payload))

    postings = await AdzunaAdapter(country="gb").fetch()

    assert len(postings) == 1
    posting = postings[0]
    assert posting.external_id == "111222"
    assert posting.title == "Software Developer"
    assert posting.company == "Acme Inc"
    assert posting.description == "Build our Python backend."
    assert posting.location == "London, UK"
    assert posting.url == "https://www.adzuna.co.uk/jobs/111222"
    assert posting.language == JobLanguage.EN
    assert posting.posted_at is not None


def test_slug_is_per_country():
    assert AdzunaAdapter(country="de").slug == "adzuna-de"


@respx.mock
async def test_fetch_sends_app_credentials_and_query(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "adzuna_app_id", "app-id")
    monkeypatch.setattr(settings, "adzuna_app_key", "app-key")
    monkeypatch.setattr(settings, "adzuna_query", "programador")

    url = ADZUNA_API_URL.format(country="mx")
    route = respx.get(url).mock(return_value=Response(200, json={"results": []}))

    await AdzunaAdapter(country="mx").fetch()

    sent_params = dict(route.calls.last.request.url.params)
    assert sent_params["app_id"] == "app-id"
    assert sent_params["app_key"] == "app-key"
    assert sent_params["what"] == "programador"


@respx.mock
async def test_fetch_handles_missing_company_and_location(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "adzuna_app_id", "app-id")
    monkeypatch.setattr(settings, "adzuna_app_key", "app-key")

    url = ADZUNA_API_URL.format(country="us")
    payload = {"results": [{"id": "1", "title": "Support Rep", "redirect_url": "https://x.example/1"}]}
    respx.get(url).mock(return_value=Response(200, json=payload))

    postings = await AdzunaAdapter(country="us").fetch()

    assert postings[0].company == ""
    assert postings[0].location is None
