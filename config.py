"""
Configuration loader and saver for Discord Printer Bot.
Reads config.yaml on startup, provides live save for settings changes.
Supports multi-printer configs with OctoEverywhere integration.
"""
from __future__ import annotations

import yaml
from pathlib import Path
from typing import Optional, Dict, List, Any

CONFIG_PATH = Path(__file__).parent / "config.yaml"

_cfg: Dict = {}
_printers: List[Dict] = []
_user_printers: Dict[int, int] = {}  # {user_id: printer_id}


def load() -> dict:
    """Load config from disk. Called once at startup."""
    global _cfg, _printers
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            "config.yaml not found! Copy config.yaml.example and fill in your values."
        )
    with open(CONFIG_PATH, encoding="utf-8") as f:
        _cfg = yaml.safe_load(f)
    _printers = _build_printer_list()
    return _cfg


def save():
    """Persist current config to disk."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(_cfg, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def get() -> dict:
    """Return the live config dict (mutable)."""
    return _cfg


# ── Printer list ──────────────────────────────────────────────────────────────

def _build_printer_list() -> list[dict]:
    """
    Build a normalized list of printers from config.
    Supports both single-printer and multi-printer configs.
    """
    if "printers" in _cfg:
        printers = []
        for i, p in enumerate(_cfg["printers"]):
            printers.append({
                "id": i,
                "name": p.get("name", f"Printer {i + 1}"),
                "moonraker": p.get("moonraker", {}),
                "octoprint": p.get("octoprint", {}),
                "octoeverywhere": p.get("octoeverywhere", {}),
                "camera": p.get("camera", {}),
                "owner_id": p.get("owner_id"),
                "is_private": p.get("is_private", False),
                "allowed_users": p.get("allowed_users", []),
            })
        return printers

    # Legacy single-printer config
    return [{
        "id": 0,
        "name": _cfg.get("printer_name", "Printer"),
        "moonraker": _cfg.get("moonraker", {}),
        "octoprint": _cfg.get("octoprint", {}),
        "octoeverywhere": _cfg.get("octoeverywhere", {}),
        "camera": _cfg.get("camera", {}),
        "owner_id": None,
        "is_private": False,
        "allowed_users": [],
    }]


def printers() -> list[dict]:
    """Return the list of configured printers."""
    return _printers


def is_multi_printer() -> bool:
    """True if more than one printer is configured."""
    return len(_printers) > 1


def get_printer(printer_id: int) -> Optional[dict]:
    """Get a printer config by its ID."""
    for p in _printers:
        if p["id"] == printer_id:
            return p
    return None


def default_printer() -> dict:
    """Return the first printer (fallback)."""
    return _printers[0] if _printers else {}


# ── Active printer per user ───────────────────────────────────────────────────

def active_printer_for(user_id: int) -> dict:
    """Get the active printer config for a user."""
    pid = _user_printers.get(user_id, 0)
    p = get_printer(pid)
    return p if p else default_printer()


def set_active_printer(user_id: int, printer_id: int):
    """Set which printer a user is controlling."""
    _user_printers[user_id] = printer_id


def active_printer_id(user_id: int) -> int:
    """Get the active printer ID for a user."""
    return _user_printers.get(user_id, 0)


def active_moonraker_url(user_id: int) -> str:
    """Moonraker URL for the user's active printer."""
    p = active_printer_for(user_id)
    return p.get("moonraker", {}).get("url", "").rstrip("/")


def active_api_key(user_id: int) -> str:
    """API key for the user's active printer."""
    p = active_printer_for(user_id)
    return p.get("moonraker", {}).get("api_key", "")


def active_octoprint_url(user_id: int) -> str:
    """OctoPrint URL for the user's active printer."""
    p = active_printer_for(user_id)
    return p.get("octoprint", {}).get("url", "").rstrip("/")


def active_octoprint_api_key(user_id: int) -> str:
    """OctoPrint API key for the user's active printer."""
    p = active_printer_for(user_id)
    return p.get("octoprint", {}).get("api_key", "")


def active_octoeverywhere_key(user_id: int) -> str:
    """OctoEverywhere key for the user's active printer."""
    p = active_printer_for(user_id)
    return p.get("octoeverywhere", {}).get("key", "")


def active_camera(user_id: int) -> dict:
    """Camera config for the user's active printer."""
    p = active_printer_for(user_id)
    return p.get("camera", {})


def active_printer_name(user_id: int) -> str:
    """Display name for the user's active printer."""
    p = active_printer_for(user_id)
    return p.get("name", "Printer")


# ── Permission system ─────────────────────────────────────────────────────────

def is_printer_owner(user_id: int, printer_id: int) -> bool:
    """Check if user is the owner of a printer."""
    printer = get_printer(printer_id)
    if not printer:
        return False
    owner_id = printer.get("owner_id")
    return owner_id is not None and owner_id == user_id


def is_printer_allowed(user_id: int, printer_id: int) -> bool:
    """Check if user is allowed to access a printer (owner or in allowed_users)."""
    printer = get_printer(printer_id)
    if not printer:
        return False
    
    # Owner always has access
    if is_printer_owner(user_id, printer_id):
        return True
    
    # Check allowed_users list
    allowed = printer.get("allowed_users", [])
    return user_id in allowed


def can_view_printer(user_id: int, printer_id: int) -> bool:
    """Check if user can view a printer (based on privacy settings)."""
    printer = get_printer(printer_id)
    if not printer:
        return False
    
    # Public printers are viewable by all
    if not printer.get("is_private", False):
        return True
    
    # Private printers require ownership or explicit allowance
    return is_printer_allowed(user_id, printer_id)


def can_control_printer(user_id: int, printer_id: int) -> bool:
    """Check if user can control a printer (owner or allowed user)."""
    return is_printer_allowed(user_id, printer_id)


def can_change_settings(user_id: int, printer_id: int) -> bool:
    """Check if user can change printer settings (owner only)."""
    return is_printer_owner(user_id, printer_id)


def get_user_accessible_printers(user_id: int) -> list[dict]:
    """Get all printers a user can access."""
    accessible = []
    for printer in _printers:
        pid = printer["id"]
        if can_view_printer(user_id, pid):
            accessible.append(printer)
    return accessible


def get_user_controllable_printers(user_id: int) -> list[dict]:
    """Get all printers a user can control."""
    controllable = []
    for printer in _printers:
        pid = printer["id"]
        if can_control_printer(user_id, pid):
            controllable.append(printer)
    return accessible


def get_user_owned_printers(user_id: int) -> list[dict]:
    """Get all printers owned by a user."""
    owned = []
    for printer in _printers:
        if printer.get("owner_id") == user_id:
            owned.append(printer)
    return owned


# ── Discord-specific config ───────────────────────────────────────────────────

def discord_token() -> str:
    """Get Discord bot token."""
    return _cfg.get("discord", {}).get("bot_token", "")


def allowed_roles() -> list[int]:
    """Get list of Discord role IDs that can use the bot."""
    return _cfg.get("discord", {}).get("allowed_role_ids", [])


def admin_ids() -> list[int]:
    """Get list of Discord user IDs that are bot admins."""
    return _cfg.get("discord", {}).get("admin_ids", [])


def is_bot_admin(user_id: int) -> bool:
    """Check if user is a bot admin."""
    return user_id in admin_ids()


# ── Settings ──────────────────────────────────────────────────────────────────

def temp_presets() -> dict:
    """Get temperature presets."""
    return _cfg.get("temp_presets", {})


def macros_config() -> dict:
    """Get macros configuration."""
    return _cfg.get("macros", {})


def files_config() -> dict:
    """Get files configuration."""
    return _cfg.get("files", {})


def monitoring_config() -> dict:
    """Get monitoring configuration."""
    return _cfg.get("monitoring", {})
