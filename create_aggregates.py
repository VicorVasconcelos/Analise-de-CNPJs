import sqlite3
import time

DB = 'cnpj_database.db'

queries = {
    'aggregates_ufs': '''
        CREATE TABLE IF NOT EXISTS aggregates_ufs AS
        SELECT uf, COUNT(*) as total_estabelecimentos
        FROM estabelecimentos_completos
        WHERE uf IS NOT NULL AND uf != ''
        GROUP BY uf
    ''',

    'aggregates_cnaes': '''
        CREATE TABLE IF NOT EXISTS aggregates_cnaes AS
        SELECT e.cnae_fiscal_principal as codigo_cnae, c.descricao_cnae, COUNT(*) as total
        FROM estabelecimentos_completos e
        LEFT JOIN cnaes c ON e.cnae_fiscal_principal = c.codigo_cnae
        WHERE e.cnae_fiscal_principal IS NOT NULL AND e.cnae_fiscal_principal != ''
        GROUP BY e.cnae_fiscal_principal
    '''

    , 'aggregates_meta': '''
        CREATE TABLE IF NOT EXISTS aggregates_meta AS
        SELECT 
            (SELECT COUNT(*) FROM empresas_completas) as total_empresas,
            (SELECT COUNT(*) FROM estabelecimentos_completos) as total_estabelecimentos,
            (SELECT COUNT(*) FROM simples) as total_simples,
            (SELECT COUNT(*) FROM cnaes) as total_cnaes
    ''',

    'aggregates_portes': '''
        CREATE TABLE IF NOT EXISTS aggregates_portes AS
        SELECT
            CASE
                WHEN opcao_mei = 'S' THEN 'MEI'
                WHEN porte IN ('49','50') THEN 'MICRO'
                WHEN porte IN ('05','16','17','19') THEN 'PEQUENO'
                WHEN porte IN ('43','34','65','59') THEN 'MEDIO'
                WHEN porte IS NOT NULL AND porte != '' THEN 'GRANDE'
                ELSE 'NAO_INFORMADO'
            END as porte_key,
            COUNT(*) as total
        FROM empresas_completas e
        LEFT JOIN simples s ON e.cnpj_basico = s.cnpj_basico
        GROUP BY porte_key
    ''',

    'aggregates_simples': '''
        CREATE TABLE IF NOT EXISTS aggregates_simples AS
        SELECT opcao_simples as opcao, COUNT(*) as total
        FROM simples
        GROUP BY opcao_simples
    ''',

    'aggregates_naturezas': '''
        CREATE TABLE IF NOT EXISTS aggregates_naturezas AS
        SELECT n.codigo_natureza, n.descricao_natureza, COUNT(*) as total
        FROM empresas_completas e
        LEFT JOIN naturezas n ON e.natureza_juridica = n.codigo_natureza
        GROUP BY n.codigo_natureza, n.descricao_natureza
        ORDER BY total DESC
    '''
}

if __name__ == '__main__':
    start = time.time()
    conn = sqlite3.connect(DB)
    conn.execute('PRAGMA journal_mode = WAL')
    conn.execute('PRAGMA synchronous = NORMAL')
    conn.execute('PRAGMA temp_store = MEMORY')
    cursor = conn.cursor()

    for name, q in queries.items():
        print(f'Criando/atualizando {name}...')
        t0 = time.time()
        cursor.execute(f'DROP TABLE IF EXISTS {name}')
        conn.commit()
        cursor.execute(q)
        conn.commit()
        t1 = time.time()
        print(f'  {name} criado em {t1 - t0:.2f}s')

    conn.close()
    print(f'Total: {time.time() - start:.2f}s')
