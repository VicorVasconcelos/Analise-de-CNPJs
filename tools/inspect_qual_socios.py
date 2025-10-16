import sqlite3, json
cnpjs=['42630573','48477551','56140865','61808492','58285950','55623009','62449767','57257910','62134347','55347134']
conn=sqlite3.connect('cnpj_database.db')
cur=conn.cursor()
print('qualificacoes count:')
try:
    cur.execute('SELECT COUNT(*) FROM qualificacoes')
    print(cur.fetchone()[0])
except Exception as e:
    print('qualificacoes table error', e)

print('\nsample socios rows:')
for c in cnpjs:
    cur.execute('SELECT cnpj_basico, nome_socio, qualificacao_socio, cnpj_cpf_socio FROM socios WHERE cnpj_basico = ? LIMIT 5', (c,))
    rows = cur.fetchall()
    print(c, rows[:5])
conn.close()
