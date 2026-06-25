#!/usr/bin/env python3
"""
MUSTAFA MIXING — Database Upgrade v2.0
Migrates JSON → SQLite (single source of truth)
Preserves all existing data
"""

import json
import sqlite3
import os
import hashlib
from datetime import datetime

BASE = "/opt/data/mustafa-mixing-archive"
DB_PATH = os.path.join(BASE, "mustafa_mixing.db")
JSON_PATH = os.path.join(BASE, "credits_database.json")
EVIDENCE_DIR = os.path.join(BASE, "evidence")

def init_schema(conn):
    """Create the full schema with all required tables."""
    conn.executescript("""
    PRAGMA journal_mode=WAL;
    PRAGMA foreign_keys=ON;

    -- Artists table (normalized)
    CREATE TABLE IF NOT EXISTS artists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        name_arabic TEXT,
        country TEXT,
        is_mustafa INTEGER DEFAULT 0,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(name)
    );

    -- Albums table
    CREATE TABLE IF NOT EXISTS albums (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        artist_id INTEGER REFERENCES artists(id),
        release_year INTEGER,
        label TEXT,
        upc TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Tracks (the core credit table)
    CREATE TABLE IF NOT EXISTS tracks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        title_arabic TEXT,
        artist_id INTEGER REFERENCES artists(id),
        album_id INTEGER REFERENCES albums(id),
        release_year INTEGER,
        country TEXT,
        genre TEXT,
        isrc TEXT,
        duration_seconds INTEGER,
        
        -- Mustafa's roles on this track (flags)
        role_mixing INTEGER DEFAULT 0,
        role_mastering INTEGER DEFAULT 0,
        role_recording INTEGER DEFAULT 0,
        role_arranging INTEGER DEFAULT 0,
        role_composing INTEGER DEFAULT 0,
        role_producing INTEGER DEFAULT 0,
        role_executive_prod INTEGER DEFAULT 0,
        role_sound_engineer INTEGER DEFAULT 0,
        role_performer TEXT,
        
        -- Credit text
        exact_credit TEXT,
        
        -- Source info
        source_url TEXT,
        platform TEXT,
        label TEXT,
        
        -- Publisher & Rights
        publisher TEXT,
        copyright_owner TEXT,
        master_owner TEXT,
        
        -- Confidence & Verification
        confidence_score INTEGER DEFAULT 50,
        confidence_level TEXT DEFAULT 'Unknown'
            CHECK(confidence_level IN ('Verified','Likely','Possible','Rejected','Unknown')),
        verification_status TEXT,
        verification_notes TEXT,
        
        -- Legal
        contract_status TEXT,
        ownership_notes TEXT,
        legal_comments TEXT,
        neighbouring_rights TEXT,
        royalty_notes TEXT,
        
        -- Metadata
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        -- Soft delete / duplicate tracking
        is_duplicate_of INTEGER REFERENCES tracks(id),
        is_active INTEGER DEFAULT 1,
        
        UNIQUE(source_url)
    );

    -- Additional collaborators (many-to-many)
    CREATE TABLE IF NOT EXISTS collaborators (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        name_arabic TEXT,
        role TEXT,
        track_id INTEGER REFERENCES tracks(id),
        UNIQUE(name, role, track_id)
    );

    -- Role history (what roles Mustafa played per track — normalized)
    CREATE TABLE IF NOT EXISTS roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        track_id INTEGER REFERENCES tracks(id),
        role_name TEXT NOT NULL,
        role_arabic TEXT,
        confidence INTEGER DEFAULT 100,
        UNIQUE(track_id, role_name)
    );

    -- Evidence files
    CREATE TABLE IF NOT EXISTS evidence (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        track_id INTEGER REFERENCES tracks(id),
        file_type TEXT,
        file_path TEXT,
        description TEXT,
        source_url TEXT,
        archived_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- API integration log
    CREATE TABLE IF NOT EXISTS api_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        action TEXT,
        status TEXT,
        data TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Backup history
    CREATE TABLE IF NOT EXISTS backups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        backup_type TEXT,
        file_path TEXT,
        record_count INTEGER,
        size_bytes INTEGER,
        md5_hash TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Reports
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_type TEXT,
        title TEXT,
        content TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Indexes for performance
    CREATE INDEX IF NOT EXISTS idx_tracks_artist ON tracks(artist_id);
    CREATE INDEX IF NOT EXISTS idx_tracks_year ON tracks(release_year);
    CREATE INDEX IF NOT EXISTS idx_tracks_confidence ON tracks(confidence_score);
    CREATE INDEX IF NOT EXISTS idx_tracks_platform ON tracks(platform);
    CREATE INDEX IF NOT EXISTS idx_tracks_country ON tracks(country);
    CREATE INDEX IF NOT EXISTS idx_tracks_isrc ON tracks(isrc);
    CREATE INDEX IF NOT EXISTS idx_roles_track ON roles(track_id);
    CREATE INDEX IF NOT EXISTS idx_collaborators_track ON collaborators(track_id);
    CREATE INDEX IF NOT EXISTS idx_evidence_track ON evidence(track_id);
    """)

def role_to_column(role_str):
    """Map a role string like 'Mix Engineer (مكس)' to a column name + normalization."""
    role_lower = role_str.lower()
    if 'mix' in role_lower or 'مكس' in role_lower or 'ميكس' in role_lower:
        return 'role_mixing'
    if 'master' in role_lower or 'ماستر' in role_lower or 'ماسترنك' in role_lower or 'ماسترينغ' in role_lower:
        return 'role_mastering'
    if 'record' in role_lower:
        return 'role_recording'
    if 'arrang' in role_lower or 'توزيع' in role_lower:
        return 'role_arranging'
    if 'compos' in role_lower or 'ألحان' in role_lower or 'تأليف' in role_lower:
        return 'role_composing'
    if 'producer' in role_lower or 'إنتاج' in role_lower:
        return 'role_producing'
    if 'executive' in role_lower or 'إشراف' in role_lower:
        return 'role_executive_prod'
    if 'sound' in role_lower or 'هندسة' in role_lower or 'audio' in role_lower:
        return 'role_sound_engineer'
    return None

def confidence_level(score):
    if score >= 90: return 'Verified'
    if score >= 70: return 'Likely'
    if score >= 30: return 'Possible'
    if score > 0: return 'Rejected'
    return 'Unknown'

def get_or_create_artist(conn, name):
    """Get artist ID or create."""
    cur = conn.execute("SELECT id FROM artists WHERE name = ?", (name,))
    row = cur.fetchone()
    if row:
        return row[0]
    conn.execute("INSERT INTO artists (name) VALUES (?)", (name,))
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

def migrate_json_to_sqlite(conn, json_path):
    """Migrate all data from JSON to SQLite."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    profile = data.get('profile', {})
    
    # Create Mustafa as artist
    conn.execute("INSERT OR IGNORE INTO artists (name, name_arabic, country, is_mustafa) VALUES (?, ?, ?, 1)",
                 (profile.get('full_name', 'Mustafa Kamal'), 'مصطفى كمال', profile.get('base_location', 'UAE')))
    mustafa_id = conn.execute("SELECT id FROM artists WHERE is_mustafa=1").fetchone()[0]

    credits = data.get('verified_credits', [])
    imported = 0

    for c in credits:
        title = c.get('track', 'Unknown')
        artist_name = c.get('artist', 'Unknown')
        year = c.get('release_year')
        
        # Get or create artist
        artist_id = get_or_create_artist(conn, artist_name)
        
        # Check if already imported by source_url
        url = c.get('source_url', '')
        existing = conn.execute("SELECT id FROM tracks WHERE source_url = ?", (url,)).fetchone()
        if existing:
            continue

        # Map roles to columns
        roles_list = c.get('roles', [])
        row_updates = {}
        performer_roles = []
        
        for r in roles_list:
            col = role_to_column(r)
            if col:
                row_updates[col] = 1
            rl = r.lower()
            if 'cello' in rl or 'تشيلو' in rl or 'جيللو' in rl:
                performer_roles.append('Cellist')
            if 'bass' in rl or 'بيز' in rl:
                performer_roles.append('Bass Guitarist')

        # Determine confidence
        score = c.get('confidence', 50)
        vstatus = c.get('verification_status', '')

        genres = c.get('genre', '')
        labels = c.get('label', '')

        track_id = conn.execute("""
            INSERT INTO tracks (
                title, artist_id, release_year, country, genre, label,
                role_mixing, role_mastering, role_recording,
                role_arranging, role_composing, role_producing,
                role_executive_prod, role_sound_engineer, role_performer,
                exact_credit, source_url, platform,
                confidence_score, confidence_level, verification_status
            ) VALUES (?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?)
        """, (
            title, artist_id, year, c.get('country', ''), genres, labels,
            row_updates.get('role_mixing', 0),
            row_updates.get('role_mastering', 0),
            row_updates.get('role_recording', 0),
            row_updates.get('role_arranging', 0),
            row_updates.get('role_composing', 0),
            row_updates.get('role_producing', 0),
            row_updates.get('role_executive_prod', 0),
            row_updates.get('role_sound_engineer', 0),
            ', '.join(performer_roles) if performer_roles else None,
            c.get('exact_credit', ''),
            url, c.get('platform', ''),
            score, confidence_level(score), vstatus
        )).lastrowid

        # Add roles to normalized roles table
        for r in roles_list:
            role_arabic = None
            if '(' in r:
                parts = r.split('(')
                role_name = parts[0].strip()
                role_arabic = parts[1].rstrip(')').strip()
            else:
                role_name = r
            conn.execute("INSERT OR IGNORE INTO roles (track_id, role_name, role_arabic) VALUES (?, ?, ?)",
                        (track_id, role_name, role_arabic))

        # Add additional credits as collaborators
        addl = c.get('additional_credits', {})
        for addl_role, addl_name in addl.items():
            if isinstance(addl_name, str):
                conn.execute("INSERT OR IGNORE INTO collaborators (name, role, track_id) VALUES (?, ?, ?)",
                            (addl_name, addl_role, track_id))

        imported += 1

    conn.commit()
    return imported, len(credits)

def export_to_json(conn):
    """Export SQLite to JSON for backup."""
    data = {
        "archive": "MUSTAFA MIXING - Global Music Credits & Rights Archive",
        "artist": "Mustafa Kamal (مصطفى كمال)",
        "last_updated": datetime.now().isoformat(),
        "database_version": "2.0.0",
        "credits": []
    }
    
    cursor = conn.execute("""
        SELECT t.*, a.name as artist_name
        FROM tracks t
        JOIN artists a ON t.artist_id = a.id
        WHERE t.is_active = 1
        ORDER BY t.release_year DESC, t.title
    """)
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    for row in rows:
        track = dict(zip(columns, row))
        # Get roles
        roles = conn.execute("SELECT role_name, role_arabic FROM roles WHERE track_id = ?", (track['id'],)).fetchall()
        track['roles'] = [f"{r[0]} ({r[1]})" if r[1] else r[0] for r in roles]
        # Get collaborators
        collabs = conn.execute("SELECT name, role FROM collaborators WHERE track_id = ?", (track['id'],)).fetchall()
        track['collaborators'] = [{"name": c[0], "role": c[1]} for c in collabs]
        data['credits'].append(track)
    
    # Export path
    export_dir = os.path.join(BASE, "exports")
    os.makedirs(export_dir, exist_ok=True)
    export_path = os.path.join(export_dir, f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(export_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return export_path

def create_backup(conn, btype='manual'):
    """Create a backup record and JSON snapshot."""
    export_path = export_to_json(conn)
    size = os.path.getsize(export_path)
    md5 = hashlib.md5(open(export_path, 'rb').read()).hexdigest()
    count = conn.execute("SELECT COUNT(*) FROM tracks WHERE is_active=1").fetchone()[0]
    
    # Copy to backups dir
    import shutil
    backup_name = f"backup_{btype}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    backup_path = os.path.join(BASE, "backups", backup_name)
    shutil.copy2(export_path, backup_path)
    
    conn.execute("""INSERT INTO backups (backup_type, file_path, record_count, size_bytes, md5_hash)
                    VALUES (?, ?, ?, ?, ?)""",
                 (btype, backup_path, count, size, md5))
    conn.commit()
    return backup_path

def main():
    print("=" * 60)
    print("MUSTAFA MIXING — Database Upgrade v2.0")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    print(f"\n📦 Database: {DB_PATH}")
    
    # Init schema
    init_schema(conn)
    print("✅ Schema created/verified")
    
    # Check if data exists
    existing = conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
    print(f"📊 Existing records in DB: {existing}")
    
    if existing == 0 and os.path.exists(JSON_PATH):
        imported, total = migrate_json_to_sqlite(conn, JSON_PATH)
        print(f"📥 Migrated {imported}/{total} credits from JSON to SQLite")
    elif existing > 0:
        print(f"ℹ️ Data already in SQLite, skipping migration")
    
    # Create backup
    backup = create_backup(conn, 'initial_migration')
    print(f"💾 Initial backup: {backup}")
    
    # Print stats
    stats = conn.execute("""
        SELECT 
            COUNT(*) as total_tracks,
            SUM(role_mixing) as mix_count,
            SUM(role_mastering) as master_count,
            SUM(role_arranging) as arrange_count,
            SUM(role_composing) as compose_count,
            SUM(role_producing) as produce_count,
            COUNT(DISTINCT artist_id) as artist_count,
            MIN(release_year) as earliest_year,
            MAX(release_year) as latest_year
        FROM tracks WHERE is_active=1
    """).fetchone()
    
    print(f"\n📈 DATABASE STATS:")
    print(f"   Total tracks: {stats['total_tracks']}")
    print(f"   Mixing: {stats['mix_count']}")
    print(f"   Mastering: {stats['master_count']}")
    print(f"   Arranging: {stats['arrange_count']}")
    print(f"   Composing: {stats['compose_count']}")
    print(f"   Producing: {stats['produce_count']}")
    print(f"   Artists: {stats['artist_count']}")
    print(f"   Year range: {stats['earliest_year']}–{stats['latest_year']}")
    
    conn.close()
    print("\n✅ Database upgrade complete!")

if __name__ == "__main__":
    main()
