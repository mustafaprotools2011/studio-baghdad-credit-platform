# MUSTAFA MIXING
## Global Music Credits & Rights Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1%2B-green)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-gold)](LICENSE)

**MUSTAFA MIXING** is a professional credits intelligence platform that discovers, verifies, archives, and monitors every publicly available music credit associated with **Mustafa Kamal** (مصطفى كمال) — Recording Engineer, Mix Engineer, Mastering Engineer, Sound Engineer, and Music Producer.

---

## Features

### 🔍 Intelligence & Search
- **Automatic Credit Discovery** — Searches across Spotify, Apple Music, YouTube, Anghami, Discogs, MusicBrainz, and more
- **OCR Credit Scanner** — Extracts credits from YouTube video outros using Tesseract OCR (Arabic + English)
- **Advanced Search** — Full-text search across tracks, artists, genres, platforms, ISRCs, and credits
- **Confidence Scoring** — Every credit is scored (0–100) and categorized: Verified, Likely, Possible, Rejected

### 📊 Analytics Dashboard
- **Interactive Dashboard** — 13+ pages: Overview, Artists, Tracks, Albums, Credits, Statistics, Reports, Verification, Legal, Royalties, Evidence, Settings
- **Visual Analytics** — Role breakdowns, year distributions, platform analytics, confidence distributions
- **Dark Theme** — Professional gold-accented UI with Cairo font and Arabic RTL support

### 🚀 API (REST)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/credits` | GET | All active credits (paginated) |
| `/api/credits/<id>` | GET | Single credit detail with roles & collaborators |
| `/api/stats` | GET | Summary statistics |
| `/api/search?q=` | GET | Full-text search |
| `/api/docs` | GET | Interactive API documentation |

### 🗄️ Database
- **Single Source of Truth** — SQLite-backed with full schema integrity
- **Versioned Schema** — Automatic upgrades with JSON backups before changes
- **Duplicate Detection** — Marks and tracks duplicate credits
- **Legal Module** — Copyright owners, master owners, publishers, contract status
- **Collaborator Tracking** — Records all collaborators per track

---

## Quick Start

### Prerequisites
- Python 3.11+
- SQLite 3 (built-in with Python)

### Installation

```bash
# Clone the repository
git clone https://github.com/mustafaprotools2011/studio-baghdad-credit-platform.git
cd studio-baghdad-credit-platform

# Install dependencies
pip install -r requirements.txt

# Run the dashboard
python app.py

# Open in browser
# http://localhost:5000
```

### Docker (Alternative)

```bash
# Build and run
docker compose up -d

# Open in browser
# http://localhost:5000
```

---

## Project Structure

```
mustafa-mixing-archive/
├── app.py                  # Flask dashboard + REST API
├── ocr_credit_scanner.py   # YouTube OCR credit extractor
├── upgrade_db.py           # Database migration tool
├── mustafa_mixing.db       # SQLite database
├── static/
│   └── style.css           # Dashboard styles (dark theme, Cairo font)
├── backups/                # JSON backups before upgrades
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker image
├── docker-compose.yml      # Docker Compose
└── README.md               # This file
```

---

## Database Schema

### `tracks` (Main table)
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| title | TEXT | Track title |
| artist_id | INTEGER | FK → artists.id |
| release_year | INTEGER | Release year |
| genre | TEXT | Music genre |
| country | TEXT | Country of origin |
| platform | TEXT | Source platform |
| label | TEXT | Record label |
| isrc | TEXT | ISRC code |
| exact_credit | TEXT | Published credit line |
| source_url | TEXT | Evidence URL |
| role_mixing | BOOLEAN | Mustafa mixed this |
| role_mastering | BOOLEAN | Mustafa mastered this |
| role_arranging | BOOLEAN | Mustafa arranged this |
| role_composing | BOOLEAN | Mustafa composed this |
| role_producing | BOOLEAN | Mustafa produced this |
| role_sound_engineer | BOOLEAN | Mustafa was sound engineer |
| role_executive_prod | BOOLEAN | Mustafa was executive producer |
| mustafa_role | TEXT | Arabic summary of roles |
| confidence_level | TEXT | Verified/Likely/Possible/Rejected |
| confidence_score | INTEGER | 0–100 confidence |
| verification_status | TEXT | Pending/Verified/Needs Review |
| verification_notes | TEXT | Notes on verification |
| is_active | BOOLEAN | Active credit flag |
| is_duplicate_of | INTEGER | FK → tracks.id (self) |
| copyright_owner | TEXT | Copyright holder |
| master_owner | TEXT | Master recording owner |
| publisher | TEXT | Publisher |
| contract_status | TEXT | Contractual relationship |
| created_at | TEXT | Creation timestamp |
| updated_at | TEXT | Last update timestamp |

### `artists`
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| name | TEXT | English name |
| name_arabic | TEXT | Arabic name |
| country | TEXT | Country |

### `roles`, `collaborators`, `albums`, `backups` — Supplementary tables for rich credit data

---

## OCR Credit Scanner

The OCR scanner extracts credits from YouTube video outros using Tesseract OCR.

```bash
# Scan a single channel
python ocr_credit_scanner.py --channel "MCP TV Music"

# Scan multiple videos from a file
python ocr_credit_scanner.py --urls-file urls.txt

# Scan a single video
python ocr_credit_scanner.py --url "https://youtube.com/watch?v=..."
```

**Requirements:**
- Tesseract-OCR (with Arabic `ara.traineddata`)
- `yt-dlp` (for downloading video segments)
- `ffmpeg` (for frame extraction)

---

## API Usage Examples

```bash
# Get all credits
curl http://localhost:5000/api/credits

# Pretty-printed stats
curl http://localhost:5000/api/stats?pretty=1

# Search
curl 'http://localhost:5000/api/search?q=Mustafa'

# Paginated results
curl 'http://localhost:5000/api/credits?limit=5&offset=0'
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      MUSTAFA MIXING                             │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌───────────┐  │
│  │ Dashboard │  │ REST API │  │ OCR Scanner  │  │ Git Sync │  │
│  └──────────┘  └──────────┘  └──────────────┘  └───────────┘  │
│                         │                                       │
│                    ┌─────▼──────┐                               │
│                    │  SQLite DB │                               │
│                    └────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Long-Term Goals

1. **Permanent Archive** — Preserve every verified professional contribution
2. **Continuous Verification** — Cross-reference multiple independent sources
3. **Royalty Tracking** — Identify copyright/royalty opportunities
4. **Vue.js Frontend** — Modern SPA frontend consuming the REST API
5. **Global Coverage** — All platforms, all regions, all roles

---

## License

MIT — See [LICENSE](LICENSE) for details.

---

## Maintained by

**Mustafa Kamal** (مصطفى كمال) — [mustafaprotools2011](https://github.com/mustafaprotools2011)
