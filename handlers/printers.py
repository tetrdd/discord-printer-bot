"""
Printer management commands for Discord Printer Bot.
Switch printers, manage permissions, configure settings.
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

import db
import permissions


class PrintersCog(commands.Cog):
    """Printer management commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="printers", description="List accessible printers")
    async def printers(self, interaction: discord.Interaction):
        """List all printers you have access to."""
        await self.show_printers(interaction)

    async def show_printers(self, interaction: discord.Interaction, edit: bool = False):
        user_id = interaction.user.id
        
        if edit:
            await interaction.response.defer()
        else:
            await interaction.response.defer(ephemeral=True)

        printers = db.get_accessible_printers(user_id)
        if printers:
            embed = discord.Embed(
                title="🖨️ Your Printers",
                description=f"You have access to **{len(printers)}** printer(s).",
                color=discord.Color.green(),
            )

            active_id = db.get_active_printer_id(user_id)

            for printer in printers:
                pid = printer['printer_id']
                name = printer['name']
                ptype = printer['type']
                privacy = printer['privacy']
                
                owner_emoji = "👑" if db.is_printer_owner(user_id, pid) else ""
                privacy_emoji = "🔒" if privacy == 'private' else "🌍"
                active_emoji = "⭐ " if pid == active_id else ""
                
                embed.add_field(
                    name=f"{active_emoji}{owner_emoji} {name}",
                    value=f"ID: `{pid}` • {ptype} • {privacy_emoji}",
                    inline=False,
                )

            view = discord.ui.View(timeout=None)
            view.add_item(discord.ui.Button(label="⬅️ Back", style=discord.ButtonStyle.secondary, custom_id="back_to_menu"))

            if edit:
                await interaction.edit_original_response(embed=embed, view=view)
            else:
                await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.followup.send("You don't have access to any printers. Use `/register-printer` to add one!", ephemeral=True)
    
    @app_commands.command(name="switch-printer", description="Switch to a different printer")
    @app_commands.describe(printer_id="Printer ID to switch to")
    async def switch_printer(self, interaction: discord.Interaction, printer_id: int):
        """Switch to a different printer."""
        user_id = interaction.user.id
        
        printer = db.get_printer(printer_id)
        
        if not printer:
            await interaction.response.send_message(
                f"❌ Printer ID {printer_id} not found.",
                ephemeral=True,
            )
            return
        
        if not db.user_can_view(user_id, printer_id):
            await interaction.response.send_message(
                "❌ You don't have permission to access this printer.",
                ephemeral=True,
            )
            return
        
        if db.set_active_printer(user_id, printer_id):
            await interaction.response.send_message(
                f"✅ Switched to: **{printer.get('name', f'Printer {printer_id}')}**",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message("❌ Failed to switch printer.", ephemeral=True)
    
    @app_commands.command(name="printer-info", description="Get printer information")
    @app_commands.describe(printer_id="Printer ID (default: current)")
    async def printer_info(self, interaction: discord.Interaction, printer_id: Optional[int] = None):
        """Get detailed information about a printer."""
        user_id = interaction.user.id
        
        if printer_id is None:
            printer_id = db.get_active_printer_id(user_id)

        if printer_id is None:
            await interaction.response.send_message("❌ No active printer set.", ephemeral=True)
            return
        
        printer = db.get_printer(printer_id)
        if not printer:
            await interaction.response.send_message("❌ Printer not found.", ephemeral=True)
            return

        if not db.user_can_view(user_id, printer_id):
            await interaction.response.send_message("❌ Access denied.", ephemeral=True)
            return

        is_owner = db.is_printer_owner(user_id, printer_id)
        
        embed = discord.Embed(
            title=f"🖨️ {printer['name']}",
            color=discord.Color.blue(),
        )
        embed.add_field(name="ID", value=f"`{printer_id}`", inline=True)
        embed.add_field(name="Type", value=printer['type'], inline=True)
        embed.add_field(name="Privacy", value=printer['privacy'], inline=True)
        
        if is_owner:
            embed.add_field(name="URL/Key", value=f"`{printer['url']}`", inline=False)

        owner_id = printer['owner_discord_id']
        embed.add_field(name="Owner", value=f"<@{owner_id}>", inline=True)
        
        allowed_users = db.get_allowed_users(printer_id)
        if allowed_users:
            users_str = ", ".join([f"<@{uid}>" for uid in allowed_users])
            embed.add_field(name="Allowed Users", value=users_str, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(PrintersCog(bot))
