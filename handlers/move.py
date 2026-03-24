"""
Movement control commands for Discord Printer Bot.
Manual axis movement and homing.
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

import db
import api
import permissions


class MoveCog(commands.Cog):
    """Movement control commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="move", description="Show movement controls")
    async def move(self, interaction: discord.Interaction):
        """Show movement control menu."""
        await self.show_move(interaction)

    async def show_move(self, interaction: discord.Interaction, edit: bool = False):
        user_id = interaction.user.id
        active_printer_id = db.get_active_printer_id(user_id)

        try:
            permissions.check_control_permission(user_id, active_printer_id)
        except permissions.PermissionError as e:
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return

        embed = discord.Embed(
            title="🎮 Movement Control",
            description="Control axes and homing. Step size: **10mm**",
            color=0x2ECC71,
        )

        view = MoveView(user_id)
        view.add_item(discord.ui.Button(label="⬅️ Back", style=discord.ButtonStyle.secondary, custom_id="back_to_menu"))

        if edit:
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class MoveView(discord.ui.View):
    """Movement control grid view."""

    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.step = 10.0

    @discord.ui.button(label="Y+", style=discord.ButtonStyle.secondary, row=0)
    async def y_plus(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._move(interaction, "Y", self.step)

    @discord.ui.button(label="X-", style=discord.ButtonStyle.secondary, row=1)
    async def x_minus(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._move(interaction, "X", -self.step)

    @discord.ui.button(label="🏠 XY", style=discord.ButtonStyle.primary, row=1)
    async def home_xy(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await api.gcode("G28 X Y", self.user_id)
        await interaction.followup.send("🏠 Homing X Y...", ephemeral=True)

    @discord.ui.button(label="X+", style=discord.ButtonStyle.secondary, row=1)
    async def x_plus(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._move(interaction, "X", self.step)

    @discord.ui.button(label="Y-", style=discord.ButtonStyle.secondary, row=2)
    async def y_minus(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._move(interaction, "Y", -self.step)

    @discord.ui.button(label="Z+", style=discord.ButtonStyle.secondary, row=0)
    async def z_plus(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._move(interaction, "Z", self.step)

    @discord.ui.button(label="🏠 Z", style=discord.ButtonStyle.primary, row=1)
    async def home_z(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await api.gcode("G28 Z", self.user_id)
        await interaction.followup.send("🏠 Homing Z...", ephemeral=True)

    @discord.ui.button(label="Z-", style=discord.ButtonStyle.secondary, row=2)
    async def z_minus(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._move(interaction, "Z", -self.step)

    @discord.ui.button(label="0.1", style=discord.ButtonStyle.secondary, row=3)
    async def step_01(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.step = 0.1
        await self._update_step(interaction)

    @discord.ui.button(label="1", style=discord.ButtonStyle.secondary, row=3)
    async def step_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.step = 1.0
        await self._update_step(interaction)

    @discord.ui.button(label="10", style=discord.ButtonStyle.primary, row=3)
    async def step_10(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.step = 10.0
        await self._update_step(interaction)

    @discord.ui.button(label="50", style=discord.ButtonStyle.secondary, row=3)
    async def step_50(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.step = 50.0
        await self._update_step(interaction)

    async def _move(self, interaction: discord.Interaction, axis: str, dist: float):
        await interaction.response.defer()
        cmd = f"G91\nG1 {axis}{dist} F3000\nG90"
        await api.gcode(cmd, self.user_id)
        await interaction.followup.send(f"Moving {axis} {dist}mm", ephemeral=True)

    async def _update_step(self, interaction: discord.Interaction):
        # Update button colors to show active step
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.label in ["0.1", "1", "10", "50"]:
                child.style = discord.ButtonStyle.primary if float(child.label) == self.step else discord.ButtonStyle.secondary

        embed = interaction.message.embeds[0]
        embed.description = f"Control axes and homing. Step size: **{self.step}mm**"
        await interaction.response.edit_message(embed=embed, view=self)


async def setup(bot: commands.Bot):
    await bot.add_cog(MoveCog(bot))
