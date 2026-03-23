"""
Printer management commands for Discord Printer Bot.
Switch printers, manage permissions, configure settings.

Note: For v2.0+, use /register-printer, /printer-settings, /my-settings
for database-driven printer management. These commands are kept for
backwards compatibility with config.yaml-based setups.
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

import config
import permissions
import db


class PrintersCog(commands.Cog):
    """Printer management commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="printers", description="List accessible printers")
    async def printers(self, interaction: discord.Interaction):
        """List all printers you have access to."""
        user_id = interaction.user.id
        
        # Try database first (v2.0+)
        try:
            printers = db.get_accessible_printers(user_id)
            if printers:
                embed = discord.Embed(
                    title="🖨️ Your Printers",
                    description=f"You have access to **{len(printers)}** printer(s).",
                    color=discord.Color.green(),
                )
                
                for printer in printers:
                    pid = printer['printer_id']
                    name = printer['name']
                    ptype = printer['type']
                    privacy = printer['privacy']
                    
                    owner_emoji = "👑" if db.is_printer_owner(user_id, pid) else ""
                    privacy_emoji = "🔒" if privacy == 'private' else "🌍"
                    
                    embed.add_field(
                        name=f"{owner_emoji} {name}",
                        value=f"ID: `{pid}` • {ptype} • {privacy_emoji}",
                        inline=False,
                    )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        except Exception:
            pass
        
        # Fallback to config.yaml (legacy)
        embed_data = permissions.get_accessible_printers_embed(user_id)
        
        embed = discord.Embed(
            title=embed_data["title"],
            description=embed_data["description"],
            color=embed_data["color"],
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="switch-printer", description="Switch to a different printer")
    @app_commands.describe(printer_id="Printer ID to switch to")
    async def switch_printer(self, interaction: discord.Interaction, printer_id: int):
        """Switch to a different printer."""
        user_id = interaction.user.id
        
        printer = config.get_printer(printer_id)
        
        if not printer:
            await interaction.response.send_message(
                f"❌ Printer ID {printer_id} not found.",
                ephemeral=True,
            )
            return
        
        if not permissions.check_view_permission(user_id, printer_id):
            await interaction.response.send_message(
                "❌ You don't have permission to access this printer.",
                ephemeral=True,
            )
            return
        
        config.set_active_printer(user_id, printer_id)
        
        await interaction.response.send_message(
            f"✅ Switched to: **{printer.get('name', f'Printer {printer_id}')}**",
            ephemeral=True,
        )
    
    @app_commands.command(name="printer-info", description="Get printer information")
    @app_commands.describe(printer_id="Printer ID (default: current)")
    async def printer_info(self, interaction: discord.Interaction, printer_id: Optional[int] = None):
        """Get detailed information about a printer."""
        user_id = interaction.user.id
        
        if printer_id is None:
            printer_id = config.active_printer_id(user_id)
        
        embed_data = permissions.get_printer_info_embed(printer_id, user_id)
        
        embed = discord.Embed(
            title=embed_data["title"],
            color=embed_data["color"],
        )
        
        for field in embed_data.get("fields", []):
            embed.add_field(**field)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="set-privacy",
        description="Set printer privacy (owner only)"
    )
    @app_commands.describe(
        printer_id="Printer ID",
        private="Set to private (true) or public (false)"
    )
    async def set_privacy(
        self,
        interaction: discord.Interaction,
        printer_id: int,
        private: bool,
    ):
        """Set printer privacy setting (owner only)."""
        user_id = interaction.user.id
        
        try:
            permissions.check_owner_permission(user_id, printer_id)
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        result = permissions.set_printer_privacy(printer_id, private)
        
        if result:
            status = "🔒 Private" if private else "🌍 Public"
            await interaction.response.send_message(
                f"✅ Printer privacy set to: {status}",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "❌ Failed to update privacy setting",
                ephemeral=True,
            )
    
    @app_commands.command(
        name="add-user",
        description="Add user to printer allowed list (owner only)"
    )
    @app_commands.describe(
        printer_id="Printer ID",
        user_id="Discord user ID to add"
    )
    async def add_user(
        self,
        interaction: discord.Interaction,
        printer_id: int,
        user_id: int,
    ):
        """Add a user to the printer's allowed users list (owner only)."""
        owner_id = interaction.user.id
        
        try:
            permissions.check_owner_permission(owner_id, printer_id)
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        result = permissions.add_allowed_user(printer_id, user_id)
        
        if result:
            await interaction.response.send_message(
                f"✅ Added <@{user_id}> to allowed users",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "❌ Failed to add user (may already be in list)",
                ephemeral=True,
            )
    
    @app_commands.command(
        name="remove-user",
        description="Remove user from printer allowed list (owner only)"
    )
    @app_commands.describe(
        printer_id="Printer ID",
        user_id="Discord user ID to remove"
    )
    async def remove_user(
        self,
        interaction: discord.Interaction,
        printer_id: int,
        user_id: int,
    ):
        """Remove a user from the printer's allowed users list (owner only)."""
        owner_id = interaction.user.id
        
        try:
            permissions.check_owner_permission(owner_id, printer_id)
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        result = permissions.remove_allowed_user(printer_id, user_id)
        
        if result:
            await interaction.response.send_message(
                f"✅ Removed <@{user_id}> from allowed users",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "❌ Failed to remove user (may not be in list)",
                ephemeral=True,
            )
    
    @app_commands.command(
        name="rename-printer",
        description="Rename a printer (owner only)"
    )
    @app_commands.describe(
        printer_id="Printer ID",
        new_name="New name for the printer"
    )
    async def rename_printer(
        self,
        interaction: discord.Interaction,
        printer_id: int,
        new_name: str,
    ):
        """Rename a printer (owner only)."""
        owner_id = interaction.user.id
        
        try:
            permissions.check_owner_permission(owner_id, printer_id)
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        result = permissions.update_printer_settings(printer_id, name=new_name)
        
        if result:
            await interaction.response.send_message(
                f"✅ Printer renamed to: **{new_name}**",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "❌ Failed to rename printer",
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(PrintersCog(bot))
