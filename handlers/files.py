"""
File browser commands for Discord Printer Bot.
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

import db
import api
import permissions


class FilesCog(commands.Cog):
    """File browser commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.user_pages = {}  # {user_id: (files, page)}
    
    @app_commands.command(name="files", description="Browse printer files")
    @app_commands.describe(page="Page number (default: 1)")
    async def files(self, interaction: discord.Interaction, page: Optional[int] = 1):
        """Browse G-code files on the printer."""
        user_id = interaction.user.id
        active_printer_id = db.get_active_printer_id(user_id)
        
        try:
            permissions.check_control_permission(user_id, active_printer_id)
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        files = await api.file_list(user_id)
        
        if not files:
            await interaction.followup.send("📁 No files found on the printer.", ephemeral=True)
            return
        
        # Sort files by modification time (newest first)
        # Moonraker uses 'modified', OctoPrint uses 'date'
        files.sort(key=lambda x: x.get("modified", x.get("date", 0)), reverse=True)
        
        files_per_page = 10
        total_pages = (len(files) + files_per_page - 1) // files_per_page
        
        if page < 1:
            page = 1
        elif page > total_pages:
            page = total_pages
        
        # Store for pagination
        self.user_pages[user_id] = (files, page)
        
        start_idx = (page - 1) * files_per_page
        end_idx = min(start_idx + files_per_page, len(files))
        page_files = files[start_idx:end_idx]
        
        embed = discord.Embed(
            title="📁 G-code Files",
            description=f"Page {page}/{total_pages} ({len(files)} files total)",
            color=0x0099FF,
        )
        
        for f in page_files:
            filename = f.get("path", f.get("name", "Unknown"))
            size = f.get("size", 0)
            size_str = self._format_size(size)
            
            # Get metadata if available
            display_name = filename.split("/")[-1]
            embed.add_field(
                name=f"📄 {display_name}",
                value=f"Size: {size_str}",
                inline=False,
            )
        
        view = FilesView(user_id, page, total_pages)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="print", description="Start printing a file")
    @app_commands.describe(filename="Name of the file to print")
    async def print_file(self, interaction: discord.Interaction, filename: str):
        """Start printing a specific file."""
        user_id = interaction.user.id
        active_printer_id = db.get_active_printer_id(user_id)
        
        try:
            permissions.check_control_permission(user_id, active_printer_id)
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        result = await api.start_print(filename, user_id)
        
        if result:
            await interaction.followup.send(f"✅ Started printing: `{filename}`", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ Failed to start print: `{filename}`", ephemeral=True)
    
    @app_commands.command(name="delete-file", description="Delete a file")
    @app_commands.describe(filename="Name of the file to delete")
    async def delete_file(self, interaction: discord.Interaction, filename: str):
        """Delete a specific file."""
        user_id = interaction.user.id
        active_printer_id = db.get_active_printer_id(user_id)
        
        try:
            permissions.check_control_permission(user_id, active_printer_id)
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        view = DeleteConfirmView(user_id, filename)
        await interaction.response.send_message(
            f"⚠️ Are you sure you want to delete `{filename}`?",
            view=view,
            ephemeral=True,
        )
    
    @app_commands.command(name="file-info", description="Get file information")
    @app_commands.describe(filename="Name of the file")
    async def file_info(self, interaction: discord.Interaction, filename: str):
        """Get detailed information about a file."""
        user_id = interaction.user.id
        active_printer_id = db.get_active_printer_id(user_id)
        
        try:
            permissions.check_control_permission(user_id, active_printer_id)
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        metadata = await api.file_metadata(filename, user_id)
        
        if not metadata:
            await interaction.followup.send(f"❌ Could not get info for `{filename}`", ephemeral=True)
            return
        
        # Extract info based on API type
        if "estimated_time" in metadata:
            # Moonraker
            estimated = metadata.get("estimated_time", 0)
            filament = metadata.get("filament_total", 0) / 1000  # mm to m
            layers = metadata.get("layer_count", 0)
            slicer = metadata.get("slicer", "Unknown")
        else:
            # OctoPrint
            estimated = metadata.get("gcodeAnalysis", {}).get("estimatedPrintTime", 0)
            filament_data = metadata.get("gcodeAnalysis", {}).get("filament", {})
            filament = sum(filament_data.values()) / 1000 if filament_data else 0
            layers = 0
            slicer = "Unknown"
        
        size = metadata.get("size", 0)
        
        embed = discord.Embed(
            title=f"📄 {filename}",
            color=0x0099FF,
        )
        
        embed.add_field(name="📦 Size", value=self._format_size(size), inline=True)
        embed.add_field(name="⏱️ Estimated", value=self._format_duration(estimated), inline=True)
        embed.add_field(name="🧵 Filament", value=f"{filament:.2f}m", inline=True)
        
        if layers > 0:
            embed.add_field(name="📊 Layers", value=str(layers), inline=True)
        embed.add_field(name="✂️ Slicer", value=slicer, inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    def _format_size(self, size: int) -> str:
        """Format file size in bytes to human readable string."""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.2f} MB"
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to human readable string."""
        if not seconds or seconds < 0:
            return "Unknown"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m"
        else:
            return f"{int(seconds)}s"


class FilesView(discord.ui.View):
    """File browser pagination view."""
    
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
            f"Use `/files page:{self.page - 1}`",
            ephemeral=True,
        )
    
    @discord.ui.button(label="⏭️ Next", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"Use `/files page:{self.page + 1}`",
            ephemeral=True,
        )


class DeleteConfirmView(discord.ui.View):
    """Confirmation view for file deletion."""
    
    def __init__(self, user_id: int, filename: str):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.filename = filename
    
    @discord.ui.button(label="Yes, Delete", style=discord.ButtonStyle.danger)
    async def confirm_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        result = await api.delete_file(self.filename, self.user_id)
        await interaction.followup.send(
            f"✅ Deleted `{self.filename}`" if result else "❌ Failed to delete",
            ephemeral=True,
        )
        self.stop()
    
    @discord.ui.button(label="No, Keep", style=discord.ButtonStyle.secondary)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("👍 Not deleted", ephemeral=True)
        self.stop()


async def setup(bot: commands.Bot):
    await bot.add_cog(FilesCog(bot))
