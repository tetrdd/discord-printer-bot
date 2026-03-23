"""
Macro commands for Discord Printer Bot.
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

import config
import api
import permissions


class MacrosCog(commands.Cog):
    """Macro commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.user_pages = {}  # {user_id: (macros, page)}
    
    @app_commands.command(name="macros", description="List available macros")
    @app_commands.describe(page="Page number (default: 1)")
    async def macros(self, interaction: discord.Interaction, page: Optional[int] = 1):
        """List available Klipper macros."""
        user_id = interaction.user.id
        
        try:
            permissions.check_control_permission(user_id, config.active_printer_id(user_id))
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        macros = await api.get_macros(user_id)
        
        if not macros:
            await interaction.followup.send(
                "📜 No macros found. (Note: Macros are only available on Moonraker/Klipper)",
                ephemeral=True,
            )
            return
        
        # Apply aliases from config
        macros_cfg = config.macros_config()
        aliases = macros_cfg.get("aliases", {})
        per_page = macros_cfg.get("per_page", 10)
        
        # Sort and paginate
        macros.sort()
        total_pages = (len(macros) + per_page - 1) // per_page
        
        if page < 1:
            page = 1
        elif page > total_pages:
            page = total_pages
        
        self.user_pages[user_id] = (macros, page)
        
        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, len(macros))
        page_macros = macros[start_idx:end_idx]
        
        embed = discord.Embed(
            title="📜 Available Macros",
            description=f"Page {page}/{total_pages} ({len(macros)} macros)",
            color=0x9B59B6,
        )
        
        for macro in page_macros:
            display_name = aliases.get(macro, macro)
            embed.add_field(
                name=f"🔹 {display_name}",
                value=f"`/{macro}`",
                inline=True,
            )
        
        view = MacrosView(user_id, page, total_pages)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="run-macro", description="Run a macro")
    @app_commands.describe(macro="Name of the macro to run")
    async def run_macro(self, interaction: discord.Interaction, macro: str):
        """Run a specific macro."""
        user_id = interaction.user.id
        
        try:
            permissions.check_control_permission(user_id, config.active_printer_id(user_id))
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        result = await api.gcode(macro, user_id)
        
        if result:
            await interaction.followup.send(f"✅ Ran macro: `{macro}`", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ Failed to run macro: `{macro}`", ephemeral=True)


class MacrosView(discord.ui.View):
    """Macro browser pagination view."""
    
    def __init__(self, user_id: int, page: int, total_pages: int):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.page = page
        self.total_pages = total_pages
        
        self.prev_btn.disabled = page <= 1
        self.next_btn.disabled = page >= total_pages
    
    @discord.ui.button(label="⏮️ Previous", style=discord.ButtonStyle.secondary)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"Use `/macros page:{self.page - 1}`",
            ephemeral=True,
        )
    
    @discord.ui.button(label="⏭️ Next", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"Use `/macros page:{self.page + 1}`",
            ephemeral=True,
        )
    
    @discord.ui.button(label="▶️ Run Selected", style=discord.ButtonStyle.primary)
    async def run_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Use `/run-macro macro:<name>` to run a macro.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(MacrosCog(bot))
