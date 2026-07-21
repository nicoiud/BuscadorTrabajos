import respx
from httpx import Response

from app.api.v1 import jobs as jobs_api
from app.services.enrichment.pipeline import EnrichResult
from app.services.ingestion.remoteok import REMOTEOK_API_URL


async def test_list_jobs_empty(client):
    response = await client.get("/api/v1/jobs")

    assert response.status_code == 200
    body = response.json()
    assert body == {"total": 0, "items": []}


@respx.mock
async def test_ingest_then_list_jobs(client, remoteok_api_fixture):
    respx.get(REMOTEOK_API_URL).mock(return_value=Response(200, json=remoteok_api_fixture))

    ingest_response = await client.post("/api/v1/jobs/ingest/remoteok")
    assert ingest_response.status_code == 200
    assert ingest_response.json() == {
        "source_slug": "remoteok",
        "fetched": 2,
        "created": 2,
        "updated": 0,
    }

    list_response = await client.get("/api/v1/jobs")
    assert list_response.status_code == 200
    body = list_response.json()
    assert body["total"] == 2
    titles = {item["title_raw"] for item in body["items"]}
    assert titles == {"Senior Backend Engineer", "Frontend Engineer"}


@respx.mock
async def test_list_jobs_filters_by_keyword(client, remoteok_api_fixture):
    respx.get(REMOTEOK_API_URL).mock(return_value=Response(200, json=remoteok_api_fixture))
    await client.post("/api/v1/jobs/ingest/remoteok")

    response = await client.get("/api/v1/jobs", params={"q": "backend"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title_raw"] == "Senior Backend Engineer"


async def test_list_jobs_rejects_invalid_limit(client):
    response = await client.get("/api/v1/jobs", params={"limit": 0})

    assert response.status_code == 422


async def test_trigger_enrichment_returns_pipeline_result(client, monkeypatch):
    async def fake_enrich_pending_jobs(db, limit=None):
        return EnrichResult(processed=3, enriched=2, failed=1)

    monkeypatch.setattr(jobs_api, "enrich_pending_jobs", fake_enrich_pending_jobs)

    response = await client.post("/api/v1/jobs/enrich")

    assert response.status_code == 200
    assert response.json() == {"processed": 3, "enriched": 2, "failed": 1}
