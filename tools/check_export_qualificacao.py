#!/usr/bin/env python3
"""
Check exported CSV for rows where NOME_SOCIO is present but QUALIFICACAO_SOCIO is empty,
and query the local SQLite DB `cnpj_database.db` for the corresponding `socios` rows.

Usage: python tools/check_export_qualificacao.py [path/to/export.csv]
If no path provided will use the default export in the workspace root.
"""
import csv
import os
import re
import sqlite3
import sys

CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..', 'cnpj_exportacao_20251015_171259.csv')
CSV_PATH = os.path.abspath(CSV_PATH)
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'cnpj_database.db'))

def only_digits(s):
    return re.sub(r"\D", "", s or "")

def cnpj_basico_from_full(cnpj_full):
    d = only_digits(cnpj_full)
    if len(d) >= 8:
        return d[:8]
    return d

def main():
    print("CSV:", CSV_PATH)
    print("DB:", DB_PATH)
    if not os.path.exists(CSV_PATH):
        print("ERROR: CSV file not found:", CSV_PATH)
        return 2
    if not os.path.exists(DB_PATH):
        print("ERROR: DB file not found:", DB_PATH)
        return 3

    samples = []
    with open(CSV_PATH, newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh, delimiter=';')
        for lineno, row in enumerate(reader, start=2):
            nome = (row.get('NOME_SOCIO') or '').strip()
            qual = (row.get('QUALIFICACAO_SOCIO') or '').strip()
            cpf = (row.get('CPF_SOCIO') or '').strip()
            cnpj = (row.get('CNPJ') or row.get('CNPJ;') or '').strip()
            if nome and not qual:
                samples.append({'lineno': lineno, 'raw': row, 'cnpj': cnpj, 'nome': nome, 'cpf': cpf})
            if len(samples) >= 20:
                break

    print(f"Found {len(samples)} sample rows with NOME_SOCIO present and QUALIFICACAO_SOCIO empty (showing up to 20):\n")
    for i, s in enumerate(samples, 1):
        # find cnpj value robustly from raw keys (handle BOM or different header names)
        raw = s['raw']
        cnpj_val = s['cnpj'] if s['cnpj'] else ''
        if not cnpj_val:
            for k in raw.keys():
                if 'cnpj' in k.lower():
                    cnpj_val = raw.get(k) or ''
                    break

        print(f"{i}. line={s['lineno']} CNPJ={cnpj_val}  NOME_SOCIO={s['nome']}  CPF_SOCIO={s['cpf']}")
        print('   raw row keys:', list(s['raw'].keys()))
        # show a compact repr of the raw row to detect misaligned columns
        compact = {k: (v if len(str(v)) < 80 else str(v)[:77] + '...') for k, v in s['raw'].items()}
        print('   raw row sample:', compact)
        # store resolved cnpj back for DB lookup
        s['resolved_cnpj'] = cnpj_val

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    print('\nDB lookups for these CNPJs (matching by cnpj_basico = first 8 digits):')
    for i, s in enumerate(samples, 1):
        basic = cnpj_basico_from_full(s.get('resolved_cnpj') or s['cnpj'])
        cur.execute("SELECT cnpj_basico, cnpj_completo, nome_socio, cnpj_cpf_socio, qualificacao_socio FROM socios WHERE cnpj_basico = ? LIMIT 5", (basic,))
        rows = cur.fetchall()
        print(f"\n{i}. cnpj_basico_query={basic}  (from export CNPJ='{s['cnpj']}') -> {len(rows)} matching rows")
        if not rows:
            print("   No rows in socios with that cnpj_basico.")
            continue
        for r in rows:
            print(f"   DB: cnpj_basico={r[0]} cnpj_completo={r[1]} nome_socio={r[2]} cnpj_cpf_socio={r[3]} qualificacao_socio={r[4]}")

    # Also check qualificacoes table content for a couple of example codes if present
    print('\nqualificacoes table info:')
    try:
        cur.execute("PRAGMA table_info('qualificacoes')")
        cols = cur.fetchall()
        if not cols:
            print('   qualificacoes table not found or empty')
        else:
            for c in cols:
                print(f"   col: {c}")
            # Try a generic select
            cur.execute('SELECT * FROM qualificacoes LIMIT 20')
            rows = cur.fetchall()
            print(f'   qualificacoes sample rows: {len(rows)}')
            for r in rows:
                print('    ', r)
    except Exception as e:
        print('   Could not inspect qualificacoes table:', e)

    conn.close()
    return 0

if __name__ == '__main__':
    sys.exit(main())
