"""Marca como `pending` los avisos ya enriquecidos, para que se vuelvan a analizar.

Uso puntual: se encontraron y arreglaron dos bugs en `extractor.py` (un modelo local
débil vía Ollama a veces devolvía el propio JSON del schema de la tool como valor de
`title_normalized`/`company_normalized`, y `requirements` como un string en vez de un
array real, lo que lo explotaba en caracteres sueltos). Los avisos ya procesados con
el bug activo quedaron con `title_normalized`/`summary`/`requirements` contaminados,
lo que además arruina el embedding usado por la búsqueda semántica (se genera texto
a partir de esos mismos campos). `POST /jobs/enrich` solo toca avisos `pending`, así
que no se corrigen solos — este script los resetea para que la próxima corrida de
"Analizar con IA" los vuelva a procesar con el extractor ya arreglado.

Por default resetea TODOS los avisos con enrichment_status != pending (done o
failed). Pasar --only-suspicious para resetear solo los que tienen la firma del bug
(campos de texto que arrancan con "{" tipo JSON, o algún item de requirements de un
solo carácter) en vez de todos.

Correr desde `backend/`, con el mismo entorno/`.env` que usa la app:
    python scripts/reset_enrichment.py
    python scripts/reset_enrichment.py --only-suspicious
"""
import asyncio
import sys

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.job_posting import EnrichmentStatus, JobPosting


def _looks_corrupted(job: JobPosting) -> bool:
    for field in (job.title_normalized, job.company_normalized, job.summary):
        if isinstance(field, str) and field.strip().startswith("{"):
            return True
    if job.requirements and any(
        isinstance(r, str) and len(r.strip()) <= 1 for r in job.requirements
    ):
        return True
    return False


async def main(only_suspicious: bool) -> None:
    async with async_session_factory() as db:
        jobs = (
            (await db.execute(select(JobPosting).where(JobPosting.enrichment_status != EnrichmentStatus.PENDING)))
            .scalars()
            .all()
        )
        reset = 0
        for job in jobs:
            if only_suspicious and not _looks_corrupted(job):
                continue
            job.enrichment_status = EnrichmentStatus.PENDING
            job.title_normalized = None
            job.company_normalized = None
            job.seniority = None
            job.modality = None
            job.salary_min = None
            job.salary_max = None
            job.currency = None
            job.requirements = None
            job.summary = None
            job.embedding = None
            job.enrichment_model = None
            reset += 1
        await db.commit()
        print(f"Revisados {len(jobs)} avisos ya procesados, {reset} vueltos a 'pending'.")


if __name__ == "__main__":
    asyncio.run(main(only_suspicious="--only-suspicious" in sys.argv))
