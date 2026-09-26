from __future__ import annotations

from services.gif_service import get_http_session
from utils.config import get_config
from utils.logging import get_logger

logger = get_logger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Free-tier Groq model. Fast and good enough for short in-voice texts.
# Swap for "llama-3.1-8b-instant" if you want even faster/cheaper replies,
# or check https://console.groq.com/docs/models for current free models.
MODEL = "openai/gpt-oss-120b"


async def generate_persona_reply(
    persona_text: str, history: list[dict], incoming: str
) -> str | None:
    """Generate a short reply in someone's own voice, based on a persona
    description they wrote about themselves. Used to auto-reply to their
    partner's DMs while they're marked AFK (see cogs/dmlink, cogs/persona).

    Returns None if no GROQ_API_KEY is configured or the call fails, so the
    caller can fall back to relaying the raw message instead of silently
    dropping it.
    """
    api_key = get_config().groq_api_key
    if not api_key:
        return None

    system = (
        "You are helping someone auto-reply to a text from their partner "
        "while they're briefly away from their phone. Write ONE short reply "
        "in first person, in this person's own words and texting style, as "
        "described below. Keep it brief and natural, like a real text "
        "(usually 1-3 short sentences) — not a formal or robotic message.\n\n"
        f"How this person talks, and anything else about them:\n{persona_text.strip()}"
    )

    messages = [{"role": "system", "content": system}, *history, {"role": "user", "content": incoming}]

    session = get_http_session()
    try:
        async with session.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": MODEL, "messages": messages, "max_tokens": 300, "temperature": 0.9},
            timeout=20,
        ) as resp:
            if resp.status != 200:
                logger.error("groq api error %s: %s", resp.status, await resp.text())
                return None
            data = await resp.json()
            text = data["choices"][0]["message"]["content"].strip()
            return text or None
    except Exception:
        logger.exception("persona reply generation failed")
        return None
