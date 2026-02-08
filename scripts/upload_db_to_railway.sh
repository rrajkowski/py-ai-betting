#!/bin/bash
# Upload local bets.db to Railway volume

echo "📤 Uploading bets.db to Railway..."
echo ""

# Step 1: Backup the existing Railway database (just in case)
echo "1️⃣ Backing up existing Railway database..."
railway ssh "cp /app/data/bets.db /app/data/bets.db.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true"

# Step 2: Copy local database to Railway via stdin
echo "2️⃣ Uploading local database (296 picks, 1.7MB)..."
cat bets.db | railway ssh "cat > /app/data/bets.db"

# Step 3: Verify the upload
echo "3️⃣ Verifying upload..."
railway ssh "ls -lh /app/data/bets.db"

# Step 4: Check record count
echo "4️⃣ Checking record count..."
railway ssh "python -c \"import sqlite3; conn = sqlite3.connect('/app/data/bets.db'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM ai_picks'); print('✅ AI Picks in Railway:', cursor.fetchone()[0]); conn.close()\""

echo ""
echo "✅ Upload complete!"

