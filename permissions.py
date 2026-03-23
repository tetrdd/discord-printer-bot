"""
Permission system for Discord Printer Bot.
Handles printer ownership, access control, and privacy settings.
"""
from __future__ import annotations

from typing import Optional, List, Dict, Any
import config


class PermissionError(Exception):
    """Raised when a user doesn't have permission for an action."""
    pass


def check_view_permission(user_id: int, printer_id: int) -> bool:
    """
    Check if user can view a printer.
    Returns True if allowed, raises PermissionError if not.
    """
    if not config.can_view_printer(user_id, printer_id):
        printer = config.get_printer(printer_id)
        printer_name = printer.get("name", f"Printer {printer_id}") if printer else "Unknown"
        raise PermissionError(f"You don't have permission to view {printer_name}")
    return True


def check_control_permission(user_id: int, printer_id: int) -> bool:
    """
    Check if user can control a printer.
    Returns True if allowed, raises PermissionError if not.
    """
    if not config.can_control_printer(user_id, printer_id):
        printer = config.get_printer(printer_id)
        printer_name = printer.get("name", f"Printer {printer_id}") if printer else "Unknown"
        raise PermissionError(f"You don't have permission to control {printer_name}")
    return True


def check_settings_permission(user_id: int, printer_id: int) -> bool:
    """
    Check if user can change printer settings.
    Only owners can change settings.
    Returns True if allowed, raises PermissionError if not.
    """
    if not config.can_change_settings(user_id, printer_id):
        printer = config.get_printer(printer_id)
        printer_name = printer.get("name", f"Printer {printer_id}") if printer else "Unknown"
        raise PermissionError(f"Only the owner can change settings for {printer_name}")
    return True


def check_owner_permission(user_id: int, printer_id: int) -> bool:
    """
    Check if user is the owner of a printer.
    Returns True if owner, raises PermissionError if not.
    """
    if not config.is_printer_owner(user_id, printer_id):
        printer = config.get_printer(printer_id)
        printer_name = printer.get("name", f"Printer {printer_id}") if printer else "Unknown"
        raise PermissionError(f"Only the owner can perform this action on {printer_name}")
    return True


def get_user_permission_level(user_id: int, printer_id: int) -> str:
    """
    Get the user's permission level for a printer.
    Returns: 'owner', 'allowed', 'view_only', or 'none'
    """
    if config.is_printer_owner(user_id, printer_id):
        return "owner"
    elif config.is_printer_allowed(user_id, printer_id):
        return "allowed"
    elif config.can_view_printer(user_id, printer_id):
        return "view_only"
    else:
        return "none"


def format_permission_level(level: str) -> str:
    """Format permission level for display."""
    levels = {
        "owner": "👑 Owner",
        "allowed": "✅ Allowed",
        "view_only": "👁️ View Only",
        "none": "❌ No Access",
    }
    return levels.get(level, "Unknown")


# ── Printer management ────────────────────────────────────────────────────────

def add_printer(
    name: str,
    moonraker_url: str = None,
    moonraker_api_key: str = None,
    octoprint_url: str = None,
    octoprint_api_key: str = None,
    octoeverywhere_key: str = None,
    owner_id: int = None,
    is_private: bool = False,
    allowed_users: List[int] = None,
) -> int:
    """
    Add a new printer to the configuration.
    Returns the new printer ID.
    """
    cfg = config.get()
    
    if "printers" not in cfg:
        cfg["printers"] = []
    
    new_id = len(cfg["printers"])
    
    printer_config = {
        "name": name,
        "owner_id": owner_id,
        "is_private": is_private,
        "allowed_users": allowed_users or [],
    }
    
    if moonraker_url:
        printer_config["moonraker"] = {
            "url": moonraker_url,
            "api_key": moonraker_api_key or "",
        }
    
    if octoprint_url:
        printer_config["octoprint"] = {
            "url": octoprint_url,
            "api_key": octoprint_api_key or "",
        }
    
    if octoeverywhere_key:
        printer_config["octoeverywhere"] = {
            "key": octoeverywhere_key,
        }
    
    cfg["printers"].append(printer_config)
    config.save()
    
    # Reload config to update internal state
    config.load()
    
    return new_id


def remove_printer(printer_id: int) -> bool:
    """
    Remove a printer from the configuration.
    Returns True if successful.
    """
    cfg = config.get()
    
    if "printers" not in cfg:
        return False
    
    if printer_id < 0 or printer_id >= len(cfg["printers"]):
        return False
    
    cfg["printers"].pop(printer_id)
    
    # Update IDs for remaining printers
    for i, printer in enumerate(cfg["printers"]):
        # The ID is implicit based on position
        pass
    
    config.save()
    config.load()
    
    return True


def update_printer_settings(
    printer_id: int,
    name: str = None,
    is_private: bool = None,
    allowed_users: List[int] = None,
) -> bool:
    """
    Update printer settings.
    Returns True if successful.
    """
    cfg = config.get()
    
    if "printers" not in cfg:
        return False
    
    if printer_id < 0 or printer_id >= len(cfg["printers"]):
        return False
    
    printer = cfg["printers"][printer_id]
    
    if name is not None:
        printer["name"] = name
    
    if is_private is not None:
        printer["is_private"] = is_private
    
    if allowed_users is not None:
        printer["allowed_users"] = allowed_users
    
    config.save()
    config.load()
    
    return True


def add_allowed_user(printer_id: int, user_id: int) -> bool:
    """Add a user to the printer's allowed users list."""
    printer = config.get_printer(printer_id)
    if not printer:
        return False
    
    allowed = printer.get("allowed_users", [])
    if user_id not in allowed:
        allowed.append(user_id)
        return update_printer_settings(printer_id, allowed_users=allowed)
    
    return True


def remove_allowed_user(printer_id: int, user_id: int) -> bool:
    """Remove a user from the printer's allowed users list."""
    printer = config.get_printer(printer_id)
    if not printer:
        return False
    
    allowed = printer.get("allowed_users", [])
    if user_id in allowed:
        allowed.remove(user_id)
        return update_printer_settings(printer_id, allowed_users=allowed)
    
    return True


def set_printer_privacy(printer_id: int, is_private: bool) -> bool:
    """Set printer privacy setting."""
    return update_printer_settings(printer_id, is_private=is_private)


# ── Helper functions for Discord commands ─────────────────────────────────────

def get_accessible_printers_embed(user_id: int) -> Dict[str, Any]:
    """
    Get an embed describing all printers a user can access.
    Returns a dict suitable for Discord embed creation.
    """
    accessible = config.get_user_accessible_printers(user_id)
    
    if not accessible:
        return {
            "title": "🖨️ Your Printers",
            "description": "You don't have access to any printers yet.",
            "color": 0xFF0000,
        }
    
    lines = []
    for printer in accessible:
        pid = printer["id"]
        name = printer.get("name", f"Printer {pid}")
        perm_level = get_user_permission_level(user_id, pid)
        perm_emoji = format_permission_level(perm_level).split()[0]
        
        privacy = "🔒 Private" if printer.get("is_private", False) else "🌍 Public"
        lines.append(f"{perm_emoji} **{name}** - {privacy}")
    
    return {
        "title": "🖨️ Your Printers",
        "description": "\n".join(lines),
        "color": 0x00FF00,
    }


def get_printer_info_embed(printer_id: int, user_id: int) -> Dict[str, Any]:
    """
    Get an embed with detailed printer information.
    Returns a dict suitable for Discord embed creation.
    """
    printer = config.get_printer(printer_id)
    
    if not printer:
        return {
            "title": "❌ Printer Not Found",
            "description": "The specified printer doesn't exist.",
            "color": 0xFF0000,
        }
    
    if not config.can_view_printer(user_id, printer_id):
        return {
            "title": "🔒 Access Denied",
            "description": "You don't have permission to view this printer.",
            "color": 0xFF0000,
        }
    
    name = printer.get("name", f"Printer {printer_id}")
    perm_level = get_user_permission_level(user_id, printer_id)
    privacy = "🔒 Private" if printer.get("is_private", False) else "🌍 Public"
    
    # Connection info (only show to owners)
    connection_info = ""
    if config.is_printer_owner(user_id, printer_id):
        if printer.get("moonraker", {}).get("url"):
            connection_info = f"**Type:** Moonraker/Klipper\n**URL:** `{printer['moonraker']['url']}`\n"
        elif printer.get("octoprint", {}).get("url"):
            connection_info = f"**Type:** OctoPrint\n**URL:** `{printer['octoprint']['url']}`\n"
        elif printer.get("octoeverywhere", {}).get("key"):
            connection_info = f"**Type:** OctoEverywhere\n**Key:** `{printer['octoeverywhere']['key'][:8]}...`\n"
    
    # Owner info
    owner_id = printer.get("owner_id")
    owner_info = f"<@{owner_id}>" if owner_id else "Not set"
    
    # Allowed users
    allowed = printer.get("allowed_users", [])
    allowed_info = ", ".join([f"<@{uid}>" for uid in allowed]) if allowed else "None"
    
    return {
        "title": f"🖨️ {name}",
        "fields": [
            {"name": "Privacy", "value": privacy, "inline": True},
            {"name": "Your Access", "value": format_permission_level(perm_level), "inline": True},
            {"name": "\u200b", "value": "\u200b", "inline": True},
            {"name": "Owner", "value": owner_info, "inline": True},
            {"name": "Allowed Users", "value": allowed_info or "None", "inline": False},
        ] + ([{"name": "Connection", "value": connection_info, "inline": False}] if connection_info else []),
        "color": 0x0099FF,
    }
