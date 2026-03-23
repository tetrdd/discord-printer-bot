#!/usr/bin/env python3
"""
Migration script: config.yaml → SQLite database.
Imports existing printer configurations from config.yaml into the new SQLite database.

Usage:
    python migrate_from_yaml.py

This script:
1. Reads config.yaml
2. Creates user entries for all printer owners
3. Imports all printers into the database
4. Preserves privacy settings and allowed users
"""
from __future__ import annotations

import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import yaml
import db

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("Migration")

CONFIG_PATH = Path(__file__).parent / "config.yaml"


def migrate():
    """Run the migration from config.yaml to SQLite."""
    
    # Check if config.yaml exists
    if not CONFIG_PATH.exists():
        logger.error("config.yaml not found!")
        logger.error("Please ensure config.yaml exists in the bot directory.")
        sys.exit(1)
    
    # Load config
    logger.info(f"Loading {CONFIG_PATH}...")
    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # Get printers list
    printers = config.get("printers", [])
    
    if not printers:
        # Check for legacy single-printer config
        if config.get("moonraker") or config.get("octoprint") or config.get("octoeverywhere"):
            logger.info("Found legacy single-printer configuration")
            printers = [{
                "name": config.get("printer_name", "Printer"),
                "moonraker": config.get("moonraker", {}),
                "octoprint": config.get("octoprint", {}),
                "octoeverywhere": config.get("octoeverywhere", {}),
                "camera": config.get("camera", {}),
                "owner_id": config.get("owner_id"),
                "is_private": config.get("is_private", False),
                "allowed_users": config.get("allowed_users", []),
            }]
        else:
            logger.warning("No printers found in config.yaml")
            logger.info("Migration complete (no printers to migrate)")
            return
    
    logger.info(f"Found {len(printers)} printer(s) to migrate")
    
    # Track migration stats
    migrated_count = 0
    user_ids = set()
    
    for i, printer in enumerate(printers):
        logger.info(f"\nMigrating printer {i + 1}/{len(printers)}: {printer.get('name', 'Unknown')}")
        
        # Get owner ID
        owner_id = printer.get("owner_id")
        if owner_id:
            user_ids.add(owner_id)
            # Ensure user exists
            db.ensure_user_exists(owner_id)
            logger.info(f"  → Ensured user {owner_id} exists")
        
        # Determine printer type and URL
        printer_type = None
        url = None
        api_key = None
        
        if printer.get("moonraker"):
            printer_type = "moonraker"
            url = printer["moonraker"].get("url", "")
            api_key = printer["moonraker"].get("api_key", "")
        elif printer.get("octoprint"):
            printer_type = "octoprint"
            url = printer["octoprint"].get("url", "")
            api_key = printer["octoprint"].get("api_key", "")
        elif printer.get("octoeverywhere"):
            printer_type = "octoeverywhere"
            url = ""
            api_key = printer["octoeverywhere"].get("key", "")
        
        if not printer_type:
            logger.warning(f"  ⚠️  Skipping: No valid connection type found")
            continue
        
        if not url and printer_type != "octoeverywhere":
            logger.warning(f"  ⚠️  Skipping: No URL found for {printer_type}")
            continue
        
        # Get privacy setting
        is_private = printer.get("is_private", False)
        privacy = "private" if is_private else "public"
        
        # Create printer in database
        try:
            printer_id = db.create_printer(
                owner_discord_id=owner_id or 0,
                name=printer.get("name", f"Printer {i + 1}"),
                printer_type=printer_type,
                url=url or "",
                api_key=api_key or None,
                privacy=privacy,
            )
            logger.info(f"  ✓ Created printer ID {printer_id}")
            migrated_count += 1
            
            # Add allowed users
            allowed_users = printer.get("allowed_users", [])
            for user_id in allowed_users:
                if user_id:
                    user_ids.add(user_id)
                    db.ensure_user_exists(user_id)
                    db.add_allowed_user(printer_id, user_id)
                    logger.info(f"  → Added allowed user {user_id}")
            
        except Exception as e:
            logger.error(f"  ✗ Failed to create printer: {e}")
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Migration Summary")
    logger.info("=" * 60)
    logger.info(f"Printers migrated: {migrated_count}/{len(printers)}")
    logger.info(f"Users created/updated: {len(user_ids)}")
    
    if migrated_count > 0:
        logger.info("\n✓ Migration completed successfully!")
        logger.info("\nNext steps:")
        logger.info("1. Verify printers with /list-printers in Discord")
        logger.info("2. Remove 'printers:' section from config.yaml")
        logger.info("3. Keep only discord token and presets in config.yaml")
    else:
        logger.warning("\n⚠️  No printers were migrated. Check the logs for errors.")


if __name__ == "__main__":
    migrate()
