import respx
from httpx import Response
from sqlalchemy import select

from app.models.job_posting import JobPosting
from app.services.ingestion.remoteok import REMOTEOK_API_URL, RemoteOkAdapter
from app.services.ingestion.runner import ingest_source


@respx.mock
async def test_ingest_source_creates_jobs_on_first_run(db_session, remoteok_api_fixture):
    respx.get(REMOTEOK_API_URL).mock(return_value=Response(200, json=remoteok_api_fixture))

    result = await ingest_source(db_session, RemoteOkAdapter())

    assert result.fetched == 2
    assert result.created == 2
    assert result.updated == 0

    rows = (await db_session.execute(select(JobPosting))).scalars().all()
    assert len(rows) == 2


@respx.mock
async def test_ingest_source_is_idempotent_on_rerun(db_session, remoteok_api_fixture):
    respx.get(REMOTEOK_API_URL).mock(return_value=Response(200, json=remoteok_api_fixture))

    await ingest_source(db_session, RemoteOkAdapter())
    second_result = await ingest_source(db_session, RemoteOkAdapter())

    assert second_result.created == 0
    assert second_result.updated == 2

    rows = (await db_session.execute(select(JobPosting))).scalars().all()
    assert len(rows) == 2  # no duplicates from (source_id, external_id) dedup


@respx.mock
async def test_ingest_source_updates_changed_fields(db_session, remoteok_api_fixture):
    respx.get(REMOTEOK_API_URL).mock(return_value=Response(200, json=remoteok_api_fixture))
    await ingest_source(db_session, RemoteOkAdapter())

    updated_fixture = [dict(entry) for entry in remoteok_api_fixture]
    updated_fixture[1]["position"] = "Staff Frontend Engineer"
    respx.get(REMOTEOK_API_URL).mock(return_value=Response(200, json=updated_fixture))

    await ingest_source(db_session, RemoteOkAdapter())

    rows = (await db_session.execute(select(JobPosting))).scalars().all()
    titles = {row.title_raw for row in rows}
    assert "Staff Frontend Engineer" in titles
