"""
Filament change helper for Discord Printer Bot.
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

import db
import api
import permissions


class FilamentCog(commands.Cog):
    """Filament change commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="filament", description="Filament change menu")
    async def filament(self, interaction: discord.Interaction):
        """Show filament change menu."""
        user_id = interaction.user.id
        active_printer_id = db.get_active_printer_id(user_id)

        try:
            permissions.check_control_permission(user_id, active_printer_id)
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return

        embed = discord.Embed(
            title="🧵 Filament Management",
            description="Quick load/unload filament (Heats to 200°C automatically).",
            color=0xE67E22,
        )

        view = FilamentView(user_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class FilamentView(discord.ui.View):
    """Filament management view."""

    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="📥 Load Filament", style=discord.ButtonStyle.success)
    async def load_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._action(interaction, "LOAD_FILAMENT")

    @discord.ui.button(label="📤 Unload Filament", style=discord.ButtonStyle.danger)
    async def unload_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._action(interaction, "UNLOAD_FILAMENT")

    async def _action(self, interaction: discord.Interaction, macro: str):
        await interaction.response.defer()
        # Heat and run macro
        cmd = f"M109 S200\n{macro}"
        await api.gcode(cmd, self.user_id)
        await interaction.followup.send(f"✅ Executing {macro} (Heating to 200°C first)", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(FilamentCog(bot))
