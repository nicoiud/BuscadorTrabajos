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
