import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import JobPosting, Source  # noqa: F401  (register on Base.metadata)
from app.services.enrichment import llm_client


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


# --- Fakes for the OpenAI-compatible chat completions client (llm_client.py) ---
# Groq/NVIDIA/OpenAI all share this response shape, so one fake covers all of them.


@dataclass
class FakeFunctionCall:
    arguments: str
    name: str = "unused"


@dataclass
class FakeToolCall:
    function: FakeFunctionCall


@dataclass
class FakeChoiceMessage:
    content: str | None = None
    tool_calls: list[FakeToolCall] | None = None


@dataclass
class FakeChoice:
    message: FakeChoiceMessage


@dataclass
class FakeChatCompletion:
    choices: list[FakeChoice] = field(default_factory=list)


class FakeChatCompletions:
    def __init__(self, response: FakeChatCompletion):
        self._response = response

    async def create(self, **kwargs: Any) -> FakeChatCompletion:
        return self._response


class FakeChat:
    def __init__(self, response: FakeChatCompletion):
        self.completions = FakeChatCompletions(response)


class FakeOpenAIClient:
    def __init__(self, response: FakeChatCompletion):
        self.chat = FakeChat(response)


def tool_call_response(arguments: dict) -> FakeChatCompletion:
    return FakeChatCompletion(
        choices=[
            FakeChoice(
                message=FakeChoiceMessage(
                    tool_calls=[FakeToolCall(function=FakeFunctionCall(arguments=json.dumps(arguments)))]
                )
            )
        ]
    )


def text_response(text: str) -> FakeChatCompletion:
    return FakeChatCompletion(choices=[FakeChoice(message=FakeChoiceMessage(content=text))])


def empty_response() -> FakeChatCompletion:
    return FakeChatCompletion(choices=[FakeChoice(message=FakeChoiceMessage())])


@pytest.fixture
def patch_llm(monkeypatch):
    def _patch(response: FakeChatCompletion) -> None:
        monkeypatch.setattr(llm_client, "get_client", lambda: FakeOpenAIClient(response))

    return _patch


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
