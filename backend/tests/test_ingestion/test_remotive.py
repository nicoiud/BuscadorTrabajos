import respx
from httpx import Response

from app.models.job_posting import JobLanguage
from app.services.ingestion.remotive import REMOTIVE_API_URL, RemotiveAdapter


@respx.mock
async def test_fetch_parses_postings():
    payload = {
        "jobs": [
            {
                "id": 12345,
                "url": "https://remotive.com/remote-jobs/software-dev/backend-engineer-12345",
                "title": "Backend Engineer",
                "company_name": "Acme Inc",
                "category": "Software Development",
                "publication_date": "2026-07-20T10:00:00",
                "candidate_required_location": "Worldwide",
                "description": "<p>Build our <strong>Python</strong> backend.</p>",
            }
        ]
    }
    respx.get(REMOTIVE_API_URL).mock(return_value=Response(200, json=payload))

    postings = await RemotiveAdapter(category="software-dev").fetch()

    assert len(postings) == 1
    posting = postings[0]
    assert posting.external_id == "12345"
    assert posting.title == "Backend Engineer"
    assert posting.company == "Acme Inc"
    assert "<" not in posting.description
    assert "Build our Python backend." in posting.description
    assert posting.location == "Worldwide"
    assert posting.url == "https://remotive.com/remote-jobs/software-dev/backend-engineer-12345"
    assert posting.language == JobLanguage.EN
    assert posting.posted_at is not None


def test_slug_is_per_category():
    assert RemotiveAdapter(category="devops").slug == "remotive-devops"


@respx.mock
async def test_fetch_sends_category_as_query_param():
    respx.get(REMOTIVE_API_URL, params={"category": "qa"}).mock(
        return_value=Response(200, json={"jobs": []})
    )

    postings = await RemotiveAdapter(category="qa").fetch()

    assert postings == []
