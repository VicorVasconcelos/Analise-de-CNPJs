"""
Script para verificar views no banco
"""
import sqlite3

conn = sqlite3.connect('data/cnpj_database.db')
cursor = conn.cursor()

cursor.execute("SELECT name, type FROM sqlite_master WHERE name LIKE '%completo%' OR name LIKE '%completa%'")
print('Tabelas/Views encontradas:')
for row in cursor.fetchall():
    print(f'  {row[0]} ({row[1]})')

conn.close()
