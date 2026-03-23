"""
Configuration handler with database integration.
Extends the original config module to work with the SQLite database.
"""

import logging
from typing import Any, Dict, Optional, List
from pathlib import Path
import yaml

import database

logger = logging.getLogger("PrinterBot")

# Default configuration
DEFAULT_CONFIG = {
    "discord_token": "",
    "printers": [],
    "camera": {},
    "owners": [],
    "permissions": {},
    "database": {
        "path": str(database.DB_PATH)
    }
}

config_data = {}
active_printers = {}


def load() -> Dict[str, Any]:
    """Load configuration from config.yaml."""
    global config_data
    
    config_path = Path(__file__).parent / "config.yaml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f) or {}
    
    # Initialize active printers
    for printer in config_data.get("printers", []):
        owner_id = printer.get("owner_id")
        if owner_id:
            active_printers[owner_id] = printer.get("id", printer.get("name"))
    
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

def get_printer(printer_id: int) -> Optional[Dict[str, Any]]:
    """Get printer configuration by ID."""
    for printer in config_data.get("printers", []):
        if printer.get("id") == printer_id:
            return printer
    return None

def discord_token() -> str:
    """Get Discord bot token."""
    return get("discord_token", "")

def get_printer_types() -> List[str]:
    """Get available printer types."""
    return ["moonraker", "octoprint", "octoeverywhere"]

# Database-integrated functions

def get_accessible_printers_embed(user_id: int) -> Dict[str, Any]:
    """Get embed data for accessible printers."""
    printers = database.db.get_printers_accessible_by_user(user_id)
    
    if not printers:
        return {
            "title": "🖨 No Printers Found",
            "description": "You don't have access to any printers. Use /register-printer to add one.",
            "color": 0xFF0000
        }
    
    printer_list = "\n".join([
        f"🖨 **{p['name']}** (ID: {p['printer_id']}) - {p['type'].title()}"
        for p in printers
    ])
    
    return {
        "title": f"🖨 Your Printers ({len(printers)})",
        "description": f"Here are the printers you can access:\n\n{printer_list}",
        "color": 0x00FF00
    }

def get_printer_info_embed(printer_id: int, user_id: int) -> Dict[str, Any]:
    """Get embed data for printer information."""
    printer = database.db.get_printer_by_id(printer_id)
    
    if not printer:
        return {
            "title": "❌ Printer Not Found",
            "color": 0xFF0000,
            "fields": []
        }
    
    # Check if user has access
    accessible_printers = database.db.get_printers_accessible_by_user(user_id)
    has_access = any(p["printer_id"] == printer_id for p in accessible_printers)
    
    if not has_access:
        return {
            "title": "❌ Access Denied",
            "color": 0xFF0000,
            "fields": []
        }
    
    privacy_status = "Public" if printer.get("privacy") == "public" else "Private"
    allowed_users = database.db.get_allowed_users(printer_id)
    
    fields = [
        {"name": "Type", "value": printer.get("type", "Unknown").title(), "inline": True},
        {"name": "URL", "value": printer.get("url", "Not configured"), "inline": True},
        {"name": "Privacy", "value": privacy_status, "inline": True},
        {"name": "Owner", "value": f"<@{printer.get('owner_discord_id', 'Unknown')}>" if printer.get('owner_discord_id') else "Unknown", "inline": True},
        {"name": "Allowed Users", "value": f"{len(allowed_users)}" if allowed_users else "None", "inline": True},
        {"name": "Created", "value": datetime.fromtimestamp(printer.get("creation_timestamp", 0)).strftime("%Y-%m-%d %H:%M:%S"), "inline": True},
    ]
    
    return {
        "title": f"🖨 {printer.get('name', 'Unknown Printer')}",
        "color": 0x0099FF,
        "fields": fields
    }