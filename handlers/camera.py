"""
Camera commands for Discord Printer Bot.
"""
from __future__ import annotations

import io
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

import db
import api
import permissions


class CameraCog(commands.Cog):
    """Camera commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="camera", description="Take a camera snapshot")
    async def camera(self, interaction: discord.Interaction):
        """Take and display a camera snapshot."""
        await self.show_camera(interaction)

    async def show_camera(self, interaction: discord.Interaction, edit: bool = False, printer_id: Optional[int] = None):
        user_id = interaction.user.id
        if printer_id is None:
            printer_id = db.get_active_printer_id(user_id)
        
        try:
            permissions.check_view_permission(user_id, printer_id)
        except permissions.PermissionError as e:
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        if edit:
            if not interaction.response.is_done():
                await interaction.response.defer()
        else:
            await interaction.response.defer(ephemeral=True)
        
        printer = db.get_printer(printer_id)
        owner_id = printer['owner_discord_id']

        # Get snapshot
        snapshot_bytes = await api.snapshot(owner_id, printer_id)
        
        if not snapshot_bytes:
            await interaction.followup.send(
                "❌ Failed to fetch camera snapshot or camera not configured.",
                ephemeral=True,
            )
            return
        
        # Get stream URL for embed
        stream_url = await api.get_stream_url(owner_id, printer_id)
        
        # Send image
        file = discord.File(io.BytesIO(snapshot_bytes), filename="snapshot.jpg")

        printer_name = printer['name'] if printer else "Printer"
        
        embed = discord.Embed(
            title="📷 Camera Snapshot",
            description=printer_name,
            color=0x0099FF,
        )
        embed.set_image(url="attachment://snapshot.jpg")
        
        if stream_url:
            embed.add_field(name="📺 Live Stream", value=f"[Click here]({stream_url})", inline=False)
        
        view = discord.ui.View(timeout=None)
        view.add_item(discord.ui.Button(label="⬅️ Back", style=discord.ButtonStyle.secondary, custom_id="back_to_menu"))

        if edit:
            await interaction.edit_original_response(file=file, embed=embed, view=view)
        else:
            await interaction.followup.send(file=file, embed=embed, view=view)
    
    @app_commands.command(name="stream", description="Get camera stream link")
    async def stream(self, interaction: discord.Interaction):
        """Get the camera stream URL."""
        user_id = interaction.user.id
        active_printer_id = db.get_active_printer_id(user_id)
        
        try:
            permissions.check_view_permission(user_id, active_printer_id)
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        stream_url = await api.get_stream_url(user_id)
        
        if not stream_url:
            await interaction.response.send_message(
                "📺 Live stream is not configured for this printer.",
                ephemeral=True,
            )
            return
        
        active_printer = db.get_active_printer(user_id)
        printer_name = active_printer['name'] if active_printer else "Printer"

        embed = discord.Embed(
            title="📺 Live Camera Stream",
            description=printer_name,
            color=0x0099FF,
        )
        embed.add_field(name="Link", value=f"[Click to watch]({stream_url})", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="pubcamera", description="Get camera snapshot publicly (with a warning if printer is private)")
    async def pubcamera(self, interaction: discord.Interaction):
        """Show current printer camera snapshot publicly, prompting a warning if the printer is private/unlisted."""
        viewer_id = interaction.user.id
        active_printer_id = db.get_active_printer_id(viewer_id)

        if active_printer_id is None:
            await interaction.response.send_message("❌ No active printer. Use `/register-printer` or `/switch-printer`.", ephemeral=True)
            return

        printer = db.get_printer(active_printer_id)
        if not printer:
            await interaction.response.send_message("❌ Printer not found.", ephemeral=True)
            return

        owner_id = printer['owner_discord_id']

        # Permissions check: Can the viewer control/request public camera? Only owner/allowed.
        if not db.user_can_control(viewer_id, active_printer_id):
            await interaction.response.send_message("❌ You don't have permission to share this printer camera publicly.", ephemeral=True)
            return

        # If printer is private or unlisted, show warning confirmation view ephemerally
        if printer['privacy'] in ('private', 'unlisted'):
            view = PubCameraConfirmView(owner_id, printer, self, caller_id=viewer_id)
            await interaction.response.send_message(
                f"⚠️ **Warning: Your printer privacy is set to `{printer['privacy']}`. Do you really want to send a public camera snapshot?**",
                view=view,
                ephemeral=True
            )
        else:
            # Already public, just send snapshot publicly directly
            await interaction.response.defer(ephemeral=False)
            snapshot_bytes = await api.snapshot(owner_id, active_printer_id)
            if not snapshot_bytes:
                await interaction.followup.send("❌ Failed to fetch camera snapshot or camera not configured.", ephemeral=True)
                return

            stream_url = await api.get_stream_url(owner_id, active_printer_id)
            file = discord.File(io.BytesIO(snapshot_bytes), filename="snapshot.jpg")

            embed = discord.Embed(
                title="📷 Camera Snapshot",
                description=printer['name'],
                color=0x0099FF,
            )
            embed.set_image(url="attachment://snapshot.jpg")

            if stream_url:
                embed.add_field(name="📺 Live Stream", value=f"[Click here]({stream_url})", inline=False)

            view = PubCameraDeleteView(active_printer_id, caller_id=viewer_id)
            await interaction.followup.send(file=file, embed=embed, view=view)


class PubCameraConfirmView(discord.ui.View):
    """Confirmation view for opening a public camera snapshot."""

    def __init__(self, owner_id: int, printer: dict, camera_cog: CameraCog, caller_id: int):
        super().__init__(timeout=60)
        self.owner_id = owner_id
        self.printer = printer
        self.camera_cog = camera_cog
        self.caller_id = caller_id

    @discord.ui.button(label="Yes, send publicly", style=discord.ButtonStyle.success)
    async def confirm_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        printer_id = self.printer['printer_id']

        # Get snapshot
        snapshot_bytes = await api.snapshot(self.owner_id, printer_id)
        if not snapshot_bytes:
            await interaction.followup.send("❌ Failed to fetch camera snapshot or camera not configured.", ephemeral=True)
            self.stop()
            return

        stream_url = await api.get_stream_url(self.owner_id, printer_id)
        file = discord.File(io.BytesIO(snapshot_bytes), filename="snapshot.jpg")

        embed = discord.Embed(
            title="📷 Camera Snapshot",
            description=self.printer['name'],
            color=0x0099FF,
        )
        embed.set_image(url="attachment://snapshot.jpg")

        if stream_url:
            embed.add_field(name="📺 Live Stream", value=f"[Click here]({stream_url})", inline=False)

        view = PubCameraDeleteView(printer_id, caller_id=self.caller_id)
        await interaction.channel.send(file=file, embed=embed, view=view)
        await interaction.edit_original_response(content="✅ Public camera snapshot sent below.", view=None)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Cancelled.", view=None)
        self.stop()


class PubCameraDeleteView(discord.ui.View):
    """View with a delete button for public camera snapshots."""

    def __init__(self, printer_id: int, caller_id: int):
        super().__init__(timeout=None)
        self.printer_id = printer_id
        self.caller_id = caller_id

    @discord.ui.button(label="🗑️ Delete", style=discord.ButtonStyle.danger)
    async def delete_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Only the caller of the command can delete the public page
        if interaction.user.id == self.caller_id:
            await interaction.message.delete()
        else:
            await interaction.response.send_message("❌ Only the caller of this command can delete this message.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(CameraCog(bot))
