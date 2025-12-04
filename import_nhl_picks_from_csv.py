#!/usr/bin/env python3
"""
Import NHL picks from CSV export and add them to the database.
This script reads the CSV export and inserts NHL picks into bets.db.
"""

from app.db import get_db
import sys
import os
import csv
import sqlite3
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))


def parse_confidence(confidence_str):
    """Convert star emoji string to numeric confidence (3-5)."""
    if not confidence_str:
        return 3
    star_count = confidence_str.count('⭐')
    return max(3, min(5, star_count))  # Clamp to 3-5 range


def import_picks_from_csv(csv_path):
    """Import picks from CSV export file."""

    if not os.path.exists(csv_path):
        print(f"❌ Error: CSV file not found at '{csv_path}'")
        return 0

    conn = get_db()
    cur = conn.cursor()

    # Read existing picks to avoid duplicates
    cur.execute("SELECT game, pick, market FROM ai_picks")
    existing_picks = {(row[0], row[1], row[2]) for row in cur.fetchall()}

    imported = 0
    skipped = 0

    print(f"\n📂 Reading CSV: {csv_path}")
    print("="*60)

    with open(csv_path, 'r', encoding='utf-8-sig') as f:  # utf-8-sig to handle BOM
        reader = csv.DictReader(f)  # Default delimiter is comma

        for row in reader:
            sport = row.get('sport', '').strip()

            # Only import NHL picks
            if sport != 'NHL':
                continue

            game = row.get('game', '').strip()
            pick = row.get('pick', '').strip()
            market = row.get('market', '').strip()
            line = row.get('line', '').strip()
            odds = row.get('odds_american', '').strip()
            result = row.get('result', 'Pending').strip()
            confidence_str = row.get('confidence', '').strip()
            commence_time = row.get('date', '').strip()

            # Skip if already exists
            if (game, pick, market) in existing_picks:
                print(f"⏭️  SKIP: {game} - {pick} ({market}) - Already exists")
                skipped += 1
                continue

            # Parse values
            confidence = parse_confidence(confidence_str)

            try:
                line_value = float(line) if line else None
            except ValueError:
                line_value = None

            try:
                odds_value = int(odds) if odds else None
            except ValueError:
                odds_value = None

            # Insert into database
            try:
                cur.execute("""
                    INSERT INTO ai_picks 
                    (date, sport, game, pick, market, line, odds_american, result, confidence, reasoning, commence_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    commence_time,  # date
                    sport,
                    game,
                    pick,
                    market,
                    line_value,
                    odds_value,
                    result,
                    str(confidence),
                    f"Imported from CSV export on {datetime.now().strftime('%Y-%m-%d')}",
                    commence_time
                ))

                print(f"✅ IMPORT: {game}")
                print(f"   Pick: {pick} ({market})")
                print(f"   Confidence: {'⭐' * confidence}")
                print(f"   Result: {result}")
                print()

                imported += 1

            except Exception as e:
                print(f"❌ ERROR importing {game}: {e}")
                continue

    conn.commit()
    conn.close()

    print("="*60)
    print(f"✅ Import complete!")
    print(f"   Imported: {imported} picks")
    print(f"   Skipped: {skipped} picks (already exist)")
    print("="*60)

    return imported


def verify_import():
    """Verify the imported picks are in the database."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM ai_picks WHERE sport = 'NHL'")
    nhl_count = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(*) FROM ai_picks WHERE sport = 'NHL' AND result = 'Pending'")
    pending_count = cur.fetchone()[0]

    print("\n📊 Database Status:")
    print(f"   Total NHL picks: {nhl_count}")
    print(f"   Pending NHL picks: {pending_count}")

    if pending_count > 0:
        print("\n🔍 Pending NHL picks:")
        cur.execute("""
            SELECT game, pick, market, confidence, commence_time 
            FROM ai_picks 
            WHERE sport = 'NHL' AND result = 'Pending'
            ORDER BY commence_time
        """)
        for row in cur.fetchall():
            game, pick, market, confidence, commence_time = row
            print(f"   - {game}")
            print(f"     Pick: {pick} ({market}) - {'⭐' * int(confidence)}")
            print(f"     Date: {commence_time}")

    conn.close()


if __name__ == "__main__":
    csv_path = "/Users/rubenrajkowski/Sites/py-ai-betting/2025-12-04T01-05_export.csv"

    print("\n" + "="*60)
    print("NHL PICKS CSV IMPORT TOOL")
    print("="*60)

    imported = import_picks_from_csv(csv_path)

    if imported > 0:
        verify_import()
        print("\n✅ NHL picks imported successfully!")
        print("\n📝 Next steps:")
        print("   1. Commit the updated bets.db to git")
        print("   2. Push to GitHub")
        print("   3. Streamlit Cloud will auto-deploy")
        print("   4. Picks will be graded automatically on next page load")
    else:
        print("\n⚠️  No new picks were imported")
