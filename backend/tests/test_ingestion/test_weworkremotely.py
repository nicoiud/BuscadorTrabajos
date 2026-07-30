import respx
from httpx import Response

from app.models.job_posting import JobLanguage
from app.services.ingestion.weworkremotely import WeWorkRemotelyAdapter

FEED_URL = "https://weworkremotely.com/categories/remote-programming-jobs.rss"

_SAMPLE_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>We Work Remotely: Remote Programming Jobs</title>
<item>
<title>Acme Inc: Senior Backend Engineer</title>
<link>https://weworkremotely.com/remote-jobs/acme-senior-backend-engineer</link>
<pubDate>Mon, 20 Jul 2026 10:00:00 +0000</pubDate>
<description><![CDATA[<p>Build our <strong>Python</strong> backend.</p>]]></description>
<guid isPermaLink="true">https://weworkremotely.com/remote-jobs/acme-senior-backend-engineer</guid>
</item>
<item>
<title>Frontend Developer Wanted</title>
<link>https://weworkremotely.com/remote-jobs/frontend-developer-wanted</link>
<pubDate>Mon, 20 Jul 2026 09:00:00 +0000</pubDate>
<description><![CDATA[<p>React and TypeScript.</p>]]></description>
<guid isPermaLink="true">https://weworkremotely.com/remote-jobs/frontend-developer-wanted</guid>
</item>
</channel>
</rss>
"""


@respx.mock
async def test_fetch_parses_feed_entries_splitting_company_from_title(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "weworkremotely_feed_urls", FEED_URL)
    respx.get(FEED_URL).mock(return_value=Response(200, content=_SAMPLE_FEED.encode("utf-8")))

    postings = await WeWorkRemotelyAdapter().fetch()

    assert len(postings) == 2
    first = postings[0]
    assert first.company == "Acme Inc"
    assert first.title == "Senior Backend Engineer"
    assert "<" not in first.description
    assert "Build our Python backend." in first.description
    assert first.external_id == "https://weworkremotely.com/remote-jobs/acme-senior-backend-engineer"
    assert first.posted_at is not None
    assert first.language == JobLanguage.EN


@respx.mock
async def test_fetch_falls_back_to_full_title_when_no_company_prefix(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "weworkremotely_feed_urls", FEED_URL)
    respx.get(FEED_URL).mock(return_value=Response(200, content=_SAMPLE_FEED.encode("utf-8")))

    postings = await WeWorkRemotelyAdapter().fetch()

    second = postings[1]
    assert second.title == "Frontend Developer Wanted"
    assert second.company == "Empresa sin especificar"


@respx.mock
async def test_fetch_skips_broken_feed_url_without_failing_the_rest(monkeypatch):
    from app.core.config import settings

    other_url = "https://weworkremotely.com/categories/remote-design-jobs.rss"
    monkeypatch.setattr(settings, "weworkremotely_feed_urls", f"{other_url},{FEED_URL}")
    respx.get(other_url).mock(return_value=Response(500))
    respx.get(FEED_URL).mock(return_value=Response(200, content=_SAMPLE_FEED.encode("utf-8")))

    postings = await WeWorkRemotelyAdapter().fetch()

    assert len(postings) == 2
