"""
Permission system with database integration.
Handles user permissions, printer ownership, and access control.
"""

import logging
from typing import List, Dict, Any

import database

logger = logging.getLogger("PrinterBot")

class PermissionError(Exception):
    """Custom exception for permission errors."""
    pass


def check_view_permission(user_id: int, printer_id: int) -> bool:
    """Check if a user can view a printer."""
    printer = database.db.get_printer_by_id(printer_id)
    if not printer:
        return False
    
    # Owner can always view
    if printer.get("owner_discord_id") == user_id:
        return True
    
    # Check if printer is public or user is allowed
    if printer.get("privacy") == "public":
        return True
    
    # Check allowed users
    allowed_users = database.db.get_allowed_users(printer_id)
    return user_id in allowed_users

def check_owner_permission(user_id: int, printer_id: int) -> None:
    """Check if a user is the owner of a printer."""
    printer = database.db.get_printer_by_id(printer_id)
    if not printer:
        raise PermissionError(f"Printer ID {printer_id} not found")
    
    if printer.get("owner_discord_id") != user_id:
        raise PermissionError("You are not the owner of this printer")

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

def set_printer_privacy(printer_id: int, private: bool) -> bool:
    """Set printer privacy setting."""
    privacy = "private" if private else "public"
    return database.db.set_printer_privacy(printer_id, privacy)

def add_allowed_user(printer_id: int, user_id: int) -> bool:
    """Add a user to the allowed users list."""
    return database.db.add_allowed_user(printer_id, user_id)

def remove_allowed_user(printer_id: int, user_id: int) -> bool:
    """Remove a user from the allowed users list."""
    return database.db.remove_allowed_user(printer_id, user_id)

def update_printer_settings(printer_id: int, **kwargs) -> bool:
    """Update printer settings."""
    return database.db.update_printer(printer_id, **kwargs)

def check_printer_exists(name: str) -> bool:
    """Check if a printer with the given name exists."""
    printer = database.db.get_printer_by_name(name)
    return printer is not None