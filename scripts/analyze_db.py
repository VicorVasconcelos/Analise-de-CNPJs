import sqlite3

con = sqlite3.connect('data/cnpj_database.db')
cur = con.cursor()
print('Running ANALYZE...')
cur.execute('ANALYZE')
con.commit()
con.close()
print('ANALYZE complete')
