import sqlite3

conn = sqlite3.connect('cnpj_database.db')
cur = conn.cursor()

print('PRAGMA table_info(socios):')
try:
    cur.execute("PRAGMA table_info(socios)")
    for r in cur.fetchall():
        print(r)
except Exception as e:
    print('Error reading table_info:', e)

print('\nCounts:')
try:
    cur.execute('SELECT COUNT(*) FROM socios')
    total = cur.fetchone()[0]
    print('total socios rows:', total)
    cur.execute("SELECT COUNT(*) FROM socios WHERE nome_socio IS NOT NULL AND TRIM(nome_socio) != ''")
    nome_count = cur.fetchone()[0]
    print('rows with nome_socio:', nome_count)
    cur.execute("SELECT COUNT(*) FROM socios WHERE qualificacao_socio IS NOT NULL AND TRIM(qualificacao_socio) != ''")
    qual_count = cur.fetchone()[0]
    print('rows with qualificacao_socio:', qual_count)
    cur.execute("SELECT COUNT(*) FROM socios WHERE cnpj_cpf_socio IS NOT NULL AND TRIM(cnpj_cpf_socio) != ''")
    cpf_count = cur.fetchone()[0]
    print('rows with cnpj_cpf_socio:', cpf_count)
except Exception as e:
    print('Error counting:', e)

print('\nSample rows where nome_socio present but qualificacao_socio empty:')
try:
    cur.execute("SELECT cnpj_basico, nome_socio, qualificacao_socio, cnpj_cpf_socio FROM socios WHERE nome_socio IS NOT NULL AND TRIM(nome_socio) != '' AND (qualificacao_socio IS NULL OR TRIM(qualificacao_socio) = '') LIMIT 20")
    for r in cur.fetchall():
        print(r)
except Exception as e:
    print('Error sampling:', e)

print('\nDistinct qualificacao_socio values (non-empty):')
try:
    cur.execute("SELECT DISTINCT qualificacao_socio FROM socios WHERE qualificacao_socio IS NOT NULL AND TRIM(qualificacao_socio) != '' LIMIT 50")
    print(cur.fetchall())
except Exception as e:
    print('Error distinct:', e)

conn.close()
