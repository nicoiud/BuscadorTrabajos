import respx
from httpx import Response
from sqlalchemy import select

from app.api.v1 import jobs as jobs_api
from app.models.job_posting import EnrichmentStatus, JobPosting
from app.services.enrichment.cover_letter import CoverLetterDraft
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


@respx.mock
async def test_list_jobs_filters_by_enrichment_status(client, db_session, remoteok_api_fixture):
    respx.get(REMOTEOK_API_URL).mock(return_value=Response(200, json=remoteok_api_fixture))
    await client.post("/api/v1/jobs/ingest/remoteok")

    jobs = (await db_session.execute(select(JobPosting))).scalars().all()
    jobs[0].enrichment_status = EnrichmentStatus.DONE
    await db_session.commit()

    response = await client.get("/api/v1/jobs", params={"enrichment_status": "done"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["enrichment_status"] == "done"


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


@respx.mock
async def test_generate_cover_letter_for_existing_job(client, remoteok_api_fixture, monkeypatch):
    respx.get(REMOTEOK_API_URL).mock(return_value=Response(200, json=remoteok_api_fixture))
    await client.post("/api/v1/jobs/ingest/remoteok")
    jobs = (await client.get("/api/v1/jobs")).json()["items"]
    job_id = jobs[0]["id"]

    async def fake_generate_cover_letter(title, company, description, profile_text):
        assert profile_text == "Soy dev Python senior con 5 años de experiencia."
        return CoverLetterDraft(cover_letter="Estimados, ...", key_points=["Punto 1", "Punto 2"])

    monkeypatch.setattr(jobs_api, "generate_cover_letter", fake_generate_cover_letter)

    response = await client.post(
        f"/api/v1/jobs/{job_id}/cover-letter",
        json={"profile_text": "Soy dev Python senior con 5 años de experiencia."},
    )

    assert response.status_code == 200
    assert response.json() == {"cover_letter": "Estimados, ...", "key_points": ["Punto 1", "Punto 2"]}


async def test_generate_cover_letter_404_for_unknown_job(client):
    response = await client.post(
        "/api/v1/jobs/00000000-0000-0000-0000-000000000000/cover-letter",
        json={"profile_text": "Perfil"},
    )

    assert response.status_code == 404
