"""
Configuration loader for Discord Printer Bot.
Reads global settings from environment variables or config.yaml.
"""
from __future__ import annotations

import os
import yaml
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any

logger = logging.getLogger("PrinterBot.config")

CONFIG_PATH = Path(__file__).parent / "config.yaml"

_cfg: Dict = {}


def load() -> dict:
    """Load config from disk. Called once at startup."""
    global _cfg
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            _cfg = yaml.safe_load(f) or {}
    else:
        logger.warning("config.yaml not found, using environment variables.")
        _cfg = {}
    return _cfg


def get() -> dict:
    """Return the loaded config dict."""
    return _cfg


# ── Discord Configuration ─────────────────────────────────────────────────────

def discord_token() -> str:
    """Get Discord bot token from environment or config."""
    token = os.environ.get("DISCORD_TOKEN")
    if token:
        return token
    return _cfg.get("discord", {}).get("bot_token", "")


def admin_ids() -> list[int]:
    """Get list of Discord user IDs that are bot admins."""
    return _cfg.get("discord", {}).get("admin_ids", [])


def is_bot_admin(user_id: int) -> bool:
    """Check if user is a bot admin."""
    return user_id in admin_ids()


# ── Global Settings ───────────────────────────────────────────────────────────

def temp_presets() -> dict:
    """
    Get global temperature presets (deprecated).
    Use db.get_temp_presets(user_id) instead for per-user presets.
    """
    return _cfg.get("temp_presets", {})


def macros_config() -> dict:
    """Get global macros configuration."""
    return _cfg.get("macros", {})


def monitoring_config() -> dict:
    """Get monitoring configuration."""
    return _cfg.get("monitoring", {})
