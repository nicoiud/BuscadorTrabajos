import respx
from httpx import Response

from app.models.job_posting import JobLanguage
from app.services.ingestion.lever import LEVER_API_URL, LeverAdapter


@respx.mock
async def test_fetch_parses_postings_using_plain_description():
    url = LEVER_API_URL.format(company="acme")
    payload = [
        {
            "id": "abc-123",
            "text": "Senior Backend Engineer",
            "descriptionPlain": "Build our Python backend with a great team.",
            "description": "<p>Build our <strong>Python</strong> backend.</p>",
            "categories": {"location": "Remote"},
            "hostedUrl": "https://jobs.lever.co/acme/abc-123",
            "createdAt": 1753000000000,
        }
    ]
    respx.get(url).mock(return_value=Response(200, json=payload))

    postings = await LeverAdapter(company="acme", company_name="Acme Inc").fetch()

    assert len(postings) == 1
    posting = postings[0]
    assert posting.external_id == "abc-123"
    assert posting.title == "Senior Backend Engineer"
    assert posting.company == "Acme Inc"
    assert posting.description == "Build our Python backend with a great team."
    assert posting.location == "Remote"
    assert posting.url == "https://jobs.lever.co/acme/abc-123"
    assert posting.language == JobLanguage.EN
    assert posting.posted_at is not None


@respx.mock
async def test_fetch_falls_back_to_html_description_when_plain_missing():
    url = LEVER_API_URL.format(company="acme")
    payload = [
        {
            "id": "abc-456",
            "text": "Frontend Engineer",
            "description": "<p>React and <br>TypeScript.</p>",
            "hostedUrl": "https://jobs.lever.co/acme/abc-456",
        }
    ]
    respx.get(url).mock(return_value=Response(200, json=payload))

    postings = await LeverAdapter(company="acme").fetch()

    assert "<" not in postings[0].description
    assert "React and" in postings[0].description
    assert postings[0].location is None
    assert postings[0].posted_at is None


@respx.mock
async def test_fetch_defaults_company_name_from_slug():
    url = LEVER_API_URL.format(company="widget-co")
    respx.get(url).mock(return_value=Response(200, json=[]))

    adapter = LeverAdapter(company="widget-co")

    assert adapter.company_name == "Widget Co"
    assert adapter.slug == "lever-widget-co"
