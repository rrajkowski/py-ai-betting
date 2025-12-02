#!/bin/bash
# Restore production database from git (undo local changes)
# Use this if you accidentally modify bets.db locally and want to restore the production version

set -e

echo "================================================================================"
echo "RESTORE PRODUCTION DATABASE FROM GIT"
echo "================================================================================"
echo ""
echo "This will:"
echo "  1. Discard any local changes to bets.db"
echo "  2. Restore the production version from git"
echo ""

# Check if there are local changes
if git diff --quiet bets.db && git diff --cached --quiet bets.db; then
    echo "✅ No local changes detected. Database is already in sync with production."
    exit 0
fi

echo "⚠️  Local changes detected in bets.db"
echo ""

# Show what will be lost
echo "Current local database stats:"
sqlite3 bets.db "SELECT 
    COUNT(*) as total_picks,
    SUM(CASE WHEN result = 'Win' THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN result = 'Loss' THEN 1 ELSE 0 END) as losses,
    SUM(CASE WHEN result = 'Pending' THEN 1 ELSE 0 END) as pending
FROM ai_picks" 2>/dev/null || echo "Unable to read database"

echo ""
read -p "⚠️  This will DISCARD local changes. Continue? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cancelled."
    exit 1
fi

# Create backup before restoring
timestamp=$(date +%Y%m%d_%H%M%S)
backup_file="bets_local_backup_${timestamp}.db"
cp bets.db "$backup_file"
echo "✅ Local backup created: $backup_file"

# Restore from git
git restore bets.db

echo ""
echo "================================================================================"
echo "✅ SUCCESS! Production database restored from git"
echo "================================================================================"
echo ""
echo "Production database stats:"
sqlite3 bets.db "SELECT 
    COUNT(*) as total_picks,
    SUM(CASE WHEN result = 'Win' THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN result = 'Loss' THEN 1 ELSE 0 END) as losses,
    SUM(CASE WHEN result = 'Pending' THEN 1 ELSE 0 END) as pending
FROM ai_picks"
echo ""
echo "Your local changes were backed up to: $backup_file"
echo ""

