#!/usr/bin/env python3
"""
Discord Printer Bot - Main entry point.
A Discord bot for controlling 3D printers via Moonraker, OctoPrint, or OctoEverywhere.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path so imports work
sys.path.insert(0, str(Path(__file__).parent))

import discord
from discord import app_commands
from discord.ext import commands, tasks

import config

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("PrinterBot")


class PrinterBot(commands.Bot):
    """Custom bot class with setup handling."""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            description="3D Printer Control Bot for Discord",
        )
    
    async def setup_hook(self):
        """Load cogs on startup."""
        # Load all handler cogs
        cogs = [
            "handlers.status",
            "handlers.control",
            "handlers.temps",
            "handlers.files",
            "handlers.camera",
            "handlers.macros",
            "handlers.adjust",
            "handlers.history",
            "handlers.bed_mesh",
            "handlers.printers",
        ]
        
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}")
        
        # Sync commands
        self.tree.copy_global_to(guilds=None)
        await self.tree.sync()
        logger.info("Synced slash commands")
    
    async def on_ready(self):
        """Called when bot is ready."""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="your 3D prints 🖨️",
            )
        )


async def main():
    """Main entry point."""
    # Load configuration
    try:
        cfg = config.load()
        logger.info("Configuration loaded successfully")
    except FileNotFoundError as e:
        logger.error(e)
        logger.error("Please copy config.yaml.example to config.yaml and configure it")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)
    
    # Get Discord token
    token = config.discord_token()
    if not token or token == "YOUR_DISCORD_BOT_TOKEN_HERE":
        logger.error("Discord bot token not configured in config.yaml")
        logger.error("Please get a token from https://discord.com/developers/applications")
        sys.exit(1)
    
    # Create and run bot
    bot = PrinterBot()
    
    try:
        await bot.start(token)
    except discord.LoginFailure:
        logger.error("Invalid Discord bot token")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Bot error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
