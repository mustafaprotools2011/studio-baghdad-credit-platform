#!/usr/bin/env python3
"""
MUSTAFA MIXING — Initialize Database Schema
=============================================
تشغيل: python init_db.py
ينشئ قاعدة البيانات الكاملة بكل الجداول.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mustafa_mixing.db")

SCHEMA = """
-- Artists table
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

-- Tracks table (main credits table)
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
    mustafa_role TEXT,
    youtube_url TEXT,
    video_duration INTEGER,
    thumbnail_url TEXT,

    UNIQUE(source_url)
);

-- Collaborators table (other artists involved)
CREATE TABLE IF NOT EXISTS collaborators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    name_arabic TEXT,
    role TEXT,
    track_id INTEGER REFERENCES tracks(id),
    UNIQUE(name, role, track_id)
);

-- Roles table (detailed role breakdown)
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id INTEGER REFERENCES tracks(id),
    role_name TEXT NOT NULL,
    role_arabic TEXT,
    confidence INTEGER DEFAULT 100,
    UNIQUE(track_id, role_name)
);

-- Evidence table (screenshots, PDFs)
CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id INTEGER REFERENCES tracks(id),
    file_type TEXT,
    file_path TEXT,
    description TEXT,
    source_url TEXT,
    archived_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- API log
CREATE TABLE IF NOT EXISTS api_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT,
    action TEXT,
    status TEXT,
    data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Backups log
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
"""


def init_db():
    print(f"📦 Initializing database at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.commit()

    # Verify tables
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    print(f"✅ Created {len(tables)} tables:")
    for t in tables:
        count = conn.execute(
            f"SELECT COUNT(*) FROM [{t[0]}]"
        ).fetchone()[0]
        print(f"   📊 {t[0]:20s} → {count} records")

    conn.close()
    print("\n🎉 Database ready!")


if __name__ == "__main__":
    init_db()
