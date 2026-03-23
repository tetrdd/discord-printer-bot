"""
Temperature control commands for Discord Printer Bot.
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

import config
import api
import permissions


class TempsCog(commands.Cog):
    """Temperature control commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="temperatures", description="Temperature control menu")
    async def temperatures(self, interaction: discord.Interaction):
        """Show temperature control menu."""
        user_id = interaction.user.id
        
        try:
            permissions.check_control_permission(user_id, config.active_printer_id(user_id))
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        status_data = await api.printer_status(user_id)
        
        # Extract current temps
        if status_data and "extruder" in status_data:
            # Moonraker
            ext_temp = status_data.get("extruder", {}).get("temperature", 0)
            ext_target = status_data.get("extruder", {}).get("target", 0)
            bed_temp = status_data.get("heater_bed", {}).get("temperature", 0)
            bed_target = status_data.get("heater_bed", {}).get("target", 0)
        elif status_data and "temperatures" in status_data:
            # OctoPrint
            temps = status_data.get("temperatures", {})
            ext_temp = temps.get("tool0", {}).get("actual", 0) if temps else 0
            ext_target = temps.get("tool0", {}).get("target", 0) if temps else 0
            bed_temp = temps.get("bed", {}).get("actual", 0) if temps else 0
            bed_target = temps.get("bed", {}).get("target", 0) if temps else 0
        else:
            ext_temp = ext_target = bed_temp = bed_target = 0
        
        embed = discord.Embed(
            title="🌡️ Temperature Control",
            color=0xFF6600,
        )
        
        embed.add_field(
            name="🔥 Hotend",
            value=f"{ext_temp:.1f}°C → {ext_target:.0f}°C",
            inline=False,
        )
        embed.add_field(
            name="🛏️ Bed",
            value=f"{bed_temp:.1f}°C → {bed_target:.0f}°C",
            inline=False,
        )
        
        view = TempsView(user_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(
        name="set-hotend",
        description="Set hotend target temperature"
    )
    @app_commands.describe(temperature="Target temperature in °C (0 to cool)")
    async def set_hotend(self, interaction: discord.Interaction, temperature: float):
        """Set hotend target temperature."""
        user_id = interaction.user.id
        
        try:
            permissions.check_control_permission(user_id, config.active_printer_id(user_id))
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        if temperature < 0 or temperature > 300:
            await interaction.response.send_message(
                "❌ Temperature must be between 0 and 300°C",
                ephemeral=True,
            )
            return
        
        await interaction.response.defer()
        
        result = await api.set_hotend_temp(temperature, user_id)
        
        if result:
            await interaction.followup.send(
                f"✅ Hotend set to {temperature:.0f}°C",
                ephemeral=True,
            )
        else:
            await interaction.followup.send("❌ Failed to set temperature", ephemeral=True)
    
    @app_commands.command(
        name="set-bed",
        description="Set bed target temperature"
    )
    @app_commands.describe(temperature="Target temperature in °C (0 to cool)")
    async def set_bed(self, interaction: discord.Interaction, temperature: float):
        """Set bed target temperature."""
        user_id = interaction.user.id
        
        try:
            permissions.check_control_permission(user_id, config.active_printer_id(user_id))
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        if temperature < 0 or temperature > 120:
            await interaction.response.send_message(
                "❌ Temperature must be between 0 and 120°C",
                ephemeral=True,
            )
            return
        
        await interaction.response.defer()
        
        result = await api.set_bed_temp(temperature, user_id)
        
        if result:
            await interaction.followup.send(
                f"✅ Bed set to {temperature:.0f}°C",
                ephemeral=True,
            )
        else:
            await interaction.followup.send("❌ Failed to set temperature", ephemeral=True)
    
    @app_commands.command(name="cool-all", description="Turn off all heaters")
    async def cool_all(self, interaction: discord.Interaction):
        """Turn off all heaters."""
        user_id = interaction.user.id
        
        try:
            permissions.check_control_permission(user_id, config.active_printer_id(user_id))
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        hotend_result = await api.set_hotend_temp(0, user_id)
        bed_result = await api.set_bed_temp(0, user_id)
        
        if hotend_result and bed_result:
            await interaction.followup.send("✅ All heaters turned off", ephemeral=True)
        else:
            await interaction.followup.send("❌ Failed to turn off heaters", ephemeral=True)


class TempsView(discord.ui.View):
    """Temperature control view with presets."""
    
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id
        
        # Get presets from config
        presets = config.temp_presets()
        self.hotend_presets = presets.get("hotend", {
            "PLA": 200,
            "PETG": 230,
            "ABS": 245,
            "Cool": 0,
        })
        self.bed_presets = presets.get("bed", {
            "PLA": 60,
            "PETG": 80,
            "ABS": 100,
            "Cool": 0,
        })
    
    @discord.ui.button(label="🔥 Hotend Presets", style=discord.ButtonStyle.primary)
    async def hotend_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = PresetSelectView(self.user_id, "hotend", self.hotend_presets)
        await interaction.response.send_message(
            "Select hotend preset:",
            view=view,
            ephemeral=True,
        )
    
    @discord.ui.button(label="🛏️ Bed Presets", style=discord.ButtonStyle.primary)
    async def bed_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = PresetSelectView(self.user_id, "bed", self.bed_presets)
        await interaction.response.send_message(
            "Select bed preset:",
            view=view,
            ephemeral=True,
        )
    
    @discord.ui.button(label="❄️ Cool All", style=discord.ButtonStyle.danger)
    async def cool_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        hotend_result = await api.set_hotend_temp(0, self.user_id)
        bed_result = await api.set_bed_temp(0, self.user_id)
        await interaction.followup.send(
            "✅ All heaters off" if (hotend_result and bed_result) else "❌ Failed",
            ephemeral=True,
        )


class PresetSelectView(discord.ui.View):
    """View for selecting temperature presets."""
    
    def __init__(self, user_id: int, heater_type: str, presets: dict):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.heater_type = heater_type
        self.presets = presets
        
        # Add buttons for each preset
        for i, (name, temp) in enumerate(presets.items()):
            button = discord.ui.Button(
                label=f"{name}: {temp}°C",
                style=discord.ButtonStyle.secondary,
                custom_id=f"preset_{heater_type}_{name}",
            )
            button.callback = self.make_callback(name, temp)
            self.add_item(button)
    
    def make_callback(self, name: str, temp: float):
        """Create a callback for a preset button."""
        async def callback(interaction: discord.Interaction):
            await interaction.response.defer()
            
            if self.heater_type == "hotend":
                result = await api.set_hotend_temp(temp, self.user_id)
                msg = f"Hotend set to {temp}°C ({name})"
            else:
                result = await api.set_bed_temp(temp, self.user_id)
                msg = f"Bed set to {temp}°C ({name})"
            
            await interaction.followup.send(
                f"✅ {msg}" if result else f"❌ Failed to set {self.heater_type}",
                ephemeral=True,
            )
        
        return callback


async def setup(bot: commands.Bot):
    await bot.add_cog(TempsCog(bot))
