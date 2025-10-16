import sqlite3

conn = sqlite3.connect('cnpj_database.db')
cur = conn.cursor()

print('Distinct non-empty qualificacao_socio (sample up to 50):')
cur.execute("SELECT qualificacao_socio, COUNT(*) as cnt FROM socios WHERE qualificacao_socio IS NOT NULL AND TRIM(qualificacao_socio) != '' GROUP BY qualificacao_socio ORDER BY cnt DESC LIMIT 50")
rows = cur.fetchall()
if not rows:
    print('  (none)')
else:
    for q,c in rows:
        print(f'  {q} -> {c}')

print('\nqualificacoes table exists?')
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='qualificacoes'")
if cur.fetchone():
    print(' yes - sample mappings (up to 50):')
    cur.execute('SELECT codigo_qualificacao, descricao_qualificacao FROM qualificacoes LIMIT 50')
    for code, desc in cur.fetchall():
        print(f'  {code} -> {desc}')
else:
    print(' no')

conn.close()
