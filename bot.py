#!/usr/bin/env python3
"""
Discord Printer Bot - Main entry point.
A Discord bot for controlling 3D printers via Moonraker, OctoPrint, or OctoEverywhere.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path so imports work
sys.path.insert(0, str(Path(__file__).parent))

import discord
from discord import app_commands
from discord.ext import commands, tasks

import config
import db

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("PrinterBot")


class PrinterBot(commands.Bot):
    """Custom bot class with setup handling."""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            description="3D Printer Control Bot for Discord",
        )
    
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button clicks and other interactions."""
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get('custom_id', '')
            
            # Handle printer edit button
            if custom_id.startswith('printer_edit:'):
                printer_id = int(custom_id.split(':')[1])
                await self.handle_printer_edit(interaction, printer_id)
            
            # Handle printer delete button
            elif custom_id.startswith('printer_delete:'):
                printer_id = int(custom_id.split(':')[1])
                await self.handle_printer_delete(interaction, printer_id)
            
            # Handle printer users button
            elif custom_id.startswith('printer_users:'):
                printer_id = int(custom_id.split(':')[1])
                await self.handle_printer_users(interaction, printer_id)
            
            # Handle user settings edit button
            elif custom_id.startswith('user_settings_edit:'):
                user_id = int(custom_id.split(':')[1])
                await self.handle_user_settings_edit(interaction, user_id)

            # Handle printer activation button
            elif custom_id.startswith('printer_activate:'):
                printer_id = int(custom_id.split(':')[1])
                await self.handle_printer_activate(interaction, printer_id)
    
    async def handle_printer_edit(self, interaction: discord.Interaction, printer_id: int):
        """Handle printer edit button click."""
        from handlers.printer_config import PrinterSettingsModal
        
        user_id = interaction.user.id
        
        # Check ownership
        if not db.is_printer_owner(user_id, printer_id):
            await interaction.response.send_message(
                "❌ Only the printer owner can edit these settings.",
                ephemeral=True,
            )
            return
        
        printer = db.get_printer(printer_id)
        if not printer:
            await interaction.response.send_message(
                "❌ Printer not found.",
                ephemeral=True,
            )
            return
        
        await interaction.response.send_modal(PrinterSettingsModal(printer_id, printer))
    
    async def handle_printer_delete(self, interaction: discord.Interaction, printer_id: int):
        """Handle printer delete button click."""
        user_id = interaction.user.id
        
        # Check ownership
        if not db.is_printer_owner(user_id, printer_id):
            await interaction.response.send_message(
                "❌ Only the printer owner can delete this printer.",
                ephemeral=True,
            )
            return
        
        printer = db.get_printer(printer_id)
        if not printer:
            await interaction.response.send_message(
                "❌ Printer not found.",
                ephemeral=True,
            )
            return
        
        # Show confirmation view
        view = discord.ui.View(timeout=30.0)
        
        async def confirm_callback(interaction: discord.Interaction):
            db.delete_printer(printer_id)
            await interaction.response.edit_message(
                content=f"✅ Printer **{printer['name']}** has been deleted.",
                view=None,
            )
        
        async def cancel_callback(interaction: discord.Interaction):
            await interaction.response.edit_message(
                content="❌ Deletion cancelled.",
                view=None,
            )
        
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.danger,
                label="Confirm Delete",
                custom_id="confirm_delete",
            )
        )
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.secondary,
                label="Cancel",
                custom_id="cancel_delete",
            )
        )
        
        # Set callbacks
        for item in view.children:
            if item.custom_id == "confirm_delete":
                item.callback = confirm_callback
            elif item.custom_id == "cancel_delete":
                item.callback = cancel_callback
        
        await interaction.response.send_message(
            f"⚠️ Are you sure you want to delete **{printer['name']}**? This cannot be undone.",
            view=view,
            ephemeral=True,
        )
    
    async def handle_printer_users(self, interaction: discord.Interaction, printer_id: int):
        """Handle printer manage users button click."""
        from handlers.printer_config import AllowedUsersView
        
        user_id = interaction.user.id
        
        # Check ownership
        if not db.is_printer_owner(user_id, printer_id):
            await interaction.response.send_message(
                "❌ Only the printer owner can manage users.",
                ephemeral=True,
            )
            return
        
        printer = db.get_printer(printer_id)
        if not printer:
            await interaction.response.send_message(
                "❌ Printer not found.",
                ephemeral=True,
            )
            return
        
        allowed_users = db.get_allowed_users(printer_id)
        
        embed = discord.Embed(
            title=f"👥 Manage Users - {printer['name']}",
            description=f"Printer ID: `{printer_id}`",
            color=discord.Color.blue(),
        )
        
        if allowed_users:
            users_str = "\n".join([f"• <@{uid}> (`{uid}`)" for uid in allowed_users])
            embed.add_field(
                name="Allowed Users",
                value=users_str,
                inline=False,
            )
        else:
            embed.add_field(
                name="Allowed Users",
                value="No users have been added yet.",
                inline=False,
            )
        
        embed.add_field(
            name="Add User",
            value="Use `/add-user {printer_id} <user>`",
            inline=False,
        )
        
        view = AllowedUsersView(printer_id, allowed_users) if allowed_users else None
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def handle_user_settings_edit(self, interaction: discord.Interaction, user_id: int):
        """Handle user settings edit button click."""
        from handlers.printer_config import UserSettingsModal
        
        if interaction.user.id != user_id:
            await interaction.response.send_message(
                "❌ You can only edit your own settings.",
                ephemeral=True,
            )
            return
        
        user = interaction.user
        await interaction.response.send_modal(UserSettingsModal(user))

    async def handle_printer_activate(self, interaction: discord.Interaction, printer_id: int):
        """Handle printer activation button click."""
        user_id = interaction.user.id

        if db.set_active_printer(user_id, printer_id):
            printer = db.get_printer(printer_id)
            await interaction.response.send_message(
                f"✅ **{printer['name']}** is now your active printer.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "❌ Failed to set active printer. Do you have access?",
                ephemeral=True,
            )
    
    async def setup_hook(self):
        """Load cogs on startup."""
        # Load all handler cogs
        cogs = [
            "handlers.status",
            "handlers.control",
            "handlers.temps",
            "handlers.files",
            "handlers.camera",
            "handlers.macros",
            "handlers.adjust",
            "handlers.history",
            "handlers.bed_mesh",
            "handlers.printers",
            "handlers.printer_config",
        ]
        
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}")
        
        # Sync commands
        self.tree.copy_global_to(guilds=None)
        await self.tree.sync()
        logger.info("Synced slash commands")
    
    async def on_ready(self):
        """Called when bot is ready."""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="your 3D prints 🖨️",
            )
        )


async def main():
    """Main entry point."""
    # Initialize DB
    db.init_db()

    # Load configuration
    config.load()
    
    # Get Discord token
    token = config.discord_token()
    if not token or token == "YOUR_DISCORD_BOT_TOKEN_HERE":
        logger.error("Discord bot token not configured")
        logger.error("Please set DISCORD_TOKEN env var or configure in config.yaml")
        sys.exit(1)
    
    # Create and run bot
    bot = PrinterBot()
    
    try:
        await bot.start(token)
    except discord.LoginFailure:
        logger.error("Invalid Discord bot token")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Bot error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
