import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, Literal
import asyncio

# Database simulation (Replace with your actual DB logic)
# In a real bot, use SQLite, PostgreSQL, or MongoDB
user_profiles = {} 

class GenderSelect(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.selected_gender = None

    @discord.ui.button(label="Male", style=discord.ButtonStyle.blurple, emoji="👨")
    async def male_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.selected_gender = "male"
        await self.finalize_selection(interaction, "Male")

    @discord.ui.button(label="Female", style=discord.ButtonStyle.pink, emoji="👩")
    async def female_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.selected_gender = "female"
        await self.finalize_selection(interaction, "Female")

    @discord.ui.button(label="Non-Binary", style=discord.ButtonStyle.grey, emoji="⚧️")
    async def nb_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.selected_gender = "non-binary"
        await self.finalize_selection(interaction, "Non-Binary")

    async def finalize_selection(self, interaction: discord.Interaction, gender_label: str):
        # Save to "database"
        if self.user_id not in user_profiles:
            user_profiles[self.user_id] = {}
        
        user_profiles[self.user_id]['gender'] = self.selected_gender
        user_profiles[self.user_id]['consent_given'] = False # Reset consent to force re-agreement
        
        embed = discord.Embed(
            title="✅ Gender Updated",
            description=f"You have identified as **{gender_label}**.",
            color=discord.Color.green()
        )
        embed.add_field(name="Next Step", value="You must now agree to the Community Guidelines to access restricted commands.")
        
        await interaction.response.edit_message(embed=embed, view=ConsentView(self.user_id))

class ConsentView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="I Agree & Am 18+", style=discord.ButtonStyle.green, emoji="✅")
    async def agree_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.user_id not in user_profiles:
            user_profiles[self.user_id] = {}
            
        user_profiles[self.user_id]['consent_given'] = True
        
        embed = discord.Embed(
            title="🔓 Access Granted",
            description="You have successfully verified your age and consented to the guidelines.",
            color=discord.Color.gold()
        )
        embed.add_field(name="Status", value="You may now use restricted commands.")
        
        await interaction.response.edit_message(embed=embed, view=None)
        
    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red, emoji="❌")
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🚫 Access Denied",
            description="You must agree to the guidelines to use these commands.",
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=None)

class VerificationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_user_profile(self, user_id: int):
        return user_profiles.get(user_id, None)

    def is_verified(self, user_id: int) -> bool:
        profile = self.get_user_profile(user_id)
        if not profile:
            return False
        return profile.get('consent_given', False) and profile.get('gender') is not None

    def get_gender_text(self, user_id: int, male_text: str, female_text: str, neutral_text: str = "they") -> str:
        """Returns text based on user's selected gender."""
        profile = self.get_user_profile(user_id)
        if not profile:
            return neutral_text
        
        gender = profile.get('gender')
        if gender == 'male':
            return male_text
        elif gender == 'female':
            return female_text
        else:
            return neutral_text

    @app_commands.command(name="verify", description="Start the verification process to access restricted commands.")
    async def verify(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        
        # Check current status
        profile = self.get_user_profile(user_id)
        
        if profile and profile.get('consent_given') and profile.get('gender'):
            await interaction.response.send_message(
                "✅ You are already verified!", 
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="⚠️ Verification Required",
            description="To access restricted commands, you must verify your age and select your gender.\n\n"
                        "**Disclaimer**: By proceeding, you confirm you are at least 18 years old and agree to interact with mature content responsibly.",
            color=discord.Color.orange()
        )
        
        await interaction.response.send_message(embed=embed, view=GenderSelect(user_id))

    @app_commands.command(name="profile", description="Check your current verification status.")
    async def profile_cmd(self, interaction: discord.Interaction):
        profile = self.get_user_profile(interaction.user.id)
        
        if not profile:
            status = "❌ Not Started"
            gender = "Not Set"
            consent = "Not Given"
        else:
            status = "✅ Verified" if self.is_verified(interaction.user.id) else "⚠️ Incomplete"
            gender = profile.get('gender', 'Not Set').title()
            consent = "✅ Given" if profile.get('consent_given') else "❌ Pending"

        embed = discord.Embed(title="User Profile", color=discord.Color.blurple())
        embed.add_field(name="Status", value=status, inline=False)
        embed.add_field(name="Gender", value=gender, inline=True)
        embed.add_field(name="Consent", value=consent, inline=True)
        
        if not self.is_verified(interaction.user.id):
            embed.set_footer(text="Run /verify to complete setup.")
            
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Decorator to check verification
def requires_verification():
    async def predicate(interaction: discord.Interaction) -> bool:
        cog = interaction.client.get_cog("VerificationCog")
        if not cog:
            raise app_commands.CommandError("Verification system not loaded.")
        
        if not cog.is_verified(interaction.user.id):
            embed = discord.Embed(
                title="🔒 Command Locked",
                description="You must verify your age and gender before using this command.\nUse `/verify` to start.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

async def setup(bot):
    await bot.add_cog(VerificationCog(bot))
