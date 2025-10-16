import os, sys, time, json
from datetime import datetime
import pandas as pd
import sys
sys.path.insert(0, os.getcwd())
from database import CNPJDatabase

# This script reproduces the /export logic internally without HTTP server.
# It applies filters {'uf':'DF','socios_present': True} and writes the CSV to working dir.

def run_export(filters):
    db = CNPJDatabase('cnpj_database.db')
    if not db.connect():
        print('DB connect failed')
        return
    conn = db.connection
    cursor = conn.cursor()

    # copy of build_where_and_params minimal for our filters
    where_clauses = []
    params = []
    if filters.get('uf'):
        where_clauses.append('est.uf = ?')
        params.append(filters['uf'])
    if filters.get('socios_present'):
        where_clauses.append("EXISTS (SELECT 1 FROM socios s2 WHERE s2.cnpj_basico = est.cnpj_basico)")

    where_sql = ' AND '.join(where_clauses) if where_clauses else '1=1'

    # Check socios table
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='socios'")
    has_socios = cur.fetchone() is not None
    socios_join = ''
    if has_socios:
        socios_select = (
            "COALESCE(socios_agg.socios_nomes, '') as nome_socio, "
            "COALESCE(socios_agg.socios_quals, '') as qualificacao_socio, "
            "COALESCE(socios_agg.socios_cpfs_mid6, '') as cpf_mid6"
        )
        socios_join = ("\nLEFT JOIN (\n SELECT cnpj_basico, GROUP_CONCAT(nome_socio, ' | ') as socios_nomes, GROUP_CONCAT(qualificacao_socio, ' | ') as socios_quals, GROUP_CONCAT(\n                            CASE WHEN instr(cnpj_cpf_socio, '*') > 0 THEN REPLACE(cnpj_cpf_socio, '*', '') WHEN LENGTH(COALESCE(cnpj_cpf_socio, '')) >= 11 THEN SUBSTR(cnpj_cpf_socio, 4, 6) ELSE '' END, ' | ') as socios_cpfs_mid6 FROM socios GROUP BY cnpj_basico\n) as socios_agg ON socios_agg.cnpj_basico = e.cnpj_basico")
    else:
        socios_select = "'' as nome_socio, '' as qualificacao_socio, '' as cnpj_cpf_socio"

    sql = f"""
    SELECT DISTINCT
        SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 1, 2) || '.' ||
        SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 3, 3) || '.' ||
        SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 6, 3) || '/' ||
        SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 9, 4) || '-' ||
        SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 13, 2) as cnpj,
        COALESCE(e.razao_social, '') as razao_social,
        COALESCE(est.nome_fantasia, '') as nome_fantasia,
        CASE WHEN est.situacao_cadastral = '02' THEN 'ATIVA' ELSE 'NÃO INFORMADO' END as situacao_empresa,
        CASE WHEN LENGTH(est.data_situacao_cadastral) = 8 THEN SUBSTR(est.data_situacao_cadastral, 7, 2) || '/' || SUBSTR(est.data_situacao_cadastral, 5, 2) || '/' || SUBSTR(est.data_situacao_cadastral, 1, 4) ELSE COALESCE(est.data_situacao_cadastral, '') END as data_situacao,
    -- motivo_situacao_cadastral removed from export
        TRIM(COALESCE(est.tipo_logradouro || ' ', '') || COALESCE(est.logradouro, '') || CASE WHEN est.numero IS NOT NULL AND est.numero != '' THEN ', nº ' || est.numero ELSE '' END || CASE WHEN est.complemento IS NOT NULL AND est.complemento != '' THEN ' (' || est.complemento || ')' ELSE '' END) as endereco_completo,
        COALESCE(est.bairro, '') as bairro,
        CASE WHEN LENGTH(est.cep) >= 8 THEN SUBSTR(est.cep, 1, 5) || '-' || SUBSTR(est.cep, 6, 3) ELSE COALESCE(est.cep, '') END as cep,
        est.uf,
        COALESCE(m.nome_municipio, '') as nome_municipio,
        CASE WHEN est.ddd_1 IS NOT NULL AND est.telefone_1 IS NOT NULL THEN '(' || est.ddd_1 || ') ' || CASE WHEN LENGTH(est.telefone_1) = 9 THEN SUBSTR(est.telefone_1, 1, 5) || '-' || SUBSTR(est.telefone_1, 6, 4) WHEN LENGTH(est.telefone_1) = 8 THEN SUBSTR(est.telefone_1, 1, 4) || '-' || SUBSTR(est.telefone_1, 5, 4) ELSE est.telefone_1 END ELSE '' END as telefone_formatado,
        COALESCE(est.correio_eletronico, '') as email,
        COALESCE(c.descricao_cnae, '') as descricao_cnae,
        COALESCE(nat.descricao_natureza, '') as descricao_natureza,
        CASE WHEN s.opcao_mei = 'S' THEN 'Microempreendedor Individual (MEI)' WHEN e.porte IN ('49','50') THEN 'Microempresa (ME)' WHEN e.porte IN ('05','16','17','19') THEN 'Empresa de Pequeno Porte (EPP)' WHEN e.porte IN ('43','34','65','59') THEN 'Empresa de Médio Porte' WHEN e.porte NOT IN ('49','50','05','16','17','19','43','34','65','59') AND e.porte IS NOT NULL AND e.porte != '' THEN 'Grande Empresa' ELSE 'Não Informado' END as porte,
        CASE WHEN e.capital_social IS NOT NULL AND e.capital_social != '' AND e.capital_social != '0' THEN 'R$ ' || REPLACE(printf("%.2f", CAST(e.capital_social AS REAL) / 100.0), '.', ',') ELSE 'Não Informado' END as capital_social,
        CASE WHEN s.opcao_simples = 'S' THEN 'Sim' WHEN s.opcao_simples = 'N' THEN 'Não' ELSE 'N/A' END as opcao_simpl
        , CASE WHEN s.opcao_mei = 'S' THEN 'Sim' WHEN s.opcao_mei = 'N' THEN 'Não' ELSE 'N/A' END as opcao_mei,
        CASE WHEN est.identificador_matriz_filial = '1' THEN 'Matriz' WHEN est.identificador_matriz_filial = '2' THEN 'Filial' ELSE 'N/A' END as matriz_filial,
        {socios_select}
    FROM estabelecimentos_completos est
    LEFT JOIN empresas_completas e ON est.cnpj_basico = e.cnpj_basico
    LEFT JOIN simples s ON est.cnpj_basico = s.cnpj_basico
    LEFT JOIN cnaes c ON est.cnae_fiscal_principal = c.codigo_cnae
    LEFT JOIN naturezas nat ON e.natureza_juridica = nat.codigo_natureza
    LEFT JOIN municipios m ON est.municipio = m.codigo_municipio
    {socios_join}
    WHERE {where_sql}
    ORDER BY e.razao_social, est.cnpj_ordem
    """.format(socios_select=socios_select, socios_join=socios_join, where_sql=where_sql)

    # Debug write
    try:
        with open('server.err','a',encoding='utf-8') as fh:
            fh.write('\n--- INTERNAL EXPORT SQL START ---\n')
            fh.write(sql)
            fh.write('\n--- PARAMS: %s ---\n' % str(params))
    except Exception:
        pass

    cursor = conn.cursor()
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    headers = ['CNPJ','RAZAO_SOCIAL','NOME_FANTASIA','SITUACAO_EMPRESA','DATA_SITUACAO','ENDERECO_COMPLETO','CEP','UF','NOME_MUNICIPIO','TELEFONE_FORMATADO','EMAIL','DESCRICAO_CNAE','DESCRICAO_NATUREZA','BAIRRO','PORTE','CAPITAL_SOCIAL','OPCAO_SIMPLES','OPCAO_MEI','MATRIZ_FILIAL','NOME_SOCIO','QUALIFICACAO_SOCIO','CPF_SOCIO']
    df = pd.DataFrame(rows, columns=headers)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out = f'cnpj_exportacao_internal_{ts}.csv'
    df.to_csv(out, sep=';', index=False, encoding='utf-8-sig', lineterminator='\n', quoting=1)
    print('WROTE', out, 'ROWS', len(df))
    db.disconnect()

if __name__ == '__main__':
    run_export({'uf':'DF','socios_present': True})
