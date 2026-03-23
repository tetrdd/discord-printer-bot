"""
Database handler for Discord Printer Bot.
Handles SQLite database operations for user and printer data.
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger("PrinterBot")

DB_PATH = Path(__file__).parent / "users.db"

class Database:
    """SQLite database wrapper for user and printer management."""
    
    def __init__(self):
        self.conn = None
        self.create_tables()
    
    def connect(self):
        """Connect to the database."""
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        return self.conn
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def create_tables(self):
        """Create database tables if they don't exist."""
        with self.connect() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    discord_id INTEGER PRIMARY KEY,
                    timezone TEXT,
                    language TEXT,
                    notification_prefs TEXT
                )
            ''')
            
            # Printers table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS printers (
                    printer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_discord_id INTEGER,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    url TEXT NOT NULL,
                    api_key TEXT,
                    privacy TEXT DEFAULT 'public',
                    creation_timestamp INTEGER DEFAULT (strftime('%s', 'now')),
                    FOREIGN KEY (owner_discord_id) REFERENCES users(discord_id)
                )
            ''')
            
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
            
            conn.commit()
    
    def get_user(self, discord_id: int) -> Optional[Dict[str, Any]]:
        """Get user information by Discord ID."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE discord_id = ?", (discord_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def create_user(self, discord_id: int, **kwargs) -> bool:
        """Create a new user."""
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO users (discord_id, timezone, language, notification_prefs)
                    VALUES (?, ?, ?, ?)
                ''', (discord_id, kwargs.get('timezone'), kwargs.get('language'), kwargs.get('notification_prefs')))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False
    
    def update_user(self, discord_id: int, **kwargs) -> bool:
        """Update user information."""
        with self.connect() as conn:
            cursor = conn.cursor()
            fields = []
            values = []
            
            for key, value in kwargs.items():
                fields.append(f"{key} = ?")
                values.append(value)
            
            if not fields:
                return False
            
            values.append(discord_id)
            
            query = f"UPDATE users SET {', '.join(fields)} WHERE discord_id = ?"
            cursor.execute(query, values)
            conn.commit()
            return cursor.rowcount > 0
    
    def get_printer_by_id(self, printer_id: int) -> Optional[Dict[str, Any]]:
        """Get printer information by ID."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.*, u.timezone, u.language 
                FROM printers p 
                LEFT JOIN users u ON p.owner_discord_id = u.discord_id 
                WHERE p.printer_id = ?
            ''', (printer_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_printer_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get printer information by name."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.*, u.timezone, u.language 
                FROM printers p 
                LEFT JOIN users u ON p.owner_discord_id = u.discord_id 
                WHERE p.name = ?
            ''', (name,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_printers_by_owner(self, owner_id: int) -> List[Dict[str, Any]]:
        """Get all printers owned by a user."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.*, u.timezone, u.language 
                FROM printers p 
                LEFT JOIN users u ON p.owner_discord_id = u.discord_id 
                WHERE p.owner_discord_id = ?
                ORDER BY p.name
            ''', (owner_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_printers_accessible_by_user(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all printers accessible by a user (owned or allowed)."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT p.*, u.timezone, u.language 
                FROM printers p 
                LEFT JOIN users u ON p.owner_discord_id = u.discord_id 
                LEFT JOIN printer_allowed_users pau ON p.printer_id = pau.printer_id 
                WHERE p.owner_discord_id = ? OR pau.user_discord_id = ?
                ORDER BY p.name
            ''', (user_id, user_id))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def create_printer(self, owner_id: int, name: str, type: str, url: str, api_key: Optional[str] = None) -> int:
        """Create a new printer."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO printers (owner_discord_id, name, type, url, api_key)
                VALUES (?, ?, ?, ?, ?)
            ''', (owner_id, name, type, url, api_key))
            conn.commit()
            return cursor.lastrowid
    
    def update_printer(self, printer_id: int, **kwargs) -> bool:
        """Update printer information."""
        with self.connect() as conn:
            cursor = conn.cursor()
            fields = []
            values = []
            
            for key, value in kwargs.items():
                fields.append(f"{key} = ?")
                values.append(value)
            
            if not fields:
                return False
            
            values.append(printer_id)
            
            query = f"UPDATE printers SET {', '.join(fields)} WHERE printer_id = ?"
            cursor.execute(query, values)
            conn.commit()
            return cursor.rowcount > 0
    
    def set_printer_privacy(self, printer_id: int, privacy: str) -> bool:
        """Set printer privacy setting."""
        if privacy not in ['public', 'private']:
            return False
        
        return self.update_printer(printer_id, privacy=privacy)
    
    def add_allowed_user(self, printer_id: int, user_id: int) -> bool:
        """Add a user to the allowed users list."""
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO printer_allowed_users (printer_id, user_discord_id)
                    VALUES (?, ?)
                ''', (printer_id, user_id))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False
    
    def remove_allowed_user(self, printer_id: int, user_id: int) -> bool:
        """Remove a user from the allowed users list."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM printer_allowed_users 
                WHERE printer_id = ? AND user_discord_id = ?
            ''', (printer_id, user_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_allowed_users(self, printer_id: int) -> List[int]:
        """Get list of allowed users for a printer."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_discord_id FROM printer_allowed_users 
                WHERE printer_id = ?
            ''', (printer_id,))
            rows = cursor.fetchall()
            return [row[0] for row in rows]
    
    def delete_printer(self, printer_id: int) -> bool:
        """Delete a printer."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM printers WHERE printer_id = ?", (printer_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_user(self, discord_id: int) -> bool:
        """Delete a user and their printers."""
        with self.connect() as conn:
            cursor = conn.cursor()
            # Delete allowed users entries
            cursor.execute("DELETE FROM printer_allowed_users WHERE user_discord_id = ?", (discord_id,))
            # Delete printers
            cursor.execute("DELETE FROM printers WHERE owner_discord_id = ?", (discord_id,))
            # Delete user
            cursor.execute("DELETE FROM users WHERE discord_id = ?", (discord_id,))
            conn.commit()
            return True

# Create a global database instance
db = Database()