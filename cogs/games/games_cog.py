from __future__ import annotations

import random
import asyncio
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from repositories.user_repository import UserRepository
from utils.config import get_config
from utils.cooldowns import cache_get, cache_set
from utils.logging import get_logger

logger = get_logger(__name__)
config = get_config()


class GamesCog(commands.Cog, name="Games"):
    """Fun mini-games for users to play!"""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.user_repo = UserRepository()
        
        # Game constants
        self.rock_paper_scissors_options = ["rock", "paper", "scissors"]
        self.blackjack_cards = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
        self.blackjack_suits = ["♠️", "♥️", "♦️", "♣️"]
        self.slot_emojis = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣"]
        self.trivia_questions = [
            {
                "question": "What is the capital of France?",
                "options": ["London", "Berlin", "Paris", "Madrid"],
                "answer": 2
            },
            {
                "question": "Which planet is known as the Red Planet?",
                "options": ["Venus", "Mars", "Jupiter", "Saturn"],
                "answer": 1
            },
            {
                "question": "What is 2 + 2?",
                "options": ["3", "4", "5", "6"],
                "answer": 1
            },
            {
                "question": "Who wrote 'Romeo and Juliet'?",
                "options": ["Charles Dickens", "William Shakespeare", "Jane Austen", "Mark Twain"],
                "answer": 1
            },
            {
                "question": "What is the largest ocean on Earth?",
                "options": ["Atlantic", "Indian", "Arctic", "Pacific"],
                "answer": 3
            },
        ]

    @app_commands.command(
        name="rps",
        description="Play Rock Paper Scissors against the bot"
    )
    @app_commands.describe(choice="Choose rock, paper, or scissors")
    @app_commands.choices(
        choice=[
            app_commands.Choice(name="Rock 🪨", value="rock"),
            app_commands.Choice(name="Paper 📄", value="paper"),
            app_commands.Choice(name="Scissors ✂️", value="scissors"),
        ]
    )
    async def rock_paper_scissors(
        self,
        interaction: discord.Interaction,
        choice: str
    ) -> None:
        """Play Rock Paper Scissors against the bot."""
        await interaction.response.defer()
        
        uid = interaction.user.id
        
        # Check cooldown (5 seconds)
        if cache_get(f"rps:{uid}"):
            await interaction.followup.send(
                "⏳ Please wait a few seconds before playing again!",
                ephemeral=True
            )
            return
        
        cache_set(f"rps:{uid}", True, ttl=5)
        
        # Ensure user exists
        await self.user_repo.get_or_create(
            uid,
            interaction.user.display_name,
            str(interaction.user.display_avatar.url),
        )
        
        bot_choice = random.choice(self.rock_paper_scissors_options)
        
        # Determine winner
        emojis = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
        
        result = ""
        xp_reward = 0
        
        if choice == bot_choice:
            result = "🤝 It's a tie!"
        elif (
            (choice == "rock" and bot_choice == "scissors") or
            (choice == "paper" and bot_choice == "rock") or
            (choice == "scissors" and bot_choice == "paper")
        ):
            result = "🎉 You win!"
            xp_reward = 10
            await self.user_repo.add_xp(uid, xp_reward)
        else:
            result = "😢 You lose!"
        
        embed = discord.Embed(
            title="🎮 Rock Paper Scissors",
            color=0x7289DA,
        )
        
        embed.add_field(
            name="Your Choice",
            value=f"{emojis[choice]} **{choice.title()}**",
            inline=True
        )
        
        embed.add_field(
            name="Bot's Choice",
            value=f"{emojis[bot_choice]} **{bot_choice.title()}**",
            inline=True
        )
        
        embed.add_field(
            name="Result",
            value=result,
            inline=False
        )
        
        if xp_reward > 0:
            embed.add_field(
                name="🎁 Reward",
                value=f"+{xp_reward} XP",
                inline=True
            )
        
        embed.set_thumbnail(url=str(interaction.user.display_avatar.url))
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="coinflip",
        description="Flip a coin and guess heads or tails"
    )
    @app_commands.describe(guess="Guess heads or tails")
    @app_commands.choices(
        guess=[
            app_commands.Choice(name="Heads 👑", value="heads"),
            app_commands.Choice(name="Tails 🔢", value="tails"),
        ]
    )
    async def coinflip(
        self,
        interaction: discord.Interaction,
        guess: str
    ) -> None:
        """Flip a coin and guess the outcome."""
        await interaction.response.defer()
        
        uid = interaction.user.id
        
        # Check cooldown (5 seconds)
        if cache_get(f"coinflip:{uid}"):
            await interaction.followup.send(
                "⏳ Please wait a few seconds before flipping again!",
                ephemeral=True
            )
            return
        
        cache_set(f"coinflip:{uid}", True, ttl=5)
        
        # Ensure user exists
        await self.user_repo.get_or_create(
            uid,
            interaction.user.display_name,
            str(interaction.user.display_avatar.url),
        )
        
        result = random.choice(["heads", "tails"])
        emoji = "👑" if result == "heads" else "🔢"
        
        won = guess == result
        xp_reward = 15 if won else 0
        
        if won:
            await self.user_repo.add_xp(uid, xp_reward)
        
        embed = discord.Embed(
            title="🪙 Coin Flip",
            color=0xF1C40F if won else 0xE74C3C,
        )
        
        embed.add_field(
            name="Your Guess",
            value=f"**{guess.title()}**",
            inline=True
        )
        
        embed.add_field(
            name="Result",
            value=f"{emoji} **{result.title()}**",
            inline=True
        )
        
        embed.add_field(
            name="Outcome",
            value="🎉 You won!" if won else "😢 You lost!",
            inline=False
        )
        
        if xp_reward > 0:
            embed.add_field(
                name="🎁 Reward",
                value=f"+{xp_reward} XP",
                inline=True
            )
        
        embed.set_thumbnail(url=str(interaction.user.display_avatar.url))
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="slots",
        description="Play the slot machine!"
    )
    async def slots(self, interaction: discord.Interaction) -> None:
        """Play a slot machine game."""
        await interaction.response.defer()
        
        uid = interaction.user.id
        
        # Check cooldown (30 seconds)
        if cache_get(f"slots:{uid}"):
            await interaction.followup.send(
                "⏳ The slot machine is cooling down! Wait 30 seconds.",
                ephemeral=True
            )
            return
        
        cache_set(f"slots:{uid}", True, ttl=30)
        
        # Ensure user exists
        await self.user_repo.get_or_create(
            uid,
            interaction.user.display_name,
            str(interaction.user.display_avatar.url),
        )
        
        # Spin the slots
        reel1 = random.choice(self.slot_emojis)
        reel2 = random.choice(self.slot_emojis)
        reel3 = random.choice(self.slot_emojis)
        
        # Calculate result
        if reel1 == reel2 == reel3:
            if reel1 == "7️⃣":
                result = "🎉🎉 JACKPOT! 🎉🎉"
                xp_reward = 100
            elif reel1 == "💎":
                result = "💎 Diamond Triple! 💎"
                xp_reward = 50
            else:
                result = "🎉 Triple Match! 🎉"
                xp_reward = 25
            await self.user_repo.add_xp(uid, xp_reward)
        elif reel1 == reel2 or reel2 == reel3 or reel1 == reel3:
            result = "✨ Double Match! ✨"
            xp_reward = 10
            await self.user_repo.add_xp(uid, xp_reward)
        else:
            result = "😢 No match... Try again!"
            xp_reward = 0
        
        embed = discord.Embed(
            title="🎰 Slot Machine",
            color=0x9B59B6 if xp_reward > 0 else 0x95A5A6,
        )
        
        embed.description = f"# {reel1} | {reel2} | {reel3}"
        
        embed.add_field(
            name="Result",
            value=result,
            inline=False
        )
        
        if xp_reward > 0:
            embed.add_field(
                name="🎁 Reward",
                value=f"+{xp_reward} XP",
                inline=True
            )
        
        embed.set_footer(text="Match 2 or more symbols to win!")
        embed.set_thumbnail(url=str(interaction.user.display_avatar.url))
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="trivia",
        description="Answer a trivia question!"
    )
    async def trivia(self, interaction: discord.Interaction) -> None:
        """Answer a random trivia question."""
        await interaction.response.defer()
        
        uid = interaction.user.id
        
        # Check cooldown (60 seconds)
        if cache_get(f"trivia:{uid}"):
            await interaction.followup.send(
                "⏳ Take a break! Wait 60 seconds before the next question.",
                ephemeral=True
            )
            return
        
        cache_set(f"trivia:{uid}", True, ttl=60)
        
        # Ensure user exists
        await self.user_repo.get_or_create(
            uid,
            interaction.user.display_name,
            str(interaction.user.display_avatar.url),
        )
        
        question = random.choice(self.trivia_questions)
        
        embed = discord.Embed(
            title="🧠 Trivia Time!",
            description=f"**{question['question']}**",
            color=0x3498DB,
        )
        
        options_text = "\n".join([
            f"{i+1}. {opt}" for i, opt in enumerate(question["options"])
        ])
        
        embed.add_field(
            name="Options",
            value=options_text,
            inline=False
        )
        
        embed.set_footer(text="Reply with the number of your answer (1-4)")
        embed.set_thumbnail(url=str(interaction.user.display_avatar.url))
        embed.timestamp = discord.utils.utcnow()
        
        # Send question and wait for response
        message = await interaction.followup.send(embed=embed)
        
        # Wait for user's answer (30 seconds timeout)
        try:
            def check(msg):
                return (
                    msg.author.id == uid and
                    msg.channel.id == interaction.channel_id and
                    msg.content.isdigit() and
                    1 <= int(msg.content) <= 4
                )
            
            response = await self.bot.wait_for(
                "message",
                check=check,
                timeout=30.0
            )
            
            answer = int(response.content) - 1
            
            if answer == question["answer"]:
                xp_reward = 20
                await self.user_repo.add_xp(uid, xp_reward)
                
                result_embed = discord.Embed(
                    title="🎉 Correct!",
                    description=f"The answer was **{question['options'][question['answer']]}**!",
                    color=0x2ECC71,
                )
                result_embed.add_field(
                    name="🎁 Reward",
                    value=f"+{xp_reward} XP",
                    inline=True
                )
            else:
                result_embed = discord.Embed(
                    title="❌ Incorrect",
                    description=f"The correct answer was **{question['options'][question['answer']]}**.",
                    color=0xE74C3C,
                )
            
            result_embed.set_thumbnail(url=str(interaction.user.display_avatar.url))
            result_embed.timestamp = discord.utils.utcnow()
            
            await interaction.channel.send(embed=result_embed)
            
        except asyncio.TimeoutError:
            timeout_embed = discord.Embed(
                title="⏰ Time's Up!",
                description=f"The correct answer was **{question['options'][question['answer']]}**.",
                color=0xE74C3C,
            )
            timeout_embed.set_thumbnail(url=str(interaction.user.display_avatar.url))
            await interaction.channel.send(embed=timeout_embed)

    @app_commands.command(
        name="roll",
        description="Roll a dice (default is d6)"
    )
    @app_commands.describe(
        sides="Number of sides on the dice (default: 6)",
        count="Number of dice to roll (default: 1, max: 10)"
    )
    async def roll(
        self,
        interaction: discord.Interaction,
        sides: Optional[int] = 6,
        count: Optional[int] = 1
    ) -> None:
        """Roll one or more dice."""
        await interaction.response.defer()
        
        # Validate inputs
        if sides < 2 or sides > 1000:
            await interaction.followup.send(
                "🎲 Dice must have between 2 and 1000 sides!",
                ephemeral=True
            )
            return
        
        if count < 1 or count > 10:
            await interaction.followup.send(
                "🎲 You can roll between 1 and 10 dice!",
                ephemeral=True
            )
            return
        
        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls)
        
        embed = discord.Embed(
            title="🎲 Dice Roll",
            color=0xE67E22,
        )
        
        if count == 1:
            embed.description = f"You rolled a **d{sides}**: `{rolls[0]}`"
        else:
            rolls_str = " | ".join([str(r) for r in rolls])
            embed.description = f"You rolled {count} **d{sides}**:\n{rolls_str}"
            embed.add_field(
                name="Total",
                value=f"**{total}**",
                inline=False
            )
        
        embed.set_thumbnail(url=str(interaction.user.display_avatar.url))
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="guess",
        description="Guess a number between 1 and 100"
    )
    async def guess_number(self, interaction: discord.Interaction) -> None:
        """Guess a number between 1 and 100."""
        await interaction.response.defer()
        
        uid = interaction.user.id
        
        # Check if already playing
        if cache_get(f"guess:{uid}"):
            await interaction.followup.send(
                "🎯 You already have an active guessing game! Finish it first.",
                ephemeral=True
            )
            return
        
        # Generate random number
        target = random.randint(1, 100)
        attempts = 0
        max_attempts = 7
        
        # Store game state
        cache_set(f"guess:{uid}", {
            "target": target,
            "attempts": attempts,
            "max_attempts": max_attempts
        }, ttl=300)
        
        embed = discord.Embed(
            title="🎯 Guess the Number",
            description="I'm thinking of a number between **1 and 100**.\nYou have **7 attempts** to guess it!",
            color=0x9B59B6,
        )
        
        embed.add_field(
            name="How to Play",
            value="Type your guess in the chat!\nGood luck! 🍀",
            inline=False
        )
        
        embed.set_footer(text=f"Game ID: {uid}")
        embed.set_thumbnail(url=str(interaction.user.display_avatar.url))
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.followup.send(embed=embed)
        
        # Wait for guesses
        while True:
            try:
                def check(msg):
                    return (
                        msg.author.id == uid and
                        msg.channel.id == interaction.channel_id and
                        msg.content.isdigit()
                    )
                
                message = await self.bot.wait_for(
                    "message",
                    check=check,
                    timeout=60.0
                )
                
                guess = int(message.content)
                attempts += 1
                
                # Update attempts
                game_state = cache_get(f"guess:{uid}")
                if not game_state:
                    await interaction.channel.send(
                        "❌ Game expired! Start a new one with `/guess`"
                    )
                    break
                
                game_state["attempts"] = attempts
                cache_set(f"guess:{uid}", game_state, ttl=300)
                
                if guess < 1 or guess > 100:
                    await interaction.channel.send("🔢 Please guess a number between 1 and 100!")
                    continue
                
                if guess == target:
                    xp_reward = 30
                    await self.user_repo.add_xp(uid, xp_reward)
                    
                    win_embed = discord.Embed(
                        title="🎉 Correct!",
                        description=f"The number was **{target}**!\nYou guessed it in **{attempts}** attempts!",
                        color=0x2ECC71,
                    )
                    win_embed.add_field(
                        name="🎁 Reward",
                        value=f"+{xp_reward} XP",
                        inline=True
                    )
                    win_embed.set_thumbnail(url=str(interaction.user.display_avatar.url))
                    await interaction.channel.send(embed=win_embed)
                    
                    cache_set(f"guess:{uid}", None)
                    break
                    
                elif guess < target:
                    hint = "📈 Too low! Go higher!"
                else:
                    hint = "📉 Too high! Go lower!"
                
                remaining = max_attempts - attempts
                
                if remaining == 0:
                    lose_embed = discord.Embed(
                        title="😢 Game Over",
                        description=f"The number was **{target}**.\nBetter luck next time!",
                        color=0xE74C3C,
                    )
                    lose_embed.set_thumbnail(url=str(interaction.user.display_avatar.url))
                    await interaction.channel.send(embed=lose_embed)
                    
                    cache_set(f"guess:{uid}", None)
                    break
                else:
                    hint_embed = discord.Embed(
                        title="🎯 Keep Guessing!",
                        description=hint,
                        color=0xF39C12,
                    )
                    hint_embed.add_field(
                        name="Attempts Left",
                        value=f"**{remaining}**",
                        inline=True
                    )
                    hint_embed.set_footer(text=f"Current guess: {guess}")
                    await interaction.channel.send(embed=hint_embed)
                    
            except asyncio.TimeoutError:
                timeout_embed = discord.Embed(
                    title="⏰ Time's Up!",
                    description=f"The number was **{target}**.\nYou ran out of time!",
                    color=0xE74C3C,
                )
                timeout_embed.set_thumbnail(url=str(interaction.user.display_avatar.url))
                await interaction.channel.send(embed=timeout_embed)
                
                cache_set(f"guess:{uid}", None)
                break

    @app_commands.command(
        name="rps_pvp",
        description="Challenge another player to Rock Paper Scissors"
    )
    @app_commands.describe(opponent="The player you want to challenge")
    async def rps_pvp(
        self,
        interaction: discord.Interaction,
        opponent: discord.User
    ) -> None:
        """Challenge another player to Rock Paper Scissors."""
        await interaction.response.defer()
        
        if opponent.id == interaction.user.id:
            await interaction.followup.send("❌ You can't play against yourself!", ephemeral=True)
            return
        
        if opponent.bot:
            await interaction.followup.send("❌ You can't challenge bots! Use `/rps` instead.", ephemeral=True)
            return
        
        # Check cooldowns
        if cache_get(f"rps_pvp:{interaction.user.id}"):
            await interaction.followup.send("⏳ You're already in a game! Wait a few seconds.", ephemeral=True)
            return
        
        # Send challenge
        embed = discord.Embed(
            title="🎮 Rock Paper Scissors Challenge!",
            description=f"{interaction.user.mention} challenges {opponent.mention} to Rock Paper Scissors!",
            color=0x7289DA,
        )
        embed.add_field(
            name="How to Accept",
            value="Click the button below to accept the challenge!",
            inline=False
        )
        embed.set_footer(text="Winner gets +15 XP!")
        
        view = RPSChallengeView(interaction.user, opponent, self)
        await interaction.followup.send(embed=embed, view=view)


class RPSChoiceView(discord.ui.View):
    """View for players to choose their RPS move."""
    
    def __init__(self, player1: discord.User, player2: discord.User, game_cog: "GamesCog"):
        super().__init__(timeout=60.0)
        self.player1 = player1
        self.player2 = player2
        self.game_cog = game_cog
        self.p1_choice: str | None = None
        self.p2_choice: str | None = None
        self.p1_voted = False
        self.p2_voted = False
    
    @discord.ui.button(label="Rock 🪨", style=discord.ButtonStyle.primary)
    async def rock(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self._handle_choice(interaction, "rock")
    
    @discord.ui.button(label="Paper 📄", style=discord.ButtonStyle.primary)
    async def paper(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self._handle_choice(interaction, "paper")
    
    @discord.ui.button(label="Scissors ✂️", style=discord.ButtonStyle.primary)
    async def scissors(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self._handle_choice(interaction, "scissors")
    
    async def _handle_choice(self, interaction: discord.Interaction, choice: str):
        uid = interaction.user.id
        
        if uid == self.player1.id:
            if self.p1_voted:
                await interaction.response.send_message("✅ You've already chosen! Waiting for opponent...", ephemeral=True)
                return
            self.p1_choice = choice
            self.p1_voted = True
            await interaction.response.send_message("✅ Choice locked in! Waiting for opponent...", ephemeral=True)
        elif uid == self.player2.id:
            if self.p2_voted:
                await interaction.response.send_message("✅ You've already chosen! Waiting for opponent...", ephemeral=True)
                return
            self.p2_choice = choice
            self.p2_voted = True
            await interaction.response.send_message("✅ Choice locked in! Waiting for opponent...", ephemeral=True)
        else:
            await interaction.response.send_message("❌ This game is not for you!", ephemeral=True)
            return
        
        # Check if both voted
        if self.p1_voted and self.p2_voted:
            await self.reveal_results(interaction)
    
    async def reveal_results(self, interaction: discord.Interaction):
        self.stop()
        for item in self.children:
            item.disabled = True
        
        emojis = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
        
        # Determine winner
        result = ""
        winner = None
        xp_reward = 15
        
        if self.p1_choice == self.p2_choice:
            result = "🤝 It's a tie!"
        elif (
            (self.p1_choice == "rock" and self.p2_choice == "scissors") or
            (self.p1_choice == "paper" and self.p2_choice == "rock") or
            (self.p1_choice == "scissors" and self.p2_choice == "paper")
        ):
            result = f"🎉 {self.player1.mention} wins!"
            winner = self.player1.id
            await self.game_cog.user_repo.add_xp(winner, xp_reward)
        else:
            result = f"🎉 {self.player2.mention} wins!"
            winner = self.player2.id
            await self.game_cog.user_repo.add_xp(winner, xp_reward)
        
        embed = discord.Embed(
            title="🎮 Rock Paper Scissors - Results!",
            color=0x7289DA,
        )
        
        embed.add_field(
            name=f"{self.player1.display_name}'s Choice",
            value=f"{emojis[self.p1_choice]} **{self.p1_choice.title()}**",
            inline=True
        )
        
        embed.add_field(
            name=f"{self.player2.display_name}'s Choice",
            value=f"{emojis[self.p2_choice]} **{self.p2_choice.title()}**",
            inline=True
        )
        
        embed.add_field(
            name="Result",
            value=result,
            inline=False
        )
        
        if winner:
            embed.add_field(
                name="🎁 Reward",
                value=f"+{xp_reward} XP",
                inline=True
            )
        
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.channel.send(embed=embed)


class RPSChallengeView(discord.ui.View):
    """View for accepting an RPS challenge."""
    
    def __init__(self, challenger: discord.User, opponent: discord.User, game_cog: "GamesCog"):
        super().__init__(timeout=60.0)
        self.challenger = challenger
        self.opponent = opponent
        self.game_cog = game_cog
    
    @discord.ui.button(label="Accept Challenge 🎮", style=discord.ButtonStyle.success)
    async def accept(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("❌ Only the challenged player can accept!", ephemeral=True)
            return
        
        self.stop()
        for item in self.children:
            item.disabled = True
        
        # Start the game
        embed = discord.Embed(
            title="🎮 Rock Paper Scissors PvP",
            description=f"{self.challenger.mention} vs {self.opponent.mention}\n\nBoth players, choose your move!",
            color=0x7289DA,
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
        
        # Start the choice phase
        game_view = RPSChoiceView(self.challenger, self.opponent, self.game_cog)
        await interaction.channel.send(
            content="🎮 **Rock Paper Scissors PvP has started!**",
            embed=discord.Embed(
                description="Make your choice privately!",
                color=0x7289DA
            ),
            view=game_view
        )
    
    @discord.ui.button(label="Decline ❌", style=discord.ButtonStyle.danger)
    async def decline(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("❌ Only the challenged player can decline!", ephemeral=True)
            return
        
        self.stop()
        for item in self.children:
            item.disabled = True
        
        embed = discord.Embed(
            title="❌ Challenge Declined",
            description=f"{self.opponent.mention} declined the challenge.",
            color=0xE74C3C,
        )
        await interaction.response.edit_message(embed=embed, view=None)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(GamesCog(bot))
