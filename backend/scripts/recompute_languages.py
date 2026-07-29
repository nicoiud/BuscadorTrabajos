"""Recalcula el campo `language` de los avisos ya guardados en la base.

Uso puntual: RemoteOK solo expone los ~100 avisos más recientes en su API, así que
`POST /jobs/ingest/remoteok` nunca vuelve a tocar avisos que ya salieron de esa
ventana — quedan para siempre con el idioma que tenían la última vez que se
ingirieron. Este script recalcula `language` para TODOS los avisos existentes usando
la detección real (`detect_job_language`), sin depender de volver a pegarle a
RemoteOK. Pensado para correrse una sola vez después de agregar la detección real de
idioma (antes mandaba "en" hardcodeado para todo).

Correr desde `backend/`, con el mismo entorno/`.env` que usa la app:
    python scripts/recompute_languages.py
"""
import asyncio

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.job_posting import JobPosting
from app.services.ingestion.language_detection import detect_job_language


async def main() -> None:
    async with async_session_factory() as db:
        jobs = (await db.execute(select(JobPosting))).scalars().all()
        changed = 0
        for job in jobs:
            detected = detect_job_language(job.title_raw, job.description_raw)
            if detected != job.language:
                job.language = detected
                changed += 1
        await db.commit()
        print(f"Revisados {len(jobs)} avisos, {changed} con idioma corregido.")


if __name__ == "__main__":
    asyncio.run(main())
