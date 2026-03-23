"""
Printer API client for Discord Printer Bot.
Supports Moonraker (Klipper), OctoPrint, and OctoEverywhere for remote access.
"""
from __future__ import annotations

import logging
import urllib.parse
import aiohttp
from typing import Optional, Dict, List, Any

import config

logger = logging.getLogger("PrinterBot.api")

_TIMEOUT = aiohttp.ClientTimeout(total=10)


def _get_printer_type(user_id: int) -> str:
    """Determine which API to use for the user's active printer."""
    p = config.active_printer_for(user_id)
    if p.get("octoeverywhere", {}).get("key"):
        return "octoeverywhere"
    elif p.get("octoprint", {}).get("url"):
        return "octoprint"
    else:
        return "moonraker"


def _get_base_url(user_id: int) -> str:
    """Get the base URL for the user's active printer."""
    printer_type = _get_printer_type(user_id)
    p = config.active_printer_for(user_id)
    
    if printer_type == "octoeverywhere":
        # OctoEverywhere uses a cloud proxy
        key = p.get("octoeverywhere", {}).get("key", "")
        return f"https://api.octoeverywhere.com/api/{key}"
    elif printer_type == "octoprint":
        return p.get("octoprint", {}).get("url", "").rstrip("/")
    else:
        return p.get("moonraker", {}).get("url", "").rstrip("/")


def _get_headers(user_id: int) -> dict:
    """Get headers for API requests."""
    printer_type = _get_printer_type(user_id)
    p = config.active_printer_for(user_id)
    
    headers = {"Content-Type": "application/json"}
    
    if printer_type == "octoeverywhere":
        # OctoEverywhere uses the key in the URL
        pass
    elif printer_type == "octoprint":
        api_key = p.get("octoprint", {}).get("api_key", "")
        if api_key:
            headers["X-Api-Key"] = api_key
    else:
        api_key = p.get("moonraker", {}).get("api_key", "")
        if api_key:
            headers["X-Api-Key"] = api_key
    
    return headers


async def _get(endpoint: str, user_id: int) -> Optional[dict]:
    """GET request to printer API."""
    base = _get_base_url(user_id)
    url = f"{base}{endpoint}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=_get_headers(user_id),
                timeout=_TIMEOUT,
            ) as r:
                return await r.json() if r.status == 200 else None
    except Exception as e:
        logger.error(f"GET {endpoint}: {e}")
        return None


async def _post(endpoint: str, data: dict = None, user_id: int = None) -> Optional[dict]:
    """POST request to printer API."""
    base = _get_base_url(user_id)
    url = f"{base}{endpoint}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=_get_headers(user_id),
                json=data or {},
                timeout=_TIMEOUT,
            ) as r:
                return await r.json() if r.status == 200 else None
    except Exception as e:
        logger.error(f"POST {endpoint}: {e}")
        return None


async def _delete(endpoint: str, user_id: int) -> Optional[dict]:
    """DELETE request to printer API."""
    base = _get_base_url(user_id)
    url = f"{base}{endpoint}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                url,
                headers=_get_headers(user_id),
                timeout=_TIMEOUT,
            ) as r:
                return await r.json() if r.status == 200 else None
    except Exception as e:
        logger.error(f"DELETE {endpoint}: {e}")
        return None


async def _post_command(command: str, user_id: int) -> bool:
    """Send a command to the printer (works for both Moonraker and OctoPrint)."""
    printer_type = _get_printer_type(user_id)
    
    if printer_type == "octoprint":
        # OctoPrint API
        data = {"command": "gcode", "script": command}
        result = await _post("/api/printer/comm", data, user_id)
        return result is not None
    else:
        # Moonraker/OctoEverywhere
        encoded = urllib.parse.quote(command)
        result = await _post(f"/printer/gcode/script?script={encoded}", user_id)
        return result is not None


# ── High-level queries ────────────────────────────────────────────────────────

async def printer_status(user_id: int) -> Optional[dict]:
    """Get print stats, progress, temperatures in one call."""
    printer_type = _get_printer_type(user_id)
    
    if printer_type == "octoprint":
        # OctoPrint API
        data = await _get("/api/job", user_id)
        if not data:
            return None
        
        # Get temperatures separately
        temps = await _get("/api/printer", user_id)
        
        result = {
            "state": data.get("state", "unknown"),
            "progress": data.get("progress", 0),
            "file": data.get("job", {}).get("file", {}).get("name", ""),
            "estimated_time": data.get("job", {}).get("estimatedPrintTime", 0),
            "elapsed_time": data.get("progress", {}).get("printTime", 0),
        }
        
        if temps:
            result["temperatures"] = temps.get("temperature", {})
        
        return result
    else:
        # Moonraker/OctoEverywhere
        data = await _get(
            "/printer/objects/query?print_stats&display_status&virtual_sdcard"
            "&extruder&heater_bed&gcode_move&fan",
            user_id,
        )
        if not data:
            return None
        return data.get("result", {}).get("status", {})


async def file_list(user_id: int) -> List[dict]:
    """Get list of gcode files."""
    printer_type = _get_printer_type(user_id)
    
    if printer_type == "octoprint":
        data = await _get("/api/files/local", user_id)
        if not data:
            return []
        files = data.get("files", [])
        return [f for f in files if f.get("origin") == "local" and f.get("name", "").endswith(".gcode")]
    else:
        data = await _get("/server/files/list?root=gcodes", user_id)
        if not data:
            return []
        return data.get("result", [])


async def file_metadata(filename: str, user_id: int) -> Optional[dict]:
    """Get metadata for a specific gcode file."""
    printer_type = _get_printer_type(user_id)
    
    if printer_type == "octoprint":
        data = await _get(f"/api/files/local/{filename}", user_id)
        return data
    else:
        encoded = urllib.parse.quote(filename, safe="")
        data = await _get(f"/server/files/metadata?filename={encoded}", user_id)
        if not data:
            return None
        return data.get("result")


async def start_print(filename: str, user_id: int) -> bool:
    """Start a print job."""
    printer_type = _get_printer_type(user_id)
    
    if printer_type == "octoprint":
        data = {"command": "select", "print": True}
        result = await _post(f"/api/files/local/{filename}", data, user_id)
        return result is not None
    else:
        encoded = urllib.parse.quote(filename, safe="")
        result = await _post(f"/printer/print/start?filename={encoded}", user_id)
        return result is not None


async def pause_print(user_id: int) -> bool:
    """Pause the current print."""
    printer_type = _get_printer_type(user_id)
    
    if printer_type == "octoprint":
        data = {"command": "pause"}
        result = await _post("/api/job", data, user_id)
        return result is not None
    else:
        result = await _post("/printer/print/pause", user_id)
        return result is not None


async def resume_print(user_id: int) -> bool:
    """Resume a paused print."""
    printer_type = _get_printer_type(user_id)
    
    if printer_type == "octoprint":
        data = {"command": "resume"}
        result = await _post("/api/job", data, user_id)
        return result is not None
    else:
        result = await _post("/printer/print/resume", user_id)
        return result is not None


async def cancel_print(user_id: int) -> bool:
    """Cancel the current print."""
    printer_type = _get_printer_type(user_id)
    
    if printer_type == "octoprint":
        data = {"command": "cancel"}
        result = await _post("/api/job", data, user_id)
        return result is not None
    else:
        result = await _post("/printer/print/cancel", user_id)
        return result is not None


async def emergency_stop(user_id: int) -> bool:
    """Emergency stop the printer."""
    printer_type = _get_printer_type(user_id)
    
    if printer_type == "octoprint":
        # OctoPrint doesn't have a direct emergency stop
        # We'll send M112 which is the emergency stop G-code
        return await _post_command("M112", user_id)
    else:
        result = await _post("/printer/emergency_stop", user_id)
        return result is not None


async def delete_file(filename: str, user_id: int) -> bool:
    """Delete a file."""
    printer_type = _get_printer_type(user_id)
    
    if printer_type == "octoprint":
        result = await _delete(f"/api/files/local/{filename}", user_id)
        return result is not None
    else:
        encoded = urllib.parse.quote(filename, safe="")
        result = await _delete(f"/server/files/gcodes/{encoded}", user_id)
        return result is not None


async def server_info(user_id: int) -> Optional[dict]:
    """Get server information."""
    printer_type = _get_printer_type(user_id)
    
    if printer_type == "octoprint":
        return await _get("/api/version", user_id)
    else:
        data = await _get("/server/info", user_id)
        return data.get("result") if data else None


async def print_history(limit: int = 20, user_id: int = None) -> List[dict]:
    """Get print history."""
    printer_type = _get_printer_type(user_id)
    
    if printer_type == "octoprint":
        # OctoPrint doesn't have a built-in history API
        # Would need a plugin like PrintHistory
        return []
    else:
        data = await _get(f"/server/history/list?limit={limit}&order=desc", user_id)
        if not data:
            return []
        return data.get("result", {}).get("jobs", [])


async def bed_mesh_status(user_id: int) -> Optional[dict]:
    """Get bed mesh profile data (Moonraker only)."""
    printer_type = _get_printer_type(user_id)
    
    if printer_type == "octoprint":
        return None
    
    data = await _get("/printer/objects/query?bed_mesh", user_id)
    if not data:
        return None
    return data.get("result", {}).get("status", {}).get("bed_mesh")


async def get_macros(user_id: int) -> List[str]:
    """Get list of available macros (Moonraker only)."""
    printer_type = _get_printer_type(user_id)
    
    if printer_type == "octoprint":
        return []
    
    data = await _get("/printer/objects/list", user_id)
    if not data:
        return []
    
    objects = data.get("result", {}).get("objects", [])
    macros = []
    for obj in objects:
        if obj.startswith("gcode_macro ") and not obj.startswith("gcode_macro _"):
            macros.append(obj.replace("gcode_macro ", ""))
    
    return macros


# ── Control commands ──────────────────────────────────────────────────────────

async def gcode(cmd: str, user_id: int) -> bool:
    """Send a G-code command."""
    return await _post_command(cmd, user_id)


async def set_speed_factor(pct: int, user_id: int) -> bool:
    """Set speed override percentage."""
    return await gcode(f"M220 S{pct}", user_id)


async def set_flow_factor(pct: int, user_id: int) -> bool:
    """Set flow override percentage."""
    return await gcode(f"M221 S{pct}", user_id)


async def set_fan_speed(pct: int, user_id: int) -> bool:
    """Set fan speed percentage."""
    val = int(255 * pct / 100)
    return await gcode(f"M106 S{val}", user_id)


async def adjust_z_offset(offset: float, user_id: int) -> bool:
    """Adjust Z-offset."""
    return await gcode(f"SET_GCODE_OFFSET Z_ADJUST={offset:.3f} MOVE=1", user_id)


async def reset_z_offset(user_id: int) -> bool:
    """Reset Z-offset to zero."""
    return await gcode("SET_GCODE_OFFSET Z=0 MOVE=1", user_id)


async def home_axes(axes: str = "XYZ", user_id: int = None) -> bool:
    """Home specified axes."""
    return await gcode(f"G28 {axes}", user_id)


async def motors_off(user_id: int) -> bool:
    """Disable all motors."""
    return await gcode("M84", user_id)


async def set_hotend_temp(temp: float, user_id: int) -> bool:
    """Set hotend temperature."""
    return await gcode(f"M104 S{temp}", user_id)


async def set_bed_temp(temp: float, user_id: int) -> bool:
    """Set bed temperature."""
    return await gcode(f"M140 S{temp}", user_id)


async def wait_for_hotend(temp: float, user_id: int) -> bool:
    """Wait for hotend to reach temperature."""
    return await gcode(f"M109 S{temp}", user_id)


async def wait_for_bed(temp: float, user_id: int) -> bool:
    """Wait for bed to reach temperature."""
    return await gcode(f"M190 S{temp}", user_id)


# ── Camera ────────────────────────────────────────────────────────────────────

async def snapshot(user_id: int) -> Optional[bytes]:
    """Fetch camera snapshot image bytes."""
    p = config.active_printer_for(user_id)
    cam = p.get("camera", {})
    url = cam.get("snapshot_url", "")
    
    if not url:
        return None
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status == 200:
                    return await r.read()
    except Exception as e:
        logger.error(f"Snapshot: {e}")
    return None


async def get_stream_url(user_id: int) -> Optional[str]:
    """Get the camera stream URL."""
    p = config.active_printer_for(user_id)
    cam = p.get("camera", {})
    return cam.get("stream_url", "")
