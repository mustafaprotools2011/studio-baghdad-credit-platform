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

def bl(lvl):
    return '<span class="badge badge-{}">{}</span>'.format(lvl, lvl)

LAYOUT = '''<!DOCTYPE html>
<html lang=ar dir=rtl>
<head>
<meta charset=UTF-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>MUSTAFA MIXING — {{ t }}</title>
<link rel=stylesheet href=/static/style.css>
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
        ("settings", "Settings", "⚙️")
    ]
    for p, label, icon in items:
        act = ' active' if p == page_name else ''
        navs["nav_" + p] = '<a href="/{}" class="nav-item{}"><span class=nav-icon>{}</span> {}</a>'.format(p, act, icon, label)
    html = '<!DOCTYPE html>\n<html lang=ar dir=rtl>\n<head>\n<meta charset=UTF-8>\n<meta name=viewport content="width=device-width,initial-scale=1">\n<title>MUSTAFA MIXING — {}</title>\n<link rel=stylesheet href=/static/style.css>\n</head>\n<body>'.format(title)
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

@app.route("/settings")
def settings():
    dbc = q1("SELECT COUNT(*) as c FROM sqlite_master WHERE type='table'")['c']
    tc = q1("SELECT COUNT(*) as c FROM tracks")['c']
    bc = q1("SELECT COUNT(*) as c FROM backups")['c']
    html = '<div class=stat-grid><div class=stat-card><div class=value>{}</div><div class=label>DB Tables</div></div><div class=stat-card><div class=value>{}</div><div class=label>Total Tracks</div></div><div class=stat-card><div class=value>{}</div><div class=label>Backups</div></div><div class=stat-card><div class=value>SQLite</div><div class=label>Engine</div></div></div>'.format(dbc, tc, bc)
    html += '<div class=card><h3>System Info</h3><div class=info-row><div class=info-label>Database Path</div><div class=info-value>{}</div></div><div class=info-row><div class=info-label>Evidence Dir</div><div class=info-value>{}</div></div><div class=info-row><div class=info-label>Backups Dir</div><div class=info-value>{}</div></div><div class=info-row><div class=info-label>Git Repo</div><div class=info-value>Initialized (master)</div></div><div class=info-row><div class=info-label>API Connectors</div><div class=info-value>Spotify · YouTube · Discogs · MusicBrainz · Apple Music · Jaxsta</div></div><div class=info-row><div class=info-label>JSON Backup</div><div class=info-value>Active — exports to /exports/</div></div></div>'.format(DB_PATH, os.path.join(BASE, 'evidence'), os.path.join(BASE, 'backups'))
    return page("Settings", "System configuration", html, "settings")

if __name__ == "__main__":
    cnt = q1("SELECT COUNT(*) as c FROM tracks WHERE is_active=1")['c']
    port = int(os.environ.get("PORT", 5000))
    print("="*50)
    print("MUSTAFA MIXING Dashboard v2.0")
    print("="*50)
    print("URL: http://0.0.0.0:{}".format(port))
    print("DB: {}".format(DB_PATH))
    print("Credits: {} active".format(cnt))
    print("="*50)
    app.run(host="0.0.0.0", port=port)
