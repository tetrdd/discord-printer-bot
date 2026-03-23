# Database Migrations

This directory contains SQL migration scripts for the Discord Printer Bot database.

## Schema Versions

| Version | Date | Description |
|---------|------|-------------|
| 001 | 2026-03-23 | Initial schema with users, printers, and printer_allowed_users tables |

## Applying Migrations

Migrations are applied automatically when the bot starts. The `db.py` module creates tables if they don't exist.

For manual migrations or schema inspection:

```bash
# Open the database
sqlite3 data/printers.db

# View current schema
.schema

# Apply a specific migration manually
sqlite3 data/printers.db < migrations/001_initial_schema.sql
```

## Adding New Migrations

When adding new columns or tables:

1. Create a new SQL file: `NNN_description.sql` (e.g., `002_add_printer_status.sql`)
2. Use `CREATE TABLE IF NOT EXISTS` and `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
3. Update this README with the new version
4. Update `db.py` to include the new schema changes

Example migration:

```sql
-- Migration: 002_add_printer_status
-- Date: 2026-03-24
-- Description: Add status tracking for printers

ALTER TABLE printers ADD COLUMN last_seen DATETIME;
ALTER TABLE printers ADD COLUMN status TEXT DEFAULT 'offline';
```

## Rollback

To rollback a migration:

1. Identify the migration to rollback
2. Create a rollback script or manually execute reverse SQL
3. Be careful with data loss!

Example rollback:

```sql
-- Rollback 002
ALTER TABLE printers DROP COLUMN last_seen;
ALTER TABLE printers DROP COLUMN status;
```

## Backup

Always backup your database before running migrations:

```bash
cp data/printers.db data/printers.db.backup
```
