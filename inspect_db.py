import sqlite3
DB='cnpj_database.db'
print('Connecting to',DB)
conn=sqlite3.connect(DB)
cur=conn.cursor()

print('\nTables:')
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
for row in cur.fetchall():
    print(' -',row[0])

print('\nIndexes (first 200):')
cur.execute("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' ORDER BY tbl_name LIMIT 200")
for name,tbl,sql in cur.fetchall():
    print(f' - {tbl}.{name} ->', 'sql: '+(sql[:200] if sql else ''))

# Check for aggregates
for agg in ['aggregates_ufs','aggregates_cnaes']:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (agg,))
    exists = cur.fetchone() is not None
    print(f"\n{agg}:", 'FOUND' if exists else 'MISSING')

# Count rows in small reference tables (fast)
for t in ['cnaes','naturezas','municipios']:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,))
    if cur.fetchone():
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"{t} rows:", cur.fetchone()[0])

conn.close()
print('\nDone')
