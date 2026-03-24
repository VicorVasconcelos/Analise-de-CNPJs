"""
Script para criar as views necessárias no banco de dados
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
print("CRIANDO VIEWS NO BANCO DE DADOS")
print("=" * 80)

# Criar view empresas_completas (apenas um alias para empresas)
print("\n1. Criando view empresas_completas...")
cursor.execute("DROP VIEW IF EXISTS empresas_completas")
cursor.execute("""
    CREATE VIEW empresas_completas AS
    SELECT * FROM empresas
""")
print("   ✓ View empresas_completas criada")

# Criar view estabelecimentos_completos (apenas um alias para estabelecimentos)
print("\n2. Criando view estabelecimentos_completos...")
cursor.execute("DROP VIEW IF EXISTS estabelecimentos_completos")
cursor.execute("""
    CREATE VIEW estabelecimentos_completos AS
    SELECT * FROM estabelecimentos
""")
print("   ✓ View estabelecimentos_completos criada")

conn.commit()
conn.close()

print("\n" + "=" * 80)
print("VIEWS CRIADAS COM SUCESSO!")
print("=" * 80)
