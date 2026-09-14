from __future__ import annotations

import random
from dataclasses import dataclass, field


# Role/gender -> (subject, object, possessive) pronoun forms, e.g.
# "{author_pronoun} blushed" / "kissed {target_pronoun_obj}" / "hugged
# {target_possessive} friend". Keyed by the same values
# RoleplayProfileRepository.VALID_GENDERS accepts, plus a neutral fallback
# used whenever a user hasn't run /consent (or picked non-binary).
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
    cooldown_seconds: int
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
        /consent (one of PRONOUNS' keys).

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


# ── Affection (10) ────────────────────────────────────────────────────────────

register(ActionConfig(
    name="hug", category="affection", affection_gain=15, xp_gain=20,
    cooldown_seconds=30, gif_category="hug",
    description="Give someone a warm hug",
    response_templates=[
        "{target_mention} — **{author}** pulled {target_mention} into a warm, tight hug! 🤗",
        "{target_mention} — **{author}** wrapped their arms around {target_mention} and hugged them close! 💕",
        "{target_mention} — **{author}** ran over and gave {target_mention} the biggest hug ever! 🫂",
        "{target_mention} — **{author}** hugged {target_mention} so tightly they almost couldn't breathe!",
        "{target_mention} — **{author}** snuck up behind {target_mention} and gave them a surprise hug! 💖",
        "{target_mention} — **{author}** pulled {target_mention} close, resting {author_possessive} head on {target_possessive} shoulder! 🤗",
    ],
))

register(ActionConfig(
    name="pat", category="affection", affection_gain=10, xp_gain=15,
    cooldown_seconds=30, gif_category="pat",
    description="Pat someone on the head",
    response_templates=[
        "{target_mention} — **{author}** gently patted {target_mention}'s head! 🥺",
        "{target_mention} — **{author}** gave {target_mention} a soft, loving headpat! ✨",
        "{target_mention} — **{author}** reached up and patted {target_mention} with care! 💕",
        "{target_mention} — **{author}** tenderly patted {target_mention}'s head! 🌸",
        "{target_mention} — **{author}** ruffled {target_mention}'s hair with an affectionate pat! 😊",
    ],
))

register(ActionConfig(
    name="kiss", category="affection", affection_gain=15, xp_gain=20,
    cooldown_seconds=30, gif_category="kiss",
    description="Kiss someone",
    response_templates=[
        "{target_mention} — **{author}** gave {target_mention} a sweet kiss! 💋",
        "{target_mention} — **{author}** leaned in and kissed {target_mention} on the cheek! 😘",
        "{target_mention} — **{author}** planted a gentle kiss on {target_mention}'s forehead! 💕",
        "{target_mention} — **{author}** snuck a quick kiss on {target_mention}'s cheek! 🌸",
        "{target_mention} — **{author}** gave {target_mention} a loving kiss! 💖",
    ],
))

register(ActionConfig(
    name="cuddle", category="affection", affection_gain=15, xp_gain=20,
    cooldown_seconds=30, gif_category="cuddle",
    description="Cuddle with someone",
    response_templates=[
        "{target_mention} — **{author}** curled up and cuddled with {target_mention}! 🫂",
        "{target_mention} — **{author}** snuggled close to {target_mention} for a cozy cuddle! 💕",
        "**{target_mention}** and **{author}** cuddled together warmly! 🌸",
        "{target_mention} — **{author}** pulled {target_mention} in for a long, comfortable cuddle! 💖",
        "{target_mention} — **{author}** wrapped themselves around {target_mention} in a cuddle! 🥺",
    ],
))

register(ActionConfig(
    name="poke", category="affection", affection_gain=5, xp_gain=8,
    cooldown_seconds=30, gif_category="poke",
    description="Poke someone",
    response_templates=[
        "{target_mention} — **{author}** poked {target_mention} on the cheek! 👉",
        "{target_mention} — **{author}** jabbed {target_mention} playfully! 😄",
        "{target_mention} — **{author}** kept poking {target_mention} until they noticed! 👀",
        "{target_mention} — **{author}** sneakily poked {target_mention} and ran! 💨",
        "{target_mention} — **{author}** gave {target_mention} a little boop-poke! 🥺",
    ],
))

register(ActionConfig(
    name="boop", category="affection", affection_gain=5, xp_gain=8,
    cooldown_seconds=30, gif_category="boop",
    description="Boop someone on the nose",
    response_templates=[
        "{target_mention} — **{author}** booped {target_mention} on the nose! 👆",
        "{target_mention} — **{author}** reached over and booped {target_mention}'s snoot! 🐾",
        "{target_mention} — **{author}** gave {target_mention} the gentlest nose boop! 💕",
        "{target_mention} — **{author}** *boop* — got {target_mention}'s nose! 😄",
        "{target_mention} — **{author}** sneaked in a surprise boop on {target_mention}! ✨",
    ],
))

register(ActionConfig(
    name="headpat", category="affection", affection_gain=10, xp_gain=15,
    cooldown_seconds=30, gif_category="headpat",
    description="Give someone a headpat",
    response_templates=[
        "{target_mention} — **{author}** gave {target_mention} soft, gentle headpats! 🥺",
        "{target_mention} — **{author}** placed a warm hand on {target_mention}'s head! 💕",
        "{target_mention} — **{author}** headpatted {target_mention} like they deserved it! ✨",
        "{target_mention} — **{author}** ruffled {target_mention}'s hair with tender headpats! 🌸",
        "{target_mention} — **{author}** patted {target_mention}'s head and smiled warmly! 😊",
    ],
))

register(ActionConfig(
    name="nuzzle", category="affection", affection_gain=12, xp_gain=15,
    cooldown_seconds=30, gif_category="nuzzle",
    description="Nuzzle someone affectionately",
    response_templates=[
        "{target_mention} — **{author}** nuzzled up against {target_mention} softly! 🥰",
        "{target_mention} — **{author}** buried their face in {target_mention}'s shoulder with a happy nuzzle! 💕",
        "{target_mention} — **{author}** nuzzled {target_mention} gently! 🌸",
        "{target_mention} — **{author}** pressed their cheek to {target_mention}'s in a sweet nuzzle! ✨",
        "{target_mention} — **{author}** nuzzled {target_mention} and purred contentedly! 😸",
    ],
))

register(ActionConfig(
    name="snuggle", category="affection", affection_gain=13, xp_gain=18,
    cooldown_seconds=30, gif_category="snuggle",
    description="Snuggle with someone",
    response_templates=[
        "{target_mention} — **{author}** snuggled close to {target_mention} warmly! 🫂",
        "{target_mention} — **{author}** wrapped up with {target_mention} in a cozy snuggle! 💕",
        "**{target_mention}** and **{author}** settled in for an adorable snuggle! 🌸",
        "{target_mention} — **{author}** snuggled into {target_mention} like a sleepy puppy! 🐶",
        "{target_mention} — **{author}** pulled {target_mention} into a snuggly embrace! 💖",
    ],
))

register(ActionConfig(
    name="tackle", category="affection", affection_gain=10, xp_gain=15,
    cooldown_seconds=30, gif_category="tackle",
    description="Tackle someone in excitement",
    response_templates=[
        "{target_mention} — **{author}** tackled {target_mention} to the ground in excitement! 💨",
        "{target_mention} — **{author}** sprinted over and tackle-hugged {target_mention}! 🏃",
        "{target_mention} — **{author}** launched themselves at {target_mention} in a flying tackle! 😄",
        "{target_mention} — **{author}** caught {target_mention} off guard with a sudden tackle! 😂",
        "{target_mention} — **{author}** tackled {target_mention} and refused to let go! 🫂",
    ],
))

# ── Playful (8) ───────────────────────────────────────────────────────────────

register(ActionConfig(
    name="slap", category="playful", affection_gain=2, xp_gain=5,
    cooldown_seconds=15, gif_category="slap",
    description="Slap someone playfully",
    response_templates=[
        "{target_mention} — **{author}** slapped {target_mention} with a rubber fish! 🐟",
        "{target_mention} — **{author}** gave {target_mention} a swift smack! 👋",
        "{target_mention} — **{author}** slapped {target_mention} and ran off laughing! 😂",
        "{target_mention} — **{author}** delivered a dramatic slap to {target_mention}! 🎭",
        "{target_mention} — **{author}** slapped {target_mention} out of nowhere! 😤",
    ],
))

register(ActionConfig(
    name="punch", category="playful", affection_gain=2, xp_gain=5,
    cooldown_seconds=15, gif_category="punch",
    description="Punch someone playfully",
    response_templates=[
        "{target_mention} — **{author}** punched {target_mention} in the arm playfully! 👊",
        "{target_mention} — **{author}** threw a light punch at {target_mention}! 🥊",
        "{target_mention} — **{author}** playfully decked {target_mention}! 😤",
        "{target_mention} — **{author}** socked {target_mention} in the shoulder! 💥",
        "{target_mention} — **{author}** gave {target_mention} a friendly punch! 👊",
    ],
))

register(ActionConfig(
    name="kick", category="playful", affection_gain=2, xp_gain=5,
    cooldown_seconds=15, gif_category="kick",
    description="Kick someone playfully",
    response_templates=[
        "{target_mention} — **{author}** kicked {target_mention} playfully! 🦵",
        "{target_mention} — **{author}** launched a kick straight at {target_mention}! 💥",
        "{target_mention} — **{author}** swept {target_mention}'s leg! 🥋",
        "{target_mention} — **{author}** gave {target_mention} a not-so-gentle kick! 😅",
        "{target_mention} — **{author}** kicked {target_mention} and pretended it was an accident! 😂",
    ],
))

register(ActionConfig(
    name="bite", category="playful", affection_gain=5, xp_gain=8,
    cooldown_seconds=15, gif_category="bite",
    description="Bite someone playfully",
    response_templates=[
        "{target_mention} — **{author}** nibbled on {target_mention}'s ear! 👂",
        "{target_mention} — **{author}** chomped down on {target_mention}'s arm! 😬",
        "{target_mention} — **{author}** gave {target_mention} a playful little bite! 🐾",
        "{target_mention} — **{author}** bit {target_mention} like a tiny gremlin! 😈",
        "{target_mention} — **{author}** sank their teeth into {target_mention} — *nom nom*! 🍴",
    ],
))

register(ActionConfig(
    name="lick", category="playful", affection_gain=5, xp_gain=8,
    cooldown_seconds=15, gif_category="lick",
    description="Lick someone",
    response_templates=[
        "{target_mention} — **{author}** licked {target_mention}'s cheek like a happy puppy! 🐶",
        "{target_mention} — **{author}** snuck a big lick on {target_mention}'s face! 😝",
        "{target_mention} — **{author}** gave {target_mention} a surprise lick! 👅",
        "{target_mention} — **{author}** licked {target_mention} — because why not? 😂",
        "{target_mention} — **{author}** taste-tested {target_mention} with a lick! 😋",
    ],
))

register(ActionConfig(
    name="tickle", category="playful", affection_gain=8, xp_gain=10,
    cooldown_seconds=15, gif_category="tickle",
    description="Tickle someone",
    response_templates=[
        "{target_mention} — **{author}** started tickling {target_mention} mercilessly! 😂",
        "{target_mention} — **{author}** found {target_mention}'s tickle spot and attacked! 🎯",
        "{target_mention} — **{author}** wiggled their fingers at {target_mention} then tickled! 😈",
        "{target_mention} — **{author}** tickled {target_mention} until they couldn't breathe! 🤣",
        "{target_mention} — **{author}** ambushed {target_mention} with relentless tickles! 👐",
    ],
))

register(ActionConfig(
    name="pounce", category="playful", affection_gain=8, xp_gain=10,
    cooldown_seconds=15, gif_category="pounce",
    description="Pounce on someone",
    response_templates=[
        "{target_mention} — **{author}** pounced on {target_mention} like a cat! 🐱",
        "{target_mention} — **{author}** launched themselves at {target_mention} with a pounce! 💨",
        "{target_mention} — **{author}** crept silently... then pounced on {target_mention}! 🐆",
        "{target_mention} — **{author}** did a flying pounce straight onto {target_mention}! 🌪️",
        "{target_mention} — **{author}** pounced on {target_mention} and pinned them down! 😄",
    ],
))

register(ActionConfig(
    name="throw", category="playful", affection_gain=3, xp_gain=5,
    cooldown_seconds=15, gif_category="throw",
    description="Throw something at someone",
    response_templates=[
        "{target_mention} — **{author}** lobbed a pillow at {target_mention}! 🛌",
        "{target_mention} — **{author}** threw a snowball at {target_mention}! ❄️",
        "{target_mention} — **{author}** chucked a plushie at {target_mention}'s face! 🧸",
        "{target_mention} — **{author}** hurled a bag of chips at {target_mention}! 🍟",
        "{target_mention} — **{author}** yeeted a random object at {target_mention}! 💥",
    ],
))

# ── Emotional / self-targetable (8) ──────────────────────────────────────────

register(ActionConfig(
    name="cry", category="emotional", affection_gain=1, xp_gain=5,
    cooldown_seconds=15, gif_category="cry",
    self_targetable=True, requires_target=False,
    description="Express that you're crying",
    response_templates=[
        "**{author}** is crying... 😢",
        "**{author}** broke down in tears... 😭",
        "**{author}** started sobbing uncontrollably! 💧",
        "**{author}** is shedding a single dramatic tear... 😤",
        "**{author}** is having a full ugly cry right now! 😭",
        "**{author}** buried {author_possessive} face in {author_pronoun_obj}self and cried! 😢",
    ],
))

register(ActionConfig(
    name="wave", category="emotional", affection_gain=3, xp_gain=5,
    cooldown_seconds=15, gif_category="wave",
    self_targetable=True, requires_target=False,
    description="Wave at someone",
    response_templates=[
        "{target_mention} — **{author}** waves cheerfully at {target_mention}! 👋",
        "{target_mention} — **{author}** waves hello at {target_mention}! 😊",
        "{target_mention} — **{author}** gives {target_mention} an enthusiastic wave! ✋",
        "{target_mention} — **{author}** waves excitedly at {target_mention}! 🙌",
        "{target_mention} — **{author}** does a little wave at {target_mention}! 🌟",
    ],
))

register(ActionConfig(
    name="blush", category="emotional", affection_gain=2, xp_gain=5,
    cooldown_seconds=15, gif_category="blush",
    self_targetable=True, requires_target=False,
    description="Blush",
    response_templates=[
        "**{author}** turns bright red and covers their face! 😳",
        "{target_mention} — **{author}** blushes deeply at {target_mention}! 💕",
        "**{author}**'s cheeks go completely red! 🔴",
        "**{author}** starts blushing furiously! 😖",
        "**{author}** hides their face, blushing hard! 🙈",
        "**{author}** blushed so hard {author_pronoun} had to look away! 😳",
    ],
))

register(ActionConfig(
    name="smile", category="emotional", affection_gain=3, xp_gain=5,
    cooldown_seconds=15, gif_category="smile",
    self_targetable=True, requires_target=False,
    description="Smile warmly",
    response_templates=[
        "{target_mention} — **{author}** gives {target_mention} the most beautiful smile! 😊",
        "{target_mention} — **{author}** smiles warmly at {target_mention}! 🌸",
        "{target_mention} — **{author}** beams a giant smile at {target_mention}! ✨",
        "{target_mention} — **{author}** flashes {target_mention} a gentle smile! 💕",
        "{target_mention} — **{author}** can't stop smiling at {target_mention}! 😄",
        "**{author}** smiled so warmly {author_pronoun} lit up the whole room! ✨",
    ],
))

register(ActionConfig(
    name="wink", category="emotional", affection_gain=3, xp_gain=5,
    cooldown_seconds=15, gif_category="wink",
    self_targetable=True, requires_target=False,
    description="Wink at someone",
    response_templates=[
        "{target_mention} — **{author}** winks smoothly at {target_mention}! 😉",
        "{target_mention} — **{author}** gives {target_mention} a cheeky wink! 😏",
        "{target_mention} — **{author}** winks knowingly at {target_mention}! ✨",
        "{target_mention} — **{author}** flashes {target_mention} a wink! 💫",
        "{target_mention} — **{author}** winks playfully at {target_mention}! 😄",
        "{target_mention} — **{author}** shot {target_mention} a wink over {author_possessive} shoulder! 😉",
    ],
))

register(ActionConfig(
    name="dance", category="emotional", affection_gain=5, xp_gain=8,
    cooldown_seconds=15, gif_category="dance",
    self_targetable=True, requires_target=False,
    description="Dance",
    response_templates=[
        "**{author}** busts out some amazing dance moves! 💃",
        "**{author}** starts dancing like nobody's watching! 🕺",
        "{target_mention} — **{author}** pulls {target_mention} onto the dance floor! 🎵",
        "**{author}** does a little happy dance! 🎉",
        "**{author}** moonwalks across the room! 🌕",
    ],
))

register(ActionConfig(
    name="laugh", category="emotional", affection_gain=3, xp_gain=5,
    cooldown_seconds=15, gif_category="laugh",
    self_targetable=True, requires_target=False,
    description="Laugh out loud",
    response_templates=[
        "{target_mention} — **{author}** bursts out laughing at {target_mention}! 🤣",
        "**{author}** can't stop laughing! 😂",
        "**{author}** laughs so hard they cry! 😭😂",
        "**{author}** loses it completely! 🤣",
        "**{author}** erupts into contagious laughter! 😄",
    ],
))

register(ActionConfig(
    name="sigh", category="emotional", affection_gain=1, xp_gain=5,
    cooldown_seconds=15, gif_category="sigh",
    self_targetable=True, requires_target=False,
    description="Sigh expressively",
    response_templates=[
        "**{author}** lets out a long, dramatic sigh... 😮‍💨",
        "{target_mention} — **{author}** sighs deeply at {target_mention}... 💨",
        "**{author}** exhales with the weight of the world... 😔",
        "**{author}** releases the most defeated sigh imaginable... 😪",
        "**{author}** sighs and shakes their head... 🤦",
    ],
))

# ── Social (6) ────────────────────────────────────────────────────────────────

register(ActionConfig(
    name="highfive", category="social", affection_gain=8, xp_gain=10,
    cooldown_seconds=15, gif_category="highfive",
    description="High-five someone",
    response_templates=[
        "{target_mention} — **{author}** slapped hands with {target_mention} in a crisp high-five! 🙌",
        "**{target_mention}** and **{author}** shared a satisfying high-five! ✋",
        "{target_mention} — **{author}** gave {target_mention} the most enthusiastic high-five! 🙌",
        "{target_mention} — **{author}** didn't leave {target_mention} hanging — high five! ✋",
        "**{target_mention}** and **{author}** connected with a perfect high-five! 💥",
    ],
))

register(ActionConfig(
    name="fistbump", category="social", affection_gain=6, xp_gain=8,
    cooldown_seconds=15, gif_category="fistbump",
    description="Fist-bump someone",
    response_templates=[
        "{target_mention} — **{author}** gave {target_mention} a solid fist bump! 👊",
        "**{target_mention}** and **{author}** connected with a cool fist bump! 💪",
        "{target_mention} — **{author}** bumped fists with {target_mention} — respect! 👊",
        "{target_mention} — **{author}** offered a fist and {target_mention} bumped it! 🤜🤛",
        "**{target_mention}** and **{author}** sealed it with a fist bump! 🔥",
    ],
))

register(ActionConfig(
    name="handshake", category="social", affection_gain=5, xp_gain=8,
    cooldown_seconds=15, gif_category="handshake",
    description="Shake hands with someone",
    response_templates=[
        "{target_mention} — **{author}** extended a hand to {target_mention} for a firm handshake! 🤝",
        "**{target_mention}** and **{author}** shook hands formally! 🤝",
        "{target_mention} — **{author}** greeted {target_mention} with a respectful handshake! 🤝",
        "**{target_mention}** and **{author}** shook on it! 🤝",
        "{target_mention} — **{author}** offered {target_mention} a handshake and they accepted! 🤝",
    ],
))

register(ActionConfig(
    name="bow", category="social", affection_gain=5, xp_gain=8,
    cooldown_seconds=15, gif_category="bow",
    description="Bow respectfully",
    response_templates=[
        "{target_mention} — **{author}** bows gracefully before {target_mention}! 🙇",
        "{target_mention} — **{author}** offers {target_mention} a deep, respectful bow! ✨",
        "{target_mention} — **{author}** bowed dramatically toward {target_mention}! 🎭",
        "{target_mention} — **{author}** lowered their head in a formal bow to {target_mention}! 👑",
        "{target_mention} — **{author}** performed an elaborate bow before {target_mention}! 🌸",
    ],
))

register(ActionConfig(
    name="stare", category="social", affection_gain=3, xp_gain=5,
    cooldown_seconds=15, gif_category="stare",
    description="Stare at someone",
    response_templates=[
        "{target_mention} — **{author}** stares intensely at {target_mention} without blinking! 👁️",
        "{target_mention} — **{author}** fixes an unwavering gaze on {target_mention}... 😑",
        "{target_mention} — **{author}** stares {target_mention} down challengingly! 😤",
        "{target_mention} — **{author}** won't stop staring at {target_mention}... 👀",
        "{target_mention} — **{author}** locks eyes with {target_mention} and doesn't look away! 👁️‍🗨️",
    ],
))

register(ActionConfig(
    name="glare", category="social", affection_gain=2, xp_gain=5,
    cooldown_seconds=15, gif_category="glare",
    description="Glare at someone",
    response_templates=[
        "{target_mention} — **{author}** shot {target_mention} a withering glare! 😠",
        "{target_mention} — **{author}** glared daggers at {target_mention}! 🗡️",
        "{target_mention} — **{author}** fixed {target_mention} with an icy cold glare! 🥶",
        "{target_mention} — **{author}** narrowed their eyes and glared at {target_mention}! 😤",
        "{target_mention} — **{author}** glared at {target_mention} with maximum intensity! 💢",
    ],
))

register(ActionConfig(
    name="fuck", category="intimate", affection_gain=50, xp_gain=60,
    cooldown_seconds=300, gif_category="fuck",
    description="Have sex with someone",
    response_templates=[
        "{target_mention} — **{author}** pushed {target_mention} against the wall and fucked them senseless! 🔥",
        "{target_mention} — **{author}** bent {target_mention} over and gave them exactly what they begged for! 💦",
        "{target_mention} — **{author}** pounded {target_mention} into the mattress until they were a moaning mess! 😈",
        "{target_mention} — **{author}** grabbed {target_mention} by the hips and fucked them deep and hard! 🌶️",
        "{target_mention} — **{author}** fucked {target_mention} raw — no mercy, no stopping! 💥",
    ],
))

register(ActionConfig(
    name="blowjob", category="intimate", affection_gain=40, xp_gain=50,
    cooldown_seconds=300, gif_category="blowjob",
    description="Give someone a blowjob",
    response_templates=[
        "{target_mention} — **{author}** dropped to their knees and gave {target_mention} a sloppy, deep blowjob! 💦",
        "{target_mention} — **{author}** wrapped their lips around {target_mention} and sucked them off eagerly! 😛",
        "{target_mention} — **{author}** gagged on {target_mention} while giving them the blowjob of their life! 🔥",
        "{target_mention} — **{author}** looked up at {target_mention} with teary eyes and kept sucking! 👅",
        "{target_mention} — **{author}** took {target_mention} all the way down their throat without hesitation! 💥",
    ],
))

register(ActionConfig(
    name="creampie", category="intimate", affection_gain=55, xp_gain=65,
    cooldown_seconds=300, gif_category="creampie",
    description="Creampie someone",
    response_templates=[
        "{target_mention} — **{author}** filled {target_mention} up completely with a massive creampie! 💦",
        "{target_mention} — **{author}** came deep inside {target_mention}, leaving them dripping! 🔥",
        "{target_mention} — **{author}** pumped {target_mention} full to the brim — creampied and claimed! 😈",
        "{target_mention} — **{author}** buried themselves in {target_mention} and unloaded everything! 💥",
        "{target_mention} — **{author}** gave {target_mention} a creampie they won't forget anytime soon! 🌶️",
    ],
))

register(ActionConfig(
    name="moan", category="intimate", affection_gain=20, xp_gain=25,
    cooldown_seconds=60, gif_category="moan",
    self_targetable=True, requires_target=False,
    description="Moan at/for someone",
    response_templates=[
        "{target_mention} — **{author}** let out a loud, needy moan for {target_mention}! 😩",
        "{target_mention} — **{author}** moaned {target_mention}'s name breathlessly! 💦",
        "{target_mention} — **{author}** couldn't hold back their moans because of {target_mention}! 🔥",
        "{target_mention} — **{author}** moaned shamelessly, making {target_mention} blush! 😳",
        "{target_mention} — **{author}** let out the most obscene moan right in {target_mention}'s ear! 😈",
    ],
))

register(ActionConfig(
    name="strip", category="intimate", affection_gain=30, xp_gain=35,
    cooldown_seconds=120, gif_category="strip",
    self_targetable=True, requires_target=False,
    description="Strip for someone",
    response_templates=[
        "{target_mention} — **{author}** slowly stripped in front of {target_mention}, teasing every second! 🔥",
        "{target_mention} — **{author}** peeled off every piece of clothing for {target_mention}! 😈",
        "{target_mention} — **{author}** did a seductive striptease just for {target_mention}! 💃",
        "{target_mention} — **{author}** dropped everything and stood bare before {target_mention}! 💦",
        "{target_mention} — **{author}** stripped completely, holding {target_mention}'s gaze the entire time! 😏",
    ],
))

register(ActionConfig(
    name="spank", category="intimate", affection_gain=25, xp_gain=30,
    cooldown_seconds=60, gif_category="spank",
    description="Spank someone",
    response_templates=[
        "{target_mention} — **{author}** gave {target_mention}'s ass a firm, satisfying spank! 👋",
        "{target_mention} — **{author}** smacked {target_mention}'s rear hard enough to leave a mark! 🔥",
        "{target_mention} — **{author}** spanked {target_mention} repeatedly until they yelped! 😈",
        "{target_mention} — **{author}** grabbed {target_mention} and delivered a sharp, stinging spank! 💥",
        "{target_mention} — **{author}** spanked {target_mention} and told them they'd been very naughty! 😏",
    ],
))

register(ActionConfig(
    name="grope", category="intimate", affection_gain=25, xp_gain=30,
    cooldown_seconds=60, gif_category="grope",
    description="Grope someone",
    response_templates=[
        "{target_mention} — **{author}** reached over and groped {target_mention} shamelessly! 😏",
        "{target_mention} — **{author}** grabbed {target_mention} in all the right places! 🔥",
        "{target_mention} — **{author}** couldn't keep their hands off {target_mention} for a second! 😈",
        "{target_mention} — **{author}** groped {target_mention} from behind without any warning! 💦",
        "{target_mention} — **{author}** squeezed {target_mention} firmly and smirked! 😏",
    ],
))

register(ActionConfig(
    name="fingerfuck", category="intimate", affection_gain=35, xp_gain=45,
    cooldown_seconds=180, gif_category="fingerfuck",
    description="Finger someone",
    response_templates=[
        "{target_mention} — **{author}** slipped their fingers inside {target_mention} and worked them mercilessly! 💦",
        "{target_mention} — **{author}** fingered {target_mention} until they were a trembling, soaked mess! 🔥",
        "{target_mention} — **{author}** curled their fingers deep inside {target_mention} and hit every spot! 😈",
        "{target_mention} — **{author}** had {target_mention} squirming with just their fingers! 💥",
        "{target_mention} — **{author}** finger-fucked {target_mention} relentlessly until they begged! 🌶️",
    ],
))

register(ActionConfig(
    name="tease", category="intimate", affection_gain=20, xp_gain=25,
    cooldown_seconds=60, gif_category="tease",
    description="Tease someone sexually",
    response_templates=[
        "{target_mention} — **{author}** ran their hands all over {target_mention} without giving them what they want! 😏",
        "{target_mention} — **{author}** whispered something filthy in {target_mention}'s ear and walked away! 🔥",
        "{target_mention} — **{author}** teased {target_mention} to the edge and stopped — no relief! 😈",
        "{target_mention} — **{author}** pressed their body against {target_mention} then pulled away with a smirk! 💦",
        "{target_mention} — **{author}** had {target_mention} desperately begging with just a tease! 😩",
    ],
))

register(ActionConfig(
    name="seduce", category="intimate", affection_gain=30, xp_gain=35,
    cooldown_seconds=120, gif_category="seduce",
    description="Seduce someone",
    response_templates=[
        "{target_mention} — **{author}** seduced {target_mention} with a look that said everything! 😏",
        "{target_mention} — **{author}** moved in close and completely seduced {target_mention}! 🔥",
        "{target_mention} — **{author}** whispered something that made {target_mention} completely cave! 💋",
        "{target_mention} — **{author}** used every trick to seduce {target_mention} — and it worked! 😈",
        "{target_mention} — **{author}** seduced {target_mention} effortlessly, leaving them wanting more! 💦",
    ],
))

register(ActionConfig(
    name="makeout", category="intimate", affection_gain=30, xp_gain=35,
    cooldown_seconds=120, gif_category="makeout",
    description="Make out with someone",
    response_templates=[
        "{target_mention} — **{author}** grabbed {target_mention} and kissed them so deeply they forgot to breathe! 💋",
        "**{target_mention}** and **{author}** made out passionately, completely lost in each other! 🔥",
        "{target_mention} — **{author}** pinned {target_mention} and made out with them hungrily! 😈",
        "{target_mention} — **{author}** pulled {target_mention} into a long, hot, sloppy makeout session! 💦",
        "**{target_mention}** and **{author}** couldn't stop making out no matter who was watching! 😏",
    ],
))

register(ActionConfig(
    name="ride", category="intimate", affection_gain=45, xp_gain=55,
    cooldown_seconds=300, gif_category="ride",
    description="Ride someone",
    response_templates=[
        "{target_mention} — **{author}** climbed on top of {target_mention} and rode them hard! 🔥",
        "{target_mention} — **{author}** pinned {target_mention} down and rode them until they both lost their minds! 💦",
        "{target_mention} — **{author}** took control and rode {target_mention} at their own wild pace! 😈",
        "{target_mention} — **{author}** sat down on {target_mention} and rode them to oblivion! 💥",
        "{target_mention} — **{author}** bounced on {target_mention} relentlessly — they had zero complaints! 🌶️",
    ],
))

register(ActionConfig(
    name="cum", category="intimate", affection_gain=40, xp_gain=50,
    cooldown_seconds=300, gif_category="cum",
    self_targetable=True, requires_target=False,
    description="Cum on/for someone",
    response_templates=[
        "{target_mention} — **{author}** came all over {target_mention} and marked them completely! 💦",
        "{target_mention} — **{author}** couldn't hold back and came hard all over {target_mention}! 🔥",
        "{target_mention} — **{author}** moaned {target_mention}'s name as they came undone! 😩",
        "{target_mention} — **{author}** made a total mess on {target_mention} and didn't apologize! 😈",
        "{target_mention} — **{author}** painted {target_mention} white and stepped back to admire! 💥",
    ],
))

register(ActionConfig(
    name="undress", category="intimate", affection_gain=25, xp_gain=30,
    cooldown_seconds=120, gif_category="undress",
    description="Undress someone",
    response_templates=[
        "{target_mention} — **{author}** slowly undressed {target_mention}, taking their sweet time! 😏",
        "{target_mention} — **{author}** peeled every layer off {target_mention} with deliberate hands! 🔥",
        "{target_mention} — **{author}** undressed {target_mention} before they could even protest! 😈",
        "{target_mention} — **{author}** stripped {target_mention} down, leaving them completely bare! 💦",
        "{target_mention} — **{author}** undressed {target_mention} with hungry eyes the whole time! 💋",
    ],
))

register(ActionConfig(
    name="lickout", category="intimate", affection_gain=40, xp_gain=50,
    cooldown_seconds=240, gif_category="lickout",
    description="Go down on someone / eat someone out",
    response_templates=[
        "{target_mention} — **{author}** buried their face between {target_mention}'s thighs and went to town! 👅",
        "{target_mention} — **{author}** ate {target_mention} out until their legs stopped working! 🔥",
        "{target_mention} — **{author}** licked {target_mention} out slowly, savoring every second! 💦",
        "{target_mention} — **{author}** had {target_mention} grabbing the sheets with just their tongue! 😈",
        "{target_mention} — **{author}** went down on {target_mention} and didn't come up until they screamed! 💥",
    ],
))

register(ActionConfig(
    name="handjob", category="intimate", affection_gain=35, xp_gain=40,
    cooldown_seconds=180, gif_category="handjob",
    description="Give someone a handjob",
    response_templates=[
        "{target_mention} — **{author}** wrapped their hand around {target_mention} and stroked them slowly at first! 💦",
        "{target_mention} — **{author}** gave {target_mention} a handjob so good their knees went weak! 🔥",
        "{target_mention} — **{author}** gripped {target_mention} tight and worked them until they lost it! 😈",
        "{target_mention} — **{author}** teased {target_mention} with a slow, torturous handjob! 😏",
        "{target_mention} — **{author}** stroked {target_mention} off expertly — they didn't last long! 💥",
    ],
))

register(ActionConfig(
    name="titfuck", category="intimate", affection_gain=38, xp_gain=45,
    cooldown_seconds=240, gif_category="titfuck",
    description="Give someone a titfuck",
    response_templates=[
        "{target_mention} — **{author}** pressed {target_mention} between their chest and worked them slowly! 🔥",
        "{target_mention} — **{author}** gave {target_mention} a titfuck they'll be dreaming about for weeks! 💦",
        "{target_mention} — **{author}** squeezed {target_mention} between their breasts and looked up with a grin! 😈",
        "{target_mention} — **{author}** wrapped {target_mention} up snug and went to work — messy ending guaranteed! 💥",
        "{target_mention} — **{author}** treated {target_mention} to a slow, slippery titfuck until they exploded! 🌶️",
    ],
))

register(ActionConfig(
    name="anal", category="intimate", affection_gain=50, xp_gain=60,
    cooldown_seconds=300, gif_category="anal",
    description="Have anal sex with someone",
    response_templates=[
        "{target_mention} — **{author}** pushed into {target_mention}'s ass slowly and then gave them everything! 🔥",
        "{target_mention} — **{author}** took {target_mention}'s ass with zero hesitation! 💦",
        "{target_mention} — **{author}** spread {target_mention} open and fucked their ass deep and hard! 😈",
        "{target_mention} — **{author}** filled {target_mention}'s ass completely and didn't stop until they begged! 💥",
        "{target_mention} — **{author}** wrecked {target_mention}'s ass and left them a trembling mess! 🌶️",
    ],
))

register(ActionConfig(
    name="bondage", category="intimate", affection_gain=35, xp_gain=45,
    cooldown_seconds=240, gif_category="bondage",
    description="Tie someone up",
    response_templates=[
        "{target_mention} — **{author}** tied {target_mention} up tight and left them completely helpless! 🔥",
        "{target_mention} — **{author}** bound {target_mention}'s wrists and ankles — they weren't going anywhere! 😈",
        "{target_mention} — **{author}** wrapped {target_mention} in rope and admired their work! 💦",
        "{target_mention} — **{author}** had {target_mention} bound and blindfolded in seconds! 💥",
        "{target_mention} — **{author}** tied {target_mention} up so perfectly they couldn't even wiggle free! 🌶️",
    ],
))

register(ActionConfig(
    name="dominate", category="intimate", affection_gain=40, xp_gain=50,
    cooldown_seconds=240, gif_category="dominate",
    description="Dominate someone",
    response_templates=[
        "{target_mention} — **{author}** pinned {target_mention} down and made it very clear who was in charge! 🔥",
        "{target_mention} — **{author}** grabbed {target_mention} by the collar and dominated them completely! 😈",
        "{target_mention} — **{author}** took full control of {target_mention} and they loved every second! 💦",
        "{target_mention} — **{author}** dominated {target_mention} until they were completely and utterly broken in! 💥",
        "{target_mention} — **{author}** had {target_mention} submitting without a single word of protest! 😏",
    ],
))

register(ActionConfig(
    name="submit", category="intimate", affection_gain=35, xp_gain=45,
    cooldown_seconds=240, gif_category="submit",
    self_targetable=True, requires_target=False,
    description="Submit to someone",
    response_templates=[
        "{target_mention} — **{author}** dropped to their knees and submitted fully to {target_mention}! 💦",
        "{target_mention} — **{author}** gave themselves over to {target_mention} completely — body and soul! 🔥",
        "{target_mention} — **{author}** bowed their head and submitted to {target_mention}'s every command! 😈",
        "{target_mention} — **{author}** let {target_mention} take total control and surrendered willingly! 💥",
        "{target_mention} — **{author}** submitted to {target_mention} with a breathless, needy whimper! 😩",
    ],
))

register(ActionConfig(
    name="choke", category="intimate", affection_gain=30, xp_gain=40,
    cooldown_seconds=180, gif_category="choke",
    description="Choke someone during intimacy",
    response_templates=[
        "{target_mention} — **{author}** wrapped their hand around {target_mention}'s throat and squeezed just right! 🔥",
        "{target_mention} — **{author}** choked {target_mention} gently and watched their eyes roll back! 😈",
        "{target_mention} — **{author}** gripped {target_mention}'s throat firmly — they gasped and loved it! 💦",
        "{target_mention} — **{author}** choked {target_mention} with a steady hand and a dangerous smirk! 💥",
        "{target_mention} — **{author}** took {target_mention} by the throat and made them see stars! 🌶️",
    ],
))

register(ActionConfig(
    name="edging", category="intimate", affection_gain=38, xp_gain=48,
    cooldown_seconds=240, gif_category="edging",
    description="Edge someone relentlessly",
    response_templates=[
        "{target_mention} — **{author}** brought {target_mention} right to the edge and pulled back — again and again! 😈",
        "{target_mention} — **{author}** edged {target_mention} until they were sobbing and begging to finish! 🔥",
        "{target_mention} — **{author}** kept {target_mention} on the edge for so long they lost track of time! 💦",
        "{target_mention} — **{author}** denied {target_mention} over and over with a satisfied smirk! 😏",
        "{target_mention} — **{author}** tortured {target_mention} with relentless edging — no release in sight! 💥",
    ],
))

register(ActionConfig(
    name="gangbang", category="intimate", affection_gain=60, xp_gain=75,
    cooldown_seconds=600, gif_category="gangbang",
    description="Gangbang someone",
    response_templates=[
        "{target_mention} — **{author}** organized a full gangbang with {target_mention} at the center of it all! 🔥",
        "{target_mention} — **{author}** and a crowd took turns wrecking {target_mention} completely! 💦",
        "{target_mention} — **{author}** had {target_mention} completely surrounded and used from every angle! 😈",
        "{target_mention} — **{author}** arranged a gangbang for {target_mention} — they could barely walk after! 💥",
        "{target_mention} — **{author}** let everyone have a turn with {target_mention} until they were utterly spent! 🌶️",
    ],
))

register(ActionConfig(
    name="threesome", category="intimate", affection_gain=55, xp_gain=65,
    cooldown_seconds=420, gif_category="threesome",
    description="Have a threesome with someone",
    response_templates=[
        "{target_mention} — **{author}** pulled in a third and had an absolutely wild threesome with {target_mention}! 🔥",
        "**{target_mention}** and **{author}** invited someone extra — the night got very interesting! 💦",
        "{target_mention} — **{author}** arranged a threesome with {target_mention} and nobody left unsatisfied! 😈",
        "**{target_mention}** and **{author}** got tangled up with a third person in the best way! 💥",
        "{target_mention} — **{author}** had a filthy threesome with {target_mention} — details too hot to share! 🌶️",
    ],
))

register(ActionConfig(
    name="facesit", category="intimate", affection_gain=40, xp_gain=50,
    cooldown_seconds=240, gif_category="facesit",
    description="Sit on someone's face",
    response_templates=[
        "{target_mention} — **{author}** sat right down on {target_mention}'s face and made themselves comfortable! 💦",
        "{target_mention} — **{author}** smothered {target_mention} with a full facesit and dared them to complain! 🔥",
        "{target_mention} — **{author}** lowered themselves onto {target_mention}'s face with zero hesitation! 😈",
        "{target_mention} — **{author}** facesit on {target_mention} and rode their tongue until satisfied! 💥",
        "{target_mention} — **{author}** gave {target_mention} a facesit they'd been secretly dreaming about! 😏",
    ],
))

register(ActionConfig(
    name="cum_facial", category="intimate", affection_gain=42, xp_gain=52,
    cooldown_seconds=300, gif_category="cum_facial",
    description="Give someone a facial",
    response_templates=[
        "{target_mention} — **{author}** finished all over {target_mention}'s face and stepped back to admire! 💦",
        "{target_mention} — **{author}** gave {target_mention} a dripping facial they wore with zero shame! 🔥",
        "{target_mention} — **{author}** painted {target_mention}'s face completely and they didn't even flinch! 😈",
        "{target_mention} — **{author}** unloaded on {target_mention}'s face — they looked absolutely ruined! 💥",
        "{target_mention} — **{author}** gave {target_mention} a messy facial and called it a masterpiece! 🌶️",
    ],
))

register(ActionConfig(
    name="roleplay_sex", category="intimate", affection_gain=45, xp_gain=55,
    cooldown_seconds=300, gif_category="roleplay_sex",
    description="Do a sexual roleplay with someone",
    response_templates=[
        "{target_mention} — **{author}** dragged {target_mention} into a filthy sexual roleplay and neither held back! 🔥",
        "{target_mention} — **{author}** started a spicy roleplay scenario with {target_mention} — things escalated fast! 💦",
        "**{target_mention}** and **{author}** got into a steamy roleplay that got very explicit very quickly! 😈",
        "{target_mention} — **{author}** set the scene for a naughty roleplay and {target_mention} played along perfectly! 💥",
        "**{target_mention}** and **{author}** lost themselves completely in an explicit roleplay session! 🌶️",
    ],
))

register(ActionConfig(
    name="orgasm", category="intimate", affection_gain=50, xp_gain=60,
    cooldown_seconds=300, gif_category="orgasm",
    self_targetable=True, requires_target=False,
    description="Have an orgasm because of someone",
    response_templates=[
        "{target_mention} — **{author}** came undone because of {target_mention} — loudly and without shame! 💦",
        "{target_mention} — **{author}** hit an earth-shattering orgasm thanks to {target_mention}! 🔥",
        "{target_mention} — **{author}** screamed {target_mention}'s name as they orgasmed hard! 😩",
        "{target_mention} — **{author}** lost complete control and orgasmed right in front of {target_mention}! 💥",
        "{target_mention} — **{author}** had the most intense orgasm of their life because of {target_mention}! 🌶️",
    ],
))

register(ActionConfig(
    name="squirt", category="intimate", affection_gain=52, xp_gain=62,
    cooldown_seconds=360, gif_category="squirt",
    self_targetable=True, requires_target=False,
    description="Squirt because of someone",
    response_templates=[
        "{target_mention} — **{author}** squirted all over {target_mention} and couldn't even apologize! 💦",
        "{target_mention} — **{author}** squirted so hard because of {target_mention} — absolutely soaked! 🔥",
        "{target_mention} — **{author}** lost complete control and squirted everywhere thanks to {target_mention}! 😈",
        "{target_mention} — **{author}** made a massive mess squirting all over {target_mention}! 💥",
        "{target_mention} — **{author}** squirted uncontrollably — {target_mention} looked very proud of themselves! 😏",
    ],
))
