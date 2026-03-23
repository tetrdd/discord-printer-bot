"""
Database wrapper for Discord Printer Bot.
Handles SQLite database operations for user and printer data.
Centralized per-bot printer configuration.
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger("PrinterBot")

DB_PATH = Path(__file__).parent / "data" / "printers.db"


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory."""
    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Initialize database tables."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                discord_id INTEGER PRIMARY KEY,
                timezone TEXT,
                language TEXT,
                notify_channel TEXT,
                active_printer_id INTEGER
            )
        ''')
        
        # Check for user columns (migration)
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'active_printer_id' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN active_printer_id INTEGER")

        # Printers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS printers (
                printer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_discord_id INTEGER,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                url TEXT NOT NULL,
                api_key TEXT,
                privacy TEXT CHECK(privacy IN ('public','private')),
                creation_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                camera_url TEXT,
                stream_url TEXT,
                FOREIGN KEY (owner_discord_id) REFERENCES users(discord_id)
            )
        ''')
        
        # Check for printer columns (migration)
        cursor.execute("PRAGMA table_info(printers)")
        p_columns = [column[1] for column in cursor.fetchall()]
        if 'camera_url' not in p_columns:
            cursor.execute("ALTER TABLE printers ADD COLUMN camera_url TEXT")
        if 'stream_url' not in p_columns:
            cursor.execute("ALTER TABLE printers ADD COLUMN stream_url TEXT")

        # Printer allowed users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS printer_allowed_users (
                printer_id INTEGER,
                user_discord_id INTEGER,
                PRIMARY KEY (printer_id, user_discord_id),
                FOREIGN KEY (printer_id) REFERENCES printers(printer_id),
                FOREIGN KEY (user_discord_id) REFERENCES users(discord_id)
            )
        ''')
        
        # Temperature presets table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS temp_presets (
                preset_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_discord_id INTEGER,
                name TEXT NOT NULL,
                hotend_temp INTEGER NOT NULL,
                bed_temp INTEGER NOT NULL,
                FOREIGN KEY (user_discord_id) REFERENCES users(discord_id)
            )
        ''')

        # Index for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_printers_owner 
            ON printers(owner_discord_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_allowed_users 
            ON printer_allowed_users(user_discord_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_temp_presets_user
            ON temp_presets(user_discord_id)
        ''')

        conn.commit()
        
    logger.info("Database initialized successfully")


# ── User Operations ───────────────────────────────────────────────────────────

def get_user(discord_id: int) -> Optional[Dict[str, Any]]:
    """Get user information by Discord ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE discord_id = ?", (discord_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def create_user(
    discord_id: int,
    timezone: Optional[str] = None,
    language: Optional[str] = None,
    notify_channel: Optional[str] = None,
) -> bool:
    """Create a new user or update if exists."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO users (discord_id, timezone, language, notify_channel)
                VALUES (?, ?, ?, ?)
            ''', (discord_id, timezone, language, notify_channel))

            # If inserted, add default presets
            if cursor.rowcount > 0:
                _add_default_presets(discord_id, cursor)

            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Failed to create user: {e}")
            return False


def _add_default_presets(user_id: int, cursor: sqlite3.Cursor):
    """Add default temperature presets for a new user."""
    defaults = [
        ('PLA', 200, 60),
        ('PETG', 230, 80),
        ('ABS', 250, 100),
        ('Cooldown', 0, 0)
    ]
    cursor.executemany('''
        INSERT INTO temp_presets (user_discord_id, name, hotend_temp, bed_temp)
        VALUES (?, ?, ?, ?)
    ''', [(user_id, name, hot, bed) for name, hot, bed in defaults])


def update_user(
    discord_id: int,
    timezone: Optional[str] = None,
    language: Optional[str] = None,
    notify_channel: Optional[str] = None,
    active_printer_id: Optional[int] = None,
) -> bool:
    """Update user information."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        updates = []
        values = []
        
        if timezone is not None:
            updates.append("timezone = ?")
            values.append(timezone)
        if language is not None:
            updates.append("language = ?")
            values.append(language)
        if notify_channel is not None:
            updates.append("notify_channel = ?")
            values.append(notify_channel)
        if active_printer_id is not None:
            updates.append("active_printer_id = ?")
            values.append(active_printer_id)
        
        if not updates:
            return False
        
        values.append(discord_id)
        
        query = f"UPDATE users SET {', '.join(updates)} WHERE discord_id = ?"
        cursor.execute(query, values)
        conn.commit()
        return cursor.rowcount > 0


def ensure_user_exists(discord_id: int) -> bool:
    """Ensure a user exists in the database, create if not."""
    user = get_user(discord_id)
    if user:
        # Check if they have presets, if not add defaults (migration for existing users)
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM temp_presets WHERE user_discord_id = ? LIMIT 1", (discord_id,))
            if not cursor.fetchone():
                _add_default_presets(discord_id, cursor)
                conn.commit()
        return True
    return create_user(discord_id)


# ── Active Printer Management ────────────────────────────────────────────────

def get_active_printer_id(user_id: int) -> Optional[int]:
    """Get the active printer ID for a user."""
    user = get_user(user_id)
    if not user:
        return None

    active_id = user.get('active_printer_id')

    # If no active printer set, but user has accessible ones, pick the first one
    if active_id is None:
        printers = get_accessible_printers(user_id)
        if printers:
            active_id = printers[0]['printer_id']
            update_user(user_id, active_printer_id=active_id)

    return active_id


def get_active_printer(user_id: int) -> Optional[Dict[str, Any]]:
    """Get the active printer configuration for a user."""
    printer_id = get_active_printer_id(user_id)
    if printer_id is None:
        return None
    return get_printer(printer_id)


def set_active_printer(user_id: int, printer_id: int) -> bool:
    """Set the active printer for a user."""
    # Verify user has access to this printer
    if not user_can_view(user_id, printer_id):
        return False

    return update_user(user_id, active_printer_id=printer_id)


# ── Temperature Presets ──────────────────────────────────────────────────────

def get_temp_presets(user_id: int) -> List[Dict[str, Any]]:
    """Get all temperature presets for a user."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM temp_presets
            WHERE user_discord_id = ?
            ORDER BY name
        ''', (user_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def add_temp_preset(user_id: int, name: str, hotend: int, bed: int) -> int:
    """Add a new temperature preset."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO temp_presets (user_discord_id, name, hotend_temp, bed_temp)
            VALUES (?, ?, ?, ?)
        ''', (user_id, name, hotend, bed))
        conn.commit()
        return cursor.lastrowid


def delete_temp_preset(preset_id: int, user_id: int) -> bool:
    """Delete a temperature preset."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM temp_presets WHERE preset_id = ? AND user_discord_id = ?",
            (preset_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0


# ── Printer Operations ────────────────────────────────────────────────────────

def create_printer(
    owner_discord_id: int,
    name: str,
    printer_type: str,  # 'moonraker', 'octoprint', 'octoeverywhere'
    url: str,
    api_key: Optional[str] = None,
    privacy: str = 'public',
    camera_url: Optional[str] = None,
    stream_url: Optional[str] = None,
) -> int:
    """
    Create a new printer.
    Returns the new printer_id.
    """
    if privacy not in ('public', 'private'):
        raise ValueError("Privacy must be 'public' or 'private'")
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO printers (owner_discord_id, name, type, url, api_key, privacy, camera_url, stream_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (owner_discord_id, name, printer_type, url, api_key, privacy, camera_url, stream_url))
        conn.commit()
        printer_id = cursor.lastrowid

        # If this is the user's first printer, make it active
        user = get_user(owner_discord_id)
        if user and user.get('active_printer_id') is None:
            cursor.execute(
                "UPDATE users SET active_printer_id = ? WHERE discord_id = ?",
                (printer_id, owner_discord_id)
            )
            conn.commit()

        logger.info(f"Created printer {printer_id}: {name}")
        return printer_id


def get_printer(printer_id: int) -> Optional[Dict[str, Any]]:
    """Get printer by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM printers WHERE printer_id = ?", (printer_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_printer_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Get printer by name."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM printers WHERE name = ?", (name,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_printer(
    printer_id: int,
    name: Optional[str] = None,
    printer_type: Optional[str] = None,
    url: Optional[str] = None,
    api_key: Optional[str] = None,
    privacy: Optional[str] = None,
    camera_url: Optional[str] = None,
    stream_url: Optional[str] = None,
) -> bool:
    """Update printer information."""
    if privacy is not None and privacy not in ('public', 'private'):
        raise ValueError("Privacy must be 'public' or 'private'")
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        updates = []
        values = []
        
        if name is not None:
            updates.append("name = ?")
            values.append(name)
        if printer_type is not None:
            updates.append("type = ?")
            values.append(printer_type)
        if url is not None:
            updates.append("url = ?")
            values.append(url)
        if api_key is not None:
            updates.append("api_key = ?")
            values.append(api_key)
        if privacy is not None:
            updates.append("privacy = ?")
            values.append(privacy)
        if camera_url is not None:
            updates.append("camera_url = ?")
            values.append(camera_url)
        if stream_url is not None:
            updates.append("stream_url = ?")
            values.append(stream_url)
        
        if not updates:
            return False
        
        values.append(printer_id)
        
        query = f"UPDATE printers SET {', '.join(updates)} WHERE printer_id = ?"
        cursor.execute(query, values)
        conn.commit()
        
        if cursor.rowcount > 0:
            logger.info(f"Updated printer {printer_id}")
            return True
        return False


def delete_printer(printer_id: int) -> bool:
    """Delete a printer and its allowed users."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Unset as active printer for any users
        cursor.execute(
            "UPDATE users SET active_printer_id = NULL WHERE active_printer_id = ?",
            (printer_id,)
        )

        # Delete allowed users first (foreign key constraint)
        cursor.execute(
            "DELETE FROM printer_allowed_users WHERE printer_id = ?",
            (printer_id,)
        )
        
        # Delete printer
        cursor.execute("DELETE FROM printers WHERE printer_id = ?", (printer_id,))
        conn.commit()
        
        if cursor.rowcount > 0:
            logger.info(f"Deleted printer {printer_id}")
            return True
        return False


def get_printers_by_owner(owner_discord_id: int) -> List[Dict[str, Any]]:
    """Get all printers owned by a user."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM printers 
            WHERE owner_discord_id = ? 
            ORDER BY name
        ''', (owner_discord_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_accessible_printers(user_discord_id: int) -> List[Dict[str, Any]]:
    """
    Get all printers accessible by a user.
    Includes owned printers, private printers where user is allowed,
    and all public printers.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT p.* FROM printers p
            LEFT JOIN printer_allowed_users pau 
                ON p.printer_id = pau.printer_id
            WHERE p.owner_discord_id = ? 
               OR pau.user_discord_id = ?
               OR p.privacy = 'public'
            ORDER BY p.name
        ''', (user_discord_id, user_discord_id))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_controllable_printers(user_discord_id: int) -> List[Dict[str, Any]]:
    """
    Get all printers a user can control.
    Includes owned printers and private printers where user is allowed.
    Does NOT include public printers the user doesn't own.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT p.* FROM printers p
            LEFT JOIN printer_allowed_users pau 
                ON p.printer_id = pau.printer_id
            WHERE p.owner_discord_id = ? 
               OR pau.user_discord_id = ?
            ORDER BY p.name
        ''', (user_discord_id, user_discord_id))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def user_can_control(user_discord_id: int, printer_id: int) -> bool:
    """Check if user can control a printer (owner or allowed user)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 1 FROM printers
            WHERE printer_id = ? 
            AND (owner_discord_id = ? 
                 OR printer_id IN (
                     SELECT printer_id FROM printer_allowed_users 
                     WHERE user_discord_id = ?
                 ))
        ''', (printer_id, user_discord_id, user_discord_id))
        return cursor.fetchone() is not None


def user_can_view(user_discord_id: int, printer_id: int) -> bool:
    """Check if user can view a printer."""
    printer = get_printer(printer_id)
    if not printer:
        return False
    
    # Public printers are viewable by all
    if printer['privacy'] == 'public':
        return True
    
    # Private printers require ownership or explicit allowance
    return user_can_control(user_discord_id, printer_id)


def is_printer_owner(user_discord_id: int, printer_id: int) -> bool:
    """Check if user is the owner of a printer."""
    printer = get_printer(printer_id)
    return printer and printer['owner_discord_id'] == user_discord_id


# ── Allowed Users Operations ──────────────────────────────────────────────────

def add_allowed_user(printer_id: int, user_discord_id: int) -> bool:
    """Add a user to the printer's allowed users list."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO printer_allowed_users (printer_id, user_discord_id)
                VALUES (?, ?)
            ''', (printer_id, user_discord_id))
            conn.commit()
            logger.info(f"Added user {user_discord_id} to printer {printer_id}")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"User {user_discord_id} already allowed on printer {printer_id}")
            return False


def remove_allowed_user(printer_id: int, user_discord_id: int) -> bool:
    """Remove a user from the printer's allowed users list."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM printer_allowed_users 
            WHERE printer_id = ? AND user_discord_id = ?
        ''', (printer_id, user_discord_id))
        conn.commit()
        
        if cursor.rowcount > 0:
            logger.info(f"Removed user {user_discord_id} from printer {printer_id}")
            return True
        return False


def get_allowed_users(printer_id: int) -> List[int]:
    """Get list of allowed user Discord IDs for a printer."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_discord_id FROM printer_allowed_users 
            WHERE printer_id = ?
            ORDER BY user_discord_id
        ''', (printer_id,))
        rows = cursor.fetchall()
        return [row[0] for row in rows]


def is_user_allowed(user_discord_id: int, printer_id: int) -> bool:
    """Check if a user is in the allowed users list for a printer."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 1 FROM printer_allowed_users 
            WHERE printer_id = ? AND user_discord_id = ?
        ''', (printer_id, user_discord_id))
        return cursor.fetchone() is not None


# ── Utility Functions ─────────────────────────────────────────────────────────

def get_all_printers() -> List[Dict[str, Any]]:
    """Get all printers in the database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM printers ORDER BY name")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_all_users() -> List[Dict[str, Any]]:
    """Get all users in the database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY discord_id")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def count_printers() -> int:
    """Get total number of printers."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM printers")
        return cursor.fetchone()[0]


def count_users() -> int:
    """Get total number of users."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        return cursor.fetchone()[0]


def delete_user(discord_id: int) -> bool:
    """Delete a user and clean up related data."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Delete user's printers
        cursor.execute(
            "DELETE FROM printer_allowed_users WHERE printer_id IN (SELECT printer_id FROM printers WHERE owner_discord_id = ?)",
            (discord_id,)
        )
        cursor.execute("DELETE FROM printers WHERE owner_discord_id = ?", (discord_id,))

        # Delete from allowed_users
        cursor.execute(
            "DELETE FROM printer_allowed_users WHERE user_discord_id = ?",
            (discord_id,)
        )
        
        # Delete from temp_presets
        cursor.execute(
            "DELETE FROM temp_presets WHERE user_discord_id = ?",
            (discord_id,)
        )

        # Delete user
        cursor.execute("DELETE FROM users WHERE discord_id = ?", (discord_id,))
        conn.commit()
        
        if cursor.rowcount > 0:
            logger.info(f"Deleted user {discord_id}")
            return True
        return False


# Initialize database on module load
init_db()
