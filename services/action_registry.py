from __future__ import annotations

import random
from dataclasses import dataclass

from utils.content import load_records
from utils.logging import get_logger

logger = get_logger(__name__)


# Role/gender -> (subject, object, possessive) pronoun forms, e.g.
# "{author_pronoun} blushed" / "kissed {target_pronoun_obj}" / "hugged
# {target_possessive} friend". Keyed by the same values
# RoleplayProfileRepository.VALID_GENDERS accepts, plus a neutral fallback
# used whenever a user hasn't run /role (or picked non-binary).
PRONOUNS: dict[str, dict[str, str]] = {
    "male": {"subject": "he", "object": "him", "possessive": "his"},
    "female": {"subject": "she", "object": "her", "possessive": "her"},
    "non-binary": {"subject": "they", "object": "them", "possessive": "their"},
    "neutral": {"subject": "they", "object": "them", "possessive": "their"},
}


@dataclass
class ActionConfig:
    name: str
    category: str
    affection_gain: int
    xp_gain: int
    response_templates: list[str]
    gif_category: str
    self_targetable: bool = False
    requires_target: bool = True
    description: str = ""

    def get_response(
        self,
        author: str,
        target: str | None = None,
        author_gender: str | None = None,
        target_gender: str | None = None,
        author_mention: str | None = None,
        target_mention: str | None = None,
    ) -> str:
        """Renders a random response template.

        `author_gender`/`target_gender` are optional role selections from
        /role (one of PRONOUNS' keys).

        `author_mention`/`target_mention` should contain Discord mention
        strings such as ``<@123456789>``. When supplied, the existing
        `{author}` and `{target}` placeholders render those mentions instead
        of plain display names, so Discord will notify the tagged users.

        This keeps all existing response templates unchanged and remains
        backward compatible: if mention values are not supplied, the
        original display-name behavior is used.
        """
        template = random.choice(self.response_templates)

        author_p = PRONOUNS.get(
            author_gender or "neutral",
            PRONOUNS["neutral"],
        )
        target_p = PRONOUNS.get(
            target_gender or "neutral",
            PRONOUNS["neutral"],
        )

        # Use real Discord mentions when the caller provides them.
        # Example: <@123456789> instead of "Ayush".
        rendered_author = author_mention or author
        rendered_target = target_mention or target or author_mention or author
        # Alias used by target-first response templates.
        rendered_target_mention = rendered_target

        return template.format(
            author=rendered_author,
            target=rendered_target,
            target_mention=rendered_target_mention,
            author_pronoun=author_p["subject"],
            author_pronoun_obj=author_p["object"],
            author_possessive=author_p["possessive"],
            target_pronoun=target_p["subject"],
            target_pronoun_obj=target_p["object"],
            target_possessive=target_p["possessive"],
        )


_registry: dict[str, ActionConfig] = {}


def register(config: ActionConfig) -> None:
    _registry[config.name] = config


def get_action(name: str) -> ActionConfig | None:
    return _registry.get(name)


def get_all_actions() -> dict[str, ActionConfig]:
    return dict(_registry)


def get_by_category(category: str) -> list[ActionConfig]:
    return [a for a in _registry.values() if a.category == category]

# Content lives in content/roleplay/*.md (see utils/content.py for the format).
ACTION_FILES = ("roleplay/actions.md", "roleplay/intimate.md")


def _to_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except ValueError:
        return default


def load_actions() -> None:
    """(Re)load every action from the Markdown content files."""
    _registry.clear()
    for path in ACTION_FILES:
        for rec in load_records(path).values():
            if not rec.items:
                logger.warning("action %r in %s has no response templates; skipped", rec.name, path)
                continue
            meta = rec.meta
            register(ActionConfig(
                name=rec.name,
                category=meta.get("category", "social"),
                affection_gain=_to_int(meta.get("affection"), 2),
                xp_gain=_to_int(meta.get("xp"), 5),
                response_templates=list(rec.items),
                gif_category=meta.get("gif", rec.name),
                self_targetable=meta.get("self", "no").lower() == "yes",
                requires_target=meta.get("target", "required").lower() != "optional",
                description=meta.get("description", ""),
            ))
    logger.info("loaded %d roleplay actions", len(_registry))


load_actions()
