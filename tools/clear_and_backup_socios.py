from database import CNPJDatabase
import time

def main():
    db = CNPJDatabase('cnpj_database.db')
    if not db.connect():
        print('Erro ao conectar ao DB')
        return
    cur = db.connection.cursor()
    ts = time.strftime('%Y%m%d_%H%M%S')
    backup_name = f'socios_backup_{ts}'
    try:
        cur.execute(f"CREATE TABLE IF NOT EXISTS {backup_name} AS SELECT * FROM socios")
        db.connection.commit()
        print(f'Backup criado: {backup_name}')
        cur.execute('DELETE FROM socios')
        db.connection.commit()
        print('Tabela socios limpa (todos os registros removidos)')
    except Exception as e:
        print('Erro durante backup/limpeza:', e)
    finally:
        db.disconnect()

if __name__ == '__main__':
    main()
