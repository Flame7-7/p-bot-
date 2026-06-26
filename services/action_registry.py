from __future__ import annotations

import random
from dataclasses import dataclass, field


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

    def get_response(self, author: str, target: str | None = None) -> str:
        template = random.choice(self.response_templates)
        return template.format(author=author, target=target or author)


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
        "**{author}** pulled **{target}** into a warm, tight hug! 🤗",
        "**{author}** wrapped their arms around **{target}** and hugged them close! 💕",
        "**{author}** ran over and gave **{target}** the biggest hug ever! 🫂",
        "**{author}** hugged **{target}** so tightly they almost couldn't breathe!",
        "**{author}** snuck up behind **{target}** and gave them a surprise hug! 💖",
    ],
))

register(ActionConfig(
    name="pat", category="affection", affection_gain=10, xp_gain=15,
    cooldown_seconds=30, gif_category="pat",
    description="Pat someone on the head",
    response_templates=[
        "**{author}** gently patted **{target}**'s head! 🥺",
        "**{author}** gave **{target}** a soft, loving headpat! ✨",
        "**{author}** reached up and patted **{target}** with care! 💕",
        "**{author}** tenderly patted **{target}**'s head! 🌸",
        "**{author}** ruffled **{target}**'s hair with an affectionate pat! 😊",
    ],
))

register(ActionConfig(
    name="kiss", category="affection", affection_gain=15, xp_gain=20,
    cooldown_seconds=30, gif_category="kiss",
    description="Kiss someone",
    response_templates=[
        "**{author}** gave **{target}** a sweet kiss! 💋",
        "**{author}** leaned in and kissed **{target}** on the cheek! 😘",
        "**{author}** planted a gentle kiss on **{target}**'s forehead! 💕",
        "**{author}** snuck a quick kiss on **{target}**'s cheek! 🌸",
        "**{author}** gave **{target}** a loving kiss! 💖",
    ],
))

register(ActionConfig(
    name="cuddle", category="affection", affection_gain=15, xp_gain=20,
    cooldown_seconds=30, gif_category="cuddle",
    description="Cuddle with someone",
    response_templates=[
        "**{author}** curled up and cuddled with **{target}**! 🫂",
        "**{author}** snuggled close to **{target}** for a cozy cuddle! 💕",
        "**{author}** and **{target}** cuddled together warmly! 🌸",
        "**{author}** pulled **{target}** in for a long, comfortable cuddle! 💖",
        "**{author}** wrapped themselves around **{target}** in a cuddle! 🥺",
    ],
))

register(ActionConfig(
    name="poke", category="affection", affection_gain=5, xp_gain=8,
    cooldown_seconds=30, gif_category="poke",
    description="Poke someone",
    response_templates=[
        "**{author}** poked **{target}** on the cheek! 👉",
        "**{author}** jabbed **{target}** playfully! 😄",
        "**{author}** kept poking **{target}** until they noticed! 👀",
        "**{author}** sneakily poked **{target}** and ran! 💨",
        "**{author}** gave **{target}** a little boop-poke! 🥺",
    ],
))

register(ActionConfig(
    name="boop", category="affection", affection_gain=5, xp_gain=8,
    cooldown_seconds=30, gif_category="boop",
    description="Boop someone on the nose",
    response_templates=[
        "**{author}** booped **{target}** on the nose! 👆",
        "**{author}** reached over and booped **{target}**'s snoot! 🐾",
        "**{author}** gave **{target}** the gentlest nose boop! 💕",
        "**{author}** *boop* — got **{target}**'s nose! 😄",
        "**{author}** sneaked in a surprise boop on **{target}**! ✨",
    ],
))

register(ActionConfig(
    name="headpat", category="affection", affection_gain=10, xp_gain=15,
    cooldown_seconds=30, gif_category="headpat",
    description="Give someone a headpat",
    response_templates=[
        "**{author}** gave **{target}** soft, gentle headpats! 🥺",
        "**{author}** placed a warm hand on **{target}**'s head! 💕",
        "**{author}** headpatted **{target}** like they deserved it! ✨",
        "**{author}** ruffled **{target}**'s hair with tender headpats! 🌸",
        "**{author}** patted **{target}**'s head and smiled warmly! 😊",
    ],
))

register(ActionConfig(
    name="nuzzle", category="affection", affection_gain=12, xp_gain=15,
    cooldown_seconds=30, gif_category="nuzzle",
    description="Nuzzle someone affectionately",
    response_templates=[
        "**{author}** nuzzled up against **{target}** softly! 🥰",
        "**{author}** buried their face in **{target}**'s shoulder with a happy nuzzle! 💕",
        "**{author}** nuzzled **{target}** gently! 🌸",
        "**{author}** pressed their cheek to **{target}**'s in a sweet nuzzle! ✨",
        "**{author}** nuzzled **{target}** and purred contentedly! 😸",
    ],
))

register(ActionConfig(
    name="snuggle", category="affection", affection_gain=13, xp_gain=18,
    cooldown_seconds=30, gif_category="snuggle",
    description="Snuggle with someone",
    response_templates=[
        "**{author}** snuggled close to **{target}** warmly! 🫂",
        "**{author}** wrapped up with **{target}** in a cozy snuggle! 💕",
        "**{author}** and **{target}** settled in for an adorable snuggle! 🌸",
        "**{author}** snuggled into **{target}** like a sleepy puppy! 🐶",
        "**{author}** pulled **{target}** into a snuggly embrace! 💖",
    ],
))

register(ActionConfig(
    name="tackle", category="affection", affection_gain=10, xp_gain=15,
    cooldown_seconds=30, gif_category="tackle",
    description="Tackle someone in excitement",
    response_templates=[
        "**{author}** tackled **{target}** to the ground in excitement! 💨",
        "**{author}** sprinted over and tackle-hugged **{target}**! 🏃",
        "**{author}** launched themselves at **{target}** in a flying tackle! 😄",
        "**{author}** caught **{target}** off guard with a sudden tackle! 😂",
        "**{author}** tackled **{target}** and refused to let go! 🫂",
    ],
))

# ── Playful (8) ───────────────────────────────────────────────────────────────

register(ActionConfig(
    name="slap", category="playful", affection_gain=2, xp_gain=5,
    cooldown_seconds=15, gif_category="slap",
    description="Slap someone playfully",
    response_templates=[
        "**{author}** slapped **{target}** with a rubber fish! 🐟",
        "**{author}** gave **{target}** a swift smack! 👋",
        "**{author}** slapped **{target}** and ran off laughing! 😂",
        "**{author}** delivered a dramatic slap to **{target}**! 🎭",
        "**{author}** slapped **{target}** out of nowhere! 😤",
    ],
))

register(ActionConfig(
    name="punch", category="playful", affection_gain=2, xp_gain=5,
    cooldown_seconds=15, gif_category="punch",
    description="Punch someone playfully",
    response_templates=[
        "**{author}** punched **{target}** in the arm playfully! 👊",
        "**{author}** threw a light punch at **{target}**! 🥊",
        "**{author}** playfully decked **{target}**! 😤",
        "**{author}** socked **{target}** in the shoulder! 💥",
        "**{author}** gave **{target}** a friendly punch! 👊",
    ],
))

register(ActionConfig(
    name="kick", category="playful", affection_gain=2, xp_gain=5,
    cooldown_seconds=15, gif_category="kick",
    description="Kick someone playfully",
    response_templates=[
        "**{author}** kicked **{target}** playfully! 🦵",
        "**{author}** launched a kick straight at **{target}**! 💥",
        "**{author}** swept **{target}**'s leg! 🥋",
        "**{author}** gave **{target}** a not-so-gentle kick! 😅",
        "**{author}** kicked **{target}** and pretended it was an accident! 😂",
    ],
))

register(ActionConfig(
    name="bite", category="playful", affection_gain=5, xp_gain=8,
    cooldown_seconds=15, gif_category="bite",
    description="Bite someone playfully",
    response_templates=[
        "**{author}** nibbled on **{target}**'s ear! 👂",
        "**{author}** chomped down on **{target}**'s arm! 😬",
        "**{author}** gave **{target}** a playful little bite! 🐾",
        "**{author}** bit **{target}** like a tiny gremlin! 😈",
        "**{author}** sank their teeth into **{target}** — *nom nom*! 🍴",
    ],
))

register(ActionConfig(
    name="lick", category="playful", affection_gain=5, xp_gain=8,
    cooldown_seconds=15, gif_category="lick",
    description="Lick someone",
    response_templates=[
        "**{author}** licked **{target}**'s cheek like a happy puppy! 🐶",
        "**{author}** snuck a big lick on **{target}**'s face! 😝",
        "**{author}** gave **{target}** a surprise lick! 👅",
        "**{author}** licked **{target}** — because why not? 😂",
        "**{author}** taste-tested **{target}** with a lick! 😋",
    ],
))

register(ActionConfig(
    name="tickle", category="playful", affection_gain=8, xp_gain=10,
    cooldown_seconds=15, gif_category="tickle",
    description="Tickle someone",
    response_templates=[
        "**{author}** started tickling **{target}** mercilessly! 😂",
        "**{author}** found **{target}**'s tickle spot and attacked! 🎯",
        "**{author}** wiggled their fingers at **{target}** then tickled! 😈",
        "**{author}** tickled **{target}** until they couldn't breathe! 🤣",
        "**{author}** ambushed **{target}** with relentless tickles! 👐",
    ],
))

register(ActionConfig(
    name="pounce", category="playful", affection_gain=8, xp_gain=10,
    cooldown_seconds=15, gif_category="pounce",
    description="Pounce on someone",
    response_templates=[
        "**{author}** pounced on **{target}** like a cat! 🐱",
        "**{author}** launched themselves at **{target}** with a pounce! 💨",
        "**{author}** crept silently... then pounced on **{target}**! 🐆",
        "**{author}** did a flying pounce straight onto **{target}**! 🌪️",
        "**{author}** pounced on **{target}** and pinned them down! 😄",
    ],
))

register(ActionConfig(
    name="throw", category="playful", affection_gain=3, xp_gain=5,
    cooldown_seconds=15, gif_category="throw",
    description="Throw something at someone",
    response_templates=[
        "**{author}** lobbed a pillow at **{target}**! 🛌",
        "**{author}** threw a snowball at **{target}**! ❄️",
        "**{author}** chucked a plushie at **{target}**'s face! 🧸",
        "**{author}** hurled a bag of chips at **{target}**! 🍟",
        "**{author}** yeeted a random object at **{target}**! 💥",
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
    ],
))

register(ActionConfig(
    name="wave", category="emotional", affection_gain=3, xp_gain=5,
    cooldown_seconds=15, gif_category="wave",
    self_targetable=True, requires_target=False,
    description="Wave at someone",
    response_templates=[
        "**{author}** waves cheerfully at **{target}**! 👋",
        "**{author}** waves hello at **{target}**! 😊",
        "**{author}** gives **{target}** an enthusiastic wave! ✋",
        "**{author}** waves excitedly at **{target}**! 🙌",
        "**{author}** does a little wave at **{target}**! 🌟",
    ],
))

register(ActionConfig(
    name="blush", category="emotional", affection_gain=2, xp_gain=5,
    cooldown_seconds=15, gif_category="blush",
    self_targetable=True, requires_target=False,
    description="Blush",
    response_templates=[
        "**{author}** turns bright red and covers their face! 😳",
        "**{author}** blushes deeply at **{target}**! 💕",
        "**{author}**'s cheeks go completely red! 🔴",
        "**{author}** starts blushing furiously! 😖",
        "**{author}** hides their face, blushing hard! 🙈",
    ],
))

register(ActionConfig(
    name="smile", category="emotional", affection_gain=3, xp_gain=5,
    cooldown_seconds=15, gif_category="smile",
    self_targetable=True, requires_target=False,
    description="Smile warmly",
    response_templates=[
        "**{author}** gives **{target}** the most beautiful smile! 😊",
        "**{author}** smiles warmly at **{target}**! 🌸",
        "**{author}** beams a giant smile at **{target}**! ✨",
        "**{author}** flashes **{target}** a gentle smile! 💕",
        "**{author}** can't stop smiling at **{target}**! 😄",
    ],
))

register(ActionConfig(
    name="wink", category="emotional", affection_gain=3, xp_gain=5,
    cooldown_seconds=15, gif_category="wink",
    self_targetable=True, requires_target=False,
    description="Wink at someone",
    response_templates=[
        "**{author}** winks smoothly at **{target}**! 😉",
        "**{author}** gives **{target}** a cheeky wink! 😏",
        "**{author}** winks knowingly at **{target}**! ✨",
        "**{author}** flashes **{target}** a wink! 💫",
        "**{author}** winks playfully at **{target}**! 😄",
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
        "**{author}** pulls **{target}** onto the dance floor! 🎵",
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
        "**{author}** bursts out laughing at **{target}**! 🤣",
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
        "**{author}** sighs deeply at **{target}**... 💨",
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
        "**{author}** slapped hands with **{target}** in a crisp high-five! 🙌",
        "**{author}** and **{target}** shared a satisfying high-five! ✋",
        "**{author}** gave **{target}** the most enthusiastic high-five! 🙌",
        "**{author}** didn't leave **{target}** hanging — high five! ✋",
        "**{author}** and **{target}** connected with a perfect high-five! 💥",
    ],
))

register(ActionConfig(
    name="fistbump", category="social", affection_gain=6, xp_gain=8,
    cooldown_seconds=15, gif_category="fistbump",
    description="Fist-bump someone",
    response_templates=[
        "**{author}** gave **{target}** a solid fist bump! 👊",
        "**{author}** and **{target}** connected with a cool fist bump! 💪",
        "**{author}** bumped fists with **{target}** — respect! 👊",
        "**{author}** offered a fist and **{target}** bumped it! 🤜🤛",
        "**{author}** and **{target}** sealed it with a fist bump! 🔥",
    ],
))

register(ActionConfig(
    name="handshake", category="social", affection_gain=5, xp_gain=8,
    cooldown_seconds=15, gif_category="handshake",
    description="Shake hands with someone",
    response_templates=[
        "**{author}** extended a hand to **{target}** for a firm handshake! 🤝",
        "**{author}** and **{target}** shook hands formally! 🤝",
        "**{author}** greeted **{target}** with a respectful handshake! 🤝",
        "**{author}** and **{target}** shook on it! 🤝",
        "**{author}** offered **{target}** a handshake and they accepted! 🤝",
    ],
))

register(ActionConfig(
    name="bow", category="social", affection_gain=5, xp_gain=8,
    cooldown_seconds=15, gif_category="bow",
    description="Bow respectfully",
    response_templates=[
        "**{author}** bows gracefully before **{target}**! 🙇",
        "**{author}** offers **{target}** a deep, respectful bow! ✨",
        "**{author}** bowed dramatically toward **{target}**! 🎭",
        "**{author}** lowered their head in a formal bow to **{target}**! 👑",
        "**{author}** performed an elaborate bow before **{target}**! 🌸",
    ],
))

register(ActionConfig(
    name="stare", category="social", affection_gain=3, xp_gain=5,
    cooldown_seconds=15, gif_category="stare",
    description="Stare at someone",
    response_templates=[
        "**{author}** stares intensely at **{target}** without blinking! 👁️",
        "**{author}** fixes an unwavering gaze on **{target}**... 😑",
        "**{author}** stares **{target}** down challengingly! 😤",
        "**{author}** won't stop staring at **{target}**... 👀",
        "**{author}** locks eyes with **{target}** and doesn't look away! 👁️‍🗨️",
    ],
))

register(ActionConfig(
    name="glare", category="social", affection_gain=2, xp_gain=5,
    cooldown_seconds=15, gif_category="glare",
    description="Glare at someone",
    response_templates=[
        "**{author}** shot **{target}** a withering glare! 😠",
        "**{author}** glared daggers at **{target}**! 🗡️",
        "**{author}** fixed **{target}** with an icy cold glare! 🥶",
        "**{author}** narrowed their eyes and glared at **{target}**! 😤",
        "**{author}** glared at **{target}** with maximum intensity! 💢",
    ],
))
