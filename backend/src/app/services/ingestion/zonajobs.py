import asyncio
import logging
from datetime import UTC, datetime

import httpx

from app.core.config import settings
from app.models.job_posting import JobLanguage, JobRegion
from app.models.source import SourceLanguage, SourceRegion, SourceType
from app.services.ingestion.base import RawJobPosting, SourceAdapter
from app.services.ingestion.text_cleaning import clean_raw_text, clean_raw_text_inline

logger = logging.getLogger(__name__)

ZONAJOBS_BASE_URL = "https://www.zonajobs.com.ar"
ZONAJOBS_SEARCH_URL = f"{ZONAJOBS_BASE_URL}/api/avisos/searchV2"
ZONAJOBS_DETAIL_URL = f"{ZONAJOBS_BASE_URL}/api/candidates/fichaAvisoNormalizada/{{job_id}}"


def _parse_posted_at(aviso: dict) -> datetime | None:
    fecha_hora = aviso.get("fechaHoraPublicacion")
    if fecha_hora:
        try:
            return datetime.strptime(fecha_hora, "%d-%m-%Y %H:%M:%S").replace(tzinfo=UTC)
        except ValueError:
            pass
    fecha = aviso.get("fechaPublicacion")
    if fecha:
        try:
            return datetime.strptime(fecha, "%d-%m-%Y").replace(tzinfo=UTC)
        except ValueError:
            pass
    return None


class ZonaJobsAdapter(SourceAdapter):
    """ZonaJobs (Argentina) no tiene API pública documentada, pero su propio
    frontend (una SPA) consume una API JSON interna para listar y mostrar avisos —
    encontrada inspeccionando el tráfico de red del sitio, no scrapeando HTML.
    `robots.txt` no la bloquea (los `Disallow` son sobre parámetros puntuales de las
    páginas de búsqueda clásicas, no sobre este path). Mismo `SITE_ID` en el JS que
    Bumeran, así que probablemente comparta la misma API (pendiente de confirmar).
    """

    slug = "zonajobs"
    source_type = SourceType.SCRAPE
    source_region = SourceRegion.LATAM
    source_language = SourceLanguage.ES

    def __init__(self, page_size: int = 20):
        self.page_size = page_size

    async def fetch(self) -> list[RawJobPosting]:
        headers = {"User-Agent": settings.scraper_user_agent, "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                ZONAJOBS_SEARCH_URL,
                params={"pageSize": self.page_size, "page": 0, "sort": "RELEVANTES"},
                headers=headers,
            )
            response.raise_for_status()
            listing = response.json()

            postings: list[RawJobPosting] = []
            items = listing.get("content", [])
            for i, item in enumerate(items):
                if i > 0:
                    # Respeta el rate limit configurado — el listado es un solo
                    # pedido, pero la URL "linda" de cada aviso requiere un pedido
                    # de detalle por aviso.
                    await asyncio.sleep(settings.scraper_default_delay_seconds)
                posting = await self._fetch_detail(client, headers, item)
                if posting is not None:
                    postings.append(posting)

        return postings

    async def _fetch_detail(
        self, client: httpx.AsyncClient, headers: dict, item: dict
    ) -> RawJobPosting | None:
        job_id = item.get("id")
        if job_id is None:
            return None

        aviso: dict = {}
        try:
            response = await client.get(ZONAJOBS_DETAIL_URL.format(job_id=job_id), headers=headers)
            response.raise_for_status()
            detail = response.json()
            aviso = ((detail.get("aviso") or {}).get("aviso")) or {}
        except Exception:
            # Sin el detalle no tenemos la URL linda del aviso, pero el listado ya
            # trae todo lo demás — se arma la URL con el ID como fallback en vez de
            # perder el aviso entero.
            logger.warning(
                "No se pudo traer el detalle del aviso %s de ZonaJobs", job_id, exc_info=True
            )

        title = clean_raw_text_inline(aviso.get("titulo") or item.get("titulo", ""))

        empresa = aviso.get("empresa")
        company_raw = empresa.get("denominacion") if isinstance(empresa, dict) else None
        company = clean_raw_text_inline(company_raw or item.get("empresa") or "") or "Confidencial"

        description = clean_raw_text(aviso.get("descripcion") or item.get("detalle") or "")

        localizacion = aviso.get("localizacion")
        location_raw = (
            localizacion.get("detalle") if isinstance(localizacion, dict) else None
        ) or item.get("localizacion")
        location = clean_raw_text_inline(location_raw) if location_raw else None

        seo_url = aviso.get("seoFriendlyUrl")
        url = f"{ZONAJOBS_BASE_URL}{seo_url}" if seo_url else f"{ZONAJOBS_BASE_URL}/empleos.html?aviso={job_id}"

        return RawJobPosting(
            external_id=str(job_id),
            url=url,
            title=title,
            company=company,
            description=description,
            # ZonaJobs es un sitio local de Argentina, a diferencia de RemoteOK
            # (internacional) — acá sí se puede asumir español sin detectar.
            language=JobLanguage.ES,
            region=JobRegion.LATAM,
            location=location,
            posted_at=_parse_posted_at(aviso or item),
        )
