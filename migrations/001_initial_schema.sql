-- Migration: 001_initial_schema
-- Date: 2026-03-23
-- Description: Initial database schema for centralized printer configuration

-- Users table
CREATE TABLE IF NOT EXISTS users (
    discord_id INTEGER PRIMARY KEY,
    timezone TEXT,
    language TEXT,
    notify_channel TEXT
);

-- Printers table
CREATE TABLE IF NOT EXISTS printers (
    printer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_discord_id INTEGER,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    url TEXT NOT NULL,
    api_key TEXT,
    privacy TEXT CHECK(privacy IN ('public','private')),
    creation_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_discord_id) REFERENCES users(discord_id)
);

-- Printer allowed users table (many-to-many)
CREATE TABLE IF NOT EXISTS printer_allowed_users (
    printer_id INTEGER,
    user_discord_id INTEGER,
    PRIMARY KEY (printer_id, user_discord_id),
    FOREIGN KEY (printer_id) REFERENCES printers(printer_id),
    FOREIGN KEY (user_discord_id) REFERENCES users(discord_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_printers_owner ON printers(owner_discord_id);
CREATE INDEX IF NOT EXISTS idx_allowed_users ON printer_allowed_users(user_discord_id);
