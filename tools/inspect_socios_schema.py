import sqlite3
conn=sqlite3.connect('cnpj_database.db')
cur=conn.cursor()
cur.execute('PRAGMA table_info(socios)')
print('PRAGMA table_info(socios):')
for r in cur.fetchall():
    print(r)

cur.execute('SELECT rowid, * FROM socios LIMIT 5')
print('\nFirst 5 rows (raw):')
for r in cur.fetchall():
    print(r)
conn.close()
