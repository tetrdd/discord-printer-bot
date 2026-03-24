"""
Print control commands for Discord Printer Bot.
Pause, resume, cancel, home, motors off, etc.
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

import db
import api
import permissions


class ControlCog(commands.Cog):
    """Print control commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="control", description="Print control menu")
    async def control(self, interaction: discord.Interaction):
        """Show print control menu."""
        await self.show_control(interaction)

    async def show_control(self, interaction: discord.Interaction, edit: bool = False):
        user_id = interaction.user.id
        active_printer_id = db.get_active_printer_id(user_id)
        
        try:
            permissions.check_control_permission(user_id, active_printer_id)
        except permissions.PermissionError as e:
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        status_data = await api.printer_status(user_id)
        state = "unknown"
        
        if status_data:
            if "print_stats" in status_data:
                state = status_data.get("print_stats", {}).get("state", "unknown")
            else:
                state = status_data.get("state", "unknown")
        
        embed = discord.Embed(
            title="🎮 Print Control",
            description=f"Current state: **{state}**",
            color=0x0099FF,
        )
        
        view = ControlView(user_id, state)
        view.add_item(discord.ui.Button(label="⬅️ Back", style=discord.ButtonStyle.secondary, custom_id="back_to_menu"))

        if edit:
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="pause", description="Pause current print")
    async def pause(self, interaction: discord.Interaction):
        """Pause the current print."""
        user_id = interaction.user.id
        active_printer_id = db.get_active_printer_id(user_id)
        
        try:
            permissions.check_control_permission(user_id, active_printer_id)
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        result = await api.pause_print(user_id)
        
        if result:
            await interaction.followup.send("✅ Print paused", ephemeral=True)
        else:
            await interaction.followup.send("❌ Failed to pause print", ephemeral=True)
    
    @app_commands.command(name="resume", description="Resume paused print")
    async def resume(self, interaction: discord.Interaction):
        """Resume a paused print."""
        user_id = interaction.user.id
        active_printer_id = db.get_active_printer_id(user_id)
        
        try:
            permissions.check_control_permission(user_id, active_printer_id)
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        result = await api.resume_print(user_id)
        
        if result:
            await interaction.followup.send("✅ Print resumed", ephemeral=True)
        else:
            await interaction.followup.send("❌ Failed to resume print", ephemeral=True)
    
    @app_commands.command(name="cancel", description="Cancel current print")
    async def cancel(self, interaction: discord.Interaction):
        """Cancel the current print with confirmation."""
        user_id = interaction.user.id
        active_printer_id = db.get_active_printer_id(user_id)
        
        try:
            permissions.check_control_permission(user_id, active_printer_id)
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        view = CancelConfirmView(user_id)
        await interaction.response.send_message(
            "⚠️ **Are you sure you want to cancel the current print?**",
            view=view,
            ephemeral=True,
        )
    
    @app_commands.command(name="home", description="Home printer axes")
    async def home(self, interaction: discord.Interaction, axes: str = "XYZ"):
        """Home specified axes (default: XYZ)."""
        user_id = interaction.user.id
        active_printer_id = db.get_active_printer_id(user_id)
        
        try:
            permissions.check_control_permission(user_id, active_printer_id)
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Validate axes
        valid_axes = set("XYZE")
        axes = axes.upper()
        if not all(a in valid_axes for a in axes):
            await interaction.followup.send("❌ Invalid axes. Use X, Y, Z, or E.", ephemeral=True)
            return
        
        result = await api.home_axes(axes, user_id)
        
        if result:
            await interaction.followup.send(f"✅ Homed: {axes}", ephemeral=True)
        else:
            await interaction.followup.send("❌ Failed to home axes", ephemeral=True)
    
    @app_commands.command(name="motors-off", description="Disable all motors")
    async def motors_off(self, interaction: discord.Interaction):
        """Disable all stepper motors."""
        user_id = interaction.user.id
        active_printer_id = db.get_active_printer_id(user_id)
        
        try:
            permissions.check_control_permission(user_id, active_printer_id)
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        result = await api.motors_off(user_id)
        
        if result:
            await interaction.followup.send("✅ Motors disabled", ephemeral=True)
        else:
            await interaction.followup.send("❌ Failed to disable motors", ephemeral=True)
    
    @app_commands.command(name="estop", description="Emergency stop")
    async def estop(self, interaction: discord.Interaction):
        """Emergency stop the printer."""
        user_id = interaction.user.id
        active_printer_id = db.get_active_printer_id(user_id)
        
        # E-stop doesn't require control permission - it's always available
        # But user must have at least view access
        try:
            permissions.check_view_permission(user_id, active_printer_id)
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        view = EStopConfirmView(user_id)
        await interaction.response.send_message(
            "🚨 **EMERGENCY STOP** - This will immediately halt all printer operations!\n\n"
            "Are you sure?",
            view=view,
            ephemeral=True,
        )


class ControlView(discord.ui.View):
    """Print control view."""
    
    def __init__(self, user_id: int, state: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.state = state
        
        # Update button states based on current print state
        self.pause_btn.disabled = state != "printing"
        self.resume_btn.disabled = state != "paused"
        self.cancel_btn.disabled = state not in ["printing", "paused"]
    
    @discord.ui.button(label="⏸️ Pause", style=discord.ButtonStyle.primary)
    async def pause_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        result = await api.pause_print(self.user_id)
        await interaction.followup.send(
            "✅ Paused" if result else "❌ Failed",
            ephemeral=True,
        )
    
    @discord.ui.button(label="▶️ Resume", style=discord.ButtonStyle.success)
    async def resume_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        result = await api.resume_print(self.user_id)
        await interaction.followup.send(
            "✅ Resumed" if result else "❌ Failed",
            ephemeral=True,
        )
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Use `/cancel` for confirmation.",
            ephemeral=True,
        )
    
    @discord.ui.button(label="🏠 Home", style=discord.ButtonStyle.secondary)
    async def home_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        result = await api.home_axes("XYZ", self.user_id)
        await interaction.followup.send(
            "✅ Homed" if result else "❌ Failed",
            ephemeral=True,
        )
    
    @discord.ui.button(label="🔌 Motors Off", style=discord.ButtonStyle.secondary)
    async def motors_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        result = await api.motors_off(self.user_id)
        await interaction.followup.send(
            "✅ Disabled" if result else "❌ Failed",
            ephemeral=True,
        )


class CancelConfirmView(discord.ui.View):
    """Confirmation view for cancel action."""
    
    def __init__(self, user_id: int):
        super().__init__(timeout=30)
        self.user_id = user_id
    
    @discord.ui.button(label="Yes, Cancel", style=discord.ButtonStyle.danger)
    async def confirm_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        result = await api.cancel_print(self.user_id)
        await interaction.followup.send(
            "✅ Print cancelled" if result else "❌ Failed to cancel",
            ephemeral=True,
        )
        self.stop()
    
    @discord.ui.button(label="No, Keep Printing", style=discord.ButtonStyle.secondary)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("👍 Cancelled", ephemeral=True)
        self.stop()


class EStopConfirmView(discord.ui.View):
    """Confirmation view for emergency stop."""
    
    def __init__(self, user_id: int):
        super().__init__(timeout=30)
        self.user_id = user_id
    
    @discord.ui.button(label="🚨 YES, E-STOP!", style=discord.ButtonStyle.danger)
    async def confirm_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        result = await api.emergency_stop(self.user_id)
        await interaction.followup.send(
            "🚨 Emergency stop triggered!" if result else "❌ Failed to trigger E-stop",
            ephemeral=True,
        )
        self.stop()
    
    @discord.ui.button(label="No", style=discord.ButtonStyle.secondary)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("👍 E-stop cancelled", ephemeral=True)
        self.stop()


async def setup(bot: commands.Bot):
    await bot.add_cog(ControlCog(bot))
