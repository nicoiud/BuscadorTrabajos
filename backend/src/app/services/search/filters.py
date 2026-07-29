from sqlalchemy import ColumnElement, or_

from app.models.job_posting import JobLanguage, JobPosting, Modality


def build_job_filters(
    languages: list[JobLanguage] | None = None,
    onsite_location: str | None = None,
) -> list[ColumnElement[bool]]:
    """Filtros de preferencia de búsqueda, compartidos entre `/jobs` y `/search`.

    - `languages`: si viene con valores, solo devuelve avisos en esos idiomas. Vacío
      o None = sin restricción.
    - `onsite_location`: si un aviso es presencial (`modality=onsite`), solo lo deja
      pasar si `location_raw` contiene este texto. No afecta avisos remotos/híbridos
      ni avisos sin modalidad determinada todavía (enrichment pendiente).
    """
    filters: list[ColumnElement[bool]] = []

    if languages:
        filters.append(JobPosting.language.in_(languages))

    if onsite_location and onsite_location.strip():
        like = f"%{onsite_location.strip()}%"
        filters.append(
            or_(
                JobPosting.modality.is_(None),
                JobPosting.modality != Modality.ONSITE,
                JobPosting.location_raw.ilike(like),
            )
        )

    return filters
