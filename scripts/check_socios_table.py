import sqlite3

con = sqlite3.connect('data/cnpj_database.db')
cur = con.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='socios'")
has = cur.fetchone() is not None
print('has_socios_table', has)
if has:
    cur.execute('SELECT COUNT(*) FROM socios')
    print('socios_count', cur.fetchone()[0])
con.close()
