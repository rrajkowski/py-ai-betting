#!/usr/bin/env python3
"""
Test script to verify database migration for source column
"""
import sqlite3
from app.db import init_ai_picks, get_db

print("🔧 Testing database migration...")

# Initialize the database
init_ai_picks()
print("✅ Database initialized")

# Check if source column exists
conn = get_db()
cur = conn.cursor()
cur.execute("PRAGMA table_info(ai_picks)")
columns = [row['name'] for row in cur.fetchall()]
conn.close()

print(f"\n📋 Columns in ai_picks table:")
for col in columns:
    print(f"  - {col}")

if 'source' in columns:
    print("\n✅ SUCCESS: 'source' column exists!")
else:
    print("\n❌ ERROR: 'source' column is missing!")

if 'commence_time' in columns:
    print("✅ SUCCESS: 'commence_time' column exists!")
else:
    print("❌ ERROR: 'commence_time' column is missing!")

print("\n🎉 Database migration test complete!")

