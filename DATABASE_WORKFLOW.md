# Database Workflow Guide

## Overview

The production database (`bets.db`) is tracked in git to persist data on Streamlit Cloud (which has ephemeral filesystem). This guide explains how to work with the database safely.

## Key Concepts

- **Production Database**: Lives in git and on Streamlit Cloud
- **Local Database**: Your local copy for testing
- **Important**: Local changes should NOT be committed unless you want to update production

## Common Workflows

### 1. Testing Locally (Most Common)

When testing locally, your changes to `bets.db` will NOT affect production:

```bash
# Run app locally
streamlit run streamlit_app.py

# Generate test picks, modify data, etc.
# These changes stay local only
```

**To undo local changes and restore production version:**
```bash
./scripts/restore_production_db.sh
# OR manually:
git restore bets.db
```

### 2. Updating Production Database

Only do this when you want to push local changes to production:

```bash
# 1. Verify your local changes
sqlite3 bets.db "SELECT COUNT(*) FROM ai_picks"

# 2. Add and commit
git add bets.db
git commit -m "Update production database: [describe changes]"
git push

# 3. Wait 2-3 minutes for Streamlit Cloud to redeploy
```

### 3. Checking Database Status

**Check if you have local changes:**
```bash
git status
# If bets.db is listed, you have uncommitted changes
```

**View local database stats:**
```bash
sqlite3 bets.db "SELECT 
    COUNT(*) as total_picks,
    SUM(CASE WHEN result = 'Win' THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN result = 'Loss' THEN 1 ELSE 0 END) as losses,
    SUM(CASE WHEN result = 'Pending' THEN 1 ELSE 0 END) as pending
FROM ai_picks"
```

### 4. Creating Backups

**Manual backup:**
```bash
cp bets.db "bets_backup_$(date +%Y%m%d_%H%M%S).db"
```

**Automatic backup (before restoring):**
```bash
./scripts/restore_production_db.sh
# Creates backup automatically before restoring
```

## Important Notes

⚠️ **DO NOT** commit `bets.db` unless you want to update production

⚠️ **DO NOT** use `git add .` or `git add -A` without checking `git status` first

✅ **DO** use `git restore bets.db` to undo local changes

✅ **DO** create backups before making major changes

## Troubleshooting

### Problem: Production database is empty after deployment

**Cause**: `bets.db` was removed from git or not committed

**Solution**:
```bash
# Make sure bets.db is tracked
git add bets.db
git commit -m "Restore production database"
git push
```

### Problem: Local changes accidentally committed

**Solution**:
```bash
# Revert the commit (if not pushed yet)
git reset HEAD~1

# OR if already pushed, revert the commit
git revert HEAD
git push
```

### Problem: Database corrupted

**Solution**:
```bash
# Restore from backup
cp bets_backup_YYYYMMDD_HHMMSS.db bets.db

# OR restore from git
git restore bets.db
```

## Database Schema

### Tables

1. **ai_picks**: AI-generated picks with results
2. **bets**: Manual bet tracking
3. **prompt_context**: Scraped context data
4. **historical_games**: Cached historical game data

### Viewing Data

```bash
# Open SQLite shell
sqlite3 bets.db

# View all picks
SELECT * FROM ai_picks ORDER BY date DESC LIMIT 10;

# View performance by sport
SELECT sport, result, COUNT(*) 
FROM ai_picks 
GROUP BY sport, result 
ORDER BY sport, result;

# Exit
.quit
```

## Scripts

- `scripts/restore_production_db.sh` - Restore production database from git
- `scripts/sync_database.py` - Database sync utilities (deprecated)
- `scripts/encode_db_for_secrets.py` - Encode database for secrets (not used - DB too large)
- `scripts/upload_db_to_production.sh` - Upload database to production (deprecated)

## Future: Migrate to Cloud Database

For better scalability, consider migrating to:
- **Supabase** (PostgreSQL, free tier, 500MB)
- **PlanetScale** (MySQL, free tier, 1GB)
- **Neon** (PostgreSQL, free tier, 3GB)

This would eliminate the need to track `bets.db` in git.

