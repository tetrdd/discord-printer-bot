"""
Bed mesh visualization commands for Discord Printer Bot.
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

import db
import api
import permissions


class BedMeshCog(commands.Cog):
    """Bed mesh visualization commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="bed-mesh", description="View bed mesh profile")
    async def bed_mesh(self, interaction: discord.Interaction):
        """View bed mesh profile data."""
        user_id = interaction.user.id
        active_printer_id = db.get_active_printer_id(user_id)
        
        try:
            permissions.check_control_permission(user_id, active_printer_id)
        except permissions.PermissionError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        mesh_data = await api.bed_mesh_status(user_id)
        
        if not mesh_data:
            await interaction.followup.send(
                "📊 Bed mesh data not available. (Note: Only available on Moonraker/Klipper with bed_mesh configured)",
                ephemeral=True,
            )
            return
        
        profile_name = mesh_data.get("profile_name", "default")
        mesh_min = mesh_data.get("mesh_min", (0, 0))
        mesh_max = mesh_data.get("mesh_max", (0, 0))
        probed_matrix = mesh_data.get("probed_matrix", [])
        
        # Calculate min/max Z values
        all_z = []
        for row in probed_matrix:
            all_z.extend(row)
        
        min_z = min(all_z) if all_z else 0
        max_z = max(all_z) if all_z else 0
        range_z = max_z - min_z
        
        # Build mesh visualization
        mesh_text = self._format_mesh(probed_matrix)
        
        embed = discord.Embed(
            title="📊 Bed Mesh Profile",
            description=f"Profile: **{profile_name}**",
            color=0x2ECC71,
        )
        
        embed.add_field(name="📐 Grid", value=f"{len(probed_matrix)}x{len(probed_matrix[0]) if probed_matrix else 0}", inline=True)
        embed.add_field(name="📍 Min", value=f"{mesh_min[0]:.1f}, {mesh_min[1]:.1f}", inline=True)
        embed.add_field(name="📍 Max", value=f"{mesh_max[0]:.1f}, {mesh_max[1]:.1f}", inline=True)
        embed.add_field(name="📉 Min Z", value=f"{min_z:+.4f}mm", inline=True)
        embed.add_field(name="📈 Max Z", value=f"{max_z:+.4f}mm", inline=True)
        embed.add_field(name="📊 Range", value=f"{range_z:.4f}mm", inline=True)
        
        if mesh_text:
            # Discord has a limit for field length, truncate if needed
            if len(mesh_text) > 1000:
                mesh_text = mesh_text[:997] + "..."
            embed.add_field(
                name="🔢 Mesh Values (mm)",
                value=f"```\n{mesh_text}\n```",
                inline=False,
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    def _format_mesh(self, matrix: list) -> str:
        """Format mesh matrix as text grid."""
        if not matrix:
            return ""
        
        # Find max width for alignment
        max_width = max(len(f"{v:+.3f}") for row in matrix for v in row)
        
        lines = []
        for row in matrix:
            line = " ".join(f"{v:>+{max_width}.3f}" for v in row)
            lines.append(line)
        
        return "\n".join(lines)


async def setup(bot: commands.Bot):
    await bot.add_cog(BedMeshCog(bot))
