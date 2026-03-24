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
        self.add_item(self.name_input)
        
        self.url_input = TextInput(
            label="OctoEverywhere API URL or Key",
            placeholder="e.g. https://api.octoeverywhere.com/api/YOUR_KEY",
            min_length=1,
            max_length=200,
            required=True,
        )
        self.add_item(self.url_input)
        
        self.camera_input = TextInput(
            label="Camera Snapshot URL (Optional)",
            placeholder="http://...",
            required=False,
        )
        self.add_item(self.camera_input)

        self.stream_input = TextInput(
            label="Camera Stream URL (Optional)",
            placeholder="http://...",
            required=False,
        )
        self.add_item(self.stream_input)
        
        self.privacy_select = TextInput(
            label="Privacy (public/private/unlisted)",
            placeholder="public, private, or unlisted",
            min_length=1,
            max_length=10,
            required=True,
            default="public",
        )
        self.add_item(self.privacy_select)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        user_id = interaction.user.id
        
        # Ensure user exists
        db.ensure_user_exists(user_id)
        
        # Validate privacy
        privacy = self.privacy_select.value.lower().strip()
        if privacy not in ('public', 'private', 'unlisted'):
            await interaction.response.send_message(
                "❌ Invalid privacy setting. Must be `public`, `private`, or `unlisted`.",
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


class EditTimezoneModal(Modal, title="Edit Timezone"):
    timezone_input = TextInput(
        label="Timezone",
        placeholder="e.g., Europe/Berlin, America/New_York",
        min_length=0,
        max_length=50,
        required=False,
    )

    def __init__(self, current_timezone: str):
        super().__init__()
        self.timezone_input.default = current_timezone or ""

    async def on_submit(self, interaction: discord.Interaction):
        if db.update_user(interaction.user.id, timezone=self.timezone_input.value.strip() or None):
            await interaction.response.send_message(f"✅ Timezone updated to **{self.timezone_input.value}**", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Failed to update timezone.", ephemeral=True)

class LanguageSelectView(View):
    """View for selecting language."""

    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id

        languages = [
            ("🇺🇸 English", "en"),
            ("🇩🇪 German", "de"),
            ("🇷🇺 Russian", "ru"),
            ("🇫🇷 French", "fr"),
            ("🇪🇸 Spanish", "es"),
        ]

        for label, code in languages:
            btn = Button(label=label, style=discord.ButtonStyle.secondary, custom_id=f"lang_set:{code}")
            btn.callback = self.make_callback(code, label)
            self.add_item(btn)

    def make_callback(self, code: str, label: str):
        async def callback(interaction: discord.Interaction):
            if db.update_user(self.user_id, language=code):
                await interaction.response.send_message(f"✅ Language updated to **{label}**", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Failed to update language.", ephemeral=True)
        return callback

class EditNotifyChannelModal(Modal, title="Edit Notification Channel"):
    channel_input = TextInput(
        label="Notification Channel ID",
        placeholder="Discord channel ID",
        min_length=0,
        max_length=30,
        required=False,
    )

    def __init__(self, current_channel: str):
        super().__init__()
        self.channel_input.default = current_channel or ""

    async def on_submit(self, interaction: discord.Interaction):
        if db.update_user(interaction.user.id, notify_channel=self.channel_input.value.strip() or None):
            await interaction.response.send_message(f"✅ Notification channel updated to **{self.channel_input.value}**", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Failed to update channel.", ephemeral=True)


class EditNameModal(Modal, title="Edit Printer Name"):
    name_input = TextInput(
        label="Printer Name",
        min_length=1,
        max_length=50,
        required=True,
    )

    def __init__(self, printer_id: int, current_name: str):
        super().__init__()
        self.printer_id = printer_id
        self.name_input.default = current_name

    async def on_submit(self, interaction: discord.Interaction):
        if db.update_printer(self.printer_id, name=self.name_input.value.strip()):
            await interaction.response.send_message(f"✅ Printer name updated to **{self.name_input.value}**", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Failed to update name.", ephemeral=True)

class EditConnectionModal(Modal, title="Edit Connection Settings"):
    url_input = TextInput(
        label="OctoEverywhere API URL or Key",
        min_length=1,
        max_length=200,
        required=True,
    )

    def __init__(self, printer_id: int, current_url: str):
        super().__init__()
        self.printer_id = printer_id
        self.url_input.default = current_url

    async def on_submit(self, interaction: discord.Interaction):
        if db.update_printer(self.printer_id, url=self.url_input.value.strip()):
            await interaction.response.send_message("✅ Connection settings updated.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Failed to update connection.", ephemeral=True)

class EditCameraModal(Modal, title="Edit Camera Settings"):
    camera_input = TextInput(
        label="Camera Snapshot URL",
        placeholder="http://...",
        required=False,
    )
    stream_input = TextInput(
        label="Camera Stream URL",
        placeholder="http://...",
        required=False,
    )

    def __init__(self, printer_id: int, current_camera: str, current_stream: str):
        super().__init__()
        self.printer_id = printer_id
        self.camera_input.default = current_camera or ""
        self.stream_input.default = current_stream or ""

    async def on_submit(self, interaction: discord.Interaction):
        if db.update_printer(
            self.printer_id,
            camera_url=self.camera_input.value.strip() or None,
            stream_url=self.stream_input.value.strip() or None
        ):
            await interaction.response.send_message("✅ Camera settings updated.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Failed to update camera settings.", ephemeral=True)


# ── Views (Buttons) ───────────────────────────────────────────────────────────

class PrinterActionView(View):
    """View with action buttons for printer management."""
    
    def __init__(self, printer_id: int, is_owner: bool):
        super().__init__(timeout=None)
        self.printer_id = printer_id
        self.is_owner = is_owner
        
        if is_owner:
            # Row 0: Basic Settings
            self.add_item(
                Button(
                    style=discord.ButtonStyle.primary,
                    label="📝 Edit Name",
                    custom_id=f"printer_edit_name:{printer_id}",
                    row=0
                )
            )
            self.add_item(
                Button(
                    style=discord.ButtonStyle.primary,
                    label="🔗 Edit Connection",
                    custom_id=f"printer_edit_conn:{printer_id}",
                    row=0
                )
            )
            self.add_item(
                Button(
                    style=discord.ButtonStyle.primary,
                    label="📷 Edit Camera",
                    custom_id=f"printer_edit_cam:{printer_id}",
                    row=0
                )
            )

            # Row 1: Management & Privacy
            self.add_item(
                Button(
                    style=discord.ButtonStyle.secondary,
                    label="🔓 Toggle Privacy",
                    custom_id=f"printer_privacy_toggle:{printer_id}",
                    row=1
                )
            )
            self.add_item(
                Button(
                    style=discord.ButtonStyle.secondary,
                    label="👥 Manage Users",
                    custom_id=f"printer_users:{printer_id}",
                    row=1
                )
            )

            # Row 2: Actions
            self.add_item(
                Button(
                    style=discord.ButtonStyle.success,
                    label="⭐ Set as Active",
                    custom_id=f"printer_activate:{printer_id}",
                    row=2
                )
            )
            self.add_item(
                Button(
                    style=discord.ButtonStyle.danger,
                    label="🗑️ Delete Printer",
                    custom_id=f"printer_delete:{printer_id}",
                    row=2
                )
            )
        else:
            # Non-owner view
            self.add_item(
                Button(
                    style=discord.ButtonStyle.success,
                    label="⭐ Set as Active",
                    custom_id=f"printer_activate:{printer_id}",
                )
            )


class UserSettingsView(View):
    """View with buttons for user settings."""
    
    def __init__(self, user_id: int, active_printer_id: Optional[int] = None):
        super().__init__(timeout=None)
        
        self.add_item(
            Button(
                style=discord.ButtonStyle.primary,
                label="🌐 Timezone",
                custom_id=f"user_edit_tz:{user_id}",
            )
        )
        self.add_item(
            Button(
                style=discord.ButtonStyle.primary,
                label="🗣️ Language",
                custom_id=f"user_select_lang:{user_id}",
            )
        )
        self.add_item(
            Button(
                style=discord.ButtonStyle.primary,
                label="🔔 Notifications",
                custom_id=f"user_edit_notify:{user_id}",
            )
        )

        self.add_item(
            Button(
                style=discord.ButtonStyle.secondary,
                label="✉️ Use DMs",
                custom_id=f"user_set_dm_notify:{user_id}",
            )
        )

        if active_printer_id:
            self.add_item(
                Button(
                    style=discord.ButtonStyle.secondary,
                    label="🖨️ Printer Settings",
                    custom_id=f"user_manage_printer:{active_printer_id}",
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
        await self.show_my_settings(interaction)

    async def show_my_settings(self, interaction: discord.Interaction, edit: bool = False):
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
            tz = user_data.get('timezone')
            lang = user_data.get('language', 'en')
            chan = user_data.get('notify_channel')

            embed.add_field(
                name="Timezone",
                value=f"`{tz}`" if tz else "*Not set*",
                inline=True,
            )
            embed.add_field(
                name="Language",
                value=f"`{lang}`",
                inline=True,
            )
            embed.add_field(
                name="Notifications",
                value=f"<#{chan}>" if (chan and chan.isdigit()) else (f"`{chan}`" if chan else "*Not set*"),
                inline=True,
            )
            active_id = user_data.get('active_printer_id')
            if active_id:
                p = db.get_printer(active_id)
                active_name = p['name'] if p else "Unknown"
                embed.add_field(name="Active Printer", value=f"**{active_name}** (`{active_id}`)", inline=False)
        else:
            embed.description = "No settings configured yet. Click the button below to set them up!"
        
        active_id = user_data.get('active_printer_id') if user_data else None
        view = UserSettingsView(user_id, active_id)
        view.add_item(discord.ui.Button(label="⬅️ Back", style=discord.ButtonStyle.secondary, custom_id="back_to_menu"))
        
        if edit:
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(
        name="printer-settings",
        description="View or update printer settings"
    )
    @app_commands.describe(printer_id="Printer ID to manage")
    async def printer_settings_cmd(
        self,
        interaction: discord.Interaction,
        printer_id: int,
    ):
        """View or update printer settings."""
        await self.printer_settings(interaction, printer_id)

    async def printer_settings(
        self,
        interaction: discord.Interaction,
        printer_id: int,
        edit: bool = False,
    ):
        user_id = interaction.user.id
        
        # Get printer
        printer = db.get_printer(printer_id)
        
        if not printer:
            msg = f"❌ Printer ID `{printer_id}` not found."
            if edit:
                await interaction.response.edit_message(content=msg, embed=None, view=None)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
            return
        
        # Check access
        if not db.user_can_view(user_id, printer_id):
            msg = "❌ You don't have permission to view this printer."
            if edit:
                await interaction.response.edit_message(content=msg, embed=None, view=None)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
            return
        
        is_owner = db.is_printer_owner(user_id, printer_id)
        
        # Build embed
        embed = discord.Embed(
            title=f"🖨️ {printer['name']}",
            description=f"Printer ID: `{printer_id}`",
            color=discord.Color.green() if is_owner else discord.Color.blue(),
        )
        
        privacy = printer['privacy']
        privacy_emoji = {"public": "🌍", "private": "🔒", "unlisted": "👻"}.get(privacy, "❓")

        embed.add_field(name="Type", value=printer['type'], inline=True)
        embed.add_field(name="Privacy", value=f"{privacy_emoji} {privacy.capitalize()}", inline=True)
        
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
        view.add_item(discord.ui.Button(label="⬅️ Back", style=discord.ButtonStyle.secondary, custom_id="back_to_menu"))
        
        if edit:
            if not interaction.response.is_done():
                await interaction.response.edit_message(embed=embed, view=view)
            else:
                await interaction.edit_original_response(embed=embed, view=view)
        else:
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
