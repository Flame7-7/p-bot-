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

register(ActionConfig(
    name="fuck", category="intimate", affection_gain=50, xp_gain=60,
    cooldown_seconds=300, gif_category="fuck",
    description="Have sex with someone",
    response_templates=[
        "**{author}** pushed **{target}** against the wall and fucked them senseless! 🔥",
        "**{author}** bent **{target}** over and gave them exactly what they begged for! 💦",
        "**{author}** pounded **{target}** into the mattress until they were a moaning mess! 😈",
        "**{author}** grabbed **{target}** by the hips and fucked them deep and hard! 🌶️",
        "**{author}** fucked **{target}** raw — no mercy, no stopping! 💥",
    ],
))

register(ActionConfig(
    name="blowjob", category="intimate", affection_gain=40, xp_gain=50,
    cooldown_seconds=300, gif_category="blowjob",
    description="Give someone a blowjob",
    response_templates=[
        "**{author}** dropped to their knees and gave **{target}** a sloppy, deep blowjob! 💦",
        "**{author}** wrapped their lips around **{target}** and sucked them off eagerly! 😛",
        "**{author}** gagged on **{target}** while giving them the blowjob of their life! 🔥",
        "**{author}** looked up at **{target}** with teary eyes and kept sucking! 👅",
        "**{author}** took **{target}** all the way down their throat without hesitation! 💥",
    ],
))

register(ActionConfig(
    name="creampie", category="intimate", affection_gain=55, xp_gain=65,
    cooldown_seconds=300, gif_category="creampie",
    description="Creampie someone",
    response_templates=[
        "**{author}** filled **{target}** up completely with a massive creampie! 💦",
        "**{author}** came deep inside **{target}**, leaving them dripping! 🔥",
        "**{author}** pumped **{target}** full to the brim — creampied and claimed! 😈",
        "**{author}** buried themselves in **{target}** and unloaded everything! 💥",
        "**{author}** gave **{target}** a creampie they won't forget anytime soon! 🌶️",
    ],
))

register(ActionConfig(
    name="moan", category="intimate", affection_gain=20, xp_gain=25,
    cooldown_seconds=60, gif_category="moan",
    self_targetable=True, requires_target=False,
    description="Moan at/for someone",
    response_templates=[
        "**{author}** let out a loud, needy moan for **{target}**! 😩",
        "**{author}** moaned **{target}**'s name breathlessly! 💦",
        "**{author}** couldn't hold back their moans because of **{target}**! 🔥",
        "**{author}** moaned shamelessly, making **{target}** blush! 😳",
        "**{author}** let out the most obscene moan right in **{target}**'s ear! 😈",
    ],
))

register(ActionConfig(
    name="strip", category="intimate", affection_gain=30, xp_gain=35,
    cooldown_seconds=120, gif_category="strip",
    self_targetable=True, requires_target=False,
    description="Strip for someone",
    response_templates=[
        "**{author}** slowly stripped in front of **{target}**, teasing every second! 🔥",
        "**{author}** peeled off every piece of clothing for **{target}**! 😈",
        "**{author}** did a seductive striptease just for **{target}**! 💃",
        "**{author}** dropped everything and stood bare before **{target}**! 💦",
        "**{author}** stripped completely, holding **{target}**'s gaze the entire time! 😏",
    ],
))

register(ActionConfig(
    name="spank", category="intimate", affection_gain=25, xp_gain=30,
    cooldown_seconds=60, gif_category="spank",
    description="Spank someone",
    response_templates=[
        "**{author}** gave **{target}**'s ass a firm, satisfying spank! 👋",
        "**{author}** smacked **{target}**'s rear hard enough to leave a mark! 🔥",
        "**{author}** spanked **{target}** repeatedly until they yelped! 😈",
        "**{author}** grabbed **{target}** and delivered a sharp, stinging spank! 💥",
        "**{author}** spanked **{target}** and told them they'd been very naughty! 😏",
    ],
))

register(ActionConfig(
    name="grope", category="intimate", affection_gain=25, xp_gain=30,
    cooldown_seconds=60, gif_category="grope",
    description="Grope someone",
    response_templates=[
        "**{author}** reached over and groped **{target}** shamelessly! 😏",
        "**{author}** grabbed **{target}** in all the right places! 🔥",
        "**{author}** couldn't keep their hands off **{target}** for a second! 😈",
        "**{author}** groped **{target}** from behind without any warning! 💦",
        "**{author}** squeezed **{target}** firmly and smirked! 😏",
    ],
))

register(ActionConfig(
    name="fingerfuck", category="intimate", affection_gain=35, xp_gain=45,
    cooldown_seconds=180, gif_category="fingerfuck",
    description="Finger someone",
    response_templates=[
        "**{author}** slipped their fingers inside **{target}** and worked them mercilessly! 💦",
        "**{author}** fingered **{target}** until they were a trembling, soaked mess! 🔥",
        "**{author}** curled their fingers deep inside **{target}** and hit every spot! 😈",
        "**{author}** had **{target}** squirming with just their fingers! 💥",
        "**{author}** finger-fucked **{target}** relentlessly until they begged! 🌶️",
    ],
))

register(ActionConfig(
    name="tease", category="intimate", affection_gain=20, xp_gain=25,
    cooldown_seconds=60, gif_category="tease",
    description="Tease someone sexually",
    response_templates=[
        "**{author}** ran their hands all over **{target}** without giving them what they want! 😏",
        "**{author}** whispered something filthy in **{target}**'s ear and walked away! 🔥",
        "**{author}** teased **{target}** to the edge and stopped — no relief! 😈",
        "**{author}** pressed their body against **{target}** then pulled away with a smirk! 💦",
        "**{author}** had **{target}** desperately begging with just a tease! 😩",
    ],
))

register(ActionConfig(
    name="seduce", category="intimate", affection_gain=30, xp_gain=35,
    cooldown_seconds=120, gif_category="seduce",
    description="Seduce someone",
    response_templates=[
        "**{author}** seduced **{target}** with a look that said everything! 😏",
        "**{author}** moved in close and completely seduced **{target}**! 🔥",
        "**{author}** whispered something that made **{target}** completely cave! 💋",
        "**{author}** used every trick to seduce **{target}** — and it worked! 😈",
        "**{author}** seduced **{target}** effortlessly, leaving them wanting more! 💦",
    ],
))

register(ActionConfig(
    name="makeout", category="intimate", affection_gain=30, xp_gain=35,
    cooldown_seconds=120, gif_category="makeout",
    description="Make out with someone",
    response_templates=[
        "**{author}** grabbed **{target}** and kissed them so deeply they forgot to breathe! 💋",
        "**{author}** and **{target}** made out passionately, completely lost in each other! 🔥",
        "**{author}** pinned **{target}** and made out with them hungrily! 😈",
        "**{author}** pulled **{target}** into a long, hot, sloppy makeout session! 💦",
        "**{author}** and **{target}** couldn't stop making out no matter who was watching! 😏",
    ],
))

register(ActionConfig(
    name="ride", category="intimate", affection_gain=45, xp_gain=55,
    cooldown_seconds=300, gif_category="ride",
    description="Ride someone",
    response_templates=[
        "**{author}** climbed on top of **{target}** and rode them hard! 🔥",
        "**{author}** pinned **{target}** down and rode them until they both lost their minds! 💦",
        "**{author}** took control and rode **{target}** at their own wild pace! 😈",
        "**{author}** sat down on **{target}** and rode them to oblivion! 💥",
        "**{author}** bounced on **{target}** relentlessly — they had zero complaints! 🌶️",
    ],
))

register(ActionConfig(
    name="cum", category="intimate", affection_gain=40, xp_gain=50,
    cooldown_seconds=300, gif_category="cum",
    self_targetable=True, requires_target=False,
    description="Cum on/for someone",
    response_templates=[
        "**{author}** came all over **{target}** and marked them completely! 💦",
        "**{author}** couldn't hold back and came hard all over **{target}**! 🔥",
        "**{author}** moaned **{target}**'s name as they came undone! 😩",
        "**{author}** made a total mess on **{target}** and didn't apologize! 😈",
        "**{author}** painted **{target}** white and stepped back to admire! 💥",
    ],
))

register(ActionConfig(
    name="undress", category="intimate", affection_gain=25, xp_gain=30,
    cooldown_seconds=120, gif_category="undress",
    description="Undress someone",
    response_templates=[
        "**{author}** slowly undressed **{target}**, taking their sweet time! 😏",
        "**{author}** peeled every layer off **{target}** with deliberate hands! 🔥",
        "**{author}** undressed **{target}** before they could even protest! 😈",
        "**{author}** stripped **{target}** down, leaving them completely bare! 💦",
        "**{author}** undressed **{target}** with hungry eyes the whole time! 💋",
    ],
))

register(ActionConfig(
    name="lickout", category="intimate", affection_gain=40, xp_gain=50,
    cooldown_seconds=240, gif_category="lickout",
    description="Go down on someone / eat someone out",
    response_templates=[
        "**{author}** buried their face between **{target}**'s thighs and went to town! 👅",
        "**{author}** ate **{target}** out until their legs stopped working! 🔥",
        "**{author}** licked **{target}** out slowly, savoring every second! 💦",
        "**{author}** had **{target}** grabbing the sheets with just their tongue! 😈",
        "**{author}** went down on **{target}** and didn't come up until they screamed! 💥",
    ],
))

register(ActionConfig(
    name="handjob", category="intimate", affection_gain=35, xp_gain=40,
    cooldown_seconds=180, gif_category="handjob",
    description="Give someone a handjob",
    response_templates=[
        "**{author}** wrapped their hand around **{target}** and stroked them slowly at first! 💦",
        "**{author}** gave **{target}** a handjob so good their knees went weak! 🔥",
        "**{author}** gripped **{target}** tight and worked them until they lost it! 😈",
        "**{author}** teased **{target}** with a slow, torturous handjob! 😏",
        "**{author}** stroked **{target}** off expertly — they didn't last long! 💥",
    ],
))

register(ActionConfig(
    name="titfuck", category="intimate", affection_gain=38, xp_gain=45,
    cooldown_seconds=240, gif_category="titfuck",
    description="Give someone a titfuck",
    response_templates=[
        "**{author}** pressed **{target}** between their chest and worked them slowly! 🔥",
        "**{author}** gave **{target}** a titfuck they'll be dreaming about for weeks! 💦",
        "**{author}** squeezed **{target}** between their breasts and looked up with a grin! 😈",
        "**{author}** wrapped **{target}** up snug and went to work — messy ending guaranteed! 💥",
        "**{author}** treated **{target}** to a slow, slippery titfuck until they exploded! 🌶️",
    ],
))

register(ActionConfig(
    name="anal", category="intimate", affection_gain=50, xp_gain=60,
    cooldown_seconds=300, gif_category="anal",
    description="Have anal sex with someone",
    response_templates=[
        "**{author}** pushed into **{target}**'s ass slowly and then gave them everything! 🔥",
        "**{author}** took **{target}**'s ass with zero hesitation! 💦",
        "**{author}** spread **{target}** open and fucked their ass deep and hard! 😈",
        "**{author}** filled **{target}**'s ass completely and didn't stop until they begged! 💥",
        "**{author}** wrecked **{target}**'s ass and left them a trembling mess! 🌶️",
    ],
))

register(ActionConfig(
    name="bondage", category="intimate", affection_gain=35, xp_gain=45,
    cooldown_seconds=240, gif_category="bondage",
    description="Tie someone up",
    response_templates=[
        "**{author}** tied **{target}** up tight and left them completely helpless! 🔥",
        "**{author}** bound **{target}**'s wrists and ankles — they weren't going anywhere! 😈",
        "**{author}** wrapped **{target}** in rope and admired their work! 💦",
        "**{author}** had **{target}** bound and blindfolded in seconds! 💥",
        "**{author}** tied **{target}** up so perfectly they couldn't even wiggle free! 🌶️",
    ],
))

register(ActionConfig(
    name="dominate", category="intimate", affection_gain=40, xp_gain=50,
    cooldown_seconds=240, gif_category="dominate",
    description="Dominate someone",
    response_templates=[
        "**{author}** pinned **{target}** down and made it very clear who was in charge! 🔥",
        "**{author}** grabbed **{target}** by the collar and dominated them completely! 😈",
        "**{author}** took full control of **{target}** and they loved every second! 💦",
        "**{author}** dominated **{target}** until they were completely and utterly broken in! 💥",
        "**{author}** had **{target}** submitting without a single word of protest! 😏",
    ],
))

register(ActionConfig(
    name="submit", category="intimate", affection_gain=35, xp_gain=45,
    cooldown_seconds=240, gif_category="submit",
    self_targetable=True, requires_target=False,
    description="Submit to someone",
    response_templates=[
        "**{author}** dropped to their knees and submitted fully to **{target}**! 💦",
        "**{author}** gave themselves over to **{target}** completely — body and soul! 🔥",
        "**{author}** bowed their head and submitted to **{target}**'s every command! 😈",
        "**{author}** let **{target}** take total control and surrendered willingly! 💥",
        "**{author}** submitted to **{target}** with a breathless, needy whimper! 😩",
    ],
))

register(ActionConfig(
    name="choke", category="intimate", affection_gain=30, xp_gain=40,
    cooldown_seconds=180, gif_category="choke",
    description="Choke someone during intimacy",
    response_templates=[
        "**{author}** wrapped their hand around **{target}**'s throat and squeezed just right! 🔥",
        "**{author}** choked **{target}** gently and watched their eyes roll back! 😈",
        "**{author}** gripped **{target}**'s throat firmly — they gasped and loved it! 💦",
        "**{author}** choked **{target}** with a steady hand and a dangerous smirk! 💥",
        "**{author}** took **{target}** by the throat and made them see stars! 🌶️",
    ],
))

register(ActionConfig(
    name="edging", category="intimate", affection_gain=38, xp_gain=48,
    cooldown_seconds=240, gif_category="edging",
    description="Edge someone relentlessly",
    response_templates=[
        "**{author}** brought **{target}** right to the edge and pulled back — again and again! 😈",
        "**{author}** edged **{target}** until they were sobbing and begging to finish! 🔥",
        "**{author}** kept **{target}** on the edge for so long they lost track of time! 💦",
        "**{author}** denied **{target}** over and over with a satisfied smirk! 😏",
        "**{author}** tortured **{target}** with relentless edging — no release in sight! 💥",
    ],
))

register(ActionConfig(
    name="gangbang", category="intimate", affection_gain=60, xp_gain=75,
    cooldown_seconds=600, gif_category="gangbang",
    description="Gangbang someone",
    response_templates=[
        "**{author}** organized a full gangbang with **{target}** at the center of it all! 🔥",
        "**{author}** and a crowd took turns wrecking **{target}** completely! 💦",
        "**{author}** had **{target}** completely surrounded and used from every angle! 😈",
        "**{author}** arranged a gangbang for **{target}** — they could barely walk after! 💥",
        "**{author}** let everyone have a turn with **{target}** until they were utterly spent! 🌶️",
    ],
))

register(ActionConfig(
    name="threesome", category="intimate", affection_gain=55, xp_gain=65,
    cooldown_seconds=420, gif_category="threesome",
    description="Have a threesome with someone",
    response_templates=[
        "**{author}** pulled in a third and had an absolutely wild threesome with **{target}**! 🔥",
        "**{author}** and **{target}** invited someone extra — the night got very interesting! 💦",
        "**{author}** arranged a threesome with **{target}** and nobody left unsatisfied! 😈",
        "**{author}** and **{target}** got tangled up with a third person in the best way! 💥",
        "**{author}** had a filthy threesome with **{target}** — details too hot to share! 🌶️",
    ],
))

register(ActionConfig(
    name="facesit", category="intimate", affection_gain=40, xp_gain=50,
    cooldown_seconds=240, gif_category="facesit",
    description="Sit on someone's face",
    response_templates=[
        "**{author}** sat right down on **{target}**'s face and made themselves comfortable! 💦",
        "**{author}** smothered **{target}** with a full facesit and dared them to complain! 🔥",
        "**{author}** lowered themselves onto **{target}**'s face with zero hesitation! 😈",
        "**{author}** facesit on **{target}** and rode their tongue until satisfied! 💥",
        "**{author}** gave **{target}** a facesit they'd been secretly dreaming about! 😏",
    ],
))

register(ActionConfig(
    name="cum_facial", category="intimate", affection_gain=42, xp_gain=52,
    cooldown_seconds=300, gif_category="cum_facial",
    description="Give someone a facial",
    response_templates=[
        "**{author}** finished all over **{target}**'s face and stepped back to admire! 💦",
        "**{author}** gave **{target}** a dripping facial they wore with zero shame! 🔥",
        "**{author}** painted **{target}**'s face completely and they didn't even flinch! 😈",
        "**{author}** unloaded on **{target}**'s face — they looked absolutely ruined! 💥",
        "**{author}** gave **{target}** a messy facial and called it a masterpiece! 🌶️",
    ],
))

register(ActionConfig(
    name="roleplay_sex", category="intimate", affection_gain=45, xp_gain=55,
    cooldown_seconds=300, gif_category="roleplay_sex",
    description="Do a sexual roleplay with someone",
    response_templates=[
        "**{author}** dragged **{target}** into a filthy sexual roleplay and neither held back! 🔥",
        "**{author}** started a spicy roleplay scenario with **{target}** — things escalated fast! 💦",
        "**{author}** and **{target}** got into a steamy roleplay that got very explicit very quickly! 😈",
        "**{author}** set the scene for a naughty roleplay and **{target}** played along perfectly! 💥",
        "**{author}** and **{target}** lost themselves completely in an explicit roleplay session! 🌶️",
    ],
))

register(ActionConfig(
    name="orgasm", category="intimate", affection_gain=50, xp_gain=60,
    cooldown_seconds=300, gif_category="orgasm",
    self_targetable=True, requires_target=False,
    description="Have an orgasm because of someone",
    response_templates=[
        "**{author}** came undone because of **{target}** — loudly and without shame! 💦",
        "**{author}** hit an earth-shattering orgasm thanks to **{target}**! 🔥",
        "**{author}** screamed **{target}**'s name as they orgasmed hard! 😩",
        "**{author}** lost complete control and orgasmed right in front of **{target}**! 💥",
        "**{author}** had the most intense orgasm of their life because of **{target}**! 🌶️",
    ],
))

register(ActionConfig(
    name="squirt", category="intimate", affection_gain=52, xp_gain=62,
    cooldown_seconds=360, gif_category="squirt",
    self_targetable=True, requires_target=False,
    description="Squirt because of someone",
    response_templates=[
        "**{author}** squirted all over **{target}** and couldn't even apologize! 💦",
        "**{author}** squirted so hard because of **{target}** — absolutely soaked! 🔥",
        "**{author}** lost complete control and squirted everywhere thanks to **{target}**! 😈",
        "**{author}** made a massive mess squirting all over **{target}**! 💥",
        "**{author}** squirted uncontrollably — **{target}** looked very proud of themselves! 😏",
    ],
))
