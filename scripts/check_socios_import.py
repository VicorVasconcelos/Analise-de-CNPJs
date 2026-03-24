"""
Script para verificar a importação da tabela de sócios
"""
import sqlite3
from pathlib import Path

db_path = Path("data/cnpj_database.db")

if not db_path.exists():
    print(f"Banco de dados não encontrado: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("VERIFICAÇÃO DA IMPORTAÇÃO DE SÓCIOS")
print("=" * 80)

# Total de registros
cursor.execute('SELECT COUNT(*) FROM socios')
count = cursor.fetchone()[0]
print(f'\nTotal de registros na tabela socios: {count:,}')

# CNPJ distintos
cursor.execute('SELECT COUNT(DISTINCT cnpj_basico) FROM socios')
distinct_cnpj = cursor.fetchone()[0]
print(f'Total de CNPJ distintos com sócios: {distinct_cnpj:,}')

# Distribuição por tipo de sócio
print('\nDistribuição por tipo de sócio:')
cursor.execute('SELECT identificador_socio, COUNT(*) as total FROM socios GROUP BY identificador_socio ORDER BY total DESC')
tipos = cursor.fetchall()
for tipo, total in tipos:
    print(f'  Tipo {tipo}: {total:,}')

# Qualificações mais comuns
print('\nTop 10 qualificações de sócios mais comuns:')
cursor.execute('''
    SELECT qualificacao_socio, COUNT(*) as total 
    FROM socios 
    GROUP BY qualificacao_socio 
    ORDER BY total DESC 
    LIMIT 10
''')
quals = cursor.fetchall()
for qual, total in quals:
    print(f'  Qualificação {qual}: {total:,}')

# Verificar registros com representante legal
cursor.execute('SELECT COUNT(*) FROM socios WHERE representante_legal IS NOT NULL AND representante_legal != ""')
com_repr = cursor.fetchone()[0]
print(f'\nRegistros com representante legal: {com_repr:,}')

# Verificar alguns exemplos
print('\nExemplos de registros (5 primeiros):')
cursor.execute('SELECT cnpj_basico, identificador_socio, nome_socio, qualificacao_socio FROM socios LIMIT 5')
examples = cursor.fetchall()
for ex in examples:
    print(f'  CNPJ: {ex[0]}, Tipo: {ex[1]}, Nome: {ex[2]}, Qualif: {ex[3]}')

conn.close()
print("\n" + "=" * 80)
