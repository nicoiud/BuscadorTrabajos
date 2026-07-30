import pytest
import respx
from httpx import Response

from app.core.config import settings
from app.models.job_posting import JobLanguage, JobRegion
from app.services.ingestion.zonajobs import (
    ZONAJOBS_DETAIL_URL,
    ZONAJOBS_SEARCH_URL,
    ZonaJobsAdapter,
)


@pytest.fixture(autouse=True)
def _no_rate_limit_delay(monkeypatch):
    monkeypatch.setattr(settings, "scraper_default_delay_seconds", 0.0)

_LISTING_PAYLOAD = {
    "content": [
        {
            "id": 2186963,
            "titulo": "Analista Técnico Funcional de Macrosoluciones - Híbrido",
            "detalle": "Buscamos un analista funcional con experiencia.",
            "empresa": "Aliantec",
            "localizacion": "Capital Federal, Buenos Aires",
            "modalidadTrabajo": "Híbrido",
            "fechaPublicacion": "29-07-2026",
            "fechaHoraPublicacion": "29-07-2026 19:57:38",
        },
        {
            "id": 2186926,
            "titulo": "Analista funcional Jr",
            "detalle": "Buscamos una persona junior.",
            "empresa": "Confidencial",
            "localizacion": "Ramos Mejía, Buenos Aires",
            "modalidadTrabajo": "Presencial",
            "fechaPublicacion": "29-07-2026",
            "fechaHoraPublicacion": "29-07-2026 12:46:13",
        },
    ],
    "number": 0,
    "size": 20,
    "total": 2,
}


def _detail_payload(job_id: int, **overrides) -> dict:
    aviso = {
        "id": job_id,
        "titulo": "Analista Técnico Funcional de Macrosoluciones - Híbrido",
        "descripcion": "<p><strong>Buscamos</strong> un analista funcional.</p>",
        "empresa": {"denominacion": "Aliantec", "ciudad": "Capital Federal"},
        "localizacion": {"detalle": "Capital Federal, Buenos Aires, Argentina"},
        "modalidadTrabajo": {"nombre": "Híbrido", "idSemantico": "hibrido"},
        "nivelLaboral": {"nombre": "Senior", "idSemantico": "senior"},
        "fechaPublicacion": "29-07-2026",
        "fechaHoraPublicacion": "29-07-2026 19:57:38",
        "seoFriendlyUrl": f"/empleos/analista-tecnico-funcional-hibrido-aliantec-{job_id}.html",
        "estado": "activo",
    }
    aviso.update(overrides)
    return {"aviso": {"aviso": aviso, "avisosSimilares": []}, "productoLookAndFeel": None}


@respx.mock
async def test_fetch_combines_listing_and_detail():
    respx.get(ZONAJOBS_SEARCH_URL).mock(return_value=Response(200, json=_LISTING_PAYLOAD))
    respx.get(ZONAJOBS_DETAIL_URL.format(job_id=2186963)).mock(
        return_value=Response(200, json=_detail_payload(2186963))
    )
    respx.get(ZONAJOBS_DETAIL_URL.format(job_id=2186926)).mock(
        return_value=Response(
            200,
            json=_detail_payload(
                2186926,
                titulo="Analista funcional Jr",
                empresa={"denominacion": "Confidencial"},
                seoFriendlyUrl="/empleos/analista-funcional-jr-2186926.html",
            ),
        )
    )

    postings = await ZonaJobsAdapter(page_size=20).fetch()

    assert len(postings) == 2
    first = postings[0]
    assert first.external_id == "2186963"
    assert first.title == "Analista Técnico Funcional de Macrosoluciones - Híbrido"
    assert first.company == "Aliantec"
    assert "<" not in first.description
    assert "Buscamos un analista funcional." in first.description
    assert first.location == "Capital Federal, Buenos Aires, Argentina"
    assert first.url == (
        "https://www.zonajobs.com.ar/empleos/"
        "analista-tecnico-funcional-hibrido-aliantec-2186963.html"
    )
    assert first.language == JobLanguage.ES
    assert first.region == JobRegion.LATAM
    assert first.posted_at is not None


@respx.mock
async def test_fetch_falls_back_to_listing_fields_when_detail_request_fails():
    respx.get(ZONAJOBS_SEARCH_URL).mock(return_value=Response(200, json=_LISTING_PAYLOAD))
    respx.get(ZONAJOBS_DETAIL_URL.format(job_id=2186963)).mock(return_value=Response(500))
    respx.get(ZONAJOBS_DETAIL_URL.format(job_id=2186926)).mock(
        return_value=Response(200, json=_detail_payload(2186926))
    )

    postings = await ZonaJobsAdapter(page_size=20).fetch()

    # No se pierde el aviso aunque falle su detalle — usa lo que ya trajo el listado.
    assert len(postings) == 2
    broken = next(p for p in postings if p.external_id == "2186963")
    assert broken.title == "Analista Técnico Funcional de Macrosoluciones - Híbrido"
    assert broken.company == "Aliantec"
    assert broken.url == "https://www.zonajobs.com.ar/empleos.html?aviso=2186963"


@respx.mock
async def test_fetch_defaults_confidential_company_when_missing():
    payload = {
        "content": [
            {
                "id": 1,
                "titulo": "Puesto confidencial",
                "detalle": "desc",
                "empresa": "Confidencial",
                "localizacion": "Buenos Aires",
                "fechaPublicacion": "29-07-2026",
            }
        ]
    }
    respx.get(ZONAJOBS_SEARCH_URL).mock(return_value=Response(200, json=payload))
    respx.get(ZONAJOBS_DETAIL_URL.format(job_id=1)).mock(
        return_value=Response(200, json=_detail_payload(1, empresa={}))
    )

    postings = await ZonaJobsAdapter().fetch()

    assert postings[0].company == "Confidencial"
