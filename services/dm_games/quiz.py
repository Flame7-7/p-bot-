"""Question-driven couple games: both partners answer, then the bot reveals."""
from __future__ import annotations

import difflib
import random
import re
from dataclasses import dataclass, field

import discord

from services.dm_games.board import TurnGame
from services.dm_games.session import GOLD, GameSession, Items
from utils.content import load_list, load_pairs
from utils.interactions import respond

Style = discord.ButtonStyle
LETTERS = "ABCDEFGH"
ROUNDS = 5


def pick(items: list, n: int = ROUNDS) -> list:
    return random.sample(items, min(n, len(items)))


def normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.casefold())


def fuzzy_match(a: str, b: str) -> bool:
    x, y = normalise(a), normalise(b)
    if not x or not y:
        return False
    return x == y or (min(len(x), len(y)) >= 4 and (x in y or y in x)) or difflib.SequenceMatcher(None, x, y).ratio() >= 0.82


@dataclass
class Round:
    prompt: str
    options: list[str]
    correct: int | None = None
    answers: dict[int, int] = field(default_factory=dict)


# ── single-phase multiple choice ─────────────────────────────────────────────


class ChoiceGame(GameSession):
    """Rounds of 'everyone picks an option', revealed together, with a Next button."""

    def __init__(self, manager, p1, p2) -> None:
        super().__init__(manager, p1, p2)
        self.rounds: list[Round] = []
        self.index = 0
        self.revealed = False
        self.score = {p1.id: 0, p2.id: 0}
        self.matches = 0

    # hooks
    def make_rounds(self) -> list[Round]:
        raise NotImplementedError

    def reveal_text(self, rnd: Round) -> str:
        raise NotImplementedError

    def on_reveal(self, rnd: Round) -> None:
        a, b = self.players
        if rnd.answers[a] == rnd.answers[b]:
            self.matches += 1

    def intro(self) -> str:
        return "You both answer — nothing is shown until you've both picked 💭"

    async def finish(self, interaction: discord.Interaction) -> None:
        await self.end(
            interaction=interaction,
            reason=f"💞 You agreed on **{self.matches}/{len(self.rounds)}**!",
            points=self.matches,
        )

    # machinery
    async def setup(self) -> None:
        self.rounds = self.make_rounds()
        if not self.rounds:
            raise RuntimeError(f"no content for {self.key}")

    def _answer(self, idx: int):
        async def handler(interaction: discord.Interaction) -> bool | None:
            rnd = self.rounds[self.index]
            uid = interaction.user.id
            if self.revealed or uid in rnd.answers:
                await respond(interaction, "You already answered 💭", ephemeral=True)
                return False
            rnd.answers[uid] = idx
            if len(rnd.answers) == 2:
                self.revealed = True
                self.on_reveal(rnd)
            return None
        return handler

    async def _next(self, interaction: discord.Interaction) -> bool | None:
        if not self.revealed:
            return False
        self.index += 1
        if self.index >= len(self.rounds):
            await self.finish(interaction)
            return False
        self.revealed = False
        return None

    def option_label(self, i: int, text: str) -> str:
        return f"{LETTERS[i]}) {text}"[:80]

    def render(self, uid: int) -> tuple[discord.Embed, Items]:
        rnd = self.rounds[min(self.index, len(self.rounds) - 1)]
        head = f"Round {min(self.index + 1, len(self.rounds))}/{len(self.rounds)}"
        items: Items = []
        if self.ended_reason:
            return self.embed(f"**{rnd.prompt}**\n\n{self.reveal_text(rnd) if self.revealed else ''}\n\n{self.ended_reason}"), items
        if self.revealed:
            last = self.index == len(self.rounds) - 1
            items.append(self.button("Finish" if last else "Next", self._next, style=Style.primary, emoji="✨" if last else "▶️", row=0))
            items.append(self.quit_button(row=0))
            return self.embed(f"{head}\n\n**{rnd.prompt}**\n\n{self.reveal_text(rnd)}"), items

        mine = rnd.answers.get(uid)
        lines = "\n".join(f"**{LETTERS[i]})** {o}" for i, o in enumerate(rnd.options))
        footer = (
            f"✅ You picked **{LETTERS[mine]}** — waiting for {self.name(self.other(uid))}…" if mine is not None else self.intro()
        )
        for i, text in enumerate(rnd.options):
            items.append(self.button(
                self.option_label(i, text), self._answer(i), row=i,
                style=Style.success if mine == i else Style.primary if i % 2 == 0 else Style.secondary,
                disabled=mine is not None,
            ))
        items.append(self.quit_button(row=min(len(rnd.options), 4)))
        return self.embed(f"{head}\n\n**{rnd.prompt}**\n{lines}\n\n{footer}"), items

    def picks_text(self, rnd: Round) -> str:
        return "\n".join(f"{self.mention(u)} → **{LETTERS[rnd.answers[u]]}) {rnd.options[rnd.answers[u]]}**" for u in self.players)


class PairGame(ChoiceGame):
    """Would You Rather / This or That: two options per round, see if you agree."""

    content_path = "couple/would_you_rather.md"
    verdict_agree = "💞 You two agree!"
    verdict_differ = "🤔 Different picks — talk it out!"
    prompt = "Would you rather…"

    def make_rounds(self) -> list[Round]:
        pairs = [p for p in load_pairs(self.content_path) if len(p) == 2]
        return [Round(self.prompt, [a, b]) for a, b in pick(pairs)]

    def reveal_text(self, rnd: Round) -> str:
        a, b = self.players
        same = rnd.answers.get(a) == rnd.answers.get(b)
        return f"{self.picks_text(rnd)}\n\n{self.verdict_agree if same else self.verdict_differ}"


class WouldYouRather(PairGame):
    key, title, emoji, stats_game = "wyr", "Would You Rather", "🤍", "wyr"
    category, blurb, duration = "Funny", 'Five dilemmas — do you agree?', "~5 min"


class ThisOrThat(PairGame):
    key, title, emoji, stats_game = "thisorthat", "This or That", "⚡", "thisorthat"
    category, blurb, duration = "Funny", 'Rapid-fire preferences', "~3 min"
    content_path = "couple/this_or_that.md"
    prompt = "This or that?"


class Compatibility(ChoiceGame):
    key, title, emoji, stats_game = "compat", "Compatibility Quiz", "💘", "compat"
    category, blurb, duration = "Relationship", 'Get your match percentage', "~5 min"

    def make_rounds(self) -> list[Round]:
        rows = [r for r in load_pairs("couple/compatibility.md") if len(r) >= 3]
        return [Round(q, list(opts)) for q, *opts in pick(rows, 6)]

    def reveal_text(self, rnd: Round) -> str:
        a, b = self.players
        same = rnd.answers[a] == rnd.answers[b]
        return f"{self.picks_text(rnd)}\n\n{'💞 Match!' if same else '🌗 Opposites attract…'}"

    async def finish(self, interaction: discord.Interaction) -> None:
        pct = round(100 * self.matches / len(self.rounds))
        verdict = (
            "Soulmate energy ✨" if pct >= 80 else "Beautifully in sync 💕" if pct >= 55
            else "Different, in the best way 🌈" if pct >= 30 else "Opposites attract 🧲"
        )
        await self.end(interaction=interaction, reason=f"💘 **{pct}% compatible** — {verdict}", points=pct)


class MostLikely(ChoiceGame):
    key, title, emoji, stats_game = "mostlikely", "Who's More Likely To…", "🙋", "mostlikely"
    category, blurb, duration = "Funny", 'Point at who it would be', "~5 min"

    def make_rounds(self) -> list[Round]:
        names = [self.name(p) for p in self.players]
        return [Round(f"Who is more likely to {q}?", names) for q in pick(load_list("couple/most_likely.md"))]

    def option_label(self, i: int, text: str) -> str:
        return text[:80]

    def intro(self) -> str:
        return "Point at who it'd be (it can be yourself 😏) — revealed once you've both picked."

    def reveal_text(self, rnd: Round) -> str:
        a, b = self.players
        if rnd.answers[a] == rnd.answers[b]:
            return f"{self.picks_text(rnd)}\n\n🤝 You both say **{rnd.options[rnd.answers[a]]}**!"
        return f"{self.picks_text(rnd)}\n\n😂 You each think it's the other… or yourselves. Debate!"

    async def finish(self, interaction: discord.Interaction) -> None:
        await self.end(interaction=interaction, reason=f"🙋 You agreed on **{self.matches}/{len(self.rounds)}** rounds!", points=self.matches)


class Trivia(ChoiceGame):
    key, title, emoji, stats_game = "trivia", "Trivia", "🧩", "trivia"
    category, blurb, duration = "Brain", 'Five questions, higher score wins', "~5 min"
    difficulty = "Medium"

    def make_rounds(self) -> list[Round]:
        rows = [r for r in load_pairs("couple/trivia.md") if len(r) >= 3]
        rounds = []
        for q, correct, *wrong in pick(rows):
            options = [correct, *wrong[:3]]
            random.shuffle(options)
            rounds.append(Round(q, options, correct=options.index(correct)))
        return rounds

    def intro(self) -> str:
        return "Fastest isn't better — just get it right 🧠"

    def on_reveal(self, rnd: Round) -> None:
        for u in self.players:
            if rnd.answers[u] == rnd.correct:
                self.score[u] += 1

    def reveal_text(self, rnd: Round) -> str:
        assert rnd.correct is not None
        marks = "\n".join(
            f"{'✅' if rnd.answers[u] == rnd.correct else '❌'} {self.mention(u)} → {rnd.options[rnd.answers[u]]}"
            for u in self.players
        )
        return f"{marks}\n\nAnswer: **{LETTERS[rnd.correct]}) {rnd.options[rnd.correct]}**"

    async def finish(self, interaction: discord.Interaction) -> None:
        a, b = self.players
        summary = f"**{self.name(a)}** {self.score[a]} — {self.score[b]} **{self.name(b)}**"
        if self.score[a] == self.score[b]:
            await self.end(interaction=interaction, reason=f"{summary}\n🤝 A tie — equally clever!", draw=True)
        else:
            w = a if self.score[a] > self.score[b] else b
            await self.end(interaction=interaction, reason=f"{summary}\n🎉 {self.mention(w)} wins!", winner=w)


# ── two-phase: answer about yourself, then guess your partner ────────────────


class KnowGame(GameSession):
    """'Who knows who better?' (multiple choice) and 'Guess my favourite' (free text)."""

    key, title, emoji, stats_game = "knowme", "Who Knows Who Better?", "🔍", "knowme"
    category, blurb, duration = "Relationship", 'Answer about yourself, then guess your partner', "~8 min"
    difficulty = "Medium"
    free_text = False

    def __init__(self, manager, p1, p2) -> None:
        super().__init__(manager, p1, p2)
        self.rounds: list[Round] = []
        self.own: list[dict[int, str]] = []
        self.guess: list[dict[int, str]] = []
        self.index = 0
        self.phase = "own"  # own -> guess -> reveal
        self.score = {p1.id: 0, p2.id: 0}

    async def setup(self) -> None:
        if self.free_text:
            prompts = pick(load_list("couple/favourites.md"))
            self.rounds = [Round(p, []) for p in prompts]
        else:
            rows = [r for r in load_pairs("couple/know_me.md") if len(r) >= 3]
            self.rounds = [Round(q, list(opts)) for q, *opts in pick(rows)]
        if not self.rounds:
            raise RuntimeError("no content for know-me game")
        self.own = [{} for _ in self.rounds]
        self.guess = [{} for _ in self.rounds]

    # handlers
    async def _submit(self, interaction: discord.Interaction, text: str) -> bool | None:
        uid = interaction.user.id
        store = self.own[self.index] if self.phase == "own" else self.guess[self.index]
        if self.phase == "reveal" or uid in store:
            await respond(interaction, "You already answered 💭", ephemeral=True)
            return False
        store[uid] = text
        if len(store) == 2:
            if self.phase == "own":
                self.phase = "guess"
            else:
                self.phase = "reveal"
                for u in self.players:
                    if self._correct(self.guess[self.index][u], self.own[self.index][self.other(u)]):
                        self.score[u] += 1
        return None

    def _correct(self, guess: str, truth: str) -> bool:
        return fuzzy_match(guess, truth) if self.free_text else guess == truth

    def _choose(self, option: str):
        async def handler(interaction: discord.Interaction) -> bool | None:
            return await self._submit(interaction, option)
        return handler

    async def _open_modal(self, interaction: discord.Interaction) -> bool:
        about = "about YOU" if self.phase == "own" else f"about {self.name(self.other(interaction.user.id))}"
        return await self.ask(
            interaction, "Your answer", f"Your answer ({about})"[:45], self._submit, max_length=80,
            placeholder="keep it short",
        )

    async def _next(self, interaction: discord.Interaction) -> bool | None:
        if self.phase != "reveal":
            return False
        self.index += 1
        if self.index >= len(self.rounds):
            a, b = self.players
            summary = f"**{self.name(a)}** {self.score[a]} — {self.score[b]} **{self.name(b)}**"
            if self.score[a] == self.score[b]:
                await self.end(interaction=interaction, reason=f"{summary}\n💞 You know each other equally well!", draw=True)
            else:
                w = a if self.score[a] > self.score[b] else b
                await self.end(interaction=interaction, reason=f"{summary}\n🎉 {self.mention(w)} knows their partner best!", winner=w)
            return False
        self.phase = "own"
        return None

    def render(self, uid: int) -> tuple[discord.Embed, Items]:
        i = min(self.index, len(self.rounds) - 1)
        rnd = self.rounds[i]
        head = f"Round {i + 1}/{len(self.rounds)}"
        partner = self.name(self.other(uid))
        items: Items = []
        if self.ended_reason:
            return self.embed(f"{head}\n\n**{rnd.prompt}**\n\n{self.ended_reason}"), items

        if self.phase == "reveal":
            lines = []
            for u in self.players:
                truth = self.own[i][u]
                guess = self.guess[i][self.other(u)]
                ok = self._correct(guess, truth)
                lines.append(f"{'✅' if ok else '❌'} {self.name(u)} is: **{truth}** — {self.name(self.other(u))} guessed **{guess}**")
            last = self.index == len(self.rounds) - 1
            items.append(self.button("Finish" if last else "Next", self._next, style=Style.primary, emoji="▶️", row=0))
            items.append(self.quit_button(row=0))
            return self.embed(f"{head}\n\n**{rnd.prompt}**\n\n" + "\n".join(lines)), items

        store = self.own[i] if self.phase == "own" else self.guess[i]
        done = uid in store
        if self.phase == "own":
            ask = f"**Answer for yourself.** {partner} will try to guess it later 🤫"
        else:
            ask = f"**Now guess what {partner} answered.**"
        status = f"✅ Locked in — waiting for {partner}…" if done else ask
        if self.free_text:
            items.append(self.button("Answer", self._open_modal, style=Style.primary, emoji="✏️", row=0, disabled=done))
            items.append(self.quit_button(row=0))
        else:
            for k, opt in enumerate(rnd.options):
                items.append(self.button(f"{LETTERS[k]}) {opt}"[:80], self._choose(opt), row=k, style=Style.primary, disabled=done))
            items.append(self.quit_button(row=min(len(rnd.options), 4)))
        opts = "\n".join(f"**{LETTERS[k]})** {o}" for k, o in enumerate(rnd.options))
        phase_tag = "Step 1 · about you" if self.phase == "own" else "Step 2 · guess your partner"
        return self.embed(f"{head} — *{phase_tag}*\n\n**{rnd.prompt}**\n{opts}\n\n{status}"), items


class GuessFavourite(KnowGame):
    key, title, emoji, stats_game = "favourite", "Guess My Favourite", "💝", "favourite"
    category, blurb, duration = "Relationship", "Free-text favourites, guess each other's", "~8 min"
    difficulty = "Medium"
    free_text = True


# ── first to guess (emoji / scrambled word) ──────────────────────────────────


class GuessRounds(GameSession):
    """Both guess the same puzzle; first correct answer wins the round."""

    puzzle_label = "Puzzle"
    content_path = ""
    MAX_WRONG = 4

    def __init__(self, manager, p1, p2) -> None:
        super().__init__(manager, p1, p2)
        self.puzzles: list[tuple[str, list[str]]] = []
        self.index = 0
        self.round_over = False
        self.round_note = ""
        self.wrong = 0
        self.score = {p1.id: 0, p2.id: 0}

    def make_puzzles(self) -> list[tuple[str, list[str]]]:
        raise NotImplementedError

    async def setup(self) -> None:
        self.puzzles = self.make_puzzles()
        if not self.puzzles:
            raise RuntimeError(f"no content for {self.key}")

    async def _guess(self, interaction: discord.Interaction, text: str) -> bool | None:
        if self.round_over:
            await respond(interaction, "Too slow — that round is over!", ephemeral=True)
            return False
        _, answers = self.puzzles[self.index]
        if any(normalise(text) == normalise(a) for a in answers):
            uid = interaction.user.id
            self.score[uid] += 1
            self.round_over = True
            self.round_note = f"🎉 {self.mention(uid)} got it: **{answers[0]}**"
            return None
        self.wrong += 1
        if self.wrong >= self.MAX_WRONG:
            self.round_over = True
            self.round_note = f"😅 Nobody got it — it was **{answers[0]}**"
            return None
        await respond(interaction, f"Not quite! ({self.MAX_WRONG - self.wrong} tries left for the team)", ephemeral=True)
        return False

    async def _open(self, interaction: discord.Interaction) -> bool:
        return await self.ask(interaction, "Your guess", "What is it?", self._guess, max_length=60)

    async def _skip(self, interaction: discord.Interaction) -> bool | None:
        if self.round_over:
            return False
        self.round_over = True
        self.round_note = f"⏭️ Skipped — it was **{self.puzzles[self.index][1][0]}**"
        return None

    async def _next(self, interaction: discord.Interaction) -> bool | None:
        if not self.round_over:
            return False
        self.index += 1
        if self.index >= len(self.puzzles):
            a, b = self.players
            summary = f"**{self.name(a)}** {self.score[a]} — {self.score[b]} **{self.name(b)}**"
            if self.score[a] == self.score[b]:
                await self.end(interaction=interaction, reason=f"{summary}\n🤝 A tie!", draw=True)
            else:
                w = a if self.score[a] > self.score[b] else b
                await self.end(interaction=interaction, reason=f"{summary}\n🎉 {self.mention(w)} wins!", winner=w)
            return False
        self.round_over = False
        self.round_note = ""
        self.wrong = 0
        return None

    def render(self, uid: int) -> tuple[discord.Embed, Items]:
        i = min(self.index, len(self.puzzles) - 1)
        puzzle, _ = self.puzzles[i]
        a, b = self.players
        desc = (
            f"Round {i + 1}/{len(self.puzzles)} • **{self.name(a)}** {self.score[a]} — {self.score[b]} **{self.name(b)}**\n\n"
            f"{self.puzzle_label}: # {puzzle}\n\n"
        )
        items: Items = []
        if self.ended_reason:
            return self.embed(desc + (self.round_note or "") + f"\n\n{self.ended_reason}"), items
        if self.round_over:
            last = self.index == len(self.puzzles) - 1
            items.append(self.button("Finish" if last else "Next", self._next, style=Style.primary, emoji="▶️", row=0))
            desc += self.round_note
        else:
            items.append(self.button("Guess", self._open, style=Style.primary, emoji="💭", row=0))
            items.append(self.button("Skip", self._skip, row=0, emoji="⏭️"))
            desc += "First correct guess wins the round!"
        items.append(self.quit_button(row=0))
        return self.embed(desc), items


class EmojiGuess(GuessRounds):
    key, title, emoji, stats_game = "emoji", "Emoji Guessing", "😎", "emoji"
    category, blurb, duration = "Brain", 'Decode the emoji puzzle first', "~5 min"
    difficulty = "Medium"
    puzzle_label = "Guess the movie / phrase"

    def make_puzzles(self) -> list[tuple[str, list[str]]]:
        rows = [r for r in load_pairs("couple/emoji_puzzles.md") if len(r) == 2]
        return [(e, [x.strip() for x in ans.split("/")]) for e, ans in pick(rows)]


class WordScramble(GuessRounds):
    key, title, emoji, stats_game = "word", "Word Guessing", "🔤", "word"
    category, blurb, duration = "Brain", 'Unscramble the word first', "~5 min"
    difficulty = "Medium"
    puzzle_label = "Unscramble"

    def make_puzzles(self) -> list[tuple[str, list[str]]]:
        puzzles = []
        for word in pick(load_list("couple/words.md")):
            letters = list(word.upper())
            for _ in range(10):
                random.shuffle(letters)
                if "".join(letters) != word.upper():
                    break
            puzzles.append((" ".join(letters), [word]))
        return puzzles


# ── Truth or Dare (open-ended, take turns) ───────────────────────────────────


class TruthOrDare(TurnGame):
    key, title, emoji = "truthordare", "Truth or Dare", "🎭"
    category, blurb, duration = "Funny", 'Take turns, couple edition', "Open-ended"
    stats_game = None

    def __init__(self, manager, p1, p2) -> None:
        super().__init__(manager, p1, p2)
        self.kind: str | None = None
        self.prompt: str | None = None
        self.rerolled = False
        self.done = {"truth": 0, "dare": 0}
        self._seen: set[str] = set()

    def _roll(self, kind: str) -> str:
        pool = load_list(f"couple/{kind}.md") or ["Tell your partner something you love about them."]
        fresh = [p for p in pool if p not in self._seen] or pool
        choice = random.choice(fresh)
        self._seen.add(choice)
        return choice

    def _choose(self, kind: str):
        async def handler(interaction: discord.Interaction) -> bool | None:
            if not await self.guard_turn(interaction):
                return False
            self.kind, self.prompt, self.rerolled = kind, self._roll(kind), False
            return None
        return handler

    async def _reroll(self, interaction: discord.Interaction) -> bool | None:
        if not await self.guard_turn(interaction) or not self.kind or self.rerolled:
            return False
        self.prompt, self.rerolled = self._roll(self.kind), True
        return None

    def _finish_turn(self, completed: bool):
        async def handler(interaction: discord.Interaction) -> bool | None:
            if not await self.guard_turn(interaction) or not self.kind:
                return False
            if completed:
                self.done[self.kind] += 1
            self.kind = self.prompt = None
            self.switch_turn()
            return None
        return handler

    def render(self, uid: int) -> tuple[discord.Embed, Items]:
        mine = uid == self.turn and self.active
        tally = f"💭 {self.done['truth']} truths • 🎯 {self.done['dare']} dares done"
        items: Items = []
        if self.ended_reason:
            return self.embed(f"{tally}\n\n{self.ended_reason}"), items
        if self.kind is None:
            desc = f"{self.status_line()}\nPick **Truth** or **Dare**!" if mine else f"Waiting for {self.mention(self.turn)} to choose…"
            items.append(self.button("Truth", self._choose("truth"), style=Style.primary, emoji="💭", row=0, disabled=not mine))
            items.append(self.button("Dare", self._choose("dare"), style=Style.danger, emoji="🎯", row=0, disabled=not mine))
        else:
            label = "💭 Truth" if self.kind == "truth" else "🎯 Dare"
            desc = (
                f"{self.mention(self.turn)} — **{label}**\n\n> {self.prompt}\n\n"
                "Reply right here in your DMs — I'll pass your messages along. Tap **Done** when you've done it."
            )
            items.append(self.button("Done", self._finish_turn(True), style=Style.success, emoji="✅", row=0, disabled=not mine))
            items.append(self.button("Another", self._reroll, emoji="🔄", row=0, disabled=not mine or self.rerolled))
            items.append(self.button("Skip", self._finish_turn(False), emoji="⏭️", row=0, disabled=not mine))
        items.append(self.quit_button(row=0))
        return self.embed(f"{desc}\n\n{tally}", color=GOLD), items


# ── Pick one for tonight ─────────────────────────────────────────────────────


class PickOne(ChoiceGame):
    key, title, emoji, stats_game = "pickone", "Pick One for Tonight", "🌙", None
    category, blurb, duration = "Relationship", 'Settle what to do tonight', "~1 min"

    def __init__(self, manager, p1, p2) -> None:
        super().__init__(manager, p1, p2)
        self._tiebreak: str | None = None

    def make_rounds(self) -> list[Round]:
        rows = [r for r in load_pairs("couple/pick_one.md") if len(r) >= 2]
        return [Round("What are we doing tonight?", list(random.choice(rows)))]

    def intro(self) -> str:
        return "Both pick what you're in the mood for 🌙"

    def reveal_text(self, rnd: Round) -> str:
        a, b = self.players
        if rnd.answers[a] == rnd.answers[b]:
            return f"{self.picks_text(rnd)}\n\n✨ Decided: **{rnd.options[rnd.answers[a]]}**!"
        if self._tiebreak is None:
            self._tiebreak = rnd.options[rnd.answers[random.choice(self.players)]]
        return f"{self.picks_text(rnd)}\n\n🎲 Different picks — the dice say: **{self._tiebreak}**"

    async def finish(self, interaction: discord.Interaction) -> None:
        await self.end(interaction=interaction, reason="🌙 Enjoy your night together!", record=False)


# ── Daily question ───────────────────────────────────────────────────────────


class DailyQuestion(GameSession):
    """One question of the day; answers are revealed once both partners reply."""

    key, title, emoji, stats_game = "daily", "Daily Question", "☀️", "daily"

    def __init__(self, manager, p1, p2, question: str = "") -> None:
        super().__init__(manager, p1, p2)
        self.question = question
        self.answers: dict[int, str] = {}

    async def _answer(self, interaction: discord.Interaction, text: str) -> bool | None:
        uid = interaction.user.id
        if uid in self.answers:
            await respond(interaction, "You already answered 💭", ephemeral=True)
            return False
        self.answers[uid] = text
        if len(self.answers) == 2:
            await self.end(interaction=interaction, reason="💞 That's today's question — until tomorrow!")
            return False
        return None

    async def _open(self, interaction: discord.Interaction) -> bool:
        return await self.ask(
            interaction, "Today's question", "Your answer", self._answer, max_length=300, placeholder="be honest 💕"
        )

    def render(self, uid: int) -> tuple[discord.Embed, Items]:
        items: Items = []
        if len(self.answers) == 2:
            lines = "\n\n".join(f"**{self.name(u)}**\n{self.answers[u]}" for u in self.players)
            return self.embed(f"**{self.question}**\n\n{lines}\n\n{self.ended_reason or ''}"), items
        if self.ended_reason:
            return self.embed(f"**{self.question}**\n\n{self.ended_reason}"), items
        mine = uid in self.answers
        status = f"✅ Answered — waiting for {self.name(self.other(uid))}…" if mine else "Answer privately — you'll both see the replies together."
        items.append(self.button("Answer", self._open, style=Style.primary, emoji="✏️", row=0, disabled=mine))
        items.append(self.quit_button(row=0))
        return self.embed(f"**{self.question}**\n\n{status}", color=GOLD), items
