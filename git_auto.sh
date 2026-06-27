#!/usr/bin/env bash
# MUSTAFA MIXING — Git Auto Push
# ================================
# يسوي commit + push لكل التغييرات على GitHub مباشرة
# يشمل: تصدير قاعدة البيانات كـ JSON قبل الدفع

set -e
cd /opt/data/mustafa-mixing-archive

# 1. تصدير قاعدة البيانات كـ JSON
echo "📦 Exporting database to JSON..."
python3 -c "
import sqlite3, json, os
DB = '/opt/data/mustafa-mixing-archive/mustafa_mixing.db'
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
tables = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table' ORDER BY name\").fetchall()
export = {}
for t in tables:
    name = t[0]
    rows = conn.execute(f'SELECT * FROM [{name}]').fetchall()
    export[name] = [dict(r) for r in rows]
with open('/opt/data/mustafa-mixing-archive/db_export.json', 'w', encoding='utf-8') as f:
    json.dump(export, f, ensure_ascii=False, indent=2, default=str)
conn.close()
total = sum(len(v) for v in export.values())
print(f'✅ Exported {total} records to db_export.json')
"

# 2. Git add + commit + push
git add -A
if ! git diff --cached --quiet; then
    git commit -m "Auto-update $(date '+%Y-%m-%d %H:%M UTC')"
    git push origin master
    echo "✅ Pushed to GitHub"
else
    echo "✅ No changes to push"
fi
