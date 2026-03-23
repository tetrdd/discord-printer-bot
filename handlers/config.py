"""
Configuration handler.
Handles bot configuration.
"""

import logging
from typing import Any, Dict, Optional, List
from pathlib import Path
import yaml

import db

logger = logging.getLogger("PrinterBot")

# Default configuration
DEFAULT_CONFIG = {
    "discord_token": "",
    "camera": {},
}

config_data = {}
active_printers = {}


def load() -> Dict[str, Any]:
    """Load configuration from config.yaml."""
    global config_data
    
    config_path = Path(__file__).parent / "config.yaml"
    
    if not config_path.exists():
        # Create default if not exists
        return DEFAULT_CONFIG
    
    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f) or {}
    
    return config_data

def get(key: str, default: Any = None) -> Any:
    """Get a configuration value."""
    return config_data.get(key, default)

def set_active_printer(user_id: int, printer_id: int) -> None:
    """Set the active printer for a user."""
    global active_printers
    active_printers[user_id] = printer_id

def active_printer_id(user_id: int) -> Optional[int]:
    """Get the active printer ID for a user."""
    return active_printers.get(user_id)

def discord_token() -> str:
    """Get Discord bot token."""
    return get("discord_token", "")

def get_printer_types() -> List[str]:
    """Get available printer types."""
    return ["moonraker", "octoprint", "octoeverywhere"]
