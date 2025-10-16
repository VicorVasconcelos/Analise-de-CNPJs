r"""
Dry-run inspector for external socios CSVs.
Usage: python dry_run_socios_inspector.py [folder] [max_files] [lines_per_file]

Default folder: C:\Users\victor.vasconcelos\Documents\PROJETO CNPJ\Socios0
This script samples CSV files, attempts to detect delimiter and header, and prints first few rows.
It looks for likely name and cpf columns and reports masked CPFs (containing '*').
"""
import sys
import os
import csv
import glob

DEFAULT_FOLDER = r"C:\Users\victor.vasconcelos\Documents\PROJETO CNPJ\Socios0"

def detect_delimiter_and_preview(path, max_lines=5):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        sample = ''.join([f.readline() for _ in range(20)])
        # fallback delimiter
        dialect = None
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=';,|\t')
            delim = dialect.delimiter
        except Exception:
            # try common delimiters
            for d in [';', ',', '\t', '|']:
                if d in sample:
                    delim = d
                    break
            else:
                delim = ','
    # now read first max_lines rows with detected delimiter
    rows = []
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.reader(f, delimiter=delim)
        for i, r in enumerate(reader):
            rows.append(r)
            if i+1 >= max_lines:
                break
    return delim, rows


def analyze_rows(rows):
    if not rows:
        return {'has_header': False, 'header': None, 'name_idx': None, 'cpf_idx': None}
    # heuristics: header if any cell contains letters and matches common names
    first = rows[0]
    header_guess = any(cell.lower().strip() in ('nome', 'nome_socio', 'nome do socio', 'nm_socio', 'nome do sócio', 'cpf', 'cnpj_cpf_socio', 'cnpjcpf', 'cpf_socio') or 'nome' in cell.lower() or 'cpf' in cell.lower() or 'cnpj' in cell.lower() for cell in first)
    name_idx = None
    cpf_idx = None
    if header_guess:
        header = first
        data_rows = rows[1:]
    else:
        header = None
        data_rows = rows
    # attempt to find name and cpf columns either in header or by heuristics on data rows
    candidates = list(range(len(first)))
    if header:
        for i, h in enumerate(header):
            low = h.lower()
            if any(k in low for k in ('nome', 'socio', 'name')) and name_idx is None:
                name_idx = i
            if any(k in low for k in ('cpf', 'cnpj')) and cpf_idx is None:
                cpf_idx = i
    # if not found, inspect data rows
    if name_idx is None or cpf_idx is None:
        for i in candidates:
            # look at values in first few data rows
            vals = [r[i] if i < len(r) else '' for r in data_rows]
            joined = ' '.join(vals).lower()
            if name_idx is None:
                # heuristic: contains letters and spaces, not digits heavy
                letters = sum(c.isalpha() for c in joined)
                digits = sum(c.isdigit() for c in joined)
                if letters > digits and letters > 5:
                    name_idx = i
            if cpf_idx is None:
                # heuristic: contains '*' or groups of digits (length ~11) or '.' or '-'
                if '*' in joined or any(len(token) >= 6 and any(ch.isdigit() for ch in token) for token in joined.split()):
                    cpf_idx = i
            if name_idx is not None and cpf_idx is not None:
                break
    # detect masked cpfs
    masked = False
    if cpf_idx is not None:
        for r in data_rows:
            if cpf_idx < len(r):
                if '*' in r[cpf_idx]:
                    masked = True
                    break
    return {'has_header': bool(header), 'header': header, 'name_idx': name_idx, 'cpf_idx': cpf_idx, 'masked': masked}


def main(folder, max_files=5, lines_per_file=5):
    folder = folder or DEFAULT_FOLDER
    if not os.path.isdir(folder):
        print('Folder not found:', folder)
        return 2
    print('Scanning folder:', folder)
    paths = sorted(glob.glob(os.path.join(folder, '*.csv')))
    if not paths:
        print('No CSV files found in folder')
        return 1
    sample_paths = paths[:int(max_files)]
    for p in sample_paths:
        print('\n--- File:', os.path.basename(p), '---')
        delim, rows = detect_delimiter_and_preview(p, max_lines=int(lines_per_file))
        print('Detected delimiter:', repr(delim))
        for i, r in enumerate(rows):
            print(f'Row {i}:', r)
        analysis = analyze_rows(rows)
        print('Header present?', analysis['has_header'])
        if analysis['header']:
            print('Header row:', analysis['header'])
        print('Detected name column index:', analysis['name_idx'])
        print('Detected cpf column index:', analysis['cpf_idx'])
        print('Masked CPF present?', analysis['masked'])
    return 0

if __name__ == '__main__':
    folder = sys.argv[1] if len(sys.argv) > 1 else None
    max_files = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    lines_per_file = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    sys.exit(main(folder, max_files, lines_per_file))
