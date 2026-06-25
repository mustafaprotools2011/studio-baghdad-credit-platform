#!/usr/bin/env python3
"""
MUSTAFA MIXING — Web Dashboard v2.0
Flask web app — 13 pages, SQLite-backed, single source of truth.
"""

import os, sqlite3
from flask import Flask, render_template_string, request

BASE = "/opt/data/mustafa-mixing-archive"
DB_PATH = os.path.join(BASE, "mustafa_mixing.db")
app = Flask(__name__)
app.secret_key = os.urandom(16).hex()

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
<html lang=en>
<head>
<meta charset=UTF-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>MUSTAFA MIXING — {{ t }}</title>
<style>
{% raw %}*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#0a0a0f;--bg2:#111118;--bg3:#1a1a28;--border:#2a2a3e;--text:#e8e8f0;--text2:#8888aa;--accent:#f5a623;--accent2:#e8961a;--green:#22c55e;--red:#ef4444;--blue:#3b82f6;--purple:#8b5cf6}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);display:flex;min-height:100vh}
.sidebar{width:220px;background:var(--bg2);border-right:1px solid var(--border);padding:20px 0;flex-shrink:0;overflow-y:auto}
.sidebar h1{font-size:13px;padding:0 20px 16px;border-bottom:1px solid var(--border);margin-bottom:8px;color:var(--accent);letter-spacing:1px}
.sidebar h1 small{display:block;font-size:10px;color:var(--text2);margin-top:3px;letter-spacing:0}
.nav-item{display:block;padding:8px 20px;color:var(--text2);text-decoration:none;font-size:13px;transition:.15s;border-left:3px solid transparent}
.nav-item:hover,.nav-item.active{color:var(--text);background:var(--bg3)}
.nav-item.active{border-left-color:var(--accent);color:var(--accent)}
.nav-section{font-size:10px;text-transform:uppercase;letter-spacing:1.5px;color:var(--text2);padding:16px 20px 4px;opacity:.6}
.main{flex:1;padding:24px 32px;overflow-x:hidden}
.page-title{font-size:22px;margin-bottom:4px}
.page-subtitle{color:var(--text2);font-size:13px;margin-bottom:24px}
.badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600}
.badge-Verified{background:#22c55e22;color:var(--green);border:1px solid #22c55e44}
.badge-Likely{background:#3b82f622;color:var(--blue);border:1px solid #3b82f644}
.badge-Possible{background:#f5a62322;color:var(--accent);border:1px solid #f5a62344}
.badge-Rejected{background:#ef444422;color:var(--red);border:1px solid #ef44444b}
.card{background:var(--bg2);border:1px solid var(--border);border-radius:8px;padding:20px;margin-bottom:20px}
.card h3{font-size:12px;color:var(--text2);margin-bottom:12px;text-transform:uppercase;letter-spacing:.5px}
.stat-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:14px;margin-bottom:24px}
.stat-card{background:var(--bg2);border:1px solid var(--border);border-radius:8px;padding:14px}
.stat-card .value{font-size:26px;font-weight:700;color:var(--accent)}
.stat-card .label{font-size:11px;color:var(--text2);margin-top:3px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:8px 10px;border-bottom:2px solid var(--border);color:var(--text2);font-size:11px;text-transform:uppercase;letter-spacing:.5px}
td{padding:8px 10px;border-bottom:1px solid var(--border)}
tr:hover td{background:var(--bg3)}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
.search-box{display:flex;gap:10px;margin-bottom:20px;flex-wrap:wrap}
.search-box input,.search-box select{background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:8px 14px;border-radius:6px;font-size:13px}
.search-box input[type=text]{flex:1;min-width:200px}
.search-box button{background:var(--accent);color:#000;border:none;padding:8px 20px;border-radius:6px;font-weight:600;cursor:pointer}
.role-pill{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;background:var(--bg3);border:1px solid var(--border);margin:2px}
.role-mix{border-color:#3b82f666;color:#60a5fa}
.role-master{border-color:#8b5cf666;color:#a78bfa}
.role-arrange{border-color:#22c55e66;color:#4ade80}
.role-compose{border-color:#f5a62366;color:#fbbf24}
.role-produce{border-color:#ef444466;color:#f87171}
.info-row{display:flex;margin-bottom:6px}
.info-label{width:180px;color:var(--text2);font-size:12px;flex-shrink:0}
.info-value{font-size:13px}
.table-wrap{overflow-x:auto}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:20px}
{% endraw %}
</style>
</head>
<body>
<nav class=sidebar>
<h1>MUSTAFA MIXING<small>Credits Intelligence Platform</small></h1>
<div class=nav-section>Core</div>
{{ nav("overview","📊 Overview") }}
{{ nav("artists","🎤 Artists") }}
{{ nav("tracks","🎵 Tracks") }}
{{ nav("albums","💿 Albums") }}
{{ nav("credits","📝 Credits") }}
<div class=nav-section>Intelligence</div>
{{ nav("search","🔍 Search") }}
{{ nav("statistics","📈 Statistics") }}
{{ nav("reports","📋 Reports") }}
{{ nav("verification","✅ Verification") }}
{{ nav("legal","⚖️ Legal") }}
{{ nav("royalties","💰 Royalties") }}
<div class=nav-section>System</div>
{{ nav("evidence","📁 Evidence") }}
{{ nav("settings","⚙️ Settings") }}
</nav>
<div class=main>
<h1 class=page-title>{{ t }}</h1>
<p class=page-subtitle>{{ st }}</p>
{{ c }}
</div>
</body>
</html>'''

def page(title, subtitle, content, page_name):
    def nav_item(p, label):
        act = ' active' if p == page_name else ''
        return '<a href="/{}" class="nav-item{}">{}</a>'.format(p, act, label)
    return render_template_string(LAYOUT, t=title, st=subtitle, c=content, nav=nav_item)

# ─── ROUTES ─────────────────────────────────────────────────────────

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
