"""Limpia HTML crudo y repara mojibake en los avisos ya guardados en la base.

Uso puntual: se agregó limpieza de HTML (tags/entidades como `<br>`, `&amp;`) y
reparo de mojibake (`ftfy`) a la ingestion de RemoteOK, pero eso solo aplica a
avisos nuevos o re-ingeridos. Este script recalcula `title_raw`, `company_raw`,
`description_raw` y `location_raw` de TODOS los avisos ya existentes a partir de
esos mismos valores guardados, sin depender de volver a pegarle a RemoteOK.

Correr desde `backend/`, con el mismo entorno/`.env` que usa la app:
    python scripts/clean_raw_text.py
"""
import asyncio

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.job_posting import JobPosting
from app.services.ingestion.text_cleaning import clean_raw_text, clean_raw_text_inline


async def main() -> None:
    async with async_session_factory() as db:
        jobs = (await db.execute(select(JobPosting))).scalars().all()
        changed = 0
        for job in jobs:
            new_title = clean_raw_text_inline(job.title_raw)
            new_company = clean_raw_text_inline(job.company_raw)
            new_description = clean_raw_text(job.description_raw)
            new_location = clean_raw_text_inline(job.location_raw) if job.location_raw else None

            if (
                new_title != job.title_raw
                or new_company != job.company_raw
                or new_description != job.description_raw
                or new_location != job.location_raw
            ):
                job.title_raw = new_title
                job.company_raw = new_company
                job.description_raw = new_description
                job.location_raw = new_location or None
                changed += 1

        await db.commit()
        print(f"Revisados {len(jobs)} avisos, {changed} con texto limpiado.")


if __name__ == "__main__":
    asyncio.run(main())
