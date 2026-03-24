import sqlite3

con = sqlite3.connect('data/cnpj_database.db')
cur = con.cursor()
cur.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='socios'")
rows = cur.fetchall()
print('idx_count', len(rows))
for name, sql in rows[:50]:
    print(name, '|', (sql or '')[:160])
con.close()
