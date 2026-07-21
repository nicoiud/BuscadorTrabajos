from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import JobPosting, Source  # noqa: F401  (register on Base.metadata)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def remoteok_api_fixture() -> list[dict]:
    return [
        {"legal": "https://remoteok.com/legal", "api": "https://remoteok.com/api"},
        {
            "id": "1000001",
            "position": "Senior Backend Engineer",
            "company": "Acme Remote",
            "description": "<p>Build our Python backend.</p>",
            "url": "https://remoteok.com/remote-jobs/1000001",
            "location": "Worldwide",
            "date": "2026-07-15T12:00:00+00:00",
        },
        {
            "id": "1000002",
            "position": "Frontend Engineer",
            "company": "Widget Co",
            "description": "<p>React and TypeScript.</p>",
            "url": "https://remoteok.com/remote-jobs/1000002",
            "location": "Europe",
            "date": "2026-07-16T09:30:00+00:00",
        },
    ]
