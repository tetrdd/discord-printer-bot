"""
Adjustment commands for Discord Printer Bot.
Speed, flow, fan, and Z-offset adjustments.
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

import config
import api
import permissions


class AdjustCog(commands.Cog):
    """Adjustment commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="adjust", description="Adjust print parameters")
    async def adjust(self, interaction: discord.Interaction):
        """Show adjustment menu."""
        user_id = interaction.user.id
        
        try:
            permissions.check_control_permission(user_id, config.active_printer_id(user_id))
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🔧 Print Adjustments",
            description="Adjust speed, flow, fan, and Z-offset during prints.",
            color=0xF39C12,
        )
        
        view = AdjustView(user_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="speed", description="Set speed override")
    @app_commands.describe(percentage="Speed percentage (50-150)")
    async def speed(self, interaction: discord.Interaction, percentage: int):
        """Set print speed override percentage."""
        user_id = interaction.user.id
        
        try:
            permissions.check_control_permission(user_id, config.active_printer_id(user_id))
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        if percentage < 50 or percentage > 150:
            await interaction.response.send_message(
                "❌ Speed must be between 50% and 150%",
                ephemeral=True,
            )
            return
        
        await interaction.response.defer()
        
        result = await api.set_speed_factor(percentage, user_id)
        
        if result:
            await interaction.followup.send(f"✅ Speed set to {percentage}%", ephemeral=True)
        else:
            await interaction.followup.send("❌ Failed to set speed", ephemeral=True)
    
    @app_commands.command(name="flow", description="Set flow override")
    @app_commands.describe(percentage="Flow percentage (75-125)")
    async def flow(self, interaction: discord.Interaction, percentage: int):
        """Set print flow override percentage."""
        user_id = interaction.user.id
        
        try:
            permissions.check_control_permission(user_id, config.active_printer_id(user_id))
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        if percentage < 75 or percentage > 125:
            await interaction.response.send_message(
                "❌ Flow must be between 75% and 125%",
                ephemeral=True,
            )
            return
        
        await interaction.response.defer()
        
        result = await api.set_flow_factor(percentage, user_id)
        
        if result:
            await interaction.followup.send(f"✅ Flow set to {percentage}%", ephemeral=True)
        else:
            await interaction.followup.send("❌ Failed to set flow", ephemeral=True)
    
    @app_commands.command(name="fan", description="Set fan speed")
    @app_commands.describe(percentage="Fan speed percentage (0-100)")
    async def fan(self, interaction: discord.Interaction, percentage: int):
        """Set part cooling fan speed."""
        user_id = interaction.user.id
        
        try:
            permissions.check_control_permission(user_id, config.active_printer_id(user_id))
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        if percentage < 0 or percentage > 100:
            await interaction.response.send_message(
                "❌ Fan speed must be between 0% and 100%",
                ephemeral=True,
            )
            return
        
        await interaction.response.defer()
        
        result = await api.set_fan_speed(percentage, user_id)
        
        if result:
            await interaction.followup.send(f"✅ Fan set to {percentage}%", ephemeral=True)
        else:
            await interaction.followup.send("❌ Failed to set fan", ephemeral=True)
    
    @app_commands.command(name="z-offset", description="Adjust Z-offset")
    @app_commands.describe(
        adjustment="Z adjustment in mm (e.g., 0.05 or -0.05)",
        reset="Reset Z-offset to zero"
    )
    async def z_offset(
        self,
        interaction: discord.Interaction,
        adjustment: Optional[float] = None,
        reset: Optional[bool] = False,
    ):
        """Adjust Z-offset."""
        user_id = interaction.user.id
        
        try:
            permissions.check_control_permission(user_id, config.active_printer_id(user_id))
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        if reset:
            result = await api.reset_z_offset(user_id)
            msg = "Z-offset reset to zero"
        elif adjustment is not None:
            result = await api.adjust_z_offset(adjustment, user_id)
            msg = f"Z-offset adjusted by {adjustment:+.3f}mm"
        else:
            await interaction.followup.send(
                "❌ Provide either `adjustment` or set `reset` to true",
                ephemeral=True,
            )
            return
        
        if result:
            await interaction.followup.send(f"✅ {msg}", ephemeral=True)
        else:
            await interaction.followup.send("❌ Failed to adjust Z-offset", ephemeral=True)


class AdjustView(discord.ui.View):
    """Adjustment control view."""
    
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id
    
    @discord.ui.button(label="⚡ Speed 50%", style=discord.ButtonStyle.secondary)
    async def speed_50(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_speed(interaction, 50)
    
    @discord.ui.button(label="⚡ Speed 100%", style=discord.ButtonStyle.primary)
    async def speed_100(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_speed(interaction, 100)
    
    @discord.ui.button(label="⚡ Speed 125%", style=discord.ButtonStyle.secondary)
    async def speed_125(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_speed(interaction, 125)
    
    @discord.ui.button(label="💧 Flow 100%", style=discord.ButtonStyle.primary)
    async def flow_100(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_flow(interaction, 100)
    
    @discord.ui.button(label="💧 Flow 110%", style=discord.ButtonStyle.secondary)
    async def flow_110(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_flow(interaction, 110)
    
    @discord.ui.button(label="💨 Fan 0%", style=discord.ButtonStyle.secondary)
    async def fan_0(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_fan(interaction, 0)
    
    @discord.ui.button(label="💨 Fan 50%", style=discord.ButtonStyle.secondary)
    async def fan_50(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_fan(interaction, 50)
    
    @discord.ui.button(label="💨 Fan 100%", style=discord.ButtonStyle.primary)
    async def fan_100(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_fan(interaction, 100)
    
    async def _set_speed(self, interaction: discord.Interaction, pct: int):
        await interaction.response.defer()
        result = await api.set_speed_factor(pct, self.user_id)
        await interaction.followup.send(
            f"✅ Speed: {pct}%" if result else "❌ Failed",
            ephemeral=True,
        )
    
    async def _set_flow(self, interaction: discord.Interaction, pct: int):
        await interaction.response.defer()
        result = await api.set_flow_factor(pct, self.user_id)
        await interaction.followup.send(
            f"✅ Flow: {pct}%" if result else "❌ Failed",
            ephemeral=True,
        )
    
    async def _set_fan(self, interaction: discord.Interaction, pct: int):
        await interaction.response.defer()
        result = await api.set_fan_speed(pct, self.user_id)
        await interaction.followup.send(
            f"✅ Fan: {pct}%" if result else "❌ Failed",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(AdjustCog(bot))
