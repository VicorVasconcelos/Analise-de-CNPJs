"""
Scan CSV files in a Socios folder and update existing `socios` rows in the project's SQLite DB.
Behavior (dry-run by default):
- For each row detected with: cnpj_basic, nome_socio, mid6 cpf mask (like '***560201**' or '560201'), qualificacao code
- Update the `socios` table where cnpj_basico matches, setting nome_socio, cnpj_cpf_socio (store original masked string), and qualificacao_socio if the DB value is empty or different (only if allowed).
- Do not overwrite existing non-empty nome_socio unless --force is passed.
- Print a summary of updates applied.

Usage:
python apply_socios_updates.py <socios_folder> [--limit N] [--force]

This is a cautious updater to run a small dry-run sample before full import.

"""
import os
import sys
import csv
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / 'cnpj_database.db'

def detect_columns(row):
    # Improved heuristic based on observed sample rows.
    # Example split row:
    # ['52193124', '2', 'GELSON SANTOS FARIAS JUNIOR', '***197080**', '49', '20230915', '', '***000000**', '', '00', '4']
    cnpj_idx = None
    name_idx = None
    cpf_idx = None
    qual_idx = None
    # find cnpj (8 digits) and name (first token with letters)
    for i, v in enumerate(row):
        vv = v.strip()
        # detect masked CPF tokens first (they contain '*') to avoid confusion with cnpj
        if cpf_idx is None and ('*' in vv) and any(ch.isdigit() for ch in vv):
            cpf_idx = i
            continue
        if cnpj_idx is None and vv.isdigit() and len(vv) == 8:
            cnpj_idx = i
            continue
        if name_idx is None and any(ch.isalpha() for ch in vv) and len(vv) > 3:
            name_idx = i
        # fallback: detect cpf-like token (digits heavy) but avoid picking the 8-digit cnpj we already detected
        if cpf_idx is None and any(ch.isdigit() for ch in vv):
            digits_only = ''.join(ch for ch in vv if ch.isdigit())
            if len(digits_only) >= 6 and not (len(digits_only) == 8 and cnpj_idx is not None and cnpj_idx == i):
                cpf_idx = i
    # Qualificação: priorizar tokens que pertençam à lista de códigos válidos
    allowed_codes = {"00","05","08","09","10","11","12","13","14","15","16","17","18","19","20","21","22","23","24","25","26","28","29","30","31","32","33","34","35","37","38","39","40","41","42","43","46","47","48","49","50","51","52","53","54","55","56","57","58","59"}
    # primeiro, tente achar um código válido imediatamente à direita do cpf_idx
    if cpf_idx is not None:
        for j in range(cpf_idx + 1, min(len(row), cpf_idx + 6)):
            vv = row[j].strip().zfill(2) if row[j].strip().isdigit() else row[j].strip()
            if vv in allowed_codes:
                qual_idx = j
                break
    # se não encontrou, procure em toda a linha por qualquer token que seja código válido
    if qual_idx is None:
        for i, v in enumerate(row):
            vv = v.strip().zfill(2) if v.strip().isdigit() else v.strip()
            if vv in allowed_codes:
                qual_idx = i
                break
    return cnpj_idx, name_idx, cpf_idx, qual_idx


def normalize_mid6(token):
    if not token:
        return None
    t = token.strip()
    # try to extract six digits from token
    digits = ''.join(ch for ch in t if ch.isdigit())
    if len(digits) >= 6:
        # take middle 6 if longer
        if len(digits) > 6:
            return digits[:6]
        return digits.zfill(6)
    return None


def update_db_for_row(conn, cnpj_basic, nome, cpf_mask, qual, force=False):
    cur = conn.cursor()
    cur.execute("SELECT nome_socio, cnpj_cpf_socio, qualificacao_socio FROM socios WHERE cnpj_basico = ? LIMIT 1", (cnpj_basic,))
    r = cur.fetchone()
    if not r:
        return False, 'no-row'
    db_name, db_cpf, db_qual = r
    updates = {}
    if nome and (not db_name or db_name.strip() == '' or force):
        updates['nome_socio'] = nome
    if cpf_mask and (not db_cpf or db_cpf.strip() == '' or force):
        updates['cnpj_cpf_socio'] = cpf_mask
    if qual and (not db_qual or db_qual.strip() == '' or force):
        updates['qualificacao_socio'] = qual
    if not updates:
        return False, 'no-change'
    # build update SQL but execute only if force==True; dry-run will return proposed updates
    set_parts = ', '.join(f"{k} = ?" for k in updates.keys())
    params = list(updates.values()) + [cnpj_basic]
    sql = f"UPDATE socios SET {set_parts} WHERE cnpj_basico = ?"
    if force:
        cur.execute(sql, params)
        # commit later at process_files if force True
    return True, updates


def process_files(folder, limit_files=6, row_limit_per_file=6, force=False):
    folder = Path(folder)
    if not folder.exists():
        print('Folder not found:', folder)
        return
    files = sorted(folder.glob('*.csv'))
    total_files = min(len(files), limit_files)
    print(f'Processing {total_files}/{len(files)} files from {folder}')
    conn = sqlite3.connect(str(DB_PATH))
    stats = {'files':0, 'rows':0, 'updated':0, 'no_row':0, 'no_change':0}
    proposals = []
    for i, f in enumerate(files[:limit_files]):
        print('\n-- file', f.name)
        stats['files'] += 1
        with f.open('r', newline='', encoding='utf-8', errors='ignore') as fh:
            # Socios CSVs normalmente usam ponto-e-vírgula e campos entre aspas
            reader = csv.reader(fh, delimiter=';', quotechar='"')
            for ridx, row in enumerate(reader):
                if ridx >= row_limit_per_file:
                    break
                if not any(cell.strip() for cell in row):
                    continue
                stats['rows'] += 1
                print('Linha', ridx+1, row)
                # alguns arquivos podem chegar como uma única coluna contendo todos os campos separados por ';'
                if len(row) == 1 and ';' in row[0]:
                    # dividir manualmente e remover aspas extras
                    parts = [p.strip().strip('"') for p in row[0].split(';')]
                    row = parts
                cidx, nidx, pidx, qidx = detect_columns(row)
                print('Header presente?', False)
                print('Índice detectado para nome:', nidx)
                print('Índice detectado para CPF (mask):', pidx)
                # determine values
                cnpj_basic = row[cidx].strip() if cidx is not None and cidx < len(row) else None
                nome = row[nidx].strip() if nidx is not None and nidx < len(row) else None
                cpf_raw = row[pidx].strip() if pidx is not None and pidx < len(row) else None
                qual = row[qidx].strip() if qidx is not None and qidx < len(row) else None
                # preserve the original masked CPF token (including '*' characters) as requested
                cpf_to_store = cpf_raw if cpf_raw and cpf_raw.strip() != '' else None
                mid6 = None
                if cpf_raw:
                    # also extract a digits-only mid6 for diagnostics, but do not use it for storage
                    mid6 = normalize_mid6(cpf_raw)
                print('-> parseado:', {'cnpj_basic':cnpj_basic, 'nome':nome, 'cpf_mask':cpf_to_store, 'qual':qual})
                # update DB
                updated, info = update_db_for_row(conn, cnpj_basic, nome, cpf_to_store, qual, force=force)
                # collect proposal for CSV export
                cur = conn.cursor()
                cur.execute("SELECT nome_socio, cnpj_cpf_socio, qualificacao_socio FROM socios WHERE cnpj_basico = ? LIMIT 1", (cnpj_basic,))
                dbrow = cur.fetchone() or (None, None, None)
                db_name, db_cpf, db_qual = dbrow
                if updated:
                    stats['updated'] += 1
                    action = 'update'
                    print('  ATUALIZADO (proposta):', info)
                else:
                    if info == 'no-row':
                        stats['no_row'] += 1
                        action = 'no-row'
                        print('  sem linha correspondente em socios para cnpj_basico')
                    elif info == 'no-change':
                        stats['no_change'] += 1
                        action = 'no-change'
                        print('  sem alteração necessária (BD já tem valores)')
                    else:
                        action = 'other'
                proposals.append({
                    'file': f.name,
                    'row': ridx + 1,
                    'cnpj_basico': cnpj_basic,
                    'db_nome': db_name,
                    'db_cpf': db_cpf,
                    'db_qual': db_qual,
                    'proposed_nome': info if isinstance(info, dict) and 'nome_socio' in info else (nome if updated else None),
                    'proposed_cpf_mask': info['cnpj_cpf_socio'] if isinstance(info, dict) and 'cnpj_cpf_socio' in info else (cpf_to_store if updated else None),
                    'proposed_qual': info['qualificacao_socio'] if isinstance(info, dict) and 'qualificacao_socio' in info else (qual if updated else None),
                    'action': action
                })
    # commit only if force==True (apply); caso contrário, rollback para garantir dry-run
    # commit only if force==True (apply); otherwise rollback to ensure dry-run
    if force:
        conn.commit()
        print('\nAlterações aplicadas no banco de dados.')
    else:
        conn.rollback()
        print('\nDry-run concluído; nenhuma alteração foi gravada no banco.')
    # export proposals if requested via global variable set in main (hack: check for attribute)
    export_csv_path = getattr(process_files, '_export_csv_path', None)
    if export_csv_path:
        import csv as _csv
        fieldnames = ['file','row','cnpj_basico','db_nome','db_cpf','db_qual','proposed_nome','proposed_cpf_mask','proposed_qual','action']
        with open(export_csv_path, 'w', encoding='utf-8', newline='') as out:
            writer = _csv.DictWriter(out, fieldnames=fieldnames, delimiter=';')
            writer.writeheader()
            for p in proposals:
                writer.writerow(p)
        print(f"Propostas exportadas para: {export_csv_path}")
    conn.close()
    print('\nResumo:', stats)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: apply_socios_updates.py <socios_folder> [--limit N] [--rows R] [--force]')
        sys.exit(1)
    folder = sys.argv[1]
    limit = 6
    rows = 6
    force = False
    for a in sys.argv[2:]:
        if a.startswith('--limit'):
            limit = int(a.split('=')[1]) if '=' in a else int(sys.argv[sys.argv.index(a)+1])
        if a.startswith('--rows'):
            rows = int(a.split('=')[1]) if '=' in a else int(sys.argv[sys.argv.index(a)+1])
        if a == '--force':
            force = True
    export_csv = None
    for a in sys.argv[2:]:
        if a.startswith('--export-csv'):
            export_csv = a.split('=')[1] if '=' in a else 'socios_updates_proposals.csv'
            break
    # pass export path via attribute so process_files can write it at the end
    if export_csv:
        process_files._export_csv_path = os.path.abspath(export_csv)
    process_files(folder, limit_files=limit, row_limit_per_file=rows, force=force)
