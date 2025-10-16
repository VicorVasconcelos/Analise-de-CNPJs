import sqlite3
import json
import os
import sys

result = {}

db_path = r"c:\Users\victor.vasconcelos\Documents\Dashboard\cnpj_database.db"
if not os.path.exists(db_path):
    result['error'] = 'db_missing'
    result['db_path'] = db_path
    print(json.dumps(result))
    sys.exit(0)

conn = sqlite3.connect(db_path)
c = conn.cursor()
# check if socios table exists
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='socios'")
if not c.fetchone():
    result['socios_exists'] = False
    conn.close()
    print(json.dumps(result))
    sys.exit(0)

result['socios_exists'] = True
# count rows
c.execute('SELECT COUNT(*) FROM socios')
result['count'] = c.fetchone()[0]
# columns
result['columns'] = [r[1] for r in c.execute('PRAGMA table_info(socios)')]
# sample
c.execute('SELECT * FROM socios LIMIT 5')
rows = c.fetchall()
# convert rows to list of lists for JSON
result['sample_first_5'] = [list(r) for r in rows]

conn.close()
print(json.dumps(result, ensure_ascii=False))
