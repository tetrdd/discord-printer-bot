"""
Printer configuration commands for Discord Printer Bot.
Handles printer registration, user settings, and printer settings management.
Uses embeds, buttons, and modals for interactive UI.
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, TextInput, Button, View, Select
from typing import Optional, List
import logging

import db

logger = logging.getLogger("PrinterBot")


# ── Modals ────────────────────────────────────────────────────────────────────

class RegisterPrinterModal(Modal, title="Register New Printer"):
    """Modal for registering a new printer."""
    
    def __init__(self):
        super().__init__()
        
        self.name_input = TextInput(
            label="Printer Name",
            placeholder="e.g., Voron 2.4, Ender 3 Pro",
            min_length=1,
            max_length=50,
            required=True,
        )
        self.append_item(self.name_input)
        
        self.url_input = TextInput(
            label="OctoEverywhere API URL or Key",
            placeholder="e.g. https://api.octoeverywhere.com/api/YOUR_KEY",
            min_length=1,
            max_length=200,
            required=True,
        )
        self.append_item(self.url_input)
        
        self.camera_input = TextInput(
            label="Camera Snapshot URL (Optional)",
            placeholder="http://...",
            required=False,
        )
        self.append_item(self.camera_input)

        self.stream_input = TextInput(
            label="Camera Stream URL (Optional)",
            placeholder="http://...",
            required=False,
        )
        self.append_item(self.stream_input)
        
        self.privacy_select = TextInput(
            label="Privacy (public/private)",
            placeholder="public or private",
            min_length=1,
            max_length=10,
            required=True,
            default="public",
        )
        self.append_item(self.privacy_select)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        user_id = interaction.user.id
        
        # Ensure user exists
        db.ensure_user_exists(user_id)
        
        # Validate privacy
        privacy = self.privacy_select.value.lower().strip()
        if privacy not in ('public', 'private'):
            await interaction.response.send_message(
                "❌ Invalid privacy setting. Must be `public` or `private`.",
                ephemeral=True,
            )
            return
        
        try:
            # Create printer
            printer_id = db.create_printer(
                owner_discord_id=user_id,
                name=self.name_input.value.strip(),
                printer_type="octoeverywhere",
                url=self.url_input.value.strip(),
                api_key=None,
                privacy=privacy,
                camera_url=self.camera_input.value.strip() or None,
                stream_url=self.stream_input.value.strip() or None,
            )
            
            embed = discord.Embed(
                title="✅ Printer Registered!",
                description=f"Your printer **{self.name_input.value.strip()}** has been registered via OctoEverywhere.",
                color=discord.Color.green(),
            )
            embed.add_field(name="Printer ID", value=f"`{printer_id}`", inline=True)
            embed.add_field(name="Privacy", value=privacy, inline=True)
            embed.add_field(
                name="Next Steps",
                value=f"Use `/printer-settings {printer_id}` to manage this printer.",
                inline=False,
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.info(f"User {user_id} registered printer {printer_id}")
            
        except Exception as e:
            logger.error(f"Failed to register printer: {e}")
            await interaction.response.send_message(
                f"❌ Failed to register printer: {str(e)}",
                ephemeral=True,
            )


class UserSettingsModal(Modal, title="Update Your Settings"):
    """Modal for updating user settings."""
    
    def __init__(self, user: discord.User):
        super().__init__()
        
        # Get current user data
        user_data = db.get_user(user.id)
        
        self.timezone_input = TextInput(
            label="Timezone",
            placeholder="e.g., Europe/Berlin, America/New_York",
            min_length=0,
            max_length=50,
            required=False,
            default=user_data.get('timezone', '') if user_data else '',
        )
        self.append_item(self.timezone_input)
        
        self.language_input = TextInput(
            label="Language",
            placeholder="e.g., en, de, ru",
            min_length=0,
            max_length=10,
            required=False,
            default=user_data.get('language', 'en') if user_data else 'en',
        )
        self.append_item(self.language_input)
        
        self.notify_channel_input = TextInput(
            label="Notification Channel ID",
            placeholder="Discord channel ID for notifications",
            min_length=0,
            max_length=30,
            required=False,
            default=user_data.get('notify_channel', '') if user_data else '',
        )
        self.append_item(self.notify_channel_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        user_id = interaction.user.id
        
        # Ensure user exists
        db.ensure_user_exists(user_id)
        
        # Update user settings
        db.update_user(
            discord_id=user_id,
            timezone=self.timezone_input.value.strip() or None,
            language=self.language_input.value.strip() or 'en',
            notify_channel=self.notify_channel_input.value.strip() or None,
        )
        
        embed = discord.Embed(
            title="✅ Settings Updated!",
            description="Your personal settings have been saved.",
            color=discord.Color.green(),
        )
        
        if self.timezone_input.value.strip():
            embed.add_field(name="Timezone", value=f"`{self.timezone_input.value.strip()}`", inline=True)
        if self.language_input.value.strip():
            embed.add_field(name="Language", value=f"`{self.language_input.value.strip()}`", inline=True)
        if self.notify_channel_input.value.strip():
            embed.add_field(name="Notify Channel", value=f"`{self.notify_channel_input.value.strip()}`", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"User {user_id} updated their settings")


class PrinterSettingsModal(Modal, title="Update Printer Settings"):
    """Modal for updating printer settings."""
    
    def __init__(self, printer_id: int, printer_data: dict):
        super().__init__()
        
        self.printer_id = printer_id
        
        self.name_input = TextInput(
            label="Printer Name",
            min_length=1,
            max_length=50,
            required=True,
            default=printer_data.get('name', ''),
        )
        self.append_item(self.name_input)
        
        self.url_input = TextInput(
            label="OctoEverywhere API URL or Key",
            min_length=1,
            max_length=200,
            required=True,
            default=printer_data.get('url', ''),
        )
        self.append_item(self.url_input)
        
        self.camera_input = TextInput(
            label="Camera Snapshot URL",
            required=False,
            default=printer_data.get('camera_url', ''),
        )
        self.append_item(self.camera_input)

        self.stream_input = TextInput(
            label="Camera Stream URL",
            required=False,
            default=printer_data.get('stream_url', ''),
        )
        self.append_item(self.stream_input)
        
        privacy = printer_data.get('privacy', 'public')
        self.privacy_input = TextInput(
            label="Privacy (public/private)",
            min_length=1,
            max_length=10,
            required=True,
            default=privacy,
        )
        self.append_item(self.privacy_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        user_id = interaction.user.id
        
        # Validate privacy
        privacy = self.privacy_input.value.lower().strip()
        if privacy not in ('public', 'private'):
            await interaction.response.send_message(
                "❌ Invalid privacy setting. Must be `public` or `private`.",
                ephemeral=True,
            )
            return
        
        # Check ownership
        if not db.is_printer_owner(user_id, self.printer_id):
            await interaction.response.send_message(
                "❌ Only the printer owner can change these settings.",
                ephemeral=True,
            )
            return
        
        # Update printer
        db.update_printer(
            printer_id=self.printer_id,
            name=self.name_input.value.strip(),
            url=self.url_input.value.strip(),
            privacy=privacy,
            camera_url=self.camera_input.value.strip() or None,
            stream_url=self.stream_input.value.strip() or None,
        )
        
        embed = discord.Embed(
            title="✅ Printer Settings Updated!",
            description=f"Printer **{self.name_input.value.strip()}** has been updated.",
            color=discord.Color.green(),
        )
        embed.add_field(name="Printer ID", value=f"`{self.printer_id}`", inline=True)
        embed.add_field(name="Privacy", value=privacy, inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"User {user_id} updated printer {self.printer_id}")


# ── Views (Buttons) ───────────────────────────────────────────────────────────

class PrinterActionView(View):
    """View with action buttons for printer management."""
    
    def __init__(self, printer_id: int, is_owner: bool):
        super().__init__(timeout=None)
        self.printer_id = printer_id
        self.is_owner = is_owner
        
        # Edit button (owner only)
        if is_owner:
            self.add_item(
                Button(
                    style=discord.ButtonStyle.primary,
                    label="Edit Settings",
                    custom_id=f"printer_edit:{printer_id}",
                )
            )
        
        # Delete button (owner only)
        if is_owner:
            self.add_item(
                Button(
                    style=discord.ButtonStyle.danger,
                    label="Delete Printer",
                    custom_id=f"printer_delete:{printer_id}",
                )
            )
        
        # Manage users button (owner only)
        if is_owner:
            self.add_item(
                Button(
                    style=discord.ButtonStyle.secondary,
                    label="Manage Users",
                    custom_id=f"printer_users:{printer_id}",
                )
            )

        # Select as active
        self.add_item(
            Button(
                style=discord.ButtonStyle.success,
                label="Set as Active",
                custom_id=f"printer_activate:{printer_id}",
            )
        )


class UserSettingsView(View):
    """View with buttons for user settings."""
    
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        
        self.add_item(
            Button(
                style=discord.ButtonStyle.primary,
                label="Edit Settings",
                custom_id=f"user_settings_edit:{user_id}",
            )
        )


class AllowedUsersView(View):
    """View for managing allowed users on a printer."""
    
    def __init__(self, printer_id: int, allowed_users: List[int]):
        super().__init__(timeout=None)
        self.printer_id = printer_id
        
        # Add dropdown for selecting users to remove
        if allowed_users:
            select = Select(
                placeholder="Select user to remove...",
                options=[
                    discord.SelectOption(
                        label=str(uid),
                        value=str(uid),
                    )
                    for uid in allowed_users
                ],
            )
            select.callback = self.remove_user_callback
            self.add_item(select)
    
    async def remove_user_callback(self, interaction: discord.Interaction):
        """Handle user removal from dropdown."""
        user_id = int(interaction.data['values'][0])
        
        if db.remove_allowed_user(self.printer_id, user_id):
            await interaction.response.send_message(
                f"✅ Removed user `{user_id}` from allowed users.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "❌ Failed to remove user.",
                ephemeral=True,
            )


# ── Cog ───────────────────────────────────────────────────────────────────────

class PrinterConfigCog(commands.Cog):
    """Printer configuration commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="register-printer", description="Register a new printer via OctoEverywhere")
    async def register_printer(self, interaction: discord.Interaction):
        """Open modal to register a new printer."""
        await interaction.response.send_modal(RegisterPrinterModal())
    
    @app_commands.command(name="my-settings", description="View or update your personal settings")
    async def my_settings(self, interaction: discord.Interaction):
        """View or update personal user settings."""
        user_id = interaction.user.id
        
        # Ensure user exists
        db.ensure_user_exists(user_id)
        
        user_data = db.get_user(user_id)
        
        embed = discord.Embed(
            title=f"⚙️ Your Settings",
            description=f"Settings for <@{user_id}>",
            color=discord.Color.blue(),
        )
        
        if user_data:
            embed.add_field(
                name="Timezone",
                value=f"`{user_data.get('timezone', 'Not set')}`",
                inline=True,
            )
            embed.add_field(
                name="Language",
                value=f"`{user_data.get('language', 'en')}`",
                inline=True,
            )
            embed.add_field(
                name="Notify Channel",
                value=f"`{user_data.get('notify_channel', 'Not set')}`",
                inline=True,
            )
            active_id = user_data.get('active_printer_id')
            if active_id:
                p = db.get_printer(active_id)
                active_name = p['name'] if p else "Unknown"
                embed.add_field(name="Active Printer", value=f"**{active_name}** (`{active_id}`)", inline=False)
        else:
            embed.description = "No settings configured yet. Click the button below to set them up!"
        
        view = UserSettingsView(user_id)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(
        name="printer-settings",
        description="View or update printer settings"
    )
    @app_commands.describe(printer_id="Printer ID to manage")
    async def printer_settings(
        self,
        interaction: discord.Interaction,
        printer_id: int,
    ):
        """View or update printer settings."""
        user_id = interaction.user.id
        
        # Get printer
        printer = db.get_printer(printer_id)
        
        if not printer:
            await interaction.response.send_message(
                f"❌ Printer ID `{printer_id}` not found.",
                ephemeral=True,
            )
            return
        
        # Check access
        if not db.user_can_view(user_id, printer_id):
            await interaction.response.send_message(
                "❌ You don't have permission to view this printer.",
                ephemeral=True,
            )
            return
        
        is_owner = db.is_printer_owner(user_id, printer_id)
        
        # Build embed
        embed = discord.Embed(
            title=f"🖨️ {printer['name']}",
            description=f"Printer ID: `{printer_id}`",
            color=discord.Color.green() if is_owner else discord.Color.blue(),
        )
        
        embed.add_field(name="Type", value=printer['type'], inline=True)
        embed.add_field(name="Privacy", value=printer['privacy'], inline=True)
        
        if is_owner:
            embed.add_field(name="URL/Key", value=f"`{printer['url']}`", inline=False)
            if printer.get('camera_url'):
                embed.add_field(name="Camera URL", value=f"`{printer['camera_url']}`", inline=False)
            if printer.get('stream_url'):
                embed.add_field(name="Stream URL", value=f"`{printer['stream_url']}`", inline=False)
        
        # Owner info
        owner_id = printer['owner_discord_id']
        embed.add_field(name="Owner", value=f"<@{owner_id}>", inline=True)
        
        # Allowed users (only show to owner)
        if is_owner:
            allowed_users = db.get_allowed_users(printer_id)
            if allowed_users:
                users_str = ", ".join([f"<@{uid}>" for uid in allowed_users])
            else:
                users_str = "None"
            embed.add_field(name="Allowed Users", value=users_str, inline=False)
        
        # Add buttons
        view = PrinterActionView(printer_id, is_owner)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(
        name="list-printers",
        description="List all printers you can access"
    )
    async def list_printers(self, interaction: discord.Interaction):
        """List all printers accessible by the user."""
        user_id = interaction.user.id
        
        printers = db.get_accessible_printers(user_id)
        
        if not printers:
            embed = discord.Embed(
                title="🖨️ Your Printers",
                description="You don't have access to any printers yet.\nUse `/register-printer` to add one!",
                color=discord.Color.orange(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
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
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="add-user",
        description="Add a user to your printer's allowed list (owner only)"
    )
    @app_commands.describe(
        printer_id="Printer ID",
        user="Discord user to add"
    )
    async def add_user(
        self,
        interaction: discord.Interaction,
        printer_id: int,
        user: discord.User,
    ):
        """Add a user to the printer's allowed users list."""
        user_id = interaction.user.id
        
        # Check ownership
        if not db.is_printer_owner(user_id, printer_id):
            await interaction.response.send_message(
                "❌ Only the printer owner can add users.",
                ephemeral=True,
            )
            return
        
        # Check printer exists
        printer = db.get_printer(printer_id)
        if not printer:
            await interaction.response.send_message(
                f"❌ Printer ID `{printer_id}` not found.",
                ephemeral=True,
            )
            return
        
        # Add user
        if db.add_allowed_user(printer_id, user.id):
            await interaction.response.send_message(
                f"✅ Added <@{user.id}> to allowed users for **{printer['name']}**.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "❌ User is already in the allowed list.",
                ephemeral=True,
            )
    
    @app_commands.command(
        name="remove-user",
        description="Remove a user from your printer's allowed list (owner only)"
    )
    @app_commands.describe(
        printer_id="Printer ID",
        user="Discord user to remove"
    )
    async def remove_user(
        self,
        interaction: discord.Interaction,
        printer_id: int,
        user: discord.User,
    ):
        """Remove a user from the printer's allowed users list."""
        user_id = interaction.user.id
        
        # Check ownership
        if not db.is_printer_owner(user_id, printer_id):
            await interaction.response.send_message(
                "❌ Only the printer owner can remove users.",
                ephemeral=True,
            )
            return
        
        # Remove user
        if db.remove_allowed_user(printer_id, user.id):
            await interaction.response.send_message(
                f"✅ Removed <@{user.id}> from allowed users.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "❌ User was not in the allowed list.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    """Load the cog."""
    await bot.add_cog(PrinterConfigCog(bot))
    logger.info("Loaded PrinterConfigCog")
