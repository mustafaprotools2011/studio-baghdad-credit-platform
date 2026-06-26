#!/usr/bin/env python3
"""
MUSTAFA MIXING — Database Upgrade v2.1
=======================================
Adds:
  - mustafa_role TEXT column (summary of Mustafa's role extracted from exact_credit)
  - youtube_url TEXT column
  - video_duration INTEGER column
  - thumbnail_url TEXT column
Marks duplicate track #16 (Adam Ayyad) as is_duplicate_of=#13, is_active=0.
Preserves ALL existing data — only additive schema changes.
"""

import sqlite3
import os
import re
import hashlib
import shutil
from datetime import datetime

BASE = "/opt/data/mustafa-mixing-archive"
DB_PATH = os.path.join(BASE, "mustafa_mixing.db")


def extract_mustafa_role(exact_credit):
    """Parse exact_credit text and return a concise Arabic summary of Mustafa's role."""
    if not exact_credit:
        return None

    text = exact_credit.strip()

    roles = []
    # Order matters: more specific patterns must come before generic ones
    # so re.search doesn't match substrings first (e.g. إشراف عام before إشراف)
    patterns = [
        (r'إشراف\s*عام', 'إشراف عام'),
        (r'تأليف\s*موسيقي', 'تأليف موسيقي'),
        (r'ألحان', 'ألحان'),
        (r'توزيع', 'توزيع'),
        (r'هندسة\s*الصوت', 'هندسة صوت'),
        (r'هندسة\s*صوت', 'هندسة صوت'),
        (r'ماستر(?:ينغ|نك)?', 'ماسترينغ'),
        (r'مكس', 'ميكساج'),
        (r'ميكس', 'ميكساج'),
        (r'إنتاج', 'إنتاج'),
        (r'إشراف', 'إشراف'),
        (r'بيز\s*كيتار', 'عزف (بيز)'),
        (r'تشيلو', 'عزف (تشيلو)'),
        (r'جيللو', 'عزف (تشيلو)'),
        (r'cello', 'عزف (تشيلو)'),
    ]

    # Find all non-overlapping matches (priority to earlier patterns)
    matched_spans = []  # (start, end, label)
    for pattern, label in patterns:
        for m in re.finditer(pattern, text):
            start, end = m.start(), m.end()
            # Skip if this span is entirely inside an already-matched span (more specific already won)
            if any(s <= start and end <= e for s, e, _ in matched_spans):
                continue
            # Remove any existing spans that are entirely inside this new span
            matched_spans = [(s, e, l) for s, e, l in matched_spans if not (start <= s and e <= end)]
            matched_spans.append((start, end, label))

    seen = set()
    for _, _, label in sorted(matched_spans, key=lambda x: x[0]):  # sort by position in text
        if label not in seen:
            roles.append(label)
            seen.add(label)

    if not roles:
        # Fallback: return first 60 chars of credit as summary
        return text[:60] + "…" if len(text) > 60 else text

    return " | ".join(roles)


def extract_youtube_info(exact_credit, source_url):
    """
    Extract youtube_url, duration, and thumbnail from source_url if it's a YouTube link.
    Also returns None for duration/thumbnail (to be filled later via API or manual entry).
    """
    youtube_url = None
    if source_url and ('youtube.com/watch' in source_url or 'youtu.be/' in source_url):
        youtube_url = source_url
    return youtube_url, None, None  # duration & thumbnail set via API later


def upgrade_schema(conn):
    """Add new columns if they don't exist (safe, no data loss)."""
    existing_cols = [row[1] for row in conn.execute("PRAGMA table_info(tracks)").fetchall()]

    additions = []
    if 'mustafa_role' not in existing_cols:
        conn.execute("ALTER TABLE tracks ADD COLUMN mustafa_role TEXT")
        additions.append('mustafa_role')
    if 'youtube_url' not in existing_cols:
        conn.execute("ALTER TABLE tracks ADD COLUMN youtube_url TEXT")
        additions.append('youtube_url')
    if 'video_duration' not in existing_cols:
        conn.execute("ALTER TABLE tracks ADD COLUMN video_duration INTEGER")
        additions.append('video_duration')
    if 'thumbnail_url' not in existing_cols:
        conn.execute("ALTER TABLE tracks ADD COLUMN thumbnail_url TEXT")
        additions.append('thumbnail_url')

    return additions


def populate_mustafa_role(conn):
    """Fill mustafa_role from exact_credit for all tracks where it's NULL."""
    cur = conn.execute("SELECT id, exact_credit, source_url FROM tracks WHERE mustafa_role IS NULL")
    updated = 0
    for row in cur.fetchall():
        track_id, exact_credit, source_url = row
        role_summary = extract_mustafa_role(exact_credit)
        conn.execute("UPDATE tracks SET mustafa_role = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                     (role_summary, track_id))
        updated += 1
    conn.commit()
    return updated


def populate_youtube_info(conn):
    """Copy source_url → youtube_url for YouTube links where youtube_url is NULL."""
    cur = conn.execute("SELECT id, source_url FROM tracks WHERE youtube_url IS NULL AND source_url IS NOT NULL")
    updated = 0
    for row in cur.fetchall():
        track_id, source_url = row
        if 'youtube.com/watch' in source_url or 'youtu.be/' in source_url:
            conn.execute("UPDATE tracks SET youtube_url = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                         (source_url, track_id))
            updated += 1
    conn.commit()
    return updated


def handle_duplicate_track16(conn):
    """
    Track #16 "Adam Ayyad (duplicate credit)" is a duplicate of track #13 "Adam Ayyad".
    Mark it as inactive and point is_duplicate_of to track #13.
    """
    track13 = conn.execute("SELECT id, title, source_url FROM tracks WHERE id = 13").fetchone()
    track16 = conn.execute("SELECT id, title, source_url FROM tracks WHERE id = 16").fetchone()

    if not track16:
        print("  ℹ️  Track #16 not found (already removed?)")
        return

    if track16[2] and track13 and track16[2] == track13[2]:
        print(f"  ℹ️  Track #16 already points to same source_url as #13 — no action needed")
        return

    conn.execute("""
        UPDATE tracks
        SET is_duplicate_of = 13,
            is_active = 0,
            verification_status = 'duplicate',
            verification_notes = 'Duplicate of track #13 (Adam Ayyad). Same artist (Adam Ayyad), same exact_credit text, different YouTube URL.',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = 16
    """)
    conn.commit()
    return True


def verify_foreign_keys(conn):
    """Check foreign key integrity for tracks.artist_id."""
    print("\n🔍 FOREIGN KEY INTEGRITY CHECK")
    print("=" * 50)

    # Check tracks referencing non-existent artists
    bad = conn.execute("""
        SELECT t.id, t.title, t.artist_id
        FROM tracks t
        LEFT JOIN artists a ON t.artist_id = a.id
        WHERE a.id IS NULL
    """).fetchall()

    if bad:
        print(f"  ❌ {len(bad)} track(s) with dangling artist_id references:")
        for b in bad:
            print(f"     Track #{b[0]} '{b[1]}' → artist_id={b[2]} (NOT FOUND)")
        return False
    else:
        print("  ✅ All tracks have valid artist_id references.")

    # Check orphaned artists (no tracks)
    orphans = conn.execute("""
        SELECT a.id, a.name FROM artists a
        LEFT JOIN tracks t ON t.artist_id = a.id
        WHERE t.id IS NULL
    """).fetchall()
    if orphans:
        print(f"  ℹ️  {len(orphans)} artist(s) with no tracks (orphaned, non-critical):")
        for o in orphans:
            print(f"     Artist #{o[0]}: {o[1]}")
    else:
        print("  ✅ All artists have at least one track.")

    # Check album FK integrity
    bad_albums = conn.execute("""
        SELECT t.id, t.title, t.album_id
        FROM tracks t
        LEFT JOIN albums a ON t.album_id = a.id
        WHERE t.album_id IS NOT NULL AND a.id IS NULL
    """).fetchall()
    if bad_albums:
        print(f"  ❌ {len(bad_albums)} track(s) with dangling album_id references")
        for b in bad_albums:
            print(f"     Track #{b[0]} → album_id={b[2]} (NOT FOUND)")
        return False
    else:
        print("  ✅ All album_id references are valid (or NULL).")

    # Check is_duplicate_of FK
    bad_dup = conn.execute("""
        SELECT t.id, t.title, t.is_duplicate_of
        FROM tracks t
        LEFT JOIN tracks d ON t.is_duplicate_of = d.id
        WHERE t.is_duplicate_of IS NOT NULL AND d.id IS NULL
    """).fetchall()
    if bad_dup:
        print(f"  ❌ {len(bad_dup)} track(s) pointing to non-existent duplicate target")
        for b in bad_dup:
            print(f"     Track #{b[0]} → is_duplicate_of={b[2]} (NOT FOUND)")
        return False
    else:
        print("  ✅ All is_duplicate_of references are valid.")

    return True


def create_backup(conn):
    """Create a JSON backup before making changes."""
    from datetime import datetime
    import json

    backup_dir = os.path.join(BASE, "backups")
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"pre_upgrade_v2.1_{timestamp}.json")

    # Export tracks with full data
    rows = conn.execute("""
        SELECT t.*, a.name as artist_name
        FROM tracks t
        JOIN artists a ON t.artist_id = a.id
        ORDER BY t.id
    """).fetchall()
    columns = [desc[0] for desc in conn.execute("""
        SELECT t.*, a.name as artist_name
        FROM tracks t
        JOIN artists a ON t.artist_id = a.id
        ORDER BY t.id
    """).description]

    data = {
        "archive": "MUSTAFA MIXING - Pre-Upgrade Backup v2.1",
        "backup_date": timestamp,
        "tracks": [dict(zip(columns, row)) for row in rows],
        "artists": [dict(row) for row in conn.execute("SELECT * FROM artists ORDER BY id").fetchall()],
    }

    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    md5 = hashlib.md5(open(backup_path, 'rb').read()).hexdigest()
    size = os.path.getsize(backup_path)

    conn.execute("""
        INSERT INTO backups (backup_type, file_path, record_count, size_bytes, md5_hash)
        VALUES (?, ?, ?, ?, ?)
    """, ('pre_upgrade_v2.1', backup_path, len(rows), size, md5))
    conn.commit()

    return backup_path


def print_stats(conn):
    """Print database summary after upgrade."""
    stats = conn.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN is_active=1 THEN 1 ELSE 0 END) as active,
            SUM(CASE WHEN is_active=0 THEN 1 ELSE 0 END) as inactive,
            SUM(CASE WHEN is_duplicate_of IS NOT NULL THEN 1 ELSE 0 END) as duplicates,
            COUNT(DISTINCT artist_id) as artists,
            SUM(CASE WHEN youtube_url IS NOT NULL THEN 1 ELSE 0 END) as with_youtube,
            SUM(CASE WHEN mustafa_role IS NOT NULL THEN 1 ELSE 0 END) as with_role
        FROM tracks
    """).fetchone()

    print("\n📊 POST-UPGRADE STATS:")
    print(f"   Total tracks:        {stats[0]}")
    print(f"   Active tracks:       {stats[1]}")
    print(f"   Inactive (dupes):    {stats[2]}")
    print(f"   Marked as dup:       {stats[3]}")
    print(f"   Unique artists:      {stats[4]}")
    print(f"   With youtube_url:    {stats[5]}")
    print(f"   With mustafa_role:   {stats[6]}")


def main():
    print("=" * 60)
    print("MUSTAFA MIXING — Database Upgrade v2.1")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    # Step 1: Backup
    print("\n📦 Creating pre-upgrade backup...")
    backup_path = create_backup(conn)
    print(f"   ✅ Backup saved: {backup_path}")

    # Step 2: Add new columns
    print("\n📐 Adding new columns to tracks table...")
    additions = upgrade_schema(conn)
    if additions:
        print(f"   ✅ Added columns: {', '.join(additions)}")
    else:
        print("   ℹ️  All new columns already exist — no schema changes needed")

    # Step 3: Duplicate track #16 → mark as inactive
    print("\n🔀 Handling duplicate track #16 (Adam Ayyad)...")
    dup_handled = handle_duplicate_track16(conn)
    if dup_handled:
        print("   ✅ Track #16 marked as duplicate of #13, deactivated")
    else:
        print("   ℹ️  No duplicate action needed")

    # Step 4: Populate mustafa_role from exact_credit
    print("\n📝 Extracting mustafa_role from exact_credit...")
    updated_roles = populate_mustafa_role(conn)
    print(f"   ✅ Populated mustafa_role for {updated_roles} track(s)")

    # Step 5: Copy source_url → youtube_url for YouTube links
    print("\n🔗 Populating youtube_url from source_url...")
    updated_youtube = populate_youtube_info(conn)
    print(f"   ✅ Set youtube_url for {updated_youtube} track(s)")

    # Step 6: Verify foreign keys
    fk_ok = verify_foreign_keys(conn)

    # Step 7: Print final stats
    print_stats(conn)

    # Step 8: Show mustafa_role content sample
    print("\n📋 SAMPLE mustafa_role values:")
    samples = conn.execute("""
        SELECT id, title, exact_credit, mustafa_role
        FROM tracks WHERE is_active=1 ORDER BY id LIMIT 5
    """).fetchall()
    for s in samples:
        print(f"   #{s['id']} {s['title']}")
        print(f"     credit: {s['exact_credit'][:60]}…")
        print(f"     role:   {s['mustafa_role']}")
        print()

    conn.close()

    print("=" * 60)
    print("✅ Database upgrade v2.1 complete!")
    if not fk_ok:
        print("⚠️  Foreign key issues found — see details above.")
    print("=" * 60)


if __name__ == "__main__":
    main()
