#!/usr/bin/env python3
"""
MUSTAFA MIXING — Web Dashboard v2.0
Flask web app — 13 pages, SQLite-backed, single source of truth.
"""

import os, json, sqlite3, jinja2
from flask import Flask, render_template_string, request, jsonify, Response
from markupsafe import Markup
from flask_cors import CORS

BASE = os.environ.get("MUSTAFA_MIXING_BASE", os.path.dirname(os.path.abspath(__file__)))
BANNER = r'''
 _____ ___ _____ _____ _____ _   _ _____ ___  _   _  __  __   _
|     |  _|     |     |  _  | | | |   __|_  |/ \ | |/  \|  \ | |
| | | |  _| | | | | | |     | |_| |   __| __| | | |     | | \| |
|_|_|_|_| |_|_|_|_|_|_|__|__|_____|_____|___|_| \_|_|_|_|_|\___|
  ____ ___ ____   ___  ____  _____   _   _ _____ ____
 / ___|_ _|  _ \ / _ \|  _ \| ____| | \ | | ____|  _ \
| |    | || |_) | | | | |_) |  _|   |  \| |  _| | |_) |
| |___ | ||  _ <| |_| |  _ <| |___  | |\  | |___|  _ <
 \____|___|_| \_\\___/|_| \_\_____| |_| \_|_____|_| \_\
'''

DB_PATH = os.path.join(BASE, "mustafa_mixing.db")

# ─── Auto-migration: create/upgrade DB on first startup ──────────
if not os.path.exists(DB_PATH):
    print("📦 Database not found. Running upgrade_db to initialize schema...")
    try:
        from upgrade_db import main as upgrade_main
        # Patch the upgrade script's paths to match ours
        import upgrade_db as _upd_mod
        _upd_mod.BASE = BASE
        _upd_mod.DB_PATH = DB_PATH
        upgrade_main()
        print("✅ Database initialized.")
    except Exception as e:
        print(f"⚠️ Auto-migration failed: {e}")
        print("   You can run: python upgrade_db.py manually.")
# ────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = os.urandom(16).hex()
app.jinja_env.autoescape = False
# CORS: allow Vue.js frontend from any origin
CORS(app, resources={r"/api/*": {"origins": "*"}})

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def query(sql, params=None):
    conn = get_db()
    cur = conn.execute(sql, params or [])
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def q1(sql, params=None):
    rows = query(sql, params)
    return rows[0] if rows else {}

# Helpers for template building
def rp(t, col, label, cls):
    return '<span class=role-pill role-{}>{}</span>'.format(cls, label) if t.get(col) else ''

INLINE_CSS = """*{margin:0;padding:0;box-sizing:border-box}:root{--bg:#0a0a0f;--bg2:#0f0f18;--bg3:#181825;--bg4:#1e1e32;--border:#2a2a3e;--border2:#3a3a50;--text:#e8e8f0;--text2:#9898b8;--text3:#6a6a88;--gold:#d4a843;--gold2:#f5c842;--gold-dim:#a08030;--green:#22c55e;--red:#ef4444;--blue:#3b82f6;--purple:#8b5cf6;--pink:#ec4899;--cyan:#06b6d4}
body{font-family:Cairo,Inter,-apple-system,sans-serif;background:var(--bg);color:var(--text);display:flex;min-height:100vh;overflow-x:hidden}
.sidebar{width:240px;background:var(--bg2);border-right:1px solid var(--border);padding:0;display:flex;flex-direction:column;position:fixed;top:0;left:0;bottom:0;z-index:100;overflow-y:auto}
.sidebar-logo{padding:28px 20px 20px;text-align:center;border-bottom:1px solid var(--border)}
.sidebar-logo h1{font-size:16px;font-weight:900;color:var(--gold);letter-spacing:-0.5px;margin-top:6px}
.sidebar-logo small{font-size:10px;color:var(--text3);font-weight:300;display:block;margin-top:2px;text-transform:uppercase;letter-spacing:1px}
.logo-icon{font-size:32px;display:block;margin-bottom:2px}
.gold-line{width:40px;height:2px;background:linear-gradient(90deg,transparent,var(--gold),transparent);margin:10px auto 0;border-radius:2px}
.nav-section{font-size:10px;color:var(--text3);padding:16px 20px 6px;font-weight:600;text-transform:uppercase;letter-spacing:1.5px}
.nav-item{display:flex;align-items:center;gap:10px;padding:9px 20px;color:var(--text2);text-decoration:none;font-size:13px;font-weight:400;transition:all .2s;border-left:3px solid transparent;position:relative}
.nav-item:hover{color:var(--text);background:var(--bg3)}
.nav-item.active{color:var(--gold);background:linear-gradient(90deg,rgba(212,168,67,.08),transparent);border-left-color:var(--gold);font-weight:600}
.nav-item[data-icon]::before{content:attr(data-icon);font-size:14px;width:20px;text-align:center}
.main{flex:1;margin-left:240px;padding:32px 40px;min-height:100vh}
.page-header{margin-bottom:28px}
.page-title{font-size:28px;font-weight:700;color:var(--text);letter-spacing:-0.5px}
.page-subtitle{font-size:13px;color:var(--text2);margin-top:4px;font-weight:300}
.stat-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:14px;margin-bottom:28px}
.stat-card{background:var(--bg3);border:1px solid var(--border);border-radius:10px;padding:18px 16px;text-align:center;transition:all .3s}
.stat-card:hover{border-color:var(--gold-dim);transform:translateY(-2px);box-shadow:0 6px 20px rgba(212,168,67,.06)}
.stat-card .value{font-size:26px;font-weight:700;color:var(--gold);line-height:1.2}
.stat-card .label{font-size:11px;color:var(--text2);margin-top:4px;font-weight:400}
.card{background:var(--bg3);border:1px solid var(--border);border-radius:10px;padding:20px 24px;margin-bottom:20px}
.card h3{font-size:15px;font-weight:600;color:var(--gold);margin-bottom:14px;padding-bottom:8px;border-bottom:1px solid var(--border)}
.table-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:8px 12px;color:var(--text3);font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;border-bottom:2px solid var(--border)}
td{padding:8px 12px;border-bottom:1px solid var(--border);color:var(--text)}
tr:hover td{background:var(--bg4)}
a{color:var(--gold);text-decoration:none}
a:hover{text-decoration:underline}
.role-pill{display:inline-block;padding:1px 7px;border-radius:3px;font-size:10px;font-weight:600;margin:0 2px}
.role-mix{background:rgba(59,130,246,.15);color:var(--blue);border:1px solid rgba(59,130,246,.3)}
.role-master{background:rgba(139,92,246,.15);color:var(--purple);border:1px solid rgba(139,92,246,.3)}
.role-arrange{background:rgba(236,72,153,.15);color:var(--pink);border:1px solid rgba(236,72,153,.3)}
.role-compose{background:rgba(6,182,212,.15);color:var(--cyan);border:1px solid rgba(6,182,212,.3)}
.role-produce{background:rgba(34,197,94,.15);color:var(--green);border:1px solid rgba(34,197,94,.3)}
.badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:600}
.badge-Verified{background:rgba(34,197,94,.12);color:var(--green);border:1px solid rgba(34,197,94,.3)}
.badge-Likely{background:rgba(59,130,246,.12);color:var(--blue);border:1px solid rgba(59,130,246,.3)}
.badge-Possible{background:rgba(245,166,35,.12);color:var(--gold);border:1px solid rgba(212,168,67,.3)}
.badge-Rejected{background:rgba(239,68,68,.12);color:var(--red);border:1px solid rgba(239,68,68,.3)}
.info-row{display:flex;padding:6px 0;border-bottom:1px solid var(--border);font-size:13px}
.info-label{width:140px;color:var(--text3);font-weight:600;flex-shrink:0}
.info-value{color:var(--text)}
.search-box{display:flex;gap:10px;margin-bottom:20px}
.search-box input{flex:1;background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:10px 14px;color:var(--text);font-family:inherit;font-size:14px;outline:none;transition:border-color .2s}
.search-box input:focus{border-color:var(--gold)}
.search-box button{background:linear-gradient(135deg,var(--gold),var(--gold2));border:none;border-radius:6px;padding:10px 20px;color:#000;font-weight:700;font-size:13px;cursor:pointer;transition:opacity .2s;font-family:inherit}
.search-box button:hover{opacity:.9}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px}
.bg-pattern{position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:0;overflow:hidden}
.orb{position:absolute;border-radius:50%;filter:blur(80px);opacity:.12;animation:orbFloat 12s ease-in-out infinite}
.orb1{width:400px;height:400px;background:var(--gold);top:-100px;right:-100px;animation-delay:0s}
.orb2{width:300px;height:300px;background:var(--purple);bottom:-80px;left:-80px;animation-delay:-4s}
@keyframes orbFloat{0%,100%{transform:translate(0,0)}33%{transform:translate(30px,-30px)}66%{transform:translate(-20px,20px)}}
@media(max-width:768px){.sidebar{width:200px}.main{margin-left:200px;padding:20px}.stat-grid{grid-template-columns:repeat(2,1fr)}.two-col{grid-template-columns:1fr}}"""

def bl(lvl):
    return '<span class="badge badge-{}">{}</span>'.format(lvl, lvl)

LAYOUT = '''<!DOCTYPE html>
<html lang=ar dir=rtl>
<head>
<meta charset=UTF-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>MUSTAFA MIXING — {{ t }}</title>
<style>
@import url("https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;900&family=Inter:wght@300;400;600;700&display=swap");
''' + INLINE_CSS + '''
</style>
</head>
<body>
{% autoescape false %}
<div class=bg-pattern><div class="orb orb1"></div><div class="orb orb2"></div></div>
<nav class=sidebar>
<div class=sidebar-logo>
<span class=logo-icon>🎵</span>
<h1>MUSTAFA MIXING</h1>
<small>Credits Intelligence</small>
<div class=gold-line></div>
</div>
<div class=nav-section>Core</div>
{{ nav_overview|safe }}
{{ nav_artists|safe }}
{{ nav_tracks|safe }}
{{ nav_albums|safe }}
{{ nav_credits|safe }}
<div class=nav-section>Intelligence</div>
{{ nav_search|safe }}
{{ nav_statistics|safe }}
{{ nav_reports|safe }}
{{ nav_verification|safe }}
{{ nav_legal|safe }}
{{ nav_royalties|safe }}
<div class=nav-section>System</div>
{{ nav_evidence|safe }}
{{ nav_settings|safe }}
</nav>
<div class=main>
<div class=page-header>
<h1 class=page-title>{{ t }}</h1>
<p class=page-subtitle>{{ st }}</p>
</div>
{{ c }}
</div>
{% endautoescape %}
</body>
</html>'''

def page(title, subtitle, content, page_name):
    navs = {}
    items = [
        ("overview", "Overview", "📊"), ("artists", "Artists", "🎤"),
        ("tracks", "Tracks", "🎵"), ("albums", "Albums", "💿"),
        ("credits", "Credits", "📝"), ("search", "Search", "🔍"),
        ("statistics", "Statistics", "📈"), ("reports", "Reports", "📋"),
        ("verification", "Verification", "✅"), ("legal", "Legal", "⚖️"),
        ("royalties", "Royalties", "💰"), ("evidence", "Evidence", "📁"),
        ("upload-image", "Upload OCR", "📤"),
        ("add-credit", "➕ Add Credit", "➕"),
        ("advanced-search", "🔍 Advanced Search", "🔍"),
        ("settings", "Settings", "⚙️")
    ]
    for p, label, icon in items:
        act = ' active' if p == page_name else ''
        navs["nav_" + p] = '<a href="/{}" class="nav-item{}"><span class=nav-icon>{}</span> {}</a>'.format(p, act, icon, label)
    html = '<!DOCTYPE html>\n<html lang=ar dir=rtl>\n<head>\n<meta charset=UTF-8>\n<meta name=viewport content="width=device-width,initial-scale=1">\n<title>MUSTAFA MIXING — {}</title>\n<style>\n@import url("https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;900&family=Inter:wght@300;400;600;700&display=swap");\n' + INLINE_CSS + '\n</style>\n</head>\n<body>'.format(title)
    html += '<div class=bg-pattern><div class="orb orb1"></div><div class="orb orb2"></div></div>'
    html += '<nav class=sidebar>'
    html += '<div class=sidebar-logo><span class=logo-icon>🎵</span><h1>MUSTAFA MIXING</h1><small>Credits Intelligence</small><div class=gold-line></div></div>'
    html += '<div class=nav-section>Core</div>'
    for p, label, icon in items[:5]:
        act = ' active' if p == page_name else ''
        html += '<a href="/{}" class="nav-item{}" data-icon="{}">{}</a>'.format(p, act, icon, label)
    html += '<div class=nav-section>Intelligence</div>'
    for p, label, icon in items[5:11]:
        act = ' active' if p == page_name else ''
        html += '<a href="/{}" class="nav-item{}" data-icon="{}">{}</a>'.format(p, act, icon, label)
    html += '<div class=nav-section>System</div>'
    for p, label, icon in items[11:]:
        act = ' active' if p == page_name else ''
        html += '<a href="/{}" class="nav-item{}" data-icon="{}">{}</a>'.format(p, act, icon, label)
    html += '</nav><div class=main><div class=page-header><h1 class=page-title>{}</h1><p class=page-subtitle>{}</p></div>{}</div></body></html>'.format(title, subtitle, content)
    return Response(Markup(html), mimetype="text/html")

# ─── ROUTES ─────────────────────────────────────────────────────────

# ─── API helpers ─────────────────────────────────────────────────────

def api_response(data, status=200):
    """Return JSON response with optional pretty-print support."""
    pretty = request.args.get("pretty", "").lower() in ("1", "true", "yes")
    indent = 2 if pretty else None
    json_str = json.dumps(data, ensure_ascii=False, indent=indent, default=str)
    return Response(
        json_str + "\n",
        status=status,
        mimetype="application/json",
        headers={"Access-Control-Allow-Origin": "*"}
    )

def api_error(message, status=400):
    return api_response({"error": True, "message": message}, status)

# ─── API endpoints ──────────────────────────────────────────────────

@app.route("/api/credits")
def api_credits():
    """GET /api/credits — return all active credits as JSON."""
    limit = request.args.get("limit", 0, type=int)
    offset = request.args.get("offset", 0, type=int)
    sql = """
        SELECT t.*, a.name as artist_name, a.name_arabic as artist_name_arabic
        FROM tracks t
        JOIN artists a ON t.artist_id = a.id
        WHERE t.is_active = 1
        ORDER BY t.release_year DESC, t.title
    """
    if limit:
        sql += " LIMIT ? OFFSET ?"
        rows = query(sql, (limit, offset))
    else:
        rows = query(sql)
    return api_response({
        "count": len(rows),
        "results": rows
    })

@app.route("/api/credits/<int:id>")
def api_credit_detail(id):
    """GET /api/credits/<id> — return a single credit by ID."""
    row = q1("""
        SELECT t.*, a.name as artist_name, a.name_arabic as artist_name_arabic
        FROM tracks t
        JOIN artists a ON t.artist_id = a.id
        WHERE t.id = ?
    """, (id,))
    if not row:
        return api_error("Credit not found", 404)
    # Get additional data
    roles = query("SELECT * FROM roles WHERE track_id=?", (id,))
    collabs = query("SELECT * FROM collaborators WHERE track_id=?", (id,))
    row["roles"] = roles
    row["collaborators"] = collabs
    return api_response(row)

@app.route("/api/stats")
def api_stats():
    """GET /api/stats — return summary statistics."""
    s = q1("""
        SELECT
            COUNT(*) as total_credits,
            COUNT(DISTINCT artist_id) as total_artists,
            COALESCE(SUM(role_mixing), 0) as mixing,
            COALESCE(SUM(role_mastering), 0) as mastering,
            COALESCE(SUM(role_arranging), 0) as arranging,
            COALESCE(SUM(role_composing), 0) as composing,
            COALESCE(SUM(role_producing), 0) as producing,
            COALESCE(SUM(role_sound_engineer), 0) as sound_engineer,
            COALESCE(SUM(role_executive_prod), 0) as executive_production,
            MIN(release_year) as year_min,
            MAX(release_year) as year_max,
            COUNT(CASE WHEN confidence_level='Verified' THEN 1 END) as verified,
            COUNT(CASE WHEN confidence_level='Likely' THEN 1 END) as likely,
            COUNT(CASE WHEN confidence_level='Possible' THEN 1 END) as possible,
            COUNT(CASE WHEN confidence_level='Rejected' THEN 1 END) as rejected
        FROM tracks WHERE is_active=1
    """)
    years = query("""
        SELECT release_year, COUNT(*) as count
        FROM tracks WHERE is_active=1
        GROUP BY release_year ORDER BY release_year
    """)
    platforms = query("""
        SELECT platform, COUNT(*) as count
        FROM tracks WHERE is_active=1 AND platform IS NOT NULL AND platform != ''
        GROUP BY platform ORDER BY count DESC
    """)
    confidence_dist = query("""
        SELECT confidence_level, COUNT(*) as count
        FROM tracks WHERE is_active=1
        GROUP BY confidence_level ORDER BY count DESC
    """)
    return api_response({
        "summary": s,
        "by_year": years,
        "by_platform": platforms,
        "by_confidence": confidence_dist
    })

@app.route("/api/search")
def api_search():
    """GET /api/search?q= — search credits by keyword."""
    q = request.args.get("q", "").strip()
    if not q:
        return api_response({"query": "", "count": 0, "results": []})
    p = "%{}%".format(q)
    results = query("""
        SELECT t.*, a.name as artist_name, a.name_arabic as artist_name_arabic
        FROM tracks t
        JOIN artists a ON t.artist_id = a.id
        WHERE t.is_active=1
          AND (t.title LIKE ? OR a.name LIKE ? OR t.genre LIKE ? OR t.platform LIKE ?
               OR t.country LIKE ? OR t.exact_credit LIKE ? OR t.label LIKE ? OR t.isrc LIKE ?)
        ORDER BY t.release_year DESC
        LIMIT 100
    """, [p] * 8)
    return api_response({
        "query": q,
        "count": len(results),
        "results": results
    })

@app.route("/api/docs")
def api_docs():
    """GET /api/docs — HTML documentation page for the API."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MUSTAFA MIXING — API Documentation</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#0a0a0f;--bg2:#111118;--bg3:#1a1a28;--border:#2a2a3e;--text:#e8e8f0;--text2:#8888aa;--accent:#f5a623;--accent2:#e8961a;--green:#22c55e;--red:#ef4444;--blue:#3b82f6;--purple:#8b5cf6}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);padding:32px;max-width:900px;margin:0 auto}
h1{font-size:24px;color:var(--accent);margin-bottom:4px}
h2{font-size:18px;color:var(--text);margin:28px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--border)}
h3{font-size:14px;color:var(--accent2);margin:16px 0 6px}
p{font-size:13px;color:var(--text2);line-height:1.6;margin-bottom:12px}
code{background:var(--bg3);padding:2px 6px;border-radius:4px;font-size:12px;color:var(--green);border:1px solid var(--border)}
pre{background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:14px;overflow-x:auto;font-size:12px;line-height:1.5;margin:8px 0 16px}
pre code{background:transparent;border:none;padding:0;color:var(--text)}
.endpoint{background:var(--bg2);border:1px solid var(--border);border-radius:8px;padding:16px;margin-bottom:12px}
.endpoint .method{display:inline-block;padding:2px 8px;border-radius:4px;font-weight:700;font-size:11px;margin-right:8px;vertical-align:middle}
.method-get{background:var(--blue);color:#fff}
.method-post{background:var(--green);color:#000}
.method-delete{background:var(--red);color:#fff}
.endpoint .path{font-family:monospace;font-size:14px;color:var(--text);vertical-align:middle}
.endpoint .desc{color:var(--text2);font-size:12px;margin-top:6px}
.param-table{width:100%;border-collapse:collapse;font-size:12px;margin-top:8px}
.param-table th{text-align:left;padding:6px 8px;border-bottom:1px solid var(--border);color:var(--text2);font-size:11px}
.param-table td{padding:6px 8px;border-bottom:1px solid var(--border);color:var(--text)}
.tag{display:inline-block;padding:1px 6px;border-radius:3px;font-size:10px;margin:0 4px}
.tag-required{background:var(--red);color:#fff}
.tag-optional{background:var(--bg3);color:var(--text2);border:1px solid var(--border)}
a{color:var(--accent)}
a:hover{text-decoration:underline}
</style>
</head>
<body>
<h1>MUSTAFA MIXING API</h1>
<p>RESTful JSON API for the Mustafa Kamal Credits Intelligence Platform.</p>
<p>Base URL: <code>/api</code> &nbsp;|&nbsp; Pretty-print: append <code>?pretty=1</code> to any endpoint</p>

<h2>Endpoints</h2>

<div class="endpoint">
  <span class="method method-get">GET</span><span class="path">/api/credits</span>
  <div class="desc">Return all active credits as a JSON array.</div>
  <table class="param-table">
    <tr><th>Param</th><th>Type</th><th>Default</th><th>Description</th></tr>
    <tr><td><code>limit</code></td><td><span class="tag tag-optional">optional</span></td><td><em>all</em></td><td>Max results to return</td></tr>
    <tr><td><code>offset</code></td><td><span class="tag tag-optional">optional</span></td><td>0</td><td>Offset for pagination</td></tr>
    <tr><td><code>pretty</code></td><td><span class="tag tag-optional">optional</span></td><td>0</td><td>Pretty-print JSON (1/true/yes)</td></tr>
  </table>
</div>

<div class="endpoint">
  <span class="method method-get">GET</span><span class="path">/api/credits/{id}</span>
  <div class="desc">Return a single credit by its ID, including roles and collaborators.</div>
  <table class="param-table">
    <tr><th>Param</th><th>Type</th><th>Description</th></tr>
    <tr><td><code>id</code></td><td><span class="tag tag-required">required</span></td><td>Numeric track/credit ID</td></tr>
  </table>
</div>

<div class="endpoint">
  <span class="method method-get">GET</span><span class="path">/api/stats</span>
  <div class="desc">Return summary statistics: total counts, breakdowns by role, year, platform, and confidence level.</div>
</div>

<div class="endpoint">
  <span class="method method-get">GET</span><span class="path">/api/search?q=keyword</span>
  <div class="desc">Full-text search across tracks, artists, genres, platforms, countries, credits, labels, and ISRCs.</div>
  <table class="param-table">
    <tr><th>Param</th><th>Type</th><th>Description</th></tr>
    <tr><td><code>q</code></td><td><span class="tag tag-required">required</span></td><td>Search keyword</td></tr>
  </table>
</div>

<h2>Usage Examples</h2>

<h3>cURL</h3>
<pre><code># Get all credits
curl http://localhost:5000/api/credits

# Get a single credit
curl http://localhost:5000/api/credits/1

# Get stats
curl http://localhost:5000/api/stats

# Search
curl 'http://localhost:5000/api/search?q=Mustafa'

# Pretty-print
curl 'http://localhost:5000/api/credits?pretty=1'</code></pre>

<h3>JavaScript (fetch)</h3>
<pre><code>// All credits
const res = await fetch('/api/credits');
const data = await res.json();
console.log(data.count, 'results');

// Single credit
const credit = await (await fetch('/api/credits/1')).json();

// Search
const results = await (await fetch('/api/search?q=Khalid')).json();

// Paginated
const page = await (await fetch('/api/credits?limit=10&offset=0')).json();</code></pre>

<h3>Response Format</h3>
<pre><code>{
  "count": 19,
  "results": [
    {
      "id": 1,
      "title": "...",
      "artist_name": "...",
      "release_year": 2024,
      "role_mixing": 1,
      "role_mastering": 1,
      ...
    }
  ]
}</code></pre>

<h2>CORS</h2>
<p>All <code>/api/*</code> endpoints include <code>Access-Control-Allow-Origin: *</code> headers, making them accessible from any Vue.js frontend or browser-based application.</p>

<h2>Error Handling</h2>
<p>Errors return:</p>
<pre><code>{
  "error": true,
  "message": "Description of what went wrong"
}</code></pre>
<p>HTTP status codes: <code>400</code> (bad request), <code>404</code> (not found).</p>

<hr style="border:none;border-top:1px solid var(--border);margin:24px 0">
<p style="font-size:11px;color:var(--text2)">
  MUSTAFA MIXING — Credits Intelligence Platform &nbsp;|&nbsp; <a href="/">Back to Dashboard</a>
</p>
</body>
</html>"""
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/")
def overview():
    s = q1("SELECT COUNT(*) as total, COUNT(DISTINCT artist_id) as artists, SUM(role_mixing) as mix, SUM(role_mastering) as master, SUM(role_arranging) as arrange, SUM(role_composing) as compose, SUM(role_producing) as produce, SUM(role_sound_engineer) as sound, SUM(role_executive_prod) as exec_p, MIN(release_year) as yr_min, MAX(release_year) as yr_max, COUNT(CASE WHEN confidence_level='Verified' THEN 1 END) as v, COUNT(CASE WHEN confidence_level='Likely' THEN 1 END) as l, COUNT(CASE WHEN confidence_level='Possible' THEN 1 END) as p FROM tracks WHERE is_active=1")
    recent = query("SELECT t.*, a.name as an FROM tracks t JOIN artists a ON t.artist_id=a.id WHERE t.is_active=1 ORDER BY t.release_year DESC, t.id DESC LIMIT 8")
    sgrid = '<div class=stat-grid>'
    for label, key in [("Total Credits","total"),("Artists","artists"),("Mixing","mix"),("Mastering","master"),("Arranging","arrange"),("Composing","compose"),("Producing","produce"),("Verified","v"),("Years Active","yr_min")]:
        val = s[key]
        if key == "yr_min":
            val = "{}-{}".format(s["yr_min"], s["yr_max"])
        sgrid += '<div class=stat-card><div class=value>{}</div><div class=label>{}</div></div>'.format(val, label)
    sgrid += '</div>'
    rrows = ''.join('<tr><td><a href=/track/{}>{}</a></td><td>{}</td><td>{}</td><td>{}{}{}</td><td>{}</td></tr>'.format(t['id'],t['title'][:50],t['an'],t['release_year'],rp(t,'role_mixing','Mix','mix'),rp(t,'role_mastering','Master','master'),rp(t,'role_arranging','Arr','arrange'),bl(t['confidence_level'])) for t in recent)
    return page("Overview", "Mustafa Kamal — {} credits, {} artists".format(s['total'], s['artists']), sgrid + '<div class=card><h3>Recent Credits</h3><div class=table-wrap><table><tr><th>Track</th><th>Artist</th><th>Year</th><th>Roles</th><th>Confidence</th></tr>{}</table></div></div>'.format(rrows), "overview")

@app.route("/artists")
def artists():
    a = query("SELECT a.*, COUNT(t.id) as tc, SUM(t.role_mixing) as m, SUM(t.role_mastering) as mast FROM artists a LEFT JOIN tracks t ON a.id=t.artist_id AND t.is_active=1 GROUP BY a.id ORDER BY tc DESC")
    rows = ''.join('<tr><td><a href=/artist/{}>{}</a></td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'.format(x['id'],x['name'],x['name_arabic'] or '—',x['country'] or '—',x['tc'],x['m'] or 0,x['mast'] or 0) for x in a)
    return page("Artists", "{} unique artists".format(len(a)), '<div class=card><div class=table-wrap><table><tr><th>Artist</th><th>Arabic</th><th>Country</th><th>Tracks</th><th>Mix</th><th>Master</th></tr>{}</table></div></div>'.format(rows), "artists")

@app.route("/tracks")
def tracks():
    t = query("SELECT t.*, a.name as an FROM tracks t JOIN artists a ON t.artist_id=a.id WHERE t.is_active=1 ORDER BY t.release_year DESC, t.title")
    rows = ''.join('<tr><td><a href=/track/{}>{}</a></td><td>{}</td><td>{}</td><td>{}{}{}{}</td><td>{}</td><td>{}</td></tr>'.format(x['id'],x['title'][:60],x['an'],x['release_year'],rp(x,'role_mixing','M','mix'),rp(x,'role_mastering','Mst','master'),rp(x,'role_arranging','A','arrange'),rp(x,'role_composing','C','compose'),x.get('platform','') or '—',bl(x['confidence_level'])) for x in t)
    return page("Tracks", "{} total credits".format(len(t)), '<div class=card><div class=table-wrap><table><tr><th>Track</th><th>Artist</th><th>Year</th><th>Roles</th><th>Platform</th><th>Confidence</th></tr>{}</table></div></div>'.format(rows), "tracks")

@app.route("/track/<int:id>")
def track_detail(id):
    t = q1("SELECT t.*, a.name as an FROM tracks t JOIN artists a ON t.artist_id=a.id WHERE t.id=?", (id,))
    if not t: return "Not found", 404
    roles = query("SELECT * FROM roles WHERE track_id=?", (id,))
    collabs = query("SELECT * FROM collaborators WHERE track_id=?", (id,))
    rpills = ''.join('<span class=role-pill>{}{}</span> '.format(r['role_name'], ' ('+r['role_arabic']+')' if r['role_arabic'] else '') for r in roles) or '<span style=color:var(--text2)>None</span>'
    crows = ''.join('<tr><td>{}</td><td>{}</td></tr>'.format(c['name'],c['role']) for c in collabs) or '<tr><td colspan=2 style=color:var(--text2)>None</td></tr>'
    info = lambda l, v: '<div class=info-row><div class=info-label>{}</div><div class=info-value>{}</div></div>'.format(l, v)
    src_link = '<a href={} target=_blank>{}…</a>'.format(t['source_url'], t['source_url'][:70]) if t['source_url'] else '—'
    html = '<div class=card><h3>Track Details</h3>'
    for r in [("Title",t['title']),("Artist",'<a href=/artist/{}>{}</a>'.format(t['artist_id'],t['an'])),("Year",t['release_year']),("Genre",t['genre'] or '—'),("Country",t['country'] or '—'),("Platform",t['platform'] or '—'),("Label",t['label'] or '—'),("ISRC",t['isrc'] or '—'),("Confidence",bl(t['confidence_level'])+' ('+str(t['confidence_score'])+')'),("Source",src_link),("Credit Line",'<span style="direction:rtl;display:inline-block">{}</span>'.format(t['exact_credit'] or '—')),("Verification",t['verification_status'] or '—')]:
        html += info(r[0], r[1])
    html += '</div><div class=card><h3>Mustafa\'s Roles</h3>{}</div>'.format(rpills)
    html += '<div class=card><h3>Collaborators ({})</h3><div class=table-wrap><table><tr><th>Name</th><th>Role</th></tr>{}</table></div></div>'.format(len(collabs), crows)
    html += '<div class=card><h3>Legal</h3>'+info("Copyright Owner",t['copyright_owner'] or '—')+info("Master Owner",t['master_owner'] or '—')+info("Publisher",t['publisher'] or '—')+info("Contract Status",t['contract_status'] or '—')+'</div>'
    return page(t['title'], "by {} ({})".format(t['an'], t['release_year']), html, "credits")

@app.route("/artist/<int:id>")
def artist_detail(id):
    a = q1("SELECT * FROM artists WHERE id=?", (id,))
    if not a: return "Not found", 404
    t = query("SELECT * FROM tracks WHERE artist_id=? AND is_active=1 ORDER BY release_year DESC", (id,))
    rows = ''.join('<tr><td><a href=/track/{}>{}</a></td><td>{}</td><td>{}{}</td></tr>'.format(x['id'],x['title'][:50],x['release_year'],rp(x,'role_mixing','M','mix'),rp(x,'role_mastering','Mst','master')) for x in t)
    html = '<div class=card><h3>{}</h3>'.format(a['name'])+'<div class=info-row><div class=info-label>Arabic Name</div><div class=info-value>{}</div></div><div class=info-row><div class=info-label>Country</div><div class=info-value>{}</div></div><div class=info-row><div class=info-label>Tracks</div><div class=info-value>{}</div></div></div>'.format(a['name_arabic'] or '—',a['country'] or '—',len(t))
    html += '<div class=card><h3>Tracks</h3><div class=table-wrap><table><tr><th>Track</th><th>Year</th><th>Roles</th></tr>{}</table></div></div>'.format(rows)
    return page(a['name'], "Artist — {} tracks".format(len(t)), html, "artists")

@app.route("/albums")
def albums():
    a = query("SELECT t.label as name, COUNT(*) as cnt, GROUP_CONCAT(DISTINCT a.name) as arts FROM tracks t JOIN artists a ON t.artist_id=a.id WHERE t.is_active=1 AND t.label IS NOT NULL AND t.label!='' GROUP BY t.label ORDER BY cnt DESC")
    rows = ''.join('<tr><td>{}</td><td>{}</td><td>{}</td></tr>'.format(x['name'],x['cnt'],x['arts']) for x in a) or '<tr><td colspan=3 style=color:var(--text2)>No labels yet</td></tr>'
    return page("Albums & Labels", "{} labels".format(len(a)), '<div class=card><div class=table-wrap><table><tr><th>Label</th><th>Tracks</th><th>Artists</th></tr>{}</table></div></div>'.format(rows), "albums")

@app.route("/credits")
def credits():
    t = query("SELECT t.*, a.name as an FROM tracks t JOIN artists a ON t.artist_id=a.id WHERE t.is_active=1 ORDER BY t.release_year DESC, a.name")
    rows = ''.join('<tr><td><a href=/track/{}>{}</a></td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'.format(x['id'],x['title'][:50],x['an'],x['release_year'],' '.join(['Mix' if x['role_mixing'] else '','Master' if x['role_mastering'] else '','Arrange' if x['role_arranging'] else '','Compose' if x['role_composing'] else '','Produce' if x['role_producing'] else '']),x['platform'] or '—') for x in t)
    return page("All Credits", "{} total".format(len(t)), '<div class=card><div class=table-wrap><table><tr><th>Credit</th><th>Artist</th><th>Year</th><th>Role</th><th>Source</th></tr>{}</table></div></div>'.format(rows), "credits")

@app.route("/search")
def search():
    q = request.args.get("q", "")
    results = []
    if q:
        p = '%{}%'.format(q)
        results = query("SELECT t.*, a.name as an FROM tracks t JOIN artists a ON t.artist_id=a.id WHERE t.is_active=1 AND (t.title LIKE ? OR a.name LIKE ? OR t.genre LIKE ? OR t.platform LIKE ? OR t.country LIKE ? OR t.exact_credit LIKE ? OR t.label LIKE ? OR t.isrc LIKE ?) ORDER BY t.release_year DESC LIMIT 100", [p]*8)
    rrows = ''.join('<tr><td><a href=/track/{}>{}</a></td><td>{}</td><td>{}</td><td>{}{}{}</td><td>{}</td></tr>'.format(x['id'],x['title'][:50],x['an'],x['release_year'],rp(x,'role_mixing','Mix','mix'),rp(x,'role_mastering','Master','master'),rp(x,'role_arranging','Arrange','arrange'),bl(x['confidence_level'])) for x in results) if results else '<tr><td colspan=5 style=color:var(--text2)>No results</td></tr>'
    res_section = '<div class=card><h3>Results for &quot;{}&quot; ({})</h3><div class=table-wrap><table><tr><th>Track</th><th>Artist</th><th>Year</th><th>Roles</th><th>Confidence</th></tr>{}</table></div></div>'.format(q, len(results), rrows) if q else ''
    html = '<form method=GET action=/search><div class=search-box><input type=text name=q placeholder="Search artists, tracks, genres, credits…" value="{}"><button type=submit>🔍 Search</button></div></form>{}'.format(q, res_section)
    return page("Advanced Search", "Search by artist, track, year, role, platform, ISRC, keyword", html, "search")

@app.route("/statistics")
def statistics():
    s = q1("SELECT COUNT(*) as total, SUM(role_mixing) as mix, SUM(role_mastering) as master, SUM(role_arranging) as arrange, SUM(role_composing) as compose, SUM(role_producing) as produce, SUM(role_sound_engineer) as sound, SUM(role_executive_prod) as exec_p, COUNT(DISTINCT artist_id) as artists, MIN(release_year) as yr_min, MAX(release_year) as yr_max FROM tracks WHERE is_active=1")
    years = query("SELECT release_year, COUNT(*) as cnt FROM tracks WHERE is_active=1 GROUP BY release_year ORDER BY release_year")
    plats = query("SELECT platform, COUNT(*) as cnt FROM tracks WHERE is_active=1 AND platform IS NOT NULL GROUP BY platform ORDER BY cnt DESC")
    sgrid = '<div class=stat-grid>'+''.join('<div class=stat-card><div class=value>{}</div><div class=label>{}</div></div>'.format(str(s[k]),l) for l,k in [("Total","total"),("Mixing","mix"),("Mastering","master"),("Arranging","arrange"),("Composing","compose"),("Producing","produce"),("Artists","artists"),("Years","yr_min")])
    sgrid = sgrid.replace(str(s['yr_min']), '{}-{}'.format(s['yr_min'], s['yr_max']))+'</div>'
    yhtml = ''.join('<div style="display:flex;justify-content:space-between;padding:4px 0;font-size:13px;border-bottom:1px solid var(--border)"><span>{}</span><span style=color:var(--accent)>{} credits</span></div>'.format(y['release_year'],y['cnt']) for y in years)
    phtml = ''.join('<div style="display:flex;justify-content:space-between;padding:4px 0;font-size:13px;border-bottom:1px solid var(--border)"><span>{}</span><span style=color:var(--accent)>{}</span></div>'.format(p['platform'],p['cnt']) for p in plats)
    html = sgrid + '<div class=two-col><div class=card><h3>By Year</h3>{}</div><div class=card><h3>By Platform</h3>{}</div></div>'.format(yhtml, phtml)
    return page("Statistics", "Credits analytics", html, "statistics")

@app.route("/verification")
def verification():
    uv = query("SELECT t.*, a.name as an FROM tracks t JOIN artists a ON t.artist_id=a.id WHERE t.is_active=1 AND t.confidence_level!='Verified' ORDER BY t.confidence_score ASC")
    v = query("SELECT t.*, a.name as an FROM tracks t JOIN artists a ON t.artist_id=a.id WHERE t.is_active=1 AND t.confidence_level='Verified' ORDER BY t.release_year DESC")
    urows = ''.join('<tr><td><a href=/track/{}>{}</a></td><td>{}</td><td>{}</td><td>{}</td></tr>'.format(x['id'],x['title'][:50],x['an'],x['confidence_score'],bl(x['confidence_level'])) for x in uv) or '<tr><td colspan=4 style=color:var(--green)>✅ All verified!</td></tr>'
    vrows = ''.join('<tr><td><a href=/track/{}>{}</a></td><td>{}</td><td>{}</td></tr>'.format(x['id'],x['title'][:50],x['an'],x['release_year']) for x in v)
    html = '<div class=card><h3>Unverified / Pending ({})</h3><div class=table-wrap><table><tr><th>Track</th><th>Artist</th><th>Score</th><th>Level</th></tr>{}</table></div></div><div class=card><h3>Verified ({})</h3><div class=table-wrap><table><tr><th>Track</th><th>Artist</th><th>Year</th></tr>{}</table></div></div>'.format(len(uv), urows, len(v), vrows)
    return page("Verification Queue", "{} verified, {} pending".format(len(v), len(uv)), html, "verification")

@app.route("/legal")
def legal():
    t = query("SELECT t.*, a.name as an FROM tracks t JOIN artists a ON t.artist_id=a.id WHERE t.is_active=1 ORDER BY t.release_year DESC")
    rows = ''.join('<tr><td><a href=/track/{}>{}</a></td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'.format(x['id'],x['title'][:40],x['an'],x['copyright_owner'] or '—',x['master_owner'] or '—',x['publisher'] or '—',x['contract_status'] or '—') for x in t)
    return page("Legal Review", "Copyright, ownership, and rights tracking", '<div class=card><div class=table-wrap><table><tr><th>Track</th><th>Artist</th><th>Copyright Owner</th><th>Master Owner</th><th>Publisher</th><th>Contract</th></tr>{}</table></div></div>'.format(rows), "legal")

@app.route("/royalties")
def royalties():
    t = query("SELECT t.*, a.name as an FROM tracks t JOIN artists a ON t.artist_id=a.id WHERE t.is_active=1 ORDER BY t.release_year DESC")
    rows = ''.join('<tr><td><a href=/track/{}>{}</a></td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'.format(x['id'],x['title'][:40],x['an'],x['release_year'],' '.join(['Mix' if x['role_mixing'] else '','Master' if x['role_mastering'] else '','Compose' if x['role_composing'] else '','Produce' if x['role_producing'] else '']),x['publisher'] or '—',x['royalty_notes'] or 'Unregistered') for x in t)
    return page("Royalty Opportunities", "Revenue tracking", '<div class=card><div class=table-wrap><table><tr><th>Track</th><th>Artist</th><th>Year</th><th>Mustafa Role</th><th>Publisher</th><th>Royalty Notes</th></tr>{}</table></div></div>'.format(rows), "royalties")

@app.route("/evidence")
def evidence():
    evdir = os.path.join(BASE, "evidence")
    items = []
    if os.path.exists(evdir):
        for folder in sorted(os.listdir(evdir)):
            fpath = os.path.join(evdir, folder)
            if os.path.isdir(fpath):
                files = os.listdir(fpath)
                items.append({"folder": folder, "files": files, "count": len(files)})
    rows = ''.join('<tr><td>{}</td><td>{} files: {}</td></tr>'.format(i['folder'], i['count'], ', '.join(i['files'][:5]) + ('…' if i['count']>5 else '')) for i in items) or '<tr><td colspan=2 style=color:var(--text2)>No evidence folders yet</td></tr>'
    return page("Evidence", "{} work folders".format(len(items)), '<div class=card><div class=table-wrap><table><tr><th>Work Folder</th><th>Files</th></tr>{}</table></div></div>'.format(rows), "evidence")

@app.route("/reports")
def reports():
    r = query("SELECT * FROM reports ORDER BY created_at DESC")
    rows = ''.join('<tr><td>{}</td><td>{}</td><td>{}</td></tr>'.format(x['report_type'],x['title'],x['created_at']) for x in r) or '<tr><td colspan=3 style=color:var(--text2)>No reports yet</td></tr>'
    return page("Reports", "{} reports".format(len(r)), '<div class=card><div class=table-wrap><table><tr><th>Type</th><th>Title</th><th>Date</th></tr>{}</table></div></div>'.format(rows), "reports")

@app.route("/upload-image", methods=["GET", "POST"])
def upload_image():
    import base64, io, re
    from PIL import Image
    result_html = ""
    if request.method == "POST":
        file = request.files.get("image")
        if file and file.filename:
            from datetime import datetime
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            fname = f"upload_{ts}_{file.filename}"
            save_dir = os.path.join(BASE, "evidence", "uploads")
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, fname)
            file.save(save_path)
            # Basic image info
            img = Image.open(save_path)
            info = f"<p>📐 Size: {img.size[0]}×{img.size[1]} | Mode: {img.mode} | Format: {img.format}</p>"
            info += f'<p>💾 File: {fname} ({os.path.getsize(save_path)} bytes)</p>'
            # Try OCR with pytesseract if available
            try:
                import pytesseract
                text = pytesseract.image_to_string(img, lang='ara+eng')
                text_clean = text.strip() if text.strip() else "⚠️ No text detected"
                result_html = f'<div class=card><h3>📖 Extracted Text</h3><pre style="white-space:pre-wrap;background:var(--bg2);padding:1rem;border-radius:8px;direction:ltr;text-align:left;max-height:400px;overflow:auto">{text_clean}</pre></div>'
                info = ""  # Replace info with OCR result
            except ImportError:
                result_html = f'<div class=card><h3>📷 Image Saved</h3><p>OCR not installed. File saved at: <code>{save_path}</code></p><p>Install: <code>pip install pytesseract</code> + system tesseract</p></div>'
            result_html = info + result_html
            result_html += f'<div class=card><h3>🖼️ Preview</h3><img src="/evidence/uploads/{fname}" style="max-width:100%;max-height:500px;border-radius:8px"></div>'
    html = '''
    <div class=card>
        <h3>📤 Upload Image for OCR</h3>
        <form method=POST enctype=multipart/form-data>
            <input type=file name=image accept="image/*" required style="margin:1rem 0;padding:0.5rem;background:var(--bg2);color:var(--text);border:1px solid var(--border);border-radius:8px">
            <br>
            <button type=submit class=btn>🔍 Analyze Image</button>
        </form>
    </div>
    ''' + result_html
    return page("Upload Image", "Extract text from images", html, "upload-image")

@app.route("/evidence/uploads/<path:fname>")
def evidence_uploads(fname):
    from flask import send_from_directory
    return send_from_directory(os.path.join(BASE, "evidence", "uploads"), fname)


# ─── API: إضافة كريديت جديد ────────────────────────────────────────────
@app.route("/api/credits/add", methods=["POST"])
def api_add_credit():
    try:
        data = request.get_json()
        track = data.get("track", "").strip()
        artist = data.get("artist", "").strip()
        if not track or not artist:
            return jsonify({"error": "Track and artist are required"}), 400

        cur = get_db().execute(
            "INSERT INTO tracks (title, artist, release_year, role, confidence, is_active) VALUES (?, ?, ?, ?, ?, 1)",
            (track, artist, data.get("year", None), data.get("role", "Mix"), data.get("confidence", "Verified"))
        )
        get_db().commit()
        return jsonify({"id": cur.lastrowid, "message": "✅ تمت الإضافة"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── صفحة إضافة كريديت ──────────────────────────────────────────────────
@app.route("/add-credit")
def add_credit():
    html = """
    <div class=card>
        <h3>➕ إضافة كريديت جديد</h3>
        <form id=creditForm style="display:flex;flex-direction:column;gap:12px;max-width:500px">
            <input id=track name=track placeholder="اسم الأغنية (مطلوب)" required
                   style="padding:10px;background:var(--bg2);color:var(--text);border:1px solid var(--border);border-radius:8px;font-size:14px">
            <input id=artist name=artist placeholder="اسم الفنان (مطلوب)" required
                   style="padding:10px;background:var(--bg2);color:var(--text);border:1px solid var(--border);border-radius:8px;font-size:14px">
            <input id=year name=year type=number placeholder="سنة الإصدار (مثال: 2025)"
                   style="padding:10px;background:var(--bg2);color:var(--text);border:1px solid var(--border);border-radius:8px;font-size:14px">
            <select id=role name=role
                    style="padding:10px;background:var(--bg2);color:var(--text);border:1px solid var(--border);border-radius:8px;font-size:14px">
                <option value="">-- اختر الدور --</option>
                <option value="Mix">🎛️ Mix Engineer</option>
                <option value="Master">🎚️ Mastering Engineer</option>
                <option value="Arr">🎼 Arranger</option>
                <option value="Compose">✍️ Composer</option>
                <option value="Produce">🎬 Producer</option>
                <option value="Engineer">🎧 Recording Engineer</option>
                <option value="Mix,Master">🎛️ Mix + Master</option>
                <option value="Mix,Arr">🎛️ Mix + Arranger</option>
            </select>
            <select id=confidence name=confidence
                    style="padding:10px;background:var(--bg2);color:var(--text);border:1px solid var(--border);border-radius:8px;font-size:14px">
                <option value="Verified">✅ Verified</option>
                <option value="Likely">🔵 Likely</option>
                <option value="Possible">🟡 Possible</option>
            </select>
            <button type=submit class=btn style="padding:12px;background:var(--gold);color:#000;border:none;border-radius:8px;font-weight:700;font-size:15px;cursor:pointer">
                💾 حفظ الكريديت
            </button>
        </form>
        <div id=result style="margin-top:12px"></div>
    </div>
    <script>
    document.getElementById('creditForm').onsubmit = async function(e) {
        e.preventDefault();
        const btn = this.querySelector('button');
        btn.textContent = '⏳ جاري الحفظ...';
        btn.disabled = true;
        try {
            const r = await fetch('/api/credits/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    track: document.getElementById('track').value,
                    artist: document.getElementById('artist').value,
                    year: document.getElementById('year').value || null,
                    role: document.getElementById('role').value || 'Mix',
                    confidence: document.getElementById('confidence').value
                })
            });
            const d = await r.json();
            if (r.ok) {
                document.getElementById('result').innerHTML = '<div style="padding:12px;background:rgba(34,197,94,.12);border-radius:8px;color:var(--green)">✅ تم الحفظ!</div>';
                this.reset();
            } else {
                document.getElementById('result').innerHTML = '<div style="padding:12px;background:rgba(239,68,68,.12);border-radius:8px;color:var(--red)">❌ ' + d.error + '</div>';
            }
        } catch(e) {
            document.getElementById('result').innerHTML = '<div style="padding:12px;background:rgba(239,68,68,.12);border-radius:8px;color:var(--red)">❌ خطأ في الاتصال</div>';
        }
        btn.textContent = '💾 حفظ الكريديت';
        btn.disabled = false;
    };
    </script>
    """
    return page("Add Credit", "إضافة كريديت جديد", html, "add-credit")

@app.route("/advanced-search")
def advanced_search():
    html = """<div class="search-container" style="max-width:900px;margin:0 auto">
  <div class="search-header">
    <h1>🔍 بحث متقدم | Advanced Search</h1>
    <p>ابحث عن الفنان والوصف المهني والمنصة | Search for artist, profession & platform</p>
  </div>

  <form class="search-form" id="searchForm">
    <div class="form-grid" style="display:grid;grid-template-columns:1fr 1fr;gap:15px">
      <div class="form-group">
        <label for="artistName_ar">اسم الفنان (عربي)</label>
        <input type="text" id="artistName_ar" name="artistName_ar" placeholder="مثال: مصطفى كمال"
               style="width:100%;padding:10px;background:var(--bg2);color:var(--text);border:1px solid var(--border);border-radius:8px;font-size:14px">
      </div>
      <div class="form-group">
        <label for="artistName_en">Artist Name (English)</label>
        <input type="text" id="artistName_en" name="artistName_en" placeholder="Example: Mustafa Kamal"
               style="width:100%;padding:10px;background:var(--bg2);color:var(--text);border:1px solid var(--border);border-radius:8px;font-size:14px">
      </div>
      <div class="form-group">
        <label for="profession_ar">الوصف المهني (عربي)</label>
        <input type="text" id="profession_ar" name="profession_ar" placeholder="مثال: مهندس صوت"
               style="width:100%;padding:10px;background:var(--bg2);color:var(--text);border:1px solid var(--border);border-radius:8px;font-size:14px">
      </div>
      <div class="form-group">
        <label for="profession_en">Profession (English)</label>
        <input type="text" id="profession_en" name="profession_en" placeholder="Example: Sound Engineer"
               style="width:100%;padding:10px;background:var(--bg2);color:var(--text);border:1px solid var(--border);border-radius:8px;font-size:14px">
      </div>
    </div>
    <div class="form-group" style="margin-top:15px">
      <label for="platforms">اختر المنصات | Select Platforms</label>
      <select id="platforms" name="platforms" multiple style="width:100%;padding:10px;background:var(--bg2);color:var(--text);border:1px solid var(--border);border-radius:8px;font-size:14px;min-height:100px">
        <option value="youtube">🎥 YouTube</option>
        <option value="spotify">🎵 Spotify</option>
        <option value="apple-music">🎧 Apple Music</option>
        <option value="soundcloud">☁️ SoundCloud</option>
        <option value="bandcamp">🎼 Bandcamp</option>
        <option value="tiktok">📱 TikTok</option>
        <option value="instagram">📸 Instagram</option>
        <option value="">✨ جميع المنصات | All Platforms</option>
      </select>
    </div>
    <div class="button-group" style="display:flex;gap:12px;margin-top:15px">
      <button type="submit" class="btn-search" style="flex:1;padding:12px;background:var(--gold);color:var(--bg);border:none;border-radius:8px;font-weight:bold;cursor:pointer;font-size:15px">
        🔍 ابحث | Search
      </button>
      <button type="reset" class="btn-reset" style="flex:1;padding:12px;background:var(--bg2);color:var(--text);border:1px solid var(--border);border-radius:8px;cursor:pointer;font-size:15px">
        🔄 مسح | Clear
      </button>
    </div>
  </form>

  <div id="searchResults" class="search-results" style="margin-top:20px"></div>
</div>

<script>
// ===== MUSTAFA MIXING — Advanced Search (Dual: Mock + API) =====
const artistsDatabase = [
  { id: 1, name_ar: "مصطفى كمال", name_en: "Mustafa Kamal", profession_ar: "مهندس صوت", profession_en: "Sound Engineer", platforms: ["youtube", "spotify", "soundcloud"], followers: 125000, image: "🎤" },
  { id: 2, name_ar: "أحمد شريف", name_en: "Ahmed Sharif", profession_ar: "منتج موسيقي", profession_en: "Music Producer", platforms: ["youtube", "apple-music", "bandcamp"], followers: 89000, image: "🎹" },
  { id: 3, name_ar: "ليلى محمود", name_en: "Layla Mahmoud", profession_ar: "مغنية صوت", profession_en: "Vocalist", platforms: ["spotify", "apple-music", "tiktok", "instagram"], followers: 256000, image: "🎤" },
  { id: 4, name_ar: "سارة علي", name_en: "Sarah Ali", profession_ar: "منسقة موسيقية", profession_en: "Music Arranger", platforms: ["youtube", "soundcloud"], followers: 67000, image: "🎼" },
  { id: 5, name_ar: "محمود علوان", name_en: "Mahmoud Alwan", profession_ar: "مهندس ماستر", profession_en: "Mastering Engineer", platforms: ["spotify", "bandcamp"], followers: 45000, image: "🎧" },
  { id: 6, name_ar: "فاطمة حسن", name_en: "Fatima Hassan", profession_ar: "كاتبة أغاني", profession_en: "Songwriter", platforms: ["youtube", "tiktok", "instagram"], followers: 198000, image: "✍️" }
];

document.getElementById('searchForm').addEventListener('submit', function(e) {
  e.preventDefault();
  var g = function(id) { return (document.getElementById(id).value || '').trim(); };
  var artistNameAr = g('artistName_ar'), artistNameEn = g('artistName_en');
  var professionAr = g('profession_ar'), professionEn = g('profession_en');
  var sel = document.getElementById('platforms');
  var platforms = [];
  for (var i = 0; i < sel.options.length; i++) {
    if (sel.options[i].selected && sel.options[i].value) platforms.push(sel.options[i].value);
  }

  if (!artistNameAr && !artistNameEn && !professionAr && !professionEn && platforms.length === 0) {
    alert('⚠️ الرجاء ملء حقل واحد على الأقل');
    return;
  }

  var results = [];
  for (var i = 0; i < artistsDatabase.length; i++) {
    var a = artistsDatabase[i];
    var nameMatch = (!artistNameAr || a.name_ar.indexOf(artistNameAr) !== -1) &&
      (!artistNameEn || a.name_en.toLowerCase().indexOf(artistNameEn.toLowerCase()) !== -1);
    var profMatch = (!professionAr || a.profession_ar.indexOf(professionAr) !== -1) &&
      (!professionEn || a.profession_en.toLowerCase().indexOf(professionEn.toLowerCase()) !== -1);
    var platMatch = platforms.length === 0;
    for (var p = 0; p < platforms.length; p++) {
      if (a.platforms.indexOf(platforms[p]) !== -1) { platMatch = true; break; }
    }
    if (nameMatch && profMatch && platMatch) results.push(a);
  }

  var rc = document.getElementById('searchResults');
  if (results.length === 0) {
    rc.innerHTML = '<div class=card style="text-align:center;padding:30px"><h3>😔 لا توجد نتائج</h3><small>جرب بحثاً آخر</small></div>';
    return;
  }
  var icons = {youtube:'🎥',spotify:'🎵','apple-music':'🎧',soundcloud:'☁️',bandcamp:'🎼',tiktok:'📱',instagram:'📸'};
  var cards = '';
  for (var r = 0; r < results.length; r++) {
    var art = results[r];
    var phtml = '';
    for (var pi = 0; pi < art.platforms.length; pi++) {
      phtml += '<span style="display:inline-block;padding:4px 8px;background:var(--bg2);border:1px solid var(--border);border-radius:6px;font-size:12px;margin:2px">' + (icons[art.platforms[pi]] || '') + ' ' + art.platforms[pi] + '</span>';
    }
    cards += '<div class=card style="padding:15px"><div style="display:flex;align-items:center;gap:12px;margin-bottom:10px"><div style="font-size:40px">' + art.image + '</div><div><h3 style="margin:0">' + art.name_ar + ' | ' + art.name_en + '</h3><p style="margin:4px 0 0;color:var(--gold);font-size:13px">' + art.profession_ar + ' | ' + art.profession_en + '</p></div></div><div style="margin-bottom:8px"><span>👥 ' + art.followers.toLocaleString() + ' متابع</span></div><div style="margin-bottom:10px"><strong style="font-size:12px">المنصات:</strong><br>' + phtml + '</div></div>';
  }
  rc.innerHTML = '<h3 style="margin-bottom:15px">📊 ' + results.length + ' نتيجة</h3><div class="results-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:15px">' + cards + '</div>';
});
</script>"""
    return page("Advanced Search", "بحث متقدم", html, "advanced-search")


@app.route("/api/credits/search")
def api_search_credits():
    try:
        where = ["t.is_active=1"]
        params = []
        name_ar = request.args.get("artistName_ar", "").strip()
        name_en = request.args.get("artistName_en", "").strip()
        prof_ar = request.args.get("profession_ar", "").strip()
        prof_en = request.args.get("profession_en", "").strip()
        platforms = request.args.getlist("platforms")

        if name_ar:
            where.append("(t.title_arabic LIKE ? OR a.name_arabic LIKE ? OR t.notes LIKE ?)")
            like = f"%{name_ar}%"
            params.extend([like, like, like])
        if name_en:
            where.append("(t.title LIKE ? OR a.name LIKE ? OR t.exact_credit LIKE ?)")
            like = f"%{name_en}%"
            params.extend([like, like, like])
        if prof_ar:
            where.append("(t.mustafa_role LIKE ? OR t.notes LIKE ? OR c.name_arabic LIKE ?)")
            like = f"%{prof_ar}%"
            params.extend([like, like, like])
        if prof_en:
            where.append("(t.mustafa_role LIKE ? OR t.exact_credit LIKE ?)")
            like = f"%{prof_en}%"
            params.extend([like, like])
        valid_platforms = [p for p in platforms if p and p != "all"]
        if valid_platforms:
            placeholders = ",".join("?" for _ in valid_platforms)
            where.append(f"t.platform IN ({placeholders})")
            params.extend(valid_platforms)

        sql = "SELECT t.*, a.name as artist FROM tracks t LEFT JOIN artists a ON t.artist_id=a.id WHERE " + " AND ".join(where) + " ORDER BY t.release_year DESC LIMIT 100"
        return jsonify(query(sql, params))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/settings")
def settings():
    dbc = q1("SELECT COUNT(*) as c FROM sqlite_master WHERE type='table'")['c']
    tc = q1("SELECT COUNT(*) as c FROM tracks")['c']
    bc = q1("SELECT COUNT(*) as c FROM backups")['c']
    html = '<div class=stat-grid><div class=stat-card><div class=value>{}</div><div class=label>DB Tables</div></div><div class=stat-card><div class=value>{}</div><div class=label>Total Tracks</div></div><div class=stat-card><div class=value>{}</div><div class=label>Backups</div></div><div class=stat-card><div class=value>SQLite</div><div class=label>Engine</div></div></div>'.format(dbc, tc, bc)
    html += '<div class=card><h3>System Info</h3><div class=info-row><div class=info-label>Database Path</div><div class=info-value>{}</div></div><div class=info-row><div class=info-label>Evidence Dir</div><div class=info-value>{}</div></div><div class=info-row><div class=info-label>Backups Dir</div><div class=info-value>{}</div></div><div class=info-row><div class=info-label>Git Repo</div><div class=info-value>Initialized (master)</div></div><div class=info-row><div class=info-label>API Connectors</div><div class=info-value>Spotify · YouTube · Discogs · MusicBrainz · Apple Music · Jaxsta</div></div><div class=info-row><div class=info-label>JSON Backup</div><div class=info-value>Active — exports to /exports/</div></div></div>'.format(DB_PATH, os.path.join(BASE, 'evidence'), os.path.join(BASE, 'backups'))
    return page("Settings", "System configuration", html, "settings")

if __name__ == "__main__":
    # ─── إنشاء الجداول تلقائياً إذا ما موجودة ─────────────────────
    try:
        q1("SELECT COUNT(*) as c FROM tracks WHERE is_active=1")
    except Exception:
        print("📦 Initializing database tables...")
        conn = get_db()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                artist TEXT,
                album TEXT DEFAULT '',
                release_year INTEGER,
                role TEXT DEFAULT 'Mix',
                confidence TEXT DEFAULT 'Verified',
                is_active INTEGER DEFAULT 1,
                source_url TEXT DEFAULT '',
                platform TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                country TEXT DEFAULT '',
                isrc TEXT DEFAULT '',
                upc TEXT DEFAULT '',
                label TEXT DEFAULT '',
                publisher TEXT DEFAULT '',
                copyright_owner TEXT DEFAULT '',
                master_owner TEXT DEFAULT '',
                composer TEXT DEFAULT '',
                lyricist TEXT DEFAULT '',
                arranger TEXT DEFAULT '',
                producer TEXT DEFAULT '',
                recording_engineer TEXT DEFAULT '',
                mix_engineer TEXT DEFAULT '',
                mastering_engineer TEXT DEFAULT '',
                duration TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                record_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        conn.close()
        print("✅ Tables created.")
    cnt = 0
    try:
        cnt = q1("SELECT COUNT(*) as c FROM tracks WHERE is_active=1")['c']
    except Exception:
        cnt = 0
    port = int(os.environ.get("PORT", 5000))
    print("="*50)
    print("MUSTAFA MIXING Dashboard v2.0")
    print("="*50)
    print("URL: http://0.0.0.0:{}".format(port))
    print("DB: {}".format(DB_PATH))
    print("Credits: {} active".format(cnt))
    print("="*50)
    app.run(host="0.0.0.0", port=port)
