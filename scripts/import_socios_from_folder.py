import os
import re
import csv
import sqlite3
import pandas as pd
import json


def find_files(folder):
    files = []
    if not os.path.exists(folder):
        return files
    for fn in os.listdir(folder):
        if fn.lower().endswith('.csv'):
            files.append(os.path.join(folder, fn))
    return files


def try_read_csv(path):
    # Try to detect delimiter using csv.Sniffer on a small sample
    # prioritize single-byte encodings common for BR data to avoid utf-8 decode issues
    encs = ['latin-1', 'cp1252', 'utf-8-sig', 'utf-8']
    sample = None
    for enc in encs:
        try:
            with open(path, 'r', encoding=enc, errors='replace') as fh:
                sample = fh.read(8192)
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
            # fallback list
            for d in [';', ',', '\t', '|']:
                if d in sample:
                    delim = d
                    break

    # fallback encoding order
    last_exc = None
    for enc in encs:
        try:
            if delim:
                it = pd.read_csv(path, sep=delim, encoding=enc, dtype=str, keep_default_na=False, chunksize=5000)
                return it, delim, enc
            else:
                it = pd.read_csv(path, sep=None, engine='python', encoding=enc, dtype=str, keep_default_na=False, chunksize=5000)
                # pandas will infer a separator in this mode
                return it, None, enc
        except Exception as e:
            last_exc = e
            continue
    raise last_exc


def normalize_digits(s):
    if s is None:
        return ''
    return re.sub(r'\D', '', str(s))


def infer_columns(cols):
    # Return mapping for company cnpj, socio name, socio cpf, qualificacao
    low = [c.lower() for c in cols]
    def pick(predicates):
        for i, c in enumerate(low):
            for p in predicates:
                if p in c:
                    return cols[i]
        return None

    company = pick(['cnpj', 'empresa', 'empresa_cnpj', 'cnpj_basico'])
    # avoid matching cpf for company
    # socio cpf may contain cpf or cnpj_cpf
    socio_cpf = pick(['cpf', 'cnpj_cpf'])
    name = pick(['nome', 'socio', 'sócio', 'nome_socio', 'nome do socio'])
    qual = pick(['qual', 'qualificacao', 'qualifica'])
    return company, name, socio_cpf, qual


def to_cnpj_basico(value):
    d = normalize_digits(value)
    # if it's a full CNPJ (14 digits) take first 8
    if len(d) >= 14:
        return d[:8]
    # if it's already 8
    if len(d) == 8:
        return d
    # otherwise return what we have (pad left?) - keep as is
    return d


def main():
    folder = r"C:\Users\victor.vasconcelos\Documents\PROJETO CNPJ\Socios0"
    db_path = r"c:\Users\victor.vasconcelos\Documents\Dashboard\cnpj_database.db"

    out = {'folder': folder, 'db': db_path, 'files_processed': [], 'total_read': 0, 'total_inserted': 0}

    files = find_files(folder)
    if not files:
        out['error'] = 'no_files_found'
        print(json.dumps(out, ensure_ascii=False))
        return

    # open DB
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # ensure table socios exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='socios'")
    if not cur.fetchone():
        # create basic socios table
        cur.execute('''CREATE TABLE socios (
            cnpj_basico TEXT,
            nome_socio TEXT,
            cnpj_cpf_socio TEXT,
            qualificacao_socio TEXT
        )''')
        conn.commit()

    # fetch existing set for simple dedupe (cnpj_basico, nome_socio, cnpj_cpf_socio)
    cur.execute("SELECT cnpj_basico, nome_socio, cnpj_cpf_socio FROM socios")
    existing = set(cur.fetchall())

    for fpath in files:
        try:
            it, detected_delim, detected_enc = try_read_csv(fpath)
        except Exception as e:
            out.setdefault('errors', []).append({'file': fpath, 'error': str(e)})
            continue

        # iterator of DataFrame chunks
        rows_read_file = 0
        rows_inserted_file = 0
        try:
            for df in it:
                # infer columns for this chunk
                company_col, name_col, cpf_col, qual_col = infer_columns(list(df.columns))

                # fallback heuristics
                if company_col is None:
                    company_col = df.columns[0]
                if name_col is None:
                    for c in df.columns:
                        if 'nome' in c.lower() or 'socio' in c.lower():
                            name_col = c
                            break
                if cpf_col is None:
                    for c in df.columns:
                        if 'cpf' in c.lower():
                            cpf_col = c
                            break
                if qual_col is None:
                    for c in df.columns:
                        if 'qual' in c.lower():
                            qual_col = c
                            break

                chunk_rows = []
                for _, r in df.iterrows():
                    cnpj_src = r.get(company_col, '') if company_col in df.columns else ''
                    nome = r.get(name_col, '') if name_col in df.columns else ''
                    cpf = r.get(cpf_col, '') if cpf_col in df.columns else ''
                    qual = r.get(qual_col, '') if qual_col in df.columns else ''

                    cnpjb = to_cnpj_basico(cnpj_src)
                    cpf_norm = normalize_digits(cpf)
                    nome_s = str(nome).strip()
                    qual_s = str(qual).strip()

                    if not cnpjb:
                        continue
                    chunk_rows.append((cnpjb, nome_s, cpf_norm, qual_s))

                rows_read_file += len(chunk_rows)

                # dedupe against existing and within chunk
                unique_rows = []
                seen_chunk = set()
                for t in chunk_rows:
                    key = (t[0], t[1], t[2])
                    if key in existing or key in seen_chunk:
                        continue
                    seen_chunk.add(key)
                    unique_rows.append(t)

                if unique_rows:
                    try:
                        cur.execute('BEGIN')
                        cur.executemany('INSERT INTO socios (cnpj_basico, nome_socio, cnpj_cpf_socio, qualificacao_socio) VALUES (?,?,?,?)', unique_rows)
                        conn.commit()
                        inserted = len(unique_rows)
                        rows_inserted_file += inserted
                        out['total_inserted'] += inserted
                        for r in unique_rows:
                            existing.add((r[0], r[1], r[2]))
                    except Exception as e:
                        conn.rollback()
                        out.setdefault('errors', []).append({'file': fpath, 'error': str(e)})
                        # continue processing other chunks/files
                        continue

        except UnicodeDecodeError:
            # retry with latin-1 if we hit decoding issues while iterating
            try:
                fallback_enc = 'latin-1'
                if detected_delim:
                    it2 = pd.read_csv(fpath, sep=detected_delim, encoding=fallback_enc, dtype=str, keep_default_na=False, chunksize=5000)
                else:
                    it2 = pd.read_csv(fpath, sep=None, engine='python', encoding=fallback_enc, dtype=str, keep_default_na=False, chunksize=5000)
                for df in it2:
                    # repeat same processing as above for each chunk
                    company_col, name_col, cpf_col, qual_col = infer_columns(list(df.columns))
                    if company_col is None:
                        company_col = df.columns[0]
                    if name_col is None:
                        for c in df.columns:
                            if 'nome' in c.lower() or 'socio' in c.lower():
                                name_col = c
                                break
                    if cpf_col is None:
                        for c in df.columns:
                            if 'cpf' in c.lower():
                                cpf_col = c
                                break
                    if qual_col is None:
                        for c in df.columns:
                            if 'qual' in c.lower():
                                qual_col = c
                                break

                    chunk_rows = []
                    for _, r in df.iterrows():
                        cnpj_src = r.get(company_col, '') if company_col in df.columns else ''
                        nome = r.get(name_col, '') if name_col in df.columns else ''
                        cpf = r.get(cpf_col, '') if cpf_col in df.columns else ''
                        qual = r.get(qual_col, '') if qual_col in df.columns else ''

                        cnpjb = to_cnpj_basico(cnpj_src)
                        cpf_norm = normalize_digits(cpf)
                        nome_s = str(nome).strip()
                        qual_s = str(qual).strip()

                        if not cnpjb:
                            continue
                        chunk_rows.append((cnpjb, nome_s, cpf_norm, qual_s))

                    rows_read_file += len(chunk_rows)

                    unique_rows = []
                    seen_chunk = set()
                    for t in chunk_rows:
                        key = (t[0], t[1], t[2])
                        if key in existing or key in seen_chunk:
                            continue
                        seen_chunk.add(key)
                        unique_rows.append(t)

                    if unique_rows:
                        try:
                            cur.execute('BEGIN')
                            cur.executemany('INSERT INTO socios (cnpj_basico, nome_socio, cnpj_cpf_socio, qualificacao_socio) VALUES (?,?,?,?)', unique_rows)
                            conn.commit()
                            inserted = len(unique_rows)
                            rows_inserted_file += inserted
                            out['total_inserted'] += inserted
                            for r in unique_rows:
                                existing.add((r[0], r[1], r[2]))
                        except Exception as e:
                            conn.rollback()
                            out.setdefault('errors', []).append({'file': fpath, 'error': str(e)})
                            continue
            except Exception as e:
                out.setdefault('errors', []).append({'file': fpath, 'error': 'retry_failed: ' + str(e)})
        except KeyboardInterrupt:
            out.setdefault('errors', []).append({'file': fpath, 'error': 'keyboard_interrupt'})

        out['files_processed'].append({'file': os.path.basename(fpath), 'rows_read': rows_read_file, 'rows_inserted': rows_inserted_file})
        out['total_read'] += rows_read_file

    conn.close()
    print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()
