import respx
from httpx import Response

from app.models.job_posting import JobLanguage
from app.services.ingestion.arbeitnow import ARBEITNOW_API_URL, ArbeitnowAdapter


@respx.mock
async def test_fetch_parses_postings():
    payload = {
        "data": [
            {
                "slug": "acme-backend-engineer",
                "company_name": "Acme Inc",
                "title": "Backend Engineer",
                "description": "<p>Build our <strong>Python</strong> backend.</p>",
                "remote": True,
                "url": "https://www.arbeitnow.com/view/acme-backend-engineer",
                "tags": ["python", "backend"],
                "job_types": ["full-time"],
                "location": "Berlin, Germany",
                "created_at": 1753000000,
            }
        ]
    }
    respx.get(ARBEITNOW_API_URL).mock(return_value=Response(200, json=payload))

    postings = await ArbeitnowAdapter().fetch()

    assert len(postings) == 1
    posting = postings[0]
    assert posting.external_id == "acme-backend-engineer"
    assert posting.title == "Backend Engineer"
    assert posting.company == "Acme Inc"
    assert "<" not in posting.description
    assert "Build our Python backend." in posting.description
    assert posting.location == "Berlin, Germany"
    assert posting.url == "https://www.arbeitnow.com/view/acme-backend-engineer"
    assert posting.language == JobLanguage.EN
    assert posting.posted_at is not None


@respx.mock
async def test_fetch_handles_missing_location():
    payload = {
        "data": [
            {
                "slug": "acme-support",
                "company_name": "Acme Inc",
                "title": "Support Engineer",
                "description": "",
                "url": "https://www.arbeitnow.com/view/acme-support",
                "created_at": 1753000000,
            }
        ]
    }
    respx.get(ARBEITNOW_API_URL).mock(return_value=Response(200, json=payload))

    postings = await ArbeitnowAdapter().fetch()

    assert postings[0].location is None
