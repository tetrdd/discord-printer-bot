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
            
            # Handle printer edit buttons
            if custom_id.startswith('printer_edit_name:'):
                printer_id = int(custom_id.split(':')[1])
                await self.handle_printer_edit_name(interaction, printer_id)
            elif custom_id.startswith('printer_edit_conn:'):
                printer_id = int(custom_id.split(':')[1])
                await self.handle_printer_edit_conn(interaction, printer_id)
            elif custom_id.startswith('printer_edit_cam:'):
                printer_id = int(custom_id.split(':')[1])
                await self.handle_printer_edit_cam(interaction, printer_id)
            
            # Handle printer delete button
            elif custom_id.startswith('printer_delete:'):
                printer_id = int(custom_id.split(':')[1])
                await self.handle_printer_delete(interaction, printer_id)
            
            # Handle printer users button
            elif custom_id.startswith('printer_users:'):
                printer_id = int(custom_id.split(':')[1])
                await self.handle_printer_users(interaction, printer_id)
            
            # Handle user settings edit buttons
            elif custom_id.startswith('user_edit_tz:'):
                user_id = int(custom_id.split(':')[1])
                await self.handle_user_edit_tz(interaction, user_id)
            elif custom_id.startswith('user_select_lang:'):
                user_id = int(custom_id.split(':')[1])
                await self.handle_user_select_lang(interaction, user_id)
            elif custom_id.startswith('user_edit_notify:'):
                user_id = int(custom_id.split(':')[1])
                await self.handle_user_edit_notify(interaction, user_id)
            elif custom_id.startswith('user_set_dm_notify:'):
                user_id = int(custom_id.split(':')[1])
                await self.handle_user_set_dm_notify(interaction, user_id)
            elif custom_id.startswith('user_manage_printer:'):
                printer_id = int(custom_id.split(':')[1])
                from handlers.printer_config import PrinterConfigCog
                cog = self.get_cog("PrinterConfigCog")
                if cog:
                    await cog.printer_settings(interaction, printer_id)

            # Handle printer activation button
            elif custom_id.startswith('printer_activate:'):
                printer_id = int(custom_id.split(':')[1])
                await self.handle_printer_activate(interaction, printer_id)

            # Handle printer privacy toggle button
            elif custom_id.startswith('printer_privacy_toggle:'):
                printer_id = int(custom_id.split(':')[1])
                await self.handle_printer_privacy_toggle(interaction, printer_id)

            # Handle back to menu button
            elif custom_id == "back_to_menu":
                from handlers.status import StatusCog
                cog = self.get_cog("StatusCog")
                if cog:
                    await cog.show_main_menu(interaction, edit=True)
    
    async def handle_printer_edit_name(self, interaction: discord.Interaction, printer_id: int):
        from handlers.printer_config import EditNameModal
        printer = db.get_printer(printer_id)
        if not printer or not db.is_printer_owner(interaction.user.id, printer_id):
            await interaction.response.send_message("❌ Not found or no permission.", ephemeral=True)
            return
        await interaction.response.send_modal(EditNameModal(printer_id, printer['name']))

    async def handle_printer_edit_conn(self, interaction: discord.Interaction, printer_id: int):
        from handlers.printer_config import EditConnectionModal
        printer = db.get_printer(printer_id)
        if not printer or not db.is_printer_owner(interaction.user.id, printer_id):
            await interaction.response.send_message("❌ Not found or no permission.", ephemeral=True)
            return
        await interaction.response.send_modal(EditConnectionModal(printer_id, printer['url']))

    async def handle_printer_edit_cam(self, interaction: discord.Interaction, printer_id: int):
        from handlers.printer_config import EditCameraModal
        printer = db.get_printer(printer_id)
        if not printer or not db.is_printer_owner(interaction.user.id, printer_id):
            await interaction.response.send_message("❌ Not found or no permission.", ephemeral=True)
            return
        await interaction.response.send_modal(EditCameraModal(printer_id, printer.get('camera_url', ''), printer.get('stream_url', '')))
    
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
    
    async def handle_user_edit_tz(self, interaction: discord.Interaction, user_id: int):
        from handlers.printer_config import EditTimezoneModal
        if interaction.user.id != user_id:
            await interaction.response.send_message("❌ Not yours.", ephemeral=True)
            return
        user_data = db.get_user(user_id)
        await interaction.response.send_modal(EditTimezoneModal(user_data.get('timezone', '') if user_data else ''))

    async def handle_user_select_lang(self, interaction: discord.Interaction, user_id: int):
        from handlers.printer_config import LanguageSelectView
        if interaction.user.id != user_id:
            await interaction.response.send_message("❌ Not yours.", ephemeral=True)
            return
        await interaction.response.send_message("Select your language:", view=LanguageSelectView(user_id), ephemeral=True)

    async def handle_user_edit_notify(self, interaction: discord.Interaction, user_id: int):
        from handlers.printer_config import EditNotifyChannelModal
        if interaction.user.id != user_id:
            await interaction.response.send_message("❌ Not yours.", ephemeral=True)
            return
        user_data = db.get_user(user_id)
        await interaction.response.send_modal(EditNotifyChannelModal(user_data.get('notify_channel', '') if user_data else ''))

    async def handle_user_set_dm_notify(self, interaction: discord.Interaction, user_id: int):
        if interaction.user.id != user_id:
            await interaction.response.send_message("❌ Not yours.", ephemeral=True)
            return
        if db.update_user(user_id, notify_channel="DM"):
            from handlers.printer_config import PrinterConfigCog
            cog = self.get_cog("PrinterConfigCog")
            if cog:
                await cog.show_my_settings(interaction, edit=True)
            else:
                await interaction.response.send_message("✅ Notifications set to DM.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Failed to update.", ephemeral=True)

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

    async def handle_printer_privacy_toggle(self, interaction: discord.Interaction, printer_id: int):
        """Handle printer privacy toggle button click."""
        user_id = interaction.user.id

        if not db.is_printer_owner(user_id, printer_id):
            await interaction.response.send_message("❌ Only the owner can change privacy settings.", ephemeral=True)
            return

        printer = db.get_printer(printer_id)
        if not printer:
            await interaction.response.send_message("❌ Printer not found.", ephemeral=True)
            return

        # Toggle: public -> private -> unlisted -> public
        current = printer['privacy']
        if current == 'public':
            new_privacy = 'private'
        elif current == 'private':
            new_privacy = 'unlisted'
        else:
            new_privacy = 'public'

        if db.update_printer(printer_id, privacy=new_privacy):
            from handlers.printer_config import PrinterConfigCog
            cog = self.get_cog("PrinterConfigCog")
            if cog:
                await cog.printer_settings(interaction, printer_id, edit=True)
            else:
                await interaction.response.send_message(f"✅ Printer privacy set to **{new_privacy.capitalize()}**.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Failed to update privacy.", ephemeral=True)
    
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
            "handlers.move",
            "handlers.filament",
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
