"""
Temperature control commands for Discord Printer Bot.
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, TextInput, Button, View

import db
import api
import permissions


class TempsCog(commands.Cog):
    """Temperature control commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="temperatures", description="Temperature control menu")
    async def temperatures(self, interaction: discord.Interaction):
        """Show temperature control menu."""
        await self.show_temps(interaction)

    async def show_temps(self, interaction: discord.Interaction, edit: bool = False):
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
        view.add_item(discord.ui.Button(label="⬅️ Back", style=discord.ButtonStyle.secondary, custom_id="back_to_menu"))

        if edit:
            if not interaction.response.is_done():
                await interaction.response.edit_message(embed=embed, view=view)
            else:
                await interaction.edit_original_response(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="presets-manager", description="Manage your temperature presets")
    async def presets_manager(self, interaction: discord.Interaction):
        """View and manage temperature presets."""
        user_id = interaction.user.id
        db.ensure_user_exists(user_id)
        
        presets = db.get_temp_presets(user_id)
        
        embed = discord.Embed(
            title="📑 Your Temperature Presets",
            description="Manage your custom material presets.",
            color=discord.Color.blue(),
        )
        
        if presets:
            for p in presets:
                embed.add_field(
                    name=p['name'],
                    value=f"Hotend: {p['hotend_temp']}°C / Bed: {p['bed_temp']}°C",
                    inline=True,
                )
        else:
            embed.description = "You don't have any presets yet."

        view = PresetsManagerView(user_id, presets)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class TempsView(discord.ui.View):
    """Temperature control view with presets."""
    
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id
    
    @discord.ui.button(label="📑 Presets", style=discord.ButtonStyle.primary)
    async def presets_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        presets = db.get_temp_presets(self.user_id)
        if not presets:
            await interaction.response.send_message("You have no presets configured.", ephemeral=True)
            return

        view = PresetSelectView(self.user_id, presets)
        await interaction.response.send_message(
            "Select a preset to apply:",
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
    
    def __init__(self, user_id: int, presets: list):
        super().__init__(timeout=None)
        self.user_id = user_id
        
        for p in presets:
            name = p['name']
            hot = p['hotend_temp']
            bed = p['bed_temp']

            button = discord.ui.Button(
                label=f"{name} ({hot}/{bed})",
                style=discord.ButtonStyle.secondary,
            )
            button.callback = self.make_callback(name, hot, bed)
            self.add_item(button)
    
    def make_callback(self, name: str, hot: int, bed: int):
        async def callback(interaction: discord.Interaction):
            await interaction.response.defer()
            h_res = await api.set_hotend_temp(hot, self.user_id)
            b_res = await api.set_bed_temp(bed, self.user_id)
            
            if h_res and b_res:
                await interaction.followup.send(f"✅ Applied preset **{name}** ({hot}°C / {bed}°C)", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Failed to apply preset **{name}**", ephemeral=True)
        return callback


class AddPresetModal(Modal, title="Add Temperature Preset"):
    name_input = TextInput(label="Preset Name", placeholder="e.g. PLA, PETG", required=True)
    hotend_input = TextInput(label="Hotend Temp (°C)", placeholder="200", required=True)
    bed_input = TextInput(label="Bed Temp (°C)", placeholder="60", required=True)

    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            hot = int(self.hotend_input.value)
            bed = int(self.bed_input.value)
            db.add_temp_preset(self.user_id, self.name_input.value, hot, bed)
            await interaction.response.send_message(f"✅ Added preset **{self.name_input.value}**", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Temperature must be a number.", ephemeral=True)


class PresetsManagerView(discord.ui.View):
    def __init__(self, user_id: int, presets: list):
        super().__init__(timeout=None)
        self.user_id = user_id

        if presets:
            select = discord.ui.Select(placeholder="Select a preset to delete...")
            for p in presets:
                select.add_option(label=p['name'], value=str(p['preset_id']), description=f"{p['hotend_temp']}°C / {p['bed_temp']}°C")
            select.callback = self.delete_callback
            self.add_item(select)
            
    @discord.ui.button(label="➕ Add Preset", style=discord.ButtonStyle.success)
    async def add_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddPresetModal(self.user_id))
        
    async def delete_callback(self, interaction: discord.Interaction):
        preset_id = int(interaction.data['values'][0])
        if db.delete_temp_preset(preset_id, self.user_id):
            await interaction.response.send_message("✅ Preset deleted.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Failed to delete preset.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(TempsCog(bot))
