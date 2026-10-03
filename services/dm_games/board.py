"""Turn-based and simultaneous two-player games played with buttons/selects."""
from __future__ import annotations

import asyncio
import random
import re

import discord

from services.dm_games.session import GOLD, GameSession, Items
from utils.content import load_list
from utils.interactions import respond

Style = discord.ButtonStyle


class TurnGame(GameSession):
    """Adds a turn pointer and the 'not your turn' guard."""

    def __init__(self, manager, p1, p2) -> None:
        super().__init__(manager, p1, p2)
        self.turn: int = p1.id

    def switch_turn(self) -> None:
        self.turn = self.other(self.turn)

    def status_line(self) -> str:
        return f"It's {self.mention(self.turn)}'s turn 💗"

    async def guard_turn(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.turn:
            await respond(interaction, "Not your turn yet — hang tight 💕", ephemeral=True)
            return False
        return True


# ── Tic-Tac-Toe ──────────────────────────────────────────────────────────────

WIN_LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]


def ttt_result(board: list[str | None]) -> str | None:
    """The winning mark, 'draw', or None while the game is still going."""
    for a, b, c in WIN_LINES:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return "draw" if all(board) else None


class TicTacToe(TurnGame):
    key, title, emoji, stats_game = "ttt", "Tic-Tac-Toe", "⭕", "tictactoe"
    category, blurb, duration = "Competitive", 'Classic 3×3, synced across both DMs', "~3–5 min"
    difficulty = "Easy"

    def __init__(self, manager, p1, p2) -> None:
        super().__init__(manager, p1, p2)
        self.marks = {p1.id: "❌", p2.id: "⭕"}
        self.board: list[str | None] = [None] * 9

    def _play(self, idx: int):
        async def handler(interaction: discord.Interaction) -> bool | None:
            uid = interaction.user.id
            if not await self.guard_turn(interaction):
                return False
            if self.board[idx] is not None:
                await respond(interaction, "That spot's taken.", ephemeral=True)
                return False
            self.board[idx] = self.marks[uid]
            outcome = ttt_result(self.board)
            if outcome == "draw":
                await self.end(interaction=interaction, reason="🤝 It's a draw!", draw=True)
                return False
            if outcome:
                await self.end(interaction=interaction, reason=f"🎉 {self.mention(uid)} wins!", winner=uid)
                return False
            self.switch_turn()
            return None
        return handler

    def render(self, uid: int) -> tuple[discord.Embed, Items]:
        status = self.ended_reason or self.status_line()
        legend = "  ".join(f"{self.marks[p]} {self.mention(p)}" for p in self.players)
        items: Items = []
        for i, mark in enumerate(self.board):
            items.append(self.button(
                mark or "\u200b", self._play(i), row=i // 3,
                style=Style.danger if mark == "❌" else Style.success if mark == "⭕" else Style.secondary,
                disabled=mark is not None or not self.active or self.turn != uid,
            ))
        items.append(self.quit_button(row=3))
        return self.embed(f"{legend}\n\n{status}"), items


# ── Connect 4 ────────────────────────────────────────────────────────────────

C4_COLS, C4_ROWS = 7, 6


class Connect4(TurnGame):
    key, title, emoji, stats_game = "connect4", "Connect 4", "🔴", "connect4"
    category, blurb, duration = "Competitive", 'Drop discs, get four in a row', "~5–10 min"
    difficulty = "Medium"

    def __init__(self, manager, p1, p2) -> None:
        super().__init__(manager, p1, p2)
        self.marks = {p1.id: "🔴", p2.id: "🟡"}
        self.grid: list[list[str]] = [[] for _ in range(C4_COLS)]  # bottom-to-top per column

    def _cell(self, col: int, row: int) -> str | None:
        if 0 <= col < C4_COLS and 0 <= row < len(self.grid[col]):
            return self.grid[col][row]
        return None

    def result(self) -> str | None:
        for col in range(C4_COLS):
            for row in range(len(self.grid[col])):
                mark = self.grid[col][row]
                for dc, dr in ((1, 0), (0, 1), (1, 1), (1, -1)):
                    if all(self._cell(col + dc * i, row + dr * i) == mark for i in range(4)):
                        return mark
        return "draw" if all(len(c) == C4_ROWS for c in self.grid) else None

    def _drop(self, col: int):
        async def handler(interaction: discord.Interaction) -> bool | None:
            uid = interaction.user.id
            if not await self.guard_turn(interaction):
                return False
            if len(self.grid[col]) >= C4_ROWS:
                await respond(interaction, "That column's full.", ephemeral=True)
                return False
            self.grid[col].append(self.marks[uid])
            outcome = self.result()
            if outcome == "draw":
                await self.end(interaction=interaction, reason="🤝 It's a draw!", draw=True)
                return False
            if outcome:
                await self.end(interaction=interaction, reason=f"🎉 {self.mention(uid)} wins!", winner=uid)
                return False
            self.switch_turn()
            return None
        return handler

    def render(self, uid: int) -> tuple[discord.Embed, Items]:
        rows = []
        for r in reversed(range(C4_ROWS)):
            rows.append("".join(self.grid[c][r] if r < len(self.grid[c]) else "⚪" for c in range(C4_COLS)))
        rows.append("1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣7️⃣")
        legend = "  ".join(f"{self.marks[p]} {self.mention(p)}" for p in self.players)
        status = self.ended_reason or self.status_line()
        items: Items = []
        for c in range(C4_COLS):
            items.append(self.button(
                str(c + 1), self._drop(c), row=0 if c < 5 else 1,  # Discord allows 5 buttons per row
                disabled=len(self.grid[c]) >= C4_ROWS or not self.active or self.turn != uid,
            ))
        items.append(self.quit_button(row=1))
        return self.embed(f"{legend}\n\n" + "\n".join(rows) + f"\n\n{status}"), items


# ── Rock Paper Scissors (best of 3, simultaneous) ────────────────────────────

RPS_EMOJI = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
RPS_BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}


class RockPaperScissors(GameSession):
    key, title, emoji, stats_game = "rps", "Rock Paper Scissors", "✂️", "rps"
    category, blurb, duration = "Chance", 'Best of 3 with secret picks', "~2 min"
    difficulty = "Easy"
    WIN_AT = 2

    def __init__(self, manager, p1, p2) -> None:
        super().__init__(manager, p1, p2)
        self.picks: dict[int, str] = {}
        self.score = {p1.id: 0, p2.id: 0}
        self.last_round = "Pick your move — it stays secret until you both choose."

    def _pick(self, choice: str):
        async def handler(interaction: discord.Interaction) -> bool | None:
            uid = interaction.user.id
            if uid in self.picks:
                await respond(interaction, "You already chose — waiting for your partner 💭", ephemeral=True)
                return False
            self.picks[uid] = choice
            if len(self.picks) < 2:
                return None
            a, b = self.players
            pa, pb = self.picks[a], self.picks[b]
            self.picks = {}
            line = f"{RPS_EMOJI[pa]} {self.name(a)} vs {RPS_EMOJI[pb]} {self.name(b)} — "
            if pa == pb:
                self.last_round = line + "tie! Go again."
            else:
                round_winner = a if RPS_BEATS[pa] == pb else b
                self.score[round_winner] += 1
                self.last_round = line + f"{self.name(round_winner)} takes the round!"
                if self.score[round_winner] >= self.WIN_AT:
                    await self.end(
                        interaction=interaction,
                        reason=f"{self.last_round}\n🎉 {self.mention(round_winner)} wins the match!",
                        winner=round_winner,
                    )
                    return False
            return None
        return handler

    def render(self, uid: int) -> tuple[discord.Embed, Items]:
        a, b = self.players
        waiting = uid in self.picks
        desc = (
            f"**{self.name(a)}** {self.score[a]} — {self.score[b]} **{self.name(b)}**  *(first to {self.WIN_AT})*\n\n"
            f"{self.ended_reason or self.last_round}"
        )
        if waiting and self.active:
            desc += f"\n\nYou chose {RPS_EMOJI[self.picks[uid]]} — waiting for {self.name(self.other(uid))}…"
        items: Items = [
            self.button(name.title(), self._pick(name), emoji=emo, row=0, disabled=waiting or not self.active)
            for name, emo in RPS_EMOJI.items()
        ]
        items.append(self.quit_button(row=0))
        return self.embed(desc), items


# ── Memory (4x4 emoji pairs, turn-based) ─────────────────────────────────────


class MemoryGame(TurnGame):
    key, title, emoji, stats_game = "memory", "Memory", "🧠", "memory"
    category, blurb, duration = "Brain", 'Match the emoji pairs, take turns', "~5 min"
    difficulty = "Medium"
    FLIP_BACK_DELAY = 1.3

    def __init__(self, manager, p1, p2) -> None:
        super().__init__(manager, p1, p2)
        self.cards: list[str] = []
        self.matched: set[int] = set()
        self.flipped: list[int] = []
        self.score = {p1.id: 0, p2.id: 0}

    async def setup(self) -> None:
        pool = load_list("couple/memory_emojis.md") or ["🍓", "🌙", "🌸", "🎧", "🍕", "🦋", "⭐", "🐱"]
        deck = random.sample(pool, 8) * 2
        random.shuffle(deck)
        self.cards = deck

    def _flip(self, idx: int):
        async def handler(interaction: discord.Interaction) -> bool | None:
            uid = interaction.user.id
            if not await self.guard_turn(interaction):
                return False
            if idx in self.matched or idx in self.flipped:
                return False
            self.flipped.append(idx)
            if len(self.flipped) < 2:
                return None

            first, second = self.flipped
            if self.cards[first] == self.cards[second]:
                self.matched.update(self.flipped)
                self.score[uid] += 1
                self.flipped = []
                if len(self.matched) == len(self.cards):
                    a, b = self.players
                    if self.score[a] == self.score[b]:
                        await self.end(interaction=interaction, reason="🤝 All matched — it's a tie!", draw=True)
                    else:
                        w = a if self.score[a] > self.score[b] else b
                        await self.end(interaction=interaction, reason=f"🎉 {self.mention(w)} wins the memory game!", winner=w)
                    return False
                return None  # matched: same player goes again

            await self.push(interaction)  # show both cards, then flip them back
            await asyncio.sleep(self.FLIP_BACK_DELAY)
            self.flipped = []
            self.switch_turn()
            return True
        return handler

    def render(self, uid: int) -> tuple[discord.Embed, Items]:
        a, b = self.players
        items: Items = []
        for i, card in enumerate(self.cards):
            shown = i in self.matched or i in self.flipped
            items.append(self.button(
                card if shown else "❔", self._flip(i), row=i // 4,
                style=Style.success if i in self.matched else Style.primary if shown else Style.secondary,
                disabled=shown or not self.active or self.turn != uid or len(self.flipped) >= 2,
            ))
        items.append(self.quit_button(row=4))
        status = self.ended_reason or self.status_line()
        desc = f"**{self.name(a)}** {self.score[a]} — {self.score[b]} **{self.name(b)}**\n\n{status}"
        return self.embed(desc), items


# ── Hangman ──────────────────────────────────────────────────────────────────

HANGMAN_STAGES = [
    "```\n  +---+\n  |   |\n      |\n      |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n      |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n  |   |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n /|   |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n /    |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n / \\  |\n=========```",
]
WORD_RE = re.compile(r"^[A-Za-z][A-Za-z ]{1,18}[A-Za-z]$")
LETTER_HALVES = ("ABCDEFGHIJKLM", "NOPQRSTUVWXYZ")


class Hangman(GameSession):
    """The first player secretly sets a word; the other guesses it letter by letter."""

    key, title, emoji, stats_game = "hangman", "Hangman", "🪢", "hangman"
    category, blurb, duration = "Brain", 'One sets a secret word, the other guesses it', "~5 min"
    difficulty = "Medium"
    MAX_WRONG = 6

    def __init__(self, manager, p1, p2) -> None:
        super().__init__(manager, p1, p2)
        self.setter, self.guesser = p1.id, p2.id
        self.word: str | None = None
        self.guessed: set[str] = set()

    @property
    def wrong(self) -> list[str]:
        return sorted(l for l in self.guessed if self.word and l not in self.word)

    def masked(self) -> str:
        assert self.word
        return " ".join(c if c == " " or c in self.guessed else "\\_" for c in self.word.upper())

    async def _set_word(self, interaction: discord.Interaction, text: str) -> bool | None:
        if not WORD_RE.match(text):
            await respond(interaction, "Use 3–20 letters (spaces allowed), no numbers or symbols.", ephemeral=True)
            return False
        self.word = text.upper()
        return None

    async def _open_prompt(self, interaction: discord.Interaction) -> bool:
        return await self.ask(
            interaction, "Choose the secret word", "Word or short phrase", self._set_word,
            placeholder="only your partner will guess it", max_length=20, min_length=3,
        )

    def _guess(self):
        async def handler(interaction: discord.Interaction, letter: str) -> bool | None:
            if interaction.user.id != self.guesser or not self.word:
                return False
            if letter in self.guessed:
                return False
            self.guessed.add(letter)
            if all(c == " " or c in self.guessed for c in self.word):
                await self.end(interaction=interaction, reason=f"🎉 {self.mention(self.guesser)} solved it: **{self.word}**", winner=self.guesser)
                return False
            if len(self.wrong) >= self.MAX_WRONG:
                await self.end(
                    interaction=interaction,
                    reason=f"💀 Out of guesses! The word was **{self.word}** — {self.mention(self.setter)} wins.",
                    winner=self.setter,
                )
                return False
            return None
        return handler

    def render(self, uid: int) -> tuple[discord.Embed, Items]:
        items: Items = []
        if self.word is None:
            if uid == self.setter:
                desc = "Pick a secret word or phrase for your partner to guess 🤫"
                items.append(self.button("Choose the word", self._open_prompt, style=Style.primary, emoji="✏️", row=0))
            else:
                desc = f"Waiting for {self.mention(self.setter)} to choose a word…"
            if self.ended_reason:
                return self.embed(self.ended_reason), []
            items.append(self.quit_button(row=1 if uid == self.setter else 0))
            return self.embed(desc), items

        stage = HANGMAN_STAGES[min(len(self.wrong), self.MAX_WRONG)]
        desc = (
            f"{stage}\n**{self.masked()}**\n\nWrong: {' '.join(self.wrong) or '—'}\n"
            f"Setter: {self.mention(self.setter)} • Guesser: {self.mention(self.guesser)}"
        )
        if self.ended_reason:
            desc += f"\n\n{self.ended_reason}"
        elif uid == self.guesser:
            desc += "\n\nPick a letter 👇"
            for row, letters in enumerate(LETTER_HALVES):
                options = [discord.SelectOption(label=l, value=l) for l in letters if l not in self.guessed]
                if options:
                    items.append(self.select(f"Letters {letters[0]}–{letters[-1]}", options, self._guess(), row=row))
        else:
            desc += f"\n\n{self.name(self.guesser)} is guessing…"
        items.append(self.quit_button(row=2))
        return self.embed(desc), items


# ── Number guessing (take turns, shared secret) ──────────────────────────────


class NumberGuess(TurnGame):
    key, title, emoji, stats_game = "number", "Number Guessing", "🔢", "number"
    category, blurb, duration = "Brain", 'Find the secret number together', "~3 min"
    difficulty = "Easy"
    LOW, HIGH, MAX_GUESSES = 1, 100, 10

    def __init__(self, manager, p1, p2) -> None:
        super().__init__(manager, p1, p2)
        self.secret = random.randint(self.LOW, self.HIGH)
        self.history: list[str] = []
        self.guesses = 0

    async def _guess(self, interaction: discord.Interaction, text: str) -> bool | None:
        uid = interaction.user.id
        if uid != self.turn:
            await respond(interaction, "Not your turn yet — hang tight 💕", ephemeral=True)
            return False
        if not text.lstrip("-").isdigit() or not self.LOW <= int(text) <= self.HIGH:
            await respond(interaction, f"Enter a whole number from {self.LOW} to {self.HIGH}.", ephemeral=True)
            return False
        n = int(text)
        self.guesses += 1
        if n == self.secret:
            await self.end(
                interaction=interaction,
                reason=f"🎉 {self.mention(uid)} got it — **{self.secret}** in {self.guesses} guesses!",
                winner=uid,
            )
            return False
        hint = "📈 higher" if n < self.secret else "📉 lower"
        self.history.append(f"{self.name(uid)}: **{n}** → {hint}")
        if self.guesses >= self.MAX_GUESSES:
            await self.end(interaction=interaction, reason=f"😅 Out of guesses! It was **{self.secret}**.", draw=True)
            return False
        self.switch_turn()
        return None

    async def _open(self, interaction: discord.Interaction) -> bool:
        if not await self.guard_turn(interaction):
            return False
        return await self.ask(interaction, "Your guess", f"A number {self.LOW}–{self.HIGH}", self._guess, max_length=3)

    def render(self, uid: int) -> tuple[discord.Embed, Items]:
        recent = "\n".join(self.history[-6:]) or "No guesses yet."
        status = self.ended_reason or f"{self.status_line()}  ({self.MAX_GUESSES - self.guesses} guesses left)"
        desc = f"I'm thinking of a number from **{self.LOW}** to **{self.HIGH}**. Work together!\n\n{recent}\n\n{status}"
        items: Items = [
            self.button("Guess", self._open, style=Style.primary, emoji="🔢", row=0,
                        disabled=not self.active or self.turn != uid),
            self.quit_button(row=0),
        ]
        return self.embed(desc), items


# ── Higher or Lower (co-op streak) ───────────────────────────────────────────

RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
SUITS = ["♠️", "♥️", "♦️", "♣️"]


class HigherLower(TurnGame):
    key, title, emoji, stats_game = "higherlower", "Higher or Lower", "🃏", "higherlower"
    category, blurb, duration = "Chance", 'Call higher or lower and build a team streak', "~3 min"
    difficulty = "Easy"

    def __init__(self, manager, p1, p2) -> None:
        super().__init__(manager, p1, p2)
        self.card = self._draw()
        self.streak = 0
        self.last = "Is the next card higher or lower? Build a streak together!"

    @staticmethod
    def _draw() -> tuple[int, str]:
        return random.randint(1, 13), random.choice(SUITS)

    @staticmethod
    def _fmt(card: tuple[int, str]) -> str:
        return f"**{RANKS[card[0] - 1]}{card[1]}**"

    def _call(self, higher: bool):
        async def handler(interaction: discord.Interaction) -> bool | None:
            if not await self.guard_turn(interaction):
                return False
            new = self._draw()
            old = self.card
            correct = new[0] == old[0] or (new[0] > old[0]) == higher
            self.card = new
            if not correct:
                await self.end(
                    interaction=interaction,
                    reason=f"❌ {self._fmt(old)} → {self._fmt(new)}. Streak over at **{self.streak}** 💔",
                    points=self.streak,
                )
                return False
            self.streak += 1
            self.last = f"✅ {self._fmt(old)} → {self._fmt(new)} (ties count as correct)"
            self.switch_turn()
            return None
        return handler

    def render(self, uid: int) -> tuple[discord.Embed, Items]:
        status = self.ended_reason or f"{self.last}\n\n{self.status_line()}"
        desc = f"Current card: {self._fmt(self.card)}\n🔥 Team streak: **{self.streak}**\n\n{status}"
        off = not self.active or self.turn != uid
        items: Items = [
            self.button("Higher", self._call(True), style=Style.success, emoji="📈", row=0, disabled=off),
            self.button("Lower", self._call(False), style=Style.primary, emoji="📉", row=0, disabled=off),
            self.quit_button(row=0),
        ]
        return self.embed(desc, color=GOLD), items
