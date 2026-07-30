import httpx
import respx
from httpx import Response
from sqlalchemy import select

from app.models.job_posting import JobPosting
from app.models.source import Source
from app.services.ingestion.greenhouse import GREENHOUSE_API_URL
from app.services.ingestion.lever import LEVER_API_URL
from app.services.ingestion.remoteok import REMOTEOK_API_URL, RemoteOkAdapter
from app.services.ingestion.runner import ingest_all_sources, ingest_source


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


@respx.mock
async def test_ingest_source_skips_disabled_source(db_session, remoteok_api_fixture):
    respx.get(REMOTEOK_API_URL).mock(return_value=Response(200, json=remoteok_api_fixture))
    await ingest_source(db_session, RemoteOkAdapter())

    source = (await db_session.execute(select(Source).where(Source.slug == "remoteok"))).scalar_one()
    source.enabled = False
    await db_session.commit()

    result = await ingest_source(db_session, RemoteOkAdapter())

    assert result.fetched == 0
    assert result.created == 0
    assert result.updated == 0
    assert result.error == "fuente deshabilitada"


@respx.mock
async def test_ingest_all_sources_runs_remoteok_plus_configured_companies(
    db_session, remoteok_api_fixture, monkeypatch
):
    from app.services.ingestion import runner as runner_module

    monkeypatch.setattr(runner_module.settings, "greenhouse_boards", "acme")
    monkeypatch.setattr(runner_module.settings, "lever_companies", "widgetco")

    respx.get(REMOTEOK_API_URL).mock(return_value=Response(200, json=remoteok_api_fixture))
    respx.get(GREENHOUSE_API_URL.format(board="acme")).mock(
        return_value=Response(
            200,
            json={
                "jobs": [
                    {
                        "id": 1,
                        "title": "Backend Engineer",
                        "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
                    }
                ]
            },
        )
    )
    respx.get(LEVER_API_URL.format(company="widgetco")).mock(
        return_value=Response(
            200,
            json=[
                {
                    "id": "w1",
                    "text": "Support Engineer",
                    "hostedUrl": "https://jobs.lever.co/widgetco/w1",
                }
            ],
        )
    )

    results = await ingest_all_sources(db_session)

    slugs = {r.source_slug for r in results}
    assert slugs == {"remoteok", "greenhouse-acme", "lever-widgetco"}
    assert all(r.error is None for r in results)

    rows = (await db_session.execute(select(JobPosting))).scalars().all()
    assert len(rows) == 4  # 2 de remoteok + 1 de greenhouse + 1 de lever


@respx.mock
async def test_ingest_all_sources_isolates_a_failing_source(
    db_session, remoteok_api_fixture, monkeypatch
):
    from app.services.ingestion import runner as runner_module

    monkeypatch.setattr(runner_module.settings, "greenhouse_boards", "broken-board")
    monkeypatch.setattr(runner_module.settings, "lever_companies", "")

    respx.get(REMOTEOK_API_URL).mock(return_value=Response(200, json=remoteok_api_fixture))
    respx.get(GREENHOUSE_API_URL.format(board="broken-board")).mock(
        side_effect=httpx.ConnectError("simulated network failure")
    )

    results = await ingest_all_sources(db_session)

    by_slug = {r.source_slug: r for r in results}
    assert by_slug["remoteok"].error is None
    assert by_slug["remoteok"].created == 2
    assert by_slug["greenhouse-broken-board"].error is not None

    rows = (await db_session.execute(select(JobPosting))).scalars().all()
    assert len(rows) == 2  # el fallo de greenhouse no perdió lo que sí entró de remoteok
