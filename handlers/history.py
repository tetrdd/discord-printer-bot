"""
Print history commands for Discord Printer Bot.
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
from datetime import datetime

import db
import api
import permissions


class HistoryCog(commands.Cog):
    """Print history commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.user_pages = {}  # {user_id: (history, page)}
    
    @app_commands.command(name="history", description="View print history")
    @app_commands.describe(page="Page number (default: 1)")
    async def history(self, interaction: discord.Interaction, page: Optional[int] = 1):
        """View print history."""
        user_id = interaction.user.id
        active_printer_id = db.get_active_printer_id(user_id)
        
        try:
            permissions.check_control_permission(user_id, active_printer_id)
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        history = await api.print_history(limit=50, user_id=user_id)
        
        if not history:
            await interaction.followup.send(
                "📜 No print history found. (Note: History is only available on Moonraker/Klipper)",
                ephemeral=True,
            )
            return
        
        per_page = 10
        total_pages = (len(history) + per_page - 1) // per_page
        
        if page < 1:
            page = 1
        elif page > total_pages:
            page = total_pages
        
        self.user_pages[user_id] = (history, page)
        
        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, len(history))
        page_history = history[start_idx:end_idx]
        
        embed = discord.Embed(
            title="📜 Print History",
            description=f"Page {page}/{total_pages} ({len(history)} prints)",
            color=0x3498DB,
        )
        
        for job in page_history:
            status = job.get("status", "unknown")
            filename = job.get("filename", "Unknown")
            duration = job.get("print_duration", 0)
            start_time = job.get("start_time", 0)
            
            # Status emoji
            status_emoji = {
                "completed": "✅",
                "error": "❌",
                "cancelled": "⏹️",
            }.get(status, "❓")
            
            # Format duration
            duration_str = self._format_duration(duration)
            
            # Format date
            if start_time:
                date_str = datetime.fromtimestamp(start_time).strftime("%Y-%m-%d %H:%M")
            else:
                date_str = "Unknown"
            
            display_name = filename.split("/")[-1]
            embed.add_field(
                name=f"{status_emoji} {display_name}",
                value=f"⏱️ {duration_str} | 📅 {date_str}",
                inline=False,
            )
        
        view = HistoryView(user_id, page, total_pages)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to human readable string."""
        if not seconds or seconds < 0:
            return "0s"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"


class HistoryView(discord.ui.View):
    """Print history pagination view."""
    
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
            f"Use `/history page:{self.page - 1}`",
            ephemeral=True,
        )
    
    @discord.ui.button(label="⏭️ Next", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"Use `/history page:{self.page + 1}`",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(HistoryCog(bot))
