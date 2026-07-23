import json

from openai import AsyncOpenAI

from app.core.config import settings


class LLMError(Exception):
    pass


def get_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)


async def call_with_tool(
    system_prompt: str, user_message: str, tool_name: str, tool_schema: dict
) -> dict:
    """Fuerza al modelo a llamar una función/tool y devuelve sus argumentos ya parseados.

    Funciona contra cualquier endpoint compatible con la Chat Completions API de
    OpenAI (Groq, NVIDIA API Catalog, OpenAI, etc.) — el formato de tool calling es el
    mismo en los tres.
    """
    client = get_client()
    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_schema.get("description", ""),
                    "parameters": tool_schema["parameters"],
                },
            }
        ],
        tool_choice={"type": "function", "function": {"name": tool_name}},
    )

    tool_calls = response.choices[0].message.tool_calls
    if not tool_calls:
        raise LLMError("El modelo no devolvió una llamada a la función esperada.")

    try:
        return json.loads(tool_calls[0].function.arguments)
    except (json.JSONDecodeError, AttributeError, IndexError) as exc:
        raise LLMError(f"No se pudo parsear la respuesta del modelo: {exc}") from exc


async def call_text(system_prompt: str, user_message: str, max_tokens: int = 500) -> str:
    client = get_client()
    response = await client.chat.completions.create(
        model=settings.llm_model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    content = response.choices[0].message.content
    return content.strip() if content else ""
