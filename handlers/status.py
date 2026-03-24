"""
Main menu and status commands for Discord Printer Bot.
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import asyncio

import db
import api
import permissions


class StatusCog(commands.Cog):
    """Status and main menu commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._auto_refresh_tasks = {}  # {(channel_id, message_id): asyncio.Task}
    
    @app_commands.command(name="status", description="Get printer status")
    @app_commands.describe(user="Optional: User to view status of")
    async def status(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        """Show current printer status."""
        viewer_id = interaction.user.id

        if user and user.id != viewer_id:
            # Handle viewing someone else's public printer
            printers = db.get_printers_by_owner(user.id)
            # Filter for public ones
            public_printers = [p for p in printers if p['privacy'] == 'public']

            if not public_printers:
                await interaction.response.send_message(f"❌ {user.display_name} has no public printers.", ephemeral=True)
                return

            if len(public_printers) == 1:
                printer = public_printers[0]
                await self.show_printer_status(interaction, printer, viewer_id)
            else:
                # Let user choose
                await self.show_public_printer_picker(interaction, user, public_printers)
            return

        active_printer_id = db.get_active_printer_id(viewer_id)
        
        if active_printer_id is None:
            await interaction.response.send_message("❌ No active printer. Use `/register-printer` or `/switch-printer`.", ephemeral=True)
            return

        printer = db.get_printer(active_printer_id)
        if not printer:
            await interaction.response.send_message("❌ Printer not found.", ephemeral=True)
            return

        await self.show_printer_status(interaction, printer, viewer_id)

    async def show_printer_status(self, interaction: discord.Interaction, printer: dict, viewer_id: int):
        printer_id = printer['printer_id']
        owner_id = printer['owner_discord_id']

        # Permissions check for requesting status
        # Public: anyone can request
        # Private: only owner/allowed
        # Unlisted: only owner/allowed (but result is public)
        can_request = (printer['privacy'] == 'public') or db.user_can_control(viewer_id, printer_id)
        
        if not can_request:
            await interaction.response.send_message("❌ You don't have permission to request status for this printer.", ephemeral=True)
            return

        # Determine if message should be ephemeral
        # Only 'private' is ephemeral. 'public' and 'unlisted' are shared.
        is_private = printer['privacy'] == 'private'

        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=is_private)
        
        status_data = await api.printer_status(owner_id, printer_id)
        printer_name = printer['name']
        
        if not status_data:
            await interaction.followup.send(
                f"❌ Could not connect to **{printer_name}**. Is it online?",
                ephemeral=True,
            )
            return
        
        embed = self._build_status_embed(status_data, printer_name)
        
        view = StatusView(owner_id, printer_id)
        await interaction.followup.send(embed=embed, view=view)

    async def show_public_printer_picker(self, interaction: discord.Interaction, owner: discord.User, public_printers: list):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title=f"🖨️ Public Printers - {owner.display_name}",
            description="Select a printer to view its status:",
            color=discord.Color.blue()
        )

        view = discord.ui.View()
        select = discord.ui.Select(placeholder="Choose a printer...")

        for p in public_printers:
            # We need to know the state to show it in the picker as requested
            status = await api.printer_status(owner.id, p['printer_id'])
            state = "Offline"
            if status:
                state = status.get("print_stats", {}).get("state", status.get("state", "Standby")).capitalize()

            select.add_option(
                label=p['name'],
                value=str(p['printer_id']),
                description=f"Status: {state}"
            )

        async def select_callback(interaction: discord.Interaction):
            printer_id = int(select.values[0])
            printer = db.get_printer(printer_id)
            await self.show_printer_status(interaction, printer, interaction.user.id)

        select.callback = select_callback
        view.add_item(select)

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="menu", description="Show main menu")
    async def menu(self, interaction: discord.Interaction):
        """Show the main menu."""
        await self.show_main_menu(interaction)

    async def show_main_menu(self, interaction: discord.Interaction, edit: bool = False):
        """Helper to show or edit the main menu."""
        user_id = interaction.user.id
        active_printer_id = db.get_active_printer_id(user_id)
        
        # Determine printer info
        active_printer = db.get_active_printer(user_id)
        printer_name = active_printer['name'] if active_printer else "Printer"
        
        embed = discord.Embed(
            title=f"🖨️ {printer_name}",
            description="Select an option:",
            color=0x0099FF,
        )
        
        view = MenuView(user_id, active_printer_id)

        if edit:
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    def _build_status_embed(self, status: dict, printer_name: str) -> discord.Embed:
        """Build a status embed from printer data."""
        # Extract data based on API type
        if "print_stats" in status:
            # Moonraker format
            stats = status.get("print_stats", {})
            vsd = status.get("virtual_sdcard", {})
            ext = status.get("extruder", {})
            bed = status.get("heater_bed", {})
            fan = status.get("fan", {})
            display = status.get("display_status", {})
            
            state = stats.get("state", "unknown")
            filename = stats.get("filename", "—") or "—"
            pct = display.get("progress", vsd.get("progress", 0)) * 100
            duration = stats.get("print_duration", 0)
            filament = stats.get("filament_used", 0) / 1000
            
            ext_temp = ext.get("temperature", 0)
            ext_target = ext.get("target", 0)
            bed_temp = bed.get("temperature", 0)
            bed_target = bed.get("target", 0)
            fan_speed = round(fan.get("speed", 0) * 100)
        else:
            # OctoPrint format
            state = status.get("state", "unknown")
            filename = status.get("file", "—") or "—"
            pct = status.get("progress", 0) * 100
            duration = status.get("elapsed_time", 0) or 0
            filament = 0
            
            temps = status.get("temperatures", {})
            ext_temp = temps.get("tool0", {}).get("actual", 0) if temps else 0
            ext_target = temps.get("tool0", {}).get("target", 0) if temps else 0
            bed_temp = temps.get("bed", {}).get("actual", 0) if temps else 0
            bed_target = temps.get("bed", {}).get("target", 0) if temps else 0
            fan_speed = 0
        
        # Calculate ETA
        eta_str = "—"
        if pct > 1 and state == "printing":
            if duration > 0:
                remaining = (duration / (pct / 100)) - duration
                eta_str = f"~{self._format_duration(remaining)}"
        
        # Progress bar
        bar_length = 10
        filled = int(bar_length * pct / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        # State emoji
        state_emoji = {
            "printing": "🖨️",
            "paused": "⏸️",
            "complete": "✅",
            "completed": "✅",
            "operational": "✅",
            "cancelled": "❌",
            "error": "⚠️",
            "standby": "💤",
        }.get(state.lower(), "❓")
        
        embed = discord.Embed(
            title=f"{state_emoji} {printer_name}",
            color=self._get_state_color(state.lower()),
        )
        
        embed.add_field(name="📄 File", value=f"`{filename}`", inline=False)
        embed.add_field(name="📊 Progress", value=f"[{bar}] {pct:.1f}%", inline=False)
        embed.add_field(name="⏱️ Duration", value=self._format_duration(duration), inline=True)
        embed.add_field(name="⏰ ETA", value=eta_str, inline=True)
        embed.add_field(name="🧵 Filament", value=f"{filament:.2f}m", inline=True)
        
        embed.add_field(
            name="🌡️ Hotend",
            value=f"{ext_temp:.1f}°C → {ext_target:.0f}°C",
            inline=True,
        )
        embed.add_field(
            name="🌡️ Bed",
            value=f"{bed_temp:.1f}°C → {bed_target:.0f}°C",
            inline=True,
        )
        embed.add_field(name="💨 Fan", value=f"{fan_speed}%", inline=True)
        
        embed.set_footer(text=f"State: {state}")
        
        return embed
    
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
    
    def _get_state_color(self, state: str) -> int:
        """Get embed color based on printer state."""
        colors = {
            "printing": 0x00FF00,
            "paused": 0xFFA500,
            "complete": 0x00FF00,
            "completed": 0x00FF00,
            "operational": 0x00FF00,
            "cancelled": 0xFF0000,
            "error": 0xFF0000,
            "standby": 0x808080,
        }
        return colors.get(state, 0x0099FF)


class MenuView(discord.ui.View):
    """Main menu view with buttons."""
    
    def __init__(self, user_id: int, printer_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.printer_id = printer_id
    
    @discord.ui.button(label="📊 Status", style=discord.ButtonStyle.primary, row=0)
    async def status_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        status_data = await api.printer_status(self.user_id)
        active_printer = db.get_active_printer(self.user_id)
        printer_name = active_printer['name'] if active_printer else "Printer"
        if status_data:
            cog = interaction.client.get_cog("StatusCog")
            embed = cog._build_status_embed(status_data, printer_name)
            view = StatusView(self.user_id, self.printer_id)
            # Edit the existing message instead of sending a new one
            await interaction.edit_original_response(embed=embed, view=view)
        else:
            await interaction.followup.send("❌ Could not connect to printer.", ephemeral=True)
    
    @discord.ui.button(label="🎮 Control", style=discord.ButtonStyle.secondary, row=0)
    async def control_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from handlers.control import ControlCog
        cog = interaction.client.get_cog("ControlCog")
        if cog:
            await cog.show_control(interaction, edit=True)
        else:
            await interaction.response.send_message("Control feature not loaded.", ephemeral=True)
    
    @discord.ui.button(label="🌡️ Temps", style=discord.ButtonStyle.secondary, row=0)
    async def temps_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from handlers.temps import TempsCog
        cog = interaction.client.get_cog("TempsCog")
        if cog:
            await cog.show_temps(interaction, edit=True)
        else:
            await interaction.response.send_message("Temps feature not loaded.", ephemeral=True)
    
    @discord.ui.button(label="📁 Files", style=discord.ButtonStyle.secondary, row=1)
    async def files_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from handlers.files import FilesCog
        cog = interaction.client.get_cog("FilesCog")
        if cog:
            await cog.show_files(interaction, edit=True)
        else:
            await interaction.response.send_message("Files feature not loaded.", ephemeral=True)

    @discord.ui.button(label="🎮 Move", style=discord.ButtonStyle.secondary, row=1)
    async def move_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from handlers.move import MoveCog
        cog = interaction.client.get_cog("MoveCog")
        if cog:
            await cog.show_move(interaction, edit=True)
        else:
            await interaction.response.send_message("Move feature not loaded.", ephemeral=True)

    @discord.ui.button(label="🧵 Filament", style=discord.ButtonStyle.secondary, row=1)
    async def filament_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from handlers.filament import FilamentCog
        cog = interaction.client.get_cog("FilamentCog")
        if cog:
            await cog.show_filament(interaction, edit=True)
        else:
            await interaction.response.send_message("Filament feature not loaded.", ephemeral=True)
    
    @discord.ui.button(label="📷 Camera", style=discord.ButtonStyle.secondary, row=2)
    async def camera_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from handlers.camera import CameraCog
        cog = interaction.client.get_cog("CameraCog")
        if cog:
            await cog.show_camera(interaction, edit=True)
        else:
            await interaction.response.send_message("Camera feature not loaded.", ephemeral=True)

    @discord.ui.button(label="📜 History", style=discord.ButtonStyle.secondary, row=2)
    async def history_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from handlers.history import HistoryCog
        cog = interaction.client.get_cog("HistoryCog")
        if cog:
            await cog.show_history(interaction, edit=True)
        else:
            await interaction.response.send_message("History feature not loaded.", ephemeral=True)

    @discord.ui.button(label="📊 Mesh", style=discord.ButtonStyle.secondary, row=2)
    async def mesh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from handlers.bed_mesh import BedMeshCog
        cog = interaction.client.get_cog("BedMeshCog")
        if cog:
            await cog.show_bed_mesh(interaction, edit=True)
        else:
            await interaction.response.send_message("Bed Mesh feature not loaded.", ephemeral=True)

    @discord.ui.button(label="⚙️ Settings", style=discord.ButtonStyle.secondary, row=3)
    async def settings_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from handlers.printer_config import PrinterConfigCog
        cog = interaction.client.get_cog("PrinterConfigCog")
        if cog:
            await cog.show_my_settings(interaction, edit=True)
        else:
            await interaction.response.send_message("Settings feature not loaded.", ephemeral=True)

    @discord.ui.button(label="🖨️ Switch", style=discord.ButtonStyle.secondary, row=3)
    async def switch_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from handlers.printers import PrintersCog
        cog = interaction.client.get_cog("PrintersCog")
        if cog:
            await cog.show_printers(interaction, edit=True)
        else:
            await interaction.response.send_message("Printers feature not loaded.", ephemeral=True)


class StatusView(discord.ui.View):
    """Status view with action buttons."""
    
    def __init__(self, user_id: int, printer_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.printer_id = printer_id
    
    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.primary)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Determine printer for this message
        printer = db.get_printer(self.printer_id)
        if not printer:
            await interaction.response.send_message("Printer not found.", ephemeral=True)
            return

        # Permissions check for refresh
        # Public: anyone can refresh
        # Private/Unlisted: only owner/allowed can refresh
        can_refresh = (printer['privacy'] == 'public') or \
                      db.user_can_control(interaction.user.id, self.printer_id)

        if not can_refresh:
            await interaction.response.send_message("❌ You don't have permission to refresh this status.", ephemeral=True)
            return

        await interaction.response.defer()
        
        status_data = await api.printer_status(self.user_id, self.printer_id)
        printer_name = printer['name']
        
        if not status_data:
            await interaction.followup.send("❌ Could not connect to printer.", ephemeral=True)
            return
        
        cog = interaction.client.get_cog("StatusCog")
        if cog:
            embed = cog._build_status_embed(status_data, printer_name)
            await interaction.edit_original_response(embed=embed)
    
    @discord.ui.button(label="🎮 Control", style=discord.ButtonStyle.secondary)
    async def control_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from handlers.control import ControlCog
        cog = interaction.client.get_cog("ControlCog")
        if cog:
            await cog.show_control(interaction, edit=True, printer_id=self.printer_id)
        else:
            await interaction.response.send_message("Control feature not loaded.", ephemeral=True)
    
    @discord.ui.button(label="📷 Snapshot", style=discord.ButtonStyle.secondary)
    async def snapshot_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from handlers.camera import CameraCog
        cog = interaction.client.get_cog("CameraCog")
        if cog:
            await cog.show_camera(interaction, edit=True, printer_id=self.printer_id)
        else:
            await interaction.response.send_message("Camera feature not loaded.", ephemeral=True)

    @discord.ui.button(label="⬅️ Back", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("StatusCog")
        if cog:
            await cog.show_main_menu(interaction, edit=True)

    @discord.ui.button(label="🗑️ Delete", style=discord.ButtonStyle.danger)
    async def delete_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Only owner can delete
        if db.is_printer_owner(interaction.user.id, self.printer_id):
            await interaction.message.delete()
        else:
            await interaction.response.send_message("❌ Only the printer owner can delete this message.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(StatusCog(bot))
