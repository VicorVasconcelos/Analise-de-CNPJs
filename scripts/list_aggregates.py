import sqlite3
DB='data/cnpj_database.db'
conn=sqlite3.connect(DB)
cur=conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'aggregates_%' ORDER BY name")
tables=[r[0] for r in cur.fetchall()]
print('Found tables:', tables)
for t in tables:
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    print(t, 'rows=', cur.fetchone()[0])
conn.close()
