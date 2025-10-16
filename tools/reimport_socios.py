#!/usr/bin/env python3
"""
Reimporta arquivos de sócios com opções seguras:

- dry-run (padrão): apenas analisa e gera CSV de propostas sem alterar o DB
- overwrite: atualiza (UPDATE) ou insere (INSERT) linhas em `socios` por cnpj_basico
- drop-and-import: cria um backup da tabela `socios`, apaga todas as linhas e importa tudo novo

Uso exemplo:
python reimport_socios.py --folder "C:\\Users\\victor.vasconcelos\\Documents\\PROJETO CNPJ\\Socios0" --mode dry-run --limit 1 --rows 6 --export-csv propostas.csv

O script preserva o token de CPF mascarado tal como aparece no CSV (incluindo asteriscos).
"""
import argparse
import csv
import json
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
import re


def detect_file_settings(path):
    # try a few encodings and sniff delimiter from a sample
    encs = ['latin-1', 'cp1252', 'utf-8-sig', 'utf-8']
    sample = None
    enc_used = None
    for enc in encs:
        try:
            with open(path, 'r', encoding=enc, errors='replace') as fh:
                sample = fh.read(8192)
            enc_used = enc
            break
        except Exception:
            sample = None
            continue

    delim = None
    if sample:
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample)
            delim = dialect.delimiter
        except Exception:
            for d in [';', ',', '\t', '|']:
                if d in sample:
                    delim = d
                    break

    return delim, enc_used


def normalize_digits(s):
    if s is None:
        return ''
    return re.sub(r'\D', '', str(s))


def infer_columns(cols):
    low = [c.lower() for c in cols]
    def pick(preds):
        for i, c in enumerate(low):
            for p in preds:
                if p in c:
                    return cols[i]
        return None

    company = pick(['cnpj', 'empresa', 'cnpj_basico']) or (cols[0] if cols else None)
    name = pick(['nome', 'socio', 'sócio', 'nome_socio'])
    socio_cpf = pick(['cpf', 'cnpj_cpf'])
    qual = pick(['qual', 'qualificacao'])
    return company, name, socio_cpf, qual


def normalize_mid6(token):
    if not token:
        return None
    digits = ''.join(ch for ch in token if ch.isdigit())
    if len(digits) >= 6:
        return digits[:6]
    return None


def backup_socios(conn):
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_table = f'socios_backup_{ts}'
    cur = conn.cursor()
    cur.execute(f"CREATE TABLE IF NOT EXISTS {backup_table} AS SELECT * FROM socios")
    conn.commit()
    return backup_table


def ensure_socios_table(conn):
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='socios'")
    if not cur.fetchone():
        cur.execute('''CREATE TABLE socios (
            cnpj_basico TEXT,
            nome_socio TEXT,
            cnpj_cpf_socio TEXT,
            qualificacao_socio TEXT
        )''')
        conn.commit()


def process_folder(folder, db_path, mode='dry-run', limit_files=None, rows_per_file=None, export_csv=None):
    folder = Path(folder)
    if not folder.exists():
        raise FileNotFoundError(f'Folder not found: {folder}')

    files = sorted([p for p in folder.glob('*.csv')])
    if not files:
        raise FileNotFoundError('No CSV files found in folder')

    if limit_files:
        files = files[:limit_files]

    conn = sqlite3.connect(db_path)
    ensure_socios_table(conn)
    cur = conn.cursor()

    proposals = []
    stats = {'files': 0, 'rows': 0, 'to_insert': 0, 'to_update': 0, 'skipped_no_row': 0}

    # If destructive mode, create a backup first
    if mode == 'drop-and-import' or mode == 'overwrite':
        backup_table = backup_socios(conn)
        print(f'Backup criado: {backup_table}')

    if mode == 'drop-and-import':
        # truncate socios
        cur.execute('DELETE FROM socios')
        conn.commit()
        print('Tabela socios esvaziada (delete).')

    for f in files:
        stats['files'] += 1
        print(f'Processing file: {f.name}')
        delim, enc = detect_file_settings(str(f))
        print(f'  detected delim={delim!r} enc={enc!r}')
        try:
            if delim:
                it = csv.reader(open(f, 'r', encoding=enc or 'latin-1', errors='replace'), delimiter=delim, quotechar='"')
            else:
                # fallback to ; and try
                it = csv.reader(open(f, 'r', encoding=enc or 'latin-1', errors='replace'), delimiter=';', quotechar='"')
        except Exception as e:
            print('  failed to open file:', e)
            continue

        for ridx, row in enumerate(it):
            if rows_per_file and ridx >= rows_per_file:
                break
            # skip empty
            if not any(cell.strip() for cell in row):
                continue
            stats['rows'] += 1

            # some files may come as a single column with semicolons included
            if len(row) == 1 and ';' in row[0]:
                parts = [p.strip().strip('"') for p in row[0].split(';')]
                row = parts

            # Try to detect header row: if first row contains non-digit tokens and seems like header
            # We'll still treat everything as data, infer positions per row
            cidx = nidx = pidx = qidx = None
            try:
                cidx, nidx, pidx, qidx = detect_columns_row(row)
            except Exception:
                # fallback simple heuristics
                # prefer first numeric 8-digit token as cnpj
                for i, v in enumerate(row):
                    vv = v.strip()
                    if vv.isdigit() and len(vv) == 8 and cidx is None:
                        cidx = i
                    if any(ch.isalpha() for ch in vv) and nidx is None and len(vv) > 2:
                        nidx = i
                # cpf token: contains '*' or has >=6 digits
                for i, v in enumerate(row):
                    vv = v.strip()
                    if '*' in vv and pidx is None and any(ch.isdigit() for ch in vv):
                        pidx = i
                    elif pidx is None and len(''.join(ch for ch in vv if ch.isdigit())) >= 6:
                        pidx = i

            cnpj_basic = row[cidx].strip() if cidx is not None and cidx < len(row) else None
            nome = row[nidx].strip() if nidx is not None and nidx < len(row) else ''
            cpf_raw = row[pidx].strip() if pidx is not None and pidx < len(row) else ''
            qual = row[qidx].strip() if qidx is not None and qidx < len(row) else ''

            if not cnpj_basic:
                stats['skipped_no_row'] += 1
                proposals.append({'file': f.name, 'row': ridx + 1, 'cnpj_basico': None, 'action': 'skip_no_cnpj'})
                continue

            # preserve masked CPF token exactly as provided (including asterisks)
            cpf_to_store = cpf_raw if cpf_raw and cpf_raw.strip() != '' else None

            # normalize cnpj_basic digits only
            cnpj_basic_norm = normalize_digits(cnpj_basic)
            if len(cnpj_basic_norm) >= 8:
                cnpj_basic_norm = cnpj_basic_norm[:8]

            # apply according to mode
            if mode == 'dry-run':
                # only propose
                proposals.append({'file': f.name, 'row': ridx + 1, 'cnpj_basico': cnpj_basic_norm, 'proposed_nome': nome or None, 'proposed_cpf_mask': cpf_to_store or None, 'proposed_qual': qual or None, 'action': 'propose'})
                continue

            # overwrite or drop-and-import both need to write
            # check if row exists
            cur.execute('SELECT cnpj_basico FROM socios WHERE cnpj_basico = ? LIMIT 1', (cnpj_basic_norm,))
            exists = cur.fetchone() is not None
            if exists:
                # update
                cur.execute('UPDATE socios SET nome_socio = ?, cnpj_cpf_socio = ?, qualificacao_socio = ? WHERE cnpj_basico = ?', (nome, cpf_to_store, qual, cnpj_basic_norm))
                stats['to_update'] += 1
                proposals.append({'file': f.name, 'row': ridx + 1, 'cnpj_basico': cnpj_basic_norm, 'proposed_nome': nome or None, 'proposed_cpf_mask': cpf_to_store or None, 'proposed_qual': qual or None, 'action': 'update'})
            else:
                # insert
                cur.execute('INSERT INTO socios (cnpj_basico, nome_socio, cnpj_cpf_socio, qualificacao_socio) VALUES (?,?,?,?)', (cnpj_basic_norm, nome, cpf_to_store, qual))
                stats['to_insert'] += 1
                proposals.append({'file': f.name, 'row': ridx + 1, 'cnpj_basico': cnpj_basic_norm, 'proposed_nome': nome or None, 'proposed_cpf_mask': cpf_to_store or None, 'proposed_qual': qual or None, 'action': 'insert'})

    # commit for destructive modes
    if mode in ('overwrite', 'drop-and-import'):
        conn.commit()
        print('Changes committed to DB.')
    else:
        print('Dry-run complete; no DB changes were made.')

    # export proposals if requested
    if export_csv:
        fieldnames = list(proposals[0].keys()) if proposals else ['file','row','cnpj_basico','action']
        with open(export_csv, 'w', encoding='utf-8', newline='') as out:
            w = csv.DictWriter(out, fieldnames=fieldnames, delimiter=';')
            w.writeheader()
            for p in proposals:
                w.writerow(p)
        print(f'Proposals written to: {export_csv}')

    conn.close()
    return stats


def detect_columns_row(row):
    # Heuristics similar to apply_socios_updates.detect_columns
    cnpj_idx = None
    name_idx = None
    cpf_idx = None
    qual_idx = None
    for i, v in enumerate(row):
        vv = v.strip()
        if cpf_idx is None and ('*' in vv) and any(ch.isdigit() for ch in vv):
            cpf_idx = i
            continue
        if cnpj_idx is None and vv.isdigit() and len(vv) == 8:
            cnpj_idx = i
            continue
        if name_idx is None and any(ch.isalpha() for ch in vv) and len(vv) > 3:
            name_idx = i
        if cpf_idx is None and any(ch.isdigit() for ch in vv):
            digits_only = ''.join(ch for ch in vv if ch.isdigit())
            if len(digits_only) >= 6 and not (len(digits_only) == 8 and cnpj_idx is not None and cnpj_idx == i):
                cpf_idx = i

    allowed_codes = {"00","05","08","09","10","11","12","13","14","15","16","17","18","19","20","21","22","23","24","25","26","28","29","30","31","32","33","34","35","37","38","39","40","41","42","43","46","47","48","49","50","51","52","53","54","55","56","57","58","59"}
    if cpf_idx is not None:
        for j in range(cpf_idx + 1, min(len(row), cpf_idx + 6)):
            vv = row[j].strip().zfill(2) if row[j].strip().isdigit() else row[j].strip()
            if vv in allowed_codes:
                qual_idx = j
                break
    if qual_idx is None:
        for i, v in enumerate(row):
            vv = v.strip().zfill(2) if v.strip().isdigit() else v.strip()
            if vv in allowed_codes:
                qual_idx = i
                break
    return cnpj_idx, name_idx, cpf_idx, qual_idx


def main():
    p = argparse.ArgumentParser(description='Reimport socios safely')
    p.add_argument('--folder', '-f', required=False, default=r'C:\\Users\\victor.vasconcelos\\Documents\\PROJETO CNPJ\\Socios0')
    p.add_argument('--db', default='cnpj_database.db')
    p.add_argument('--mode', choices=['dry-run', 'overwrite', 'drop-and-import'], default='dry-run')
    p.add_argument('--limit', type=int, default=1, help='limit number of files for testing')
    p.add_argument('--rows', type=int, default=6, help='limit rows per file for testing')
    p.add_argument('--export-csv', default='socios_reimport_proposals.csv')
    args = p.parse_args()

    export_csv = args.export_csv
    try:
        start = time.time()
        stats = process_folder(args.folder, args.db, mode=args.mode, limit_files=args.limit, rows_per_file=args.rows, export_csv=export_csv)
        elapsed = time.time() - start
        print('\nSummary:', stats)
        print(f'Elapsed: {elapsed:.2f}s')
    except Exception as e:
        print('Error:', e)


if __name__ == '__main__':
    main()
