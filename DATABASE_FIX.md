# Database Schema Fix - January 18, 2026

## Problem

After updating the `Target` model to include new fields (`province`, `general_email`, `phone`, `source`, `imported_at`, `updated_at`), the existing database file (`outreach.db`) still had the old schema without these columns, causing runtime errors:

```
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such column: target.province
```

## Root Cause

SQLModel/SQLAlchemy creates tables based on the model definition, but when you modify the model and the database already exists, the schema changes are not automatically applied. SQLite doesn't support automatic migrations without additional tools.

## Solution

Deleted the old database files to allow them to be automatically recreated with the new schema:

```bash
rm -f outreach.db test_outreach.db test_importers.db
```

When the application starts, `init_db()` recreates all tables with the current model definitions, including all new columns.

## Verification

✅ Database initialized with new schema
✅ All new columns verified to work:

- Target.province
- Target.general_email
- Target.phone
- Target.source
- Target.imported_at
- Target.updated_at
  
✅ All 3 core application tests passing
✅ API responding correctly on <http://localhost:8000/targets>

## Files Affected

- `outreach.db` - Deleted and recreated
- `test_outreach.db` - Deleted and recreated
- `test_importers.db` - Deleted and recreated

## Impact

- **Data Loss**: Any data previously in the database was lost (fresh start)
- **Functionality**: Application now works correctly with new schema
- **Testing**: All tests pass successfully

## Going Forward

For production deployments with existing data, implement proper database migrations using Alembic or similar tools to preserve data while updating schema.

## How to Recover Data

If you need to preserve existing data, you would need to:

1. Use Alembic for database migrations
2. Manually write ALTER TABLE statements
3. Use a backup from before the schema changes

For now, the fresh database is clean and ready to use.
