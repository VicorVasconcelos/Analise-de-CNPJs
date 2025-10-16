"""
Diagnóstico rápido da tabela `socios` e da tabela `qualificacoes`.
Imprime contagens e amostras para entender por que exportações não trazem dados de sócios.
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cnpj_database.db')

conn = sqlite3.connect(DB)
cur = conn.cursor()

print('Banco:', DB)

# Check socios existence
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='socios'")
if not cur.fetchone():
    print('Tabela `socios` NÃO encontrada no banco')
    conn.close()
    raise SystemExit(1)

# Counts
cur.execute('SELECT COUNT(*) FROM socios')
total = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM socios WHERE nome_socio IS NOT NULL AND TRIM(nome_socio) != ''")
with_name = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM socios WHERE cnpj_cpf_socio IS NOT NULL AND TRIM(cnpj_cpf_socio) != ''")
with_cpf = cur.fetchone()[0]
cur.execute("SELECT COUNT(DISTINCT cnpj_basico) FROM socios")
distinct_cnpj = cur.fetchone()[0]

print('\nResumo da tabela `socios`:')
print(' total rows:', total)
print(' linhas com nome_socio não vazio:', with_name)
print(' linhas com cnpj_cpf_socio não vazio:', with_cpf)
print(' distinct cnpj_basico in socios:', distinct_cnpj)

# Show sample rows where nome or cpf present
print('\nAmostra (até 20) de rows com nome_socio ou cnpj_cpf_socio não vazios:')
cur.execute("SELECT cnpj_basico, nome_socio, cnpj_cpf_socio, qualificacao_socio FROM socios WHERE (nome_socio IS NOT NULL AND TRIM(nome_socio) != '') OR (cnpj_cpf_socio IS NOT NULL AND TRIM(cnpj_cpf_socio) != '') LIMIT 20")
rows = cur.fetchall()
if not rows:
    print(' (nenhuma linha com nome/CPF não vazio encontrada)')
else:
    for r in rows:
        print(' ', r)

# Check how many cnpj_basico in estabelecimentos_completos have matching socios rows
cur.execute('SELECT COUNT(DISTINCT est.cnpj_basico) FROM estabelecimentos_completos est JOIN socios s ON s.cnpj_basico = est.cnpj_basico')
cnpj_with_socios = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM estabelecimentos_completos')
total_est = cur.fetchone()[0]
print(f"\nEmpresas com pelo menos 1 row em socios: {cnpj_with_socios} (de {total_est} estabelecimentos)")

# Show distinct qualificacao_socio values and sample mapping
print('\nDistinct qualificacao_socio values (sample up to 50):')
cur.execute("SELECT DISTINCT qualificacao_socio FROM socios WHERE qualificacao_socio IS NOT NULL AND TRIM(qualificacao_socio) != '' LIMIT 50")
distinct_quals = [r[0] for r in cur.fetchall()]
if distinct_quals:
    print(' ', distinct_quals)
else:
    print('  (nenhum codigo não vazio encontrado na coluna qualificacao_socio)')

print('\nVerificando tabela qualificacoes (lookup):')
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='qualificacoes'")
if cur.fetchone():
    cur.execute('SELECT codigo_qualificacao, descricao_qualificacao FROM qualificacoes ORDER BY codigo_qualificacao LIMIT 200')
    for code, desc in cur.fetchall():
        print(f'  {str(code).zfill(2)} -> {desc}')
else:
    print('  tabela `qualificacoes` não encontrada')

# Check if socios cnpj_cpf_socio values look masked (contain '*') sample
print('\nAmostra de cnpj_cpf_socio contendo "*" (até 20):')
cur.execute("SELECT cnpj_basico, cnpj_cpf_socio FROM socios WHERE cnpj_cpf_socio LIKE '%*%' LIMIT 20")
rows = cur.fetchall()
if rows:
    for r in rows:
        print(' ', r)
else:
    print('  (nenhum valor com "*" encontrado)')

conn.close()
print('\nFim do diagnóstico')
