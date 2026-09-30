from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.dm_mirror import mirror_to_partner
from services.movie_service import GENRES, MovieService
from utils.logging import get_logger

logger = get_logger(__name__)

MOVIE_COLOR = 0x01B4E4  # TMDB brand blue


def build_movie_embed(movie, genre: str | None) -> discord.Embed:
    title = movie.title
    if movie.release_date:
        title += f" ({movie.release_date[:4]})"

    embed = discord.Embed(
        title=f"🎬 {title}",
        description=movie.overview[:500],
        color=MOVIE_COLOR,
        url=movie.tmdb_url,
    )
    if movie.poster_url:
        embed.set_thumbnail(url=movie.poster_url)
    if movie.vote_count > 0:
        embed.add_field(name="⭐ Rating", value=f"`{movie.vote_average:.1f}/10`", inline=True)
    if genre:
        embed.add_field(name="🎭 Genre", value=f"`{genre}`", inline=True)
    embed.set_footer(text="Powered by TMDB")
    embed.timestamp = discord.utils.utcnow()
    return embed


class MoviesCog(commands.Cog, name="Movies"):
    """Random movie recommendations, powered by TMDB."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.movie_service = MovieService()

    movie_group = app_commands.Group(name="movie", description="Movie recommendations")

    @movie_group.command(name="recommend", description="Get a random movie recommendation")
    @app_commands.describe(genre="Filter by genre (leave blank for any popular movie)")
    @app_commands.choices(
        genre=[app_commands.Choice(name=g, value=g) for g in GENRES]
    )
    async def recommend(
        self,
        interaction: discord.Interaction,
        genre: app_commands.Choice[str] | None = None,
    ) -> None:
        if not self.movie_service.enabled:
            await interaction.response.send_message(
                "🎬 Movie recommendations aren't set up yet -- the bot owner needs to add a "
                "`TMDB_API_KEY` to the `.env` file (free at themoviedb.org).",
                ephemeral=True,
            )
            return

        await interaction.response.defer()
        genre_value = genre.value if genre else None
        movie = await self.movie_service.random_movie(genre_value)

        if movie is None:
            await interaction.followup.send(
                "😕 Couldn't find a movie recommendation right now -- try again in a moment."
            )
            return

        await interaction.followup.send(embed=build_movie_embed(movie, genre_value))

        # In a DM, send your partner the same pick so movie night is a
        # joint decision instead of just showing up on one side.
        await mirror_to_partner(
            interaction,
            content=f"🎬 **{interaction.user.display_name}** found a movie night pick:",
            embed=build_movie_embed(movie, genre_value),
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MoviesCog(bot))
