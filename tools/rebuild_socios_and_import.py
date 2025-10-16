import os
import shutil
import sqlite3
from datetime import datetime
import subprocess

DB_PATH = os.path.abspath('cnpj_database.db')

def backup_db():
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    dst = DB_PATH + f'.bak_{ts}'
    print('Criando backup do banco:', dst)
    shutil.copy2(DB_PATH, dst)
    return dst

def backup_socios_table(conn):
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    cur = conn.cursor()
    # check if socios exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='socios'")
    if cur.fetchone():
        backup_name = f'socios_backup_{ts}'
        print('Criando tabela de backup:', backup_name)
        cur.execute(f"CREATE TABLE IF NOT EXISTS {backup_name} AS SELECT * FROM socios")
        conn.commit()
        print('Backup da tabela socios criado com sucesso.')
        return backup_name
    else:
        print('Tabela socios não existe; nada a backupar.')
        return None

def drop_and_recreate_socios(conn):
    cur = conn.cursor()
    # drop old table if exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='socios'")
    if cur.fetchone():
        print('Removendo tabela socios existente...')
        cur.execute('DROP TABLE socios')
        conn.commit()

    print('Criando nova tabela socios com esquema mínimo...')
    cur.execute('''CREATE TABLE socios (
        cnpj_basico TEXT,
        cnpj_completo TEXT,
        nome_socio TEXT,
        cnpj_cpf_socio TEXT,
        qualificacao_socio TEXT
    )''')
    conn.commit()
    print('Tabela socios recriada (vazia).')

def run_import():
    # run import_data.py --only socios
    cmd = ['python', 'import_data.py', '--only', 'socios']
    print('Executando import:',' '.join(cmd))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        for line in proc.stdout:
            print(line, end='')
    except Exception as e:
        print('Erro lendo output do import:', e)
    proc.wait()
    return proc.returncode

def main():
    if not os.path.exists(DB_PATH):
        print('Banco não encontrado:', DB_PATH)
        return 1

    # 1) Backup file
    bak = backup_db()

    # 2) Connect and backup socios table
    conn = sqlite3.connect(DB_PATH)
    try:
        backup_name = backup_socios_table(conn)
        # 3) Drop and recreate socios table
        drop_and_recreate_socios(conn)
    finally:
        conn.close()

    # 4) Run importer
    rc = run_import()
    if rc == 0:
        print('\nImport concluído com código 0 (sucesso esperado).')
    else:
        print(f'Import terminou com código {rc} (verifique logs).')

    print('Operação finalizada. Backup do DB em:', bak)
    return rc

if __name__ == '__main__':
    exit(main())
import os
import shutil
import sqlite3
from datetime import datetime
import subprocess

DB = 'cnpj_database.db'

def backup_db():
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    bak = f'cnpj_database.db.bak_{ts}'
    shutil.copyfile(DB, bak)
    print('Backup criado:', bak)
    return bak

def rename_socios_table():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='socios'")
    if cur.fetchone():
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        newname = f'socios_backup_{ts}'
        cur.execute(f'ALTER TABLE socios RENAME TO {newname}')
        conn.commit()
        print('Tabela socios renomeada para', newname)
    else:
        print('Tabela socios não existe; nada a renomear')
    conn.close()

def recreate_socios_table():
    # Use database.py to create the socios table schema
    from database import CNPJDatabase
    db = CNPJDatabase(DB)
    db.connect()
    cur = db.connection.cursor()
    # create table socios if not exists with the expected schema
    cur.execute('''CREATE TABLE IF NOT EXISTS socios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cnpj_basico TEXT NOT NULL,
        cnpj_completo TEXT,
        identificador_socio TEXT,
        nome_socio TEXT,
        cnpj_cpf_socio TEXT,
        qualificacao_socio TEXT,
        data_entrada_sociedade TEXT,
        pais TEXT,
        representante_legal TEXT,
        nome_representante TEXT,
        qualificacao_representante TEXT,
        faixa_etaria TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    db.connection.commit()
    db.disconnect()
    print('Tabela socios (limpa) criada')

def run_import():
    print('Iniciando import_data.py --only socios')
    res = subprocess.run(['python', 'import_data.py', '--only', 'socios'], capture_output=True, text=True)
    print('STDOUT:')
    print(res.stdout)
    print('STDERR:')
    print(res.stderr)
    return res.returncode

def main():
    if not os.path.exists(DB):
        print('Banco não encontrado:', DB)
        return 1
    bak = backup_db()
    rename_socios_table()
    recreate_socios_table()
    rc = run_import()
    if rc == 0:
        print('Import concluído com sucesso')
    else:
        print('Import finalizado com código:', rc)

if __name__ == '__main__':
    main()
