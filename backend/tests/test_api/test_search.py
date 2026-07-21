from datetime import UTC, datetime

from app.api.v1 import search as search_api
from app.models.job_posting import JobLanguage, JobPosting, JobRegion


def _fake_job(title: str) -> JobPosting:
    return JobPosting(
        id="00000000-0000-0000-0000-000000000001",
        source_id="00000000-0000-0000-0000-000000000002",
        external_id="1",
        url="https://example.com/1",
        title_raw=title,
        company_raw="Acme",
        description_raw="desc",
        scraped_at=datetime.now(UTC),
        language=JobLanguage.EN,
        region=JobRegion.REMOTE_INTL,
        enrichment_status="done",
    )


async def test_semantic_search_embeds_query_and_returns_ranked_jobs(client, monkeypatch):
    async def fake_embed_query(text: str) -> list[float]:
        assert text == "remote python backend"
        return [0.1, 0.2, 0.3]

    async def fake_semantic_search(db, query_embedding, limit):
        assert query_embedding == [0.1, 0.2, 0.3]
        assert limit == 5
        return [_fake_job("Backend Engineer")]

    monkeypatch.setattr(search_api, "embed_query", fake_embed_query)
    monkeypatch.setattr(search_api, "semantic_search", fake_semantic_search)

    response = await client.post(
        "/api/v1/search", json={"query": "remote python backend", "limit": 5}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title_raw"] == "Backend Engineer"
