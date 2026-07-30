import respx
from httpx import Response

from app.models.job_posting import JobLanguage
from app.services.ingestion.greenhouse import GREENHOUSE_API_URL, GreenhouseAdapter


@respx.mock
async def test_fetch_parses_postings():
    url = GREENHOUSE_API_URL.format(board="acme")
    payload = {
        "jobs": [
            {
                "id": 555,
                "title": "Backend Engineer &amp; Platform",
                "updated_at": "2026-07-20T10:00:00-05:00",
                "location": {"name": "Remote - US"},
                "absolute_url": "https://boards.greenhouse.io/acme/jobs/555",
                "content": "<p>Build our <strong>Python</strong> backend.</p>",
            }
        ]
    }
    respx.get(url).mock(return_value=Response(200, json=payload))

    postings = await GreenhouseAdapter(board="acme", company_name="Acme Inc").fetch()

    assert len(postings) == 1
    posting = postings[0]
    assert posting.external_id == "555"
    assert posting.title == "Backend Engineer & Platform"
    assert posting.company == "Acme Inc"
    assert "<" not in posting.description
    assert "Build our Python backend." in posting.description
    assert posting.location == "Remote - US"
    assert posting.url == "https://boards.greenhouse.io/acme/jobs/555"
    assert posting.language == JobLanguage.EN
    assert posting.posted_at is not None


@respx.mock
async def test_fetch_defaults_company_name_from_board_slug():
    url = GREENHOUSE_API_URL.format(board="widget-co")
    respx.get(url).mock(return_value=Response(200, json={"jobs": []}))

    adapter = GreenhouseAdapter(board="widget-co")

    assert adapter.company_name == "Widget Co"
    assert adapter.slug == "greenhouse-widget-co"
    assert await adapter.fetch() == []


@respx.mock
async def test_fetch_handles_missing_location_and_content():
    url = GREENHOUSE_API_URL.format(board="acme")
    payload = {"jobs": [{"id": 1, "title": "Support Rep", "absolute_url": "https://x.example/1"}]}
    respx.get(url).mock(return_value=Response(200, json=payload))

    postings = await GreenhouseAdapter(board="acme").fetch()

    assert postings[0].location is None
    assert postings[0].description == ""
