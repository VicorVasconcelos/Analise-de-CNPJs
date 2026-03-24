"""
Script para verificar tabelas no banco de dados
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
print("TABELAS NO BANCO DE DADOS")
print("=" * 80)

# Listar todas as tabelas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()

print(f"\nTotal de tabelas: {len(tables)}\n")

for table in tables:
    table_name = table[0]
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f"  {table_name}: {count:,} registros")

conn.close()
print("\n" + "=" * 80)
