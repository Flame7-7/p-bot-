from __future__ import annotations

import re
import string
from dataclasses import dataclass

import discord

from models.models import CustomCommand

COMMAND_NAME_RE = re.compile(r"^[a-z0-9_-]{1,32}$")
KNOWN_PLACEHOLDERS = {
    "user",
    "author",
    "mention",
    "target",
    "target_mention",
    "server",
}
MAX_RESPONSE_LENGTH = 2000


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    error: str | None = None


def validate_name(name: str) -> ValidationResult:
    if not COMMAND_NAME_RE.fullmatch(name):
        return ValidationResult(
            False,
            "Command names must be 1-32 characters and use only lowercase letters, numbers, `_`, or `-`.",
        )
    return ValidationResult(True)


def validate_response(response: str) -> ValidationResult:
    if not response.strip():
        return ValidationResult(False, "The response cannot be empty.")
    if len(response) > MAX_RESPONSE_LENGTH:
        return ValidationResult(False, "The response must be 2000 characters or fewer.")
    try:
        for _, field_name, _, _ in string.Formatter().parse(response):
            if field_name and field_name not in KNOWN_PLACEHOLDERS:
                return ValidationResult(False, f"Unknown placeholder `{{{field_name}}}`.")
    except ValueError as exc:
        return ValidationResult(False, f"Invalid placeholder syntax: {exc}")
    return ValidationResult(True)


def render_response(
    command: CustomCommand,
    interaction: discord.Interaction,
    target: discord.Member | None,
) -> str:
    if command.requires_target and target is None:
        raise ValueError("This custom command requires a target. Use the target option.")

    values = {
        "user": interaction.user.display_name,
        "author": interaction.user.display_name,
        "mention": interaction.user.mention,
        "target": target.display_name if target else "",
        "target_mention": target.mention if target else "",
        "server": interaction.guild.name if interaction.guild else "",
    }

    try:
        return command.response.format(**values)
    except (KeyError, ValueError, IndexError) as exc:
        raise ValueError(f"Invalid response template: {exc}") from exc
