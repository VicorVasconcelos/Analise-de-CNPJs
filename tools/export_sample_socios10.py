import sqlite3
import pandas as pd
import csv
import os
import logging
import traceback

DB = 'cnpj_database.db'
OUT = 'export_sample_10_with_socios.csv'
OUT_TMP = 'export_sample_10_with_socios.tmp.csv'
LOGFILE = os.path.join(os.path.dirname(__file__), 'export_sample_socios10.log')

# configure logger
logger = logging.getLogger('export_sample_socios10')
logger.setLevel(logging.DEBUG)
fmt = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
fh = logging.FileHandler(LOGFILE, encoding='utf-8')
fh.setLevel(logging.DEBUG)
fh.setFormatter(fmt)
if not logger.handlers:
    logger.addHandler(fh)


def log_info(msg):
    print(msg)
    logger.info(msg)


def log_error(msg):
    print(msg)
    logger.error(msg)


HEADERS = [
    'CNPJ','RAZAO_SOCIAL','NOME_FANTASIA','SITUACAO_EMPRESA','DATA_SITUACAO',
    'ENDERECO_COMPLETO','CEP','UF','NOME_MUNICIPIO','TELEFONE_FORMATADO',
    'EMAIL','DESCRICAO_CNAE','DESCRICAO_NATUREZA','BAIRRO','PORTE',
    'CAPITAL_SOCIAL','OPCAO_SIMPLES','OPCAO_MEI','MATRIZ_FILIAL',
    'NOME_SOCIO','QUALIFICACAO_SOCIO','CPF_SOCIO'
]


DATA_SQL_TEMPLATE = """
SELECT
  CASE WHEN est.cnpj_basico IS NOT NULL AND est.cnpj_ordem IS NOT NULL AND est.cnpj_dv IS NOT NULL
    THEN SUBSTR(est.cnpj_basico,1,2) || '.' || SUBSTR(est.cnpj_basico,3,3) || '.' || SUBSTR(est.cnpj_basico,6,3) || '/' || est.cnpj_ordem || '-' || est.cnpj_dv
    ELSE est.cnpj_basico
  END as cnpj,
  COALESCE(e.razao_social,'') as razao_social,
  COALESCE(est.nome_fantasia,'') as nome_fantasia,
  COALESCE(est.bairro,'') as bairro,
  COALESCE(s_first.nome_socio,'') as nome_socio,
  COALESCE(q.descricao_qualificacao, s_first.qualificacao_socio, '') as qualificacao_socio,
  CASE
    WHEN s_first.cnpj_cpf_socio IS NULL THEN ''
    WHEN instr(s_first.cnpj_cpf_socio, '*') > 0 THEN s_first.cnpj_cpf_socio
    WHEN LENGTH(TRIM(s_first.cnpj_cpf_socio)) >= 11 THEN '***' || SUBSTR(s_first.cnpj_cpf_socio, 4, 6) || '**'
    ELSE s_first.cnpj_cpf_socio
  END as cpf_masked
FROM estabelecimentos_completos est
LEFT JOIN empresas_completas e ON est.cnpj_basico = e.cnpj_basico
LEFT JOIN (
    SELECT s.cnpj_basico, s.nome_socio, s.qualificacao_socio, s.cnpj_cpf_socio, s.rowid
    FROM socios s
    INNER JOIN (SELECT cnpj_basico, MIN(rowid) AS min_rowid FROM socios WHERE cnpj_basico IN (%s) GROUP BY cnpj_basico) f
        ON f.cnpj_basico = s.cnpj_basico AND f.min_rowid = s.rowid
) s_first ON s_first.cnpj_basico = e.cnpj_basico
LEFT JOIN qualificacoes q ON q.codigo_qualificacao = s_first.qualificacao_socio
WHERE e.cnpj_basico IN (%s)
ORDER BY e.razao_social, est.cnpj_ordem
"""


def main():
    try:
        log_info('Starting export_sample_socios10')
        if not os.path.exists(DB):
            log_error(f'DB not found: {DB}')
            return
        conn = sqlite3.connect(DB)
        cur = conn.cursor()

        # pick 10 CNPJs that have socios (fast preselect)
        cur.execute("""
            SELECT DISTINCT e.cnpj_basico
            FROM estabelecimentos_completos est
            LEFT JOIN empresas_completas e ON est.cnpj_basico = e.cnpj_basico
            WHERE EXISTS(SELECT 1 FROM socios s WHERE s.cnpj_basico = e.cnpj_basico)
            ORDER BY e.razao_social, est.cnpj_ordem
            LIMIT 10
        """)
        cnpjs = [r[0] for r in cur.fetchall()]
        if not cnpjs:
            log_info('Nenhum CNPJ com sócios encontrado.')
            conn.close()
            return

        in_list = ','.join("'{}'".format(c.replace("'", "''")) for c in cnpjs)
        # fill both placeholders: one for inner MIN(rowid) selection, another for the WHERE clause
        data_sql = DATA_SQL_TEMPLATE % (in_list, in_list)

        log_info(f'Pre-selected {len(cnpjs)} CNPJs for export')
        cur.execute(data_sql)
        rows = cur.fetchall()
        log_info(f'Rows fetched: {len(rows)}')

        # write rows in streaming mode to avoid building a large DataFrame
        try:
            with open(OUT_TMP, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(HEADERS)
                for r in rows:
                    writer.writerow(r)
            log_info(f'Temporary file written: {OUT_TMP}')
        except Exception as e:
            log_error(f'Error writing temporary file {OUT_TMP}: {e}')
            logger.error(traceback.format_exc())

        try:
            if os.path.exists(OUT):
                os.remove(OUT)
            os.replace(OUT_TMP, OUT)
            log_info(f'Sample export written to {OUT} rows: {len(rows)}')
        except Exception as e:
            log_error(f'Could not replace {OUT} due to: {e}')
            logger.error(traceback.format_exc())
            log_info(f'Sample export written to temporary file {OUT_TMP} rows: {len(rows)}')

        conn.close()
    except Exception as e:
        log_error(f'Unhandled error during export: {e}')
        logger.error(traceback.format_exc())


if __name__ == '__main__':
    main()
