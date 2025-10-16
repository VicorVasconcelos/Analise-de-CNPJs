"""
Gera uma exportação de exemplo usando a mesma lógica de `app.py`, mas forçando o filtro `socios_present`=True.
Grava um CSV no diretório do projeto com nome `cnpj_exportacao_test_with_socios.csv`.
Uso: python generate_export_with_socios.py
"""
import sqlite3
import pandas as pd
import time
import os
from datetime import datetime

DB = 'cnpj_database.db'
OUT = 'cnpj_exportacao_test_with_socios.csv'

# SQL extracted from app.py, with removed CNPJ column
SQL = '''
    SELECT DISTINCT
        CASE WHEN est.cnpj_basico IS NOT NULL AND est.cnpj_ordem IS NOT NULL AND est.cnpj_dv IS NOT NULL
            THEN SUBSTR(est.cnpj_basico,1,2) || '.' || SUBSTR(est.cnpj_basico,3,3) || '.' || SUBSTR(est.cnpj_basico,6,3) || '/' || est.cnpj_ordem || '-' || est.cnpj_dv
            ELSE est.cnpj_basico
        END as cnpj,
        COALESCE(e.razao_social, '') as razao_social,
        COALESCE(est.nome_fantasia, '') as nome_fantasia,
        CASE 
            WHEN est.situacao_cadastral = '02' THEN 'ATIVA'
            WHEN est.situacao_cadastral = '03' THEN 'SUSPENSA'
            WHEN est.situacao_cadastral = '04' THEN 'INAPTA'
            WHEN est.situacao_cadastral = '08' THEN 'BAIXADA'
            ELSE 'NÃO INFORMADO'
        END as situacao_empresa,
        CASE 
            WHEN LENGTH(est.data_situacao_cadastral) = 8 THEN
                SUBSTR(est.data_situacao_cadastral, 7, 2) || '/' ||
                SUBSTR(est.data_situacao_cadastral, 5, 2) || '/' ||
                SUBSTR(est.data_situacao_cadastral, 1, 4)
            ELSE COALESCE(est.data_situacao_cadastral, '')
        END as data_situacao,
        TRIM(
            COALESCE(est.tipo_logradouro || ' ', '') ||
            COALESCE(est.logradouro, '') ||
            CASE WHEN est.numero IS NOT NULL AND est.numero != '' 
                 THEN ', nº ' || est.numero ELSE '' END ||
            CASE WHEN est.complemento IS NOT NULL AND est.complemento != '' 
                 THEN ' (' || est.complemento || ')' ELSE '' END
        ) as endereco_completo,
        CASE 
            WHEN LENGTH(est.cep) >= 8 THEN
                SUBSTR(est.cep, 1, 5) || '-' || SUBSTR(est.cep, 6, 3)
            ELSE COALESCE(est.cep, '')
        END as cep,
        est.uf,
        COALESCE(m.nome_municipio, '') as nome_municipio,
        CASE 
            WHEN est.ddd_1 IS NOT NULL AND est.telefone_1 IS NOT NULL THEN
                '(' || est.ddd_1 || ') ' ||
                CASE 
                    WHEN LENGTH(est.telefone_1) = 9 THEN
                        SUBSTR(est.telefone_1, 1, 5) || '-' || SUBSTR(est.telefone_1, 6, 4)
                    WHEN LENGTH(est.telefone_1) = 8 THEN
                        SUBSTR(est.telefone_1, 1, 4) || '-' || SUBSTR(est.telefone_1, 5, 4)
                    ELSE est.telefone_1
                END
            ELSE ''
        END as telefone_formatado,
        COALESCE(est.correio_eletronico, '') as email,
        COALESCE(c.descricao_cnae, '') as descricao_cnae,
        COALESCE(nat.descricao_natureza, '') as descricao_natureza,
        COALESCE(est.bairro, '') as bairro,
    CASE WHEN s.opcao_mei = 'S' THEN 'Microempreendedor Individual (MEI)'
        WHEN e.porte IN ('49', '50') THEN 'Microempresa (ME)'
        WHEN e.porte IN ('05', '16', '17', '19') THEN 'Empresa de Pequeno Porte (EPP)'
        WHEN e.porte IN ('43', '34', '65', '59') THEN 'Empresa de Médio Porte'
        WHEN e.porte NOT IN ('49', '50', '05', '16', '17', '19', '43', '34', '65', '59') 
            AND e.porte IS NOT NULL AND e.porte != '' THEN 'Grande Empresa'
             ELSE 'Não Informado' END as porte,
        CASE 
            WHEN e.capital_social IS NOT NULL AND e.capital_social != '' AND e.capital_social != '0' THEN
                'R$ ' || REPLACE(
                    printf("%.2f", CAST(e.capital_social AS REAL) / 100.0),
                    '.', ','
                )
            ELSE 'Não Informado'
        END as capital_social,
        CASE WHEN s.opcao_simples = 'S' THEN 'Sim' WHEN s.opcao_simples = 'N' THEN 'Não' ELSE 'N/A' END as opcao_simples,
        CASE WHEN s.opcao_mei = 'S' THEN 'Sim' WHEN s.opcao_mei = 'N' THEN 'Não' ELSE 'N/A' END as opcao_mei,
    CASE WHEN est.identificador_matriz_filial = '1' THEN 'Matriz' WHEN est.identificador_matriz_filial = '2' THEN 'Filial' ELSE 'N/A' END as matriz_filial,
    COALESCE(socios_agg.nome_socio, '') as nome_socio,
    COALESCE(socios_agg.qualificacao_socio, '') as qualificacao_socio,
    COALESCE(socios_agg.cnpj_cpf_socio, '') as cpf_masked
    FROM estabelecimentos_completos est
    LEFT JOIN empresas_completas e ON est.cnpj_basico = e.cnpj_basico
    LEFT JOIN simples s ON est.cnpj_basico = s.cnpj_basico
    LEFT JOIN cnaes c ON est.cnae_fiscal_principal = c.codigo_cnae
    LEFT JOIN naturezas nat ON e.natureza_juridica = nat.codigo_natureza
    LEFT JOIN municipios m ON est.municipio = m.codigo_municipio
    LEFT JOIN (
        -- pick the first socio per cnpj_basico using min(rowid)
        SELECT s.cnpj_basico, s.nome_socio, s.qualificacao_socio, s.cnpj_cpf_socio
        FROM socios s
        INNER JOIN (
            SELECT cnpj_basico, MIN(rowid) AS min_rowid FROM socios GROUP BY cnpj_basico
        ) f ON f.cnpj_basico = s.cnpj_basico AND f.min_rowid = s.rowid
    ) as socios_agg ON socios_agg.cnpj_basico = e.cnpj_basico
    WHERE EXISTS (SELECT 1 FROM socios s2 WHERE s2.cnpj_basico = est.cnpj_basico)
    ORDER BY e.razao_social, est.cnpj_ordem
'''

HEADERS = [
    'CNPJ', 'RAZAO_SOCIAL', 'NOME_FANTASIA', 'SITUACAO_EMPRESA', 'DATA_SITUACAO',
    'ENDERECO_COMPLETO', 'CEP', 'UF', 'NOME_MUNICIPIO', 'TELEFONE_FORMATADO',
    'EMAIL', 'DESCRICAO_CNAE', 'DESCRICAO_NATUREZA', 'BAIRRO', 'PORTE',
    'CAPITAL_SOCIAL', 'OPCAO_SIMPLES', 'OPCAO_MEI', 'MATRIZ_FILIAL',
    'NOME_SOCIO', 'QUALIFICACAO_SOCIO', 'CPF_SOCIO'
]


def load_proposals(path='socios_updates_proposals.csv'):
    import csv
    proposals = {}
    if not os.path.exists(path):
        return proposals
    with open(path, 'r', encoding='utf-8') as fh:
        reader = csv.DictReader(fh, delimiter=';')
        for r in reader:
            cnpj = r.get('cnpj_basico')
            if not cnpj:
                continue
            proposals[cnpj] = {
                'nome': r.get('proposed_nome') or '',
                'cpf_mask': r.get('proposed_cpf_mask') or '',
                'qual': r.get('proposed_qual') or ''
            }
    return proposals


def main():
    if not os.path.exists(DB):
        print('Banco não encontrado:', DB)
        return 1
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    # carregar mapa de qualificacoes
    qual_map = {}
    try:
        cur.execute("SELECT codigo_qualificacao, descricao_qualificacao FROM qualificacoes")
        qual_map = {str(code).zfill(2): desc for code, desc in cur.fetchall()}
    except Exception:
        pass

    proposals = load_proposals()

    start = time.time()
    cur.execute(SQL)

    # Stream rows to CSV to avoid high memory usage
    import csv
    written = 0
    with open(OUT, 'w', newline='', encoding='utf-8-sig') as fh:
        writer = csv.writer(fh, delimiter=';')
        writer.writerow(HEADERS)
        while True:
            r = cur.fetchone()
            if r is None:
                break
            cnpj = r[0]
            razao = r[1]
            nome_fant = r[2]
            situ = r[3]
            data_sit = r[4]
            endereco = r[5]
            cep = r[6]
            uf = r[7]
            nome_mun = r[8]
            tel = r[9]
            email = r[10]
            desc_cnae = r[11]
            desc_nat = r[12]
            bairro = r[13]
            porte = r[14]
            capital = r[15]
            op_simples = r[16]
            op_mei = r[17]
            matriz = r[18]
            nome_soc = r[19]
            qual = r[20]
            cpf_masked = r[21]

            # aplicar propostas quando existirem
            if cnpj in proposals:
                p = proposals[cnpj]
                if p.get('nome'):
                    nome_soc = p['nome']
                if p.get('cpf_mask'):
                    cpf_masked = p['cpf_mask']
                if p.get('qual'):
                    qual = p['qual']

            # traduzir qualificacao para descricao
            qual_desc = qual_map.get(str(qual).zfill(2), qual)

            writer.writerow([
                cnpj, razao, nome_fant, situ, data_sit, endereco, cep, uf, nome_mun,
                tel, email, desc_cnae, desc_nat, bairro, porte, capital, op_simples,
                op_mei, matriz, nome_soc, qual_desc, cpf_masked
            ])
            written += 1
            # test-mode: stop after 100 rows to validate output quickly
            if written >= 100:
                break

    elapsed = time.time() - start
    print(f'Export gerada: {OUT} com {written} registros em {elapsed:.2f}s')
    conn.close()
    return 0

if __name__ == '__main__':
    main()
