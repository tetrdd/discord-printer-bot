"""
Permission system for Discord Printer Bot.
Handles printer ownership, access control, and privacy settings.
Uses SQLite database for persistence.
"""
from __future__ import annotations

from typing import Optional, List, Dict, Any
import db


class PermissionError(Exception):
    """Raised when a user doesn't have permission for an action."""
    pass


def check_view_permission(user_id: int, printer_id: Optional[int]) -> bool:
    """
    Check if user can view a printer.
    Returns True if allowed, raises PermissionError if not.
    """
    if printer_id is None:
        raise PermissionError("No printer selected. Use /register-printer to add one.")

    if not db.user_can_view(user_id, printer_id):
        printer = db.get_printer(printer_id)
        printer_name = printer.get("name", f"Printer {printer_id}") if printer else "Unknown"
        raise PermissionError(f"You don't have permission to view {printer_name}")
    return True


def check_control_permission(user_id: int, printer_id: Optional[int]) -> bool:
    """
    Check if user can control a printer.
    Returns True if allowed, raises PermissionError if not.
    """
    if printer_id is None:
        raise PermissionError("No printer selected. Use /register-printer to add one.")

    if not db.user_can_control(user_id, printer_id):
        printer = db.get_printer(printer_id)
        printer_name = printer.get("name", f"Printer {printer_id}") if printer else "Unknown"
        raise PermissionError(f"You don't have permission to control {printer_name}")
    return True


def check_owner_permission(user_id: int, printer_id: Optional[int]) -> bool:
    """
    Check if user is the owner of a printer.
    Returns True if owner, raises PermissionError if not.
    """
    if printer_id is None:
        raise PermissionError("No printer selected.")

    if not db.is_printer_owner(user_id, printer_id):
        printer = db.get_printer(printer_id)
        printer_name = printer.get("name", f"Printer {printer_id}") if printer else "Unknown"
        raise PermissionError(f"Only the owner can perform this action on {printer_name}")
    return True


def get_user_permission_level(user_id: int, printer_id: int) -> str:
    """
    Get the user's permission level for a printer.
    Returns: 'owner', 'allowed', 'view_only', or 'none'
    """
    if db.is_printer_owner(user_id, printer_id):
        return "owner"
    elif db.is_user_allowed(user_id, printer_id):
        return "allowed"
    elif db.user_can_view(user_id, printer_id):
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
