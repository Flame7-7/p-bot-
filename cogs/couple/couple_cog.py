from __future__ import annotations

import hashlib
import random
from datetime import date, datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from repositories.couple_repository import CoupleRepository
from repositories.relationship_repository import RelationshipRepository
from services.dm_games.quiz import DailyQuestion
from services.dm_games.registry import BY_KEY
from services.dm_mirror import get_partner
from utils.content import load_list, load_pairs
from utils.interactions import OwnedView, respond, safe_dm
from utils.logging import get_logger

logger = get_logger(__name__)

PINK = 0xFF6FA5
NEEDS_PARTNER = "💍 You need an active partner for this — use `/propose` first."
MAX_MILESTONES = 25


def _pool(path: str) -> list[str]:
    return load_list(path) or ["Tell your partner you're thinking of them 💕"]


class PickView(OwnedView):
    """Shows one random item with 'Another' and 'Send to partner' buttons."""

    def __init__(self, owner: discord.abc.User, partner: discord.User, pool: list[str], heading: str, send_title: str) -> None:
        super().__init__([owner.id], timeout=300)
        self.owner = owner
        self.partner = partner
        self.pool = pool
        self.heading = heading
        self.send_title = send_title
        self.current = random.choice(pool)

    def embed(self) -> discord.Embed:
        return discord.Embed(title=self.heading, description=self.current, color=PINK)

    @discord.ui.button(label="Another", emoji="🔄", style=discord.ButtonStyle.secondary)
    async def another(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        choices = [p for p in self.pool if p != self.current] or self.pool
        self.current = random.choice(choices)
        await interaction.response.edit_message(embed=self.embed(), view=self)

    @discord.ui.button(label="Send to partner", emoji="💌", style=discord.ButtonStyle.primary)
    async def send(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = discord.Embed(title=self.send_title, description=self.current, color=PINK)
        embed.set_footer(text=f"From {self.owner.display_name} 💕")
        sent = await safe_dm(self.partner, embed=embed)
        button.disabled = True
        button.label = "Sent!" if sent else "Their DMs are closed"
        await interaction.response.edit_message(embed=self.embed(), view=self)


class MoodView(OwnedView):
    def __init__(self, owner: discord.abc.User, partner: discord.User) -> None:
        super().__init__([owner.id], timeout=180)
        self.owner, self.partner = owner, partner
        self.moods = {emoji: (label, reply) for emoji, label, reply in (m for m in load_pairs("couple/moods.md") if len(m) == 3)}
        select = discord.ui.Select(
            placeholder="How are you feeling?",
            options=[discord.SelectOption(label=label, emoji=emoji, value=emoji) for emoji, (label, _) in self.moods.items()],
        )
        select.callback = self._picked  # type: ignore[method-assign]
        self.select = select
        self.add_item(select)

    async def _picked(self, interaction: discord.Interaction) -> None:
        emoji = self.select.values[0]
        label, reply = self.moods[emoji]
        embed = discord.Embed(
            title=f"{emoji} {self.owner.display_name} is feeling {label.lower()}", color=PINK,
            description="Send them a little love 💞",
        )
        sent = await safe_dm(self.partner, embed=embed)
        self.select.disabled = True
        done = discord.Embed(
            title=f"{emoji} {label}",
            description=f"{reply}\n\n" + ("Your partner has been told 💌" if sent else "(I couldn't DM your partner — their DMs are closed.)"),
            color=PINK,
        )
        await interaction.response.edit_message(embed=done, view=self)
        self.stop()


class JournalModal(discord.ui.Modal, title="Shared journal"):
    entry: discord.ui.TextInput = discord.ui.TextInput(label="Your entry", style=discord.TextStyle.paragraph, max_length=1000)

    def __init__(self, repo: CoupleRepository, user_id: int, partner_id: int, prompt: str) -> None:
        super().__init__()
        self.repo, self.user_id, self.partner_id, self.prompt = repo, user_id, partner_id, prompt
        self.entry.placeholder = prompt[:100]

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.repo.add_journal(self.user_id, self.partner_id, self.user_id, str(self.entry.value).strip(), self.prompt)
        await respond(interaction, "📖 Saved to your shared journal. Read it any time with `/couple memories`.", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        logger.error("journal modal failed", exc_info=error)
        await respond(interaction, "Couldn't save that — please try again.", ephemeral=True)


def _love_verdict(percent: int) -> str:
    verdict = ""
    for threshold, text in sorted(((int(a), b) for a, b in (r for r in load_pairs("couple/love_calc.md") if len(r) == 2 and r[0].isdigit()))):
        if percent >= threshold:
            verdict = text
    return verdict


def _days_until(event: datetime, yearly: bool, today: date) -> tuple[int, date]:
    """Days until the (next) occurrence; negative when a one-off date has passed."""
    day = event.date()
    if yearly:
        try:
            nxt = day.replace(year=today.year)
        except ValueError:  # 29 Feb in a non-leap year
            nxt = date(today.year, 3, 1)
        if nxt < today:
            try:
                nxt = day.replace(year=today.year + 1)
            except ValueError:
                nxt = date(today.year + 1, 3, 1)
        return (nxt - today).days, nxt
    return (day - today).days, day


class CoupleCog(commands.Cog, name="Couple"):
    """Cute, couple-only touches: compliments, date ideas, journal, milestones and shared stats."""

    help_category = ("💕", "Couple")

    couple = app_commands.Group(name="couple", description="Little things just for the two of you")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.repo = CoupleRepository()
        self.rel_repo = RelationshipRepository()

    async def _partner(self, interaction: discord.Interaction) -> discord.User | None:
        partner = await get_partner(self.bot, interaction.user.id)
        if partner is None:
            await respond(interaction, NEEDS_PARTNER, ephemeral=True)
        return partner

    async def _send_pick(
        self, interaction: discord.Interaction, path: str, heading: str, send_title: str
    ) -> None:
        partner = await self._partner(interaction)
        if partner is None:
            return
        view = PickView(interaction.user, partner, _pool(path), heading, send_title)
        await interaction.response.send_message(embed=view.embed(), view=view, ephemeral=True)
        view.message = await interaction.original_response()

    # ── pick-and-send ────────────────────────────────────────────────────────

    @couple.command(name="compliment", description="Get a compliment to send your partner")
    async def compliment(self, interaction: discord.Interaction) -> None:
        await self._send_pick(interaction, "couple/compliments.md", "💖 A compliment", "💖 A compliment, just for you")

    @couple.command(name="cutemessage", description="Get a cute message to send your partner")
    async def cute_message(self, interaction: discord.Interaction) -> None:
        await self._send_pick(interaction, "couple/cute_messages.md", "🧸 A cute message", "🧸 Someone's thinking of you")

    @couple.command(name="dateidea", description="Get a random date idea")
    async def date_idea(self, interaction: discord.Interaction) -> None:
        await self._send_pick(interaction, "couple/date_ideas.md", "🌹 Date idea", "🌹 Date idea from your partner")

    @couple.command(name="challenge", description="Get a random couple challenge")
    async def challenge(self, interaction: discord.Interaction) -> None:
        await self._send_pick(interaction, "couple/challenges.md", "🎯 Couple challenge", "🎯 A challenge from your partner")

    # ── interactive ──────────────────────────────────────────────────────────

    @couple.command(name="mood", description="Let your partner know how you're feeling")
    async def mood(self, interaction: discord.Interaction) -> None:
        partner = await self._partner(interaction)
        if partner is None:
            return
        view = MoodView(interaction.user, partner)
        await interaction.response.send_message("How are you feeling right now?", view=view, ephemeral=True)
        view.message = await interaction.original_response()

    @couple.command(name="daily", description="Today's question — you both answer, then see each other's")
    async def daily(self, interaction: discord.Interaction) -> None:
        partner = await self._partner(interaction)
        play = self.bot.get_cog("Play")
        if partner is None:
            return
        if play is None:
            await respond(interaction, "Games aren't available right now.", ephemeral=True)
            return
        questions = _pool("couple/daily_questions.md")
        question = questions[date.today().toordinal() % len(questions)]
        await interaction.response.defer(ephemeral=True)
        await play.manager.start(interaction, partner, DailyQuestion, question=question)

    @couple.command(name="pickone", description="Both pick what to do tonight; I break ties")
    async def pick_one(self, interaction: discord.Interaction) -> None:
        play = self.bot.get_cog("Play")
        partner = await self._partner(interaction)
        if partner is None or play is None:
            return
        await interaction.response.defer(ephemeral=True)
        await play.manager.start(interaction, partner, BY_KEY["pickone"].cls)

    @couple.command(name="lovecalc", description="A playful love calculator (just for fun!)")
    @app_commands.describe(user="Who to check (defaults to your partner)")
    async def love_calc(self, interaction: discord.Interaction, user: discord.User | None = None) -> None:
        partner = await get_partner(self.bot, interaction.user.id)
        target = user or partner
        if target is None:
            await respond(interaction, "Pick someone to check, or link a partner with `/propose`.", ephemeral=True)
            return
        if target.id == interaction.user.id:
            await respond(interaction, "Self-love is great, but pick someone else 😄", ephemeral=True)
            return
        low, high = sorted((interaction.user.id, target.id))
        digest = hashlib.sha256(f"{low}:{high}:{date.today().isoformat()}".encode()).digest()
        base = int.from_bytes(digest[:4], "big")
        percent = 70 + base % 31 if (partner and target.id == partner.id) else 1 + base % 100
        filled = round(percent / 10)
        embed = discord.Embed(
            title="💘 Love calculator",
            description=(
                f"{interaction.user.mention} + {target.mention}\n\n"
                f"{'💗' * filled}{'🤍' * (10 - filled)}  **{percent}%**\n{_love_verdict(percent)}"
            ),
            color=PINK,
        )
        embed.set_footer(text="Purely for fun — it changes every day 😉")
        await respond(interaction, embed=embed)

    # ── journal ──────────────────────────────────────────────────────────────

    @couple.command(name="journal", description="Write a shared journal entry from a random prompt")
    async def journal(self, interaction: discord.Interaction) -> None:
        partner = await self._partner(interaction)
        if partner is None:
            return
        prompt = random.choice(_pool("couple/journal_prompts.md"))
        await interaction.response.send_modal(JournalModal(self.repo, interaction.user.id, partner.id, prompt))

    @couple.command(name="memories", description="Read your shared journal")
    async def memories(self, interaction: discord.Interaction) -> None:
        partner = await self._partner(interaction)
        if partner is None:
            return
        entries = await self.repo.list_journal(interaction.user.id, partner.id, limit=8)
        if not entries:
            await respond(interaction, "Nothing here yet — write the first entry with `/couple journal` 📖", ephemeral=True)
            return
        names = {interaction.user.id: interaction.user.display_name, partner.id: partner.display_name}
        blocks = []
        for e in entries:
            when = e.created_at.strftime("%b %d, %Y") if e.created_at else ""
            blocks.append(f"**{names.get(e.author_id, 'Someone')}** · {when}\n{e.text[:300]}")
        embed = discord.Embed(title="📖 Your shared journal", description="\n\n".join(blocks)[:4000], color=PINK)
        await respond(interaction, embed=embed, ephemeral=True)

    # ── milestones & countdowns ──────────────────────────────────────────────

    @couple.command(name="milestone", description="Add a date to remember or count down to")
    @app_commands.describe(title="What is it? (e.g. First date)", on="Date as YYYY-MM-DD", yearly="Celebrate every year")
    async def milestone(self, interaction: discord.Interaction, title: app_commands.Range[str, 1, 80], on: str, yearly: bool = True) -> None:
        partner = await self._partner(interaction)
        if partner is None:
            return
        try:
            when = datetime.strptime(on.strip(), "%Y-%m-%d")
        except ValueError:
            await respond(interaction, "Use the format `YYYY-MM-DD`, for example `2025-02-14`.", ephemeral=True)
            return
        if len(await self.repo.list_milestones(interaction.user.id, partner.id)) >= MAX_MILESTONES:
            await respond(interaction, f"You've reached {MAX_MILESTONES} milestones — remove one first.", ephemeral=True)
            return
        row = await self.repo.add_milestone(interaction.user.id, partner.id, title.strip(), when, yearly, interaction.user.id)
        await respond(interaction, f"💞 Saved **{row.title}** ({when:%b %d, %Y}) — see it in `/couple countdown`.", ephemeral=True)

    @couple.command(name="countdown", description="See your milestones and how far away they are")
    async def countdown(self, interaction: discord.Interaction) -> None:
        partner = await self._partner(interaction)
        if partner is None:
            return
        today = datetime.now(timezone.utc).date()
        lines: list[str] = []
        rel = await self.rel_repo.get_relationship(interaction.user.id)
        if rel and rel.started_at:
            together = (today - rel.started_at.date()).days
            to_go, nxt = _days_until(rel.started_at, True, today)
            lines.append(f"💍 **Together since {rel.started_at:%b %d, %Y}** — {together} days · next anniversary in **{to_go}** days")
        for m in await self.repo.list_milestones(interaction.user.id, partner.id):
            days, when = _days_until(m.event_date, m.yearly, today)
            if days > 0:
                timing = f"in **{days}** days"
            elif days == 0:
                timing = "**today!** 🎉"
            else:
                timing = f"{-days} days ago"
            lines.append(f"`#{m.id}` **{m.title}** — {when:%b %d, %Y} · {timing}")
        if not lines:
            await respond(interaction, "No milestones yet — add one with `/couple milestone`.", ephemeral=True)
            return
        embed = discord.Embed(title="⏳ Milestones", description="\n".join(lines), color=PINK)
        embed.set_footer(text="Remove one with /couple unmilestone <id>")
        await respond(interaction, embed=embed, ephemeral=True)

    @couple.command(name="unmilestone", description="Remove a milestone by its #id")
    async def unmilestone(self, interaction: discord.Interaction, milestone_id: int) -> None:
        partner = await self._partner(interaction)
        if partner is None:
            return
        removed = await self.repo.remove_milestone(interaction.user.id, partner.id, milestone_id)
        await respond(interaction, "Removed." if removed else "I couldn't find that milestone.", ephemeral=True)

    # ── shared stats ─────────────────────────────────────────────────────────

    @couple.command(name="stats", description="Your shared game scores")
    async def stats(self, interaction: discord.Interaction) -> None:
        partner = await self._partner(interaction)
        if partner is None:
            return
        rows = await self.repo.get_stats(interaction.user.id, partner.id)
        if not rows:
            await respond(interaction, "No games played yet — try `/play` 🎮", ephemeral=True)
            return
        me = interaction.user
        lines = []
        for r in rows:
            info = next((g for g in BY_KEY.values() if g.key == r.game or g.cls.stats_game == r.game), None)
            label = info.label if info else r.game
            mine = r.low_wins if me.id == r.user_low_id else r.high_wins
            theirs = r.high_wins if me.id == r.user_low_id else r.low_wins
            parts = [f"{r.plays} played"]
            if mine or theirs or r.draws:
                parts.append(f"{me.display_name} {mine} – {theirs} {partner.display_name}")
                if r.draws:
                    parts.append(f"{r.draws} draws")
            if r.points:
                parts.append(f"{r.points} pts")
            lines.append(f"**{label}** — " + " · ".join(parts))
        embed = discord.Embed(title=f"🏆 {me.display_name} & {partner.display_name}", description="\n".join(lines)[:4000], color=PINK)
        await respond(interaction, embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CoupleCog(bot))
