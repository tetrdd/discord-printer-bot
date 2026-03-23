"""
Camera commands for Discord Printer Bot.
"""
from __future__ import annotations

import io
import discord
from discord import app_commands
from discord.ext import commands

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
        user_id = interaction.user.id
        active_printer_id = db.get_active_printer_id(user_id)
        
        try:
            permissions.check_view_permission(user_id, active_printer_id)
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Get snapshot
        snapshot_bytes = await api.snapshot(user_id)
        
        if not snapshot_bytes:
            await interaction.followup.send(
                "❌ Failed to fetch camera snapshot or camera not configured.",
                ephemeral=True,
            )
            return
        
        # Get stream URL for embed
        stream_url = await api.get_stream_url(user_id)
        
        # Send image
        file = discord.File(io.BytesIO(snapshot_bytes), filename="snapshot.jpg")

        active_printer = db.get_active_printer(user_id)
        printer_name = active_printer['name'] if active_printer else "Printer"
        
        embed = discord.Embed(
            title="📷 Camera Snapshot",
            description=printer_name,
            color=0x0099FF,
        )
        embed.set_image(url="attachment://snapshot.jpg")
        
        if stream_url:
            embed.add_field(name="📺 Live Stream", value=f"[Click here]({stream_url})", inline=False)
        
        await interaction.followup.send(file=file, embed=embed)
    
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


async def setup(bot: commands.Bot):
    await bot.add_cog(CameraCog(bot))
