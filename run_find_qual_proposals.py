# run_find_qual_proposals.py
# Uso:
#   python run_find_qual_proposals.py "C:\caminho\para\K3241.K03200Y0.D50913.CSV"
#
# Gera: socios_proposed_updates.csv na pasta atual com propostas encontradas (pode estar vazia)

import sys, csv, re, os

if len(sys.argv) < 2:
    print("Usage: python run_find_qual_proposals.py <path-to-socios-file>")
    sys.exit(1)

socios_file = sys.argv[1]
export_file = os.path.join(os.getcwd(), "cnpj_exportacao_20251016_122006.csv")
out_file = os.path.join(os.getcwd(), "socios_proposed_updates.csv")

def read_export_rows_with_socio_and_cpf(path):
    rows = []
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        sample = f.read(8192)
        f.seek(0)
        delim = ';' if ';' in sample else (',' if ',' in sample else ';')
        reader = csv.DictReader(f, delimiter=delim)
        for i, r in enumerate(reader, start=2):
            nome = (r.get('NOME_SOCIO') or r.get('nome_socio') or '').strip()
            cpf = (r.get('CPF_SOCIO') or r.get('cpf_socio') or '').strip()
            cnpj = (r.get('CNPJ') or r.get('cnpj') or '').strip()
            if nome and cpf:
                # extract middle 6 digits from masked like ***071591**
                digits = re.sub(r'\D', '', cpf)
                mid6 = digits[3:9] if len(digits) >= 9 else digits
                rows.append({'line': i, 'cnpj_raw': cnpj, 'cnpj_basico': re.sub(r'\D','',cnpj)[:8], 'nome': nome, 'cpf_raw': cpf, 'cpf_mid6': mid6})
    return rows

def scan_socios_file_for_quals(socios_path, cpf_mid6_set):
    # returns mapping cpf_mid6 -> list of tuples (line_no, row_dict, found_qual_field, found_value)
    results = {}
    # read raw lines to preserve indexing
    try:
        with open(socios_path, 'r', encoding='utf-8', errors='ignore') as f:
            sample = f.read(8192)
            f.seek(0)
            delim = ';' if ';' in sample else (',' if ',' in sample else ';')
            reader = csv.DictReader(f, delimiter=delim)
            headers = reader.fieldnames or []
            # common candidate header names for qualification code
            qual_candidates = [h for h in headers if h and re.search(r'qual|codigo|cod', h, re.I)]
            for rowno, row in enumerate(reader, start=2):
                # try to find cpf mid in any field
                rowtext = "|".join((str(v) for v in row.values()))
                for mid in cpf_mid6_set:
                    if mid and mid in rowtext:
                        # attempt to extract qual code
                        found_qual = None
                        found_key = None
                        # check known headers first
                        for h in qual_candidates:
                            v = (row.get(h) or '').strip()
                            if v:
                                found_qual = v
                                found_key = h
                                break
                        # fallback: try any column which looks numeric and short (1-3 chars)
                        if not found_qual:
                            for k,v in row.items():
                                vv = (v or '').strip()
                                if vv and re.fullmatch(r'\d{1,3}', vv):
                                    found_qual = vv
                                    found_key = k
                                    break
                        results.setdefault(mid, []).append({'line': rowno, 'row': row, 'found_key': found_key, 'found_qual': found_qual})
    except FileNotFoundError:
        print("Arquivo não encontrado:", socios_path)
        return results, None
    return results, headers

def main():
    if not os.path.exists(export_file):
        print("Export file not found in workspace path:", export_file)
        sys.exit(1)
    exp_rows = read_export_rows_with_socio_and_cpf(export_file)
    if not exp_rows:
        print("Nenhuma linha com NOME_SOCIO + CPF_SOCIO encontrada no export.")
        sys.exit(0)
    cpf_mids = set(r['cpf_mid6'] for r in exp_rows if r['cpf_mid6'])
    print(f"Encontradas {len(exp_rows)} linhas no export com NOME+CPF. Procurando {len(cpf_mids)} CPFs (mid6).")
    matched, headers = scan_socios_file_for_quals(socios_file, cpf_mids)
    # produce result CSV
    with open(out_file, 'w', newline='', encoding='utf-8') as outf:
        w = csv.writer(outf)
        w.writerow(['cnpj_basico','nome_socio','cpf_mid6','proposed_qual','source_file','source_line','source_field','source_row_preview'])
        for r in exp_rows:
            mid = r['cpf_mid6']
            matches = matched.get(mid, [])
            if matches:
                # choose first non-empty found_qual (report all later)
                chosen = None
                for m in matches:
                    if m['found_qual']:
                        chosen = m
                        break
                if chosen:
                    preview = str({k: (v[:80] if isinstance(v,str) else v) for k,v in chosen['row'].items()})
                    w.writerow([r['cnpj_basico'], r['nome'], mid, chosen['found_qual'], socios_file, chosen['line'], chosen['found_key'], preview])
                else:
                    # matched by cpf but no qual found
                    w.writerow([r['cnpj_basico'], r['nome'], mid, '', socios_file, matches[0]['line'], matches[0]['found_key'], str({k: (v[:80] if isinstance(v,str) else v) for k,v in matches[0]['row'].items()})])
            else:
                w.writerow([r['cnpj_basico'], r['nome'], mid, '', '', '', '', ''])
    # print summary
    print("Arquivo de propostas gerado:", out_file)
    # print quick summary of matches
    for r in exp_rows:
        mid = r['cpf_mid6']
        m = matched.get(mid)
        if not m:
            print(f"CSV line {r['line']} {r['nome']} cpf_mid6={mid} => no match in source file")
        else:
            quals = [mm['found_qual'] for mm in m if mm['found_qual']]
            print(f"CSV line {r['line']} {r['nome']} cpf_mid6={mid} => matches: {len(m)} rows; qual candidates: {quals if quals else 'none'}")
    print("Terminei. Verifique", out_file, "e me diga se quer que eu aplique as atualizações (dry-run antes).")

if __name__ == '__main__':
    main()
