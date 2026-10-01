from __future__ import annotations

import aiohttp

from utils.config import get_config
from utils.content import load_text
from utils.http import get_http_session
from utils.logging import get_logger

logger = get_logger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=20)


def build_system_prompt(persona_text: str, owner_name: str, speaker_name: str) -> str:
    template = load_text("persona/system_prompt.md")
    return (
        template.replace("{owner}", owner_name)
        .replace("{speaker}", speaker_name)
        .replace("{persona}", persona_text.strip())
    )


async def generate_persona_reply(
    persona_text: str,
    history: list[dict[str, str]],
    incoming: str,
    *,
    owner_name: str = "this person",
    speaker_name: str = "someone",
) -> str | None:
    """Generate a short reply in someone's own voice from the persona they wrote.

    Returns None if no GROQ_API_KEY is configured or the call fails, so callers
    can stay silent rather than post an error into a channel.
    """
    config = get_config()
    if not config.groq_api_key:
        return None

    messages = [
        {"role": "system", "content": build_system_prompt(persona_text, owner_name, speaker_name)},
        *history,
        {"role": "user", "content": incoming},
    ]
    try:
        async with get_http_session().post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {config.groq_api_key}"},
            json={"model": config.persona_model, "messages": messages, "max_tokens": 300, "temperature": 0.9},
            timeout=REQUEST_TIMEOUT,
        ) as resp:
            if resp.status != 200:
                logger.error("groq api error %s", resp.status)  # body omitted: may echo prompt content
                return None
            data = await resp.json()
            text = (data["choices"][0]["message"]["content"] or "").strip()
            return text[:1900] or None
    except (aiohttp.ClientError, TimeoutError, KeyError, IndexError, ValueError):
        logger.exception("persona reply generation failed")
        return None
