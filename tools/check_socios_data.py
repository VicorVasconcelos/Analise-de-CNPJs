import sqlite3, csv, re, os

DB = 'cnpj_database.db'
CSV = 'cnpj_exportacao_internal_20251013_134100.csv'

def only_digits(s):
    return re.sub(r'\D', '', s or '')

conn = sqlite3.connect(DB)
cur = conn.cursor()

print('DB:', DB)
cur.execute('SELECT COUNT(*) FROM socios')
print('socios total rows:', cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM socios WHERE (nome_socio IS NOT NULL AND TRIM(nome_socio) != '') OR (cnpj_cpf_socio IS NOT NULL AND TRIM(cnpj_cpf_socio) != '')")
print('socios rows with nome/cpf non-empty:', cur.fetchone()[0])

cur.execute('SELECT COUNT(DISTINCT cnpj_basico) FROM socios')
print('distinct cnpj_basico in socios:', cur.fetchone()[0])

# show sample of socios where nome not empty
print('\nSample socios with nome_socio non-empty:')
for row in cur.execute("SELECT cnpj_basico, nome_socio, cnpj_cpf_socio, qualificacao_socio FROM socios WHERE nome_socio IS NOT NULL AND TRIM(nome_socio) != '' LIMIT 5").fetchall():
    print(row)

# Read first 20 CNPJs from the CSV and map to cnpj_basico format
if not os.path.exists(CSV):
    print('\nCSV not found:', CSV)
else:
    print('\nChecking first 20 CNPJs from', CSV)
    with open(CSV, 'r', encoding='utf-8-sig', errors='replace') as fh:
        rdr = csv.reader(fh, delimiter=';')
        header = next(rdr, None)
        count = 0
        for r in rdr:
            if not r:
                continue
            cnpj_formatted = r[0].strip().strip('"')
            digits = only_digits(cnpj_formatted)
            cnpj_basico = digits[:8] if len(digits) >= 8 else digits
            # Query socios for this cnpj_basico
            cur.execute('SELECT COUNT(*) FROM socios WHERE cnpj_basico = ?', (cnpj_basico,))
            total = cur.fetchone()[0]
            cur.execute('SELECT COUNT(*) FROM socios WHERE cnpj_basico = ? AND nome_socio IS NOT NULL AND TRIM(nome_socio) != ""', (cnpj_basico,))
            have_names = cur.fetchone()[0]
            print(f'CNPJ: {cnpj_formatted} -> cnpj_basico={cnpj_basico} | socios rows={total} | with_nome={have_names}')
            if total > 0 and have_names == 0:
                # show up to 3 sample rows
                print(' Sample socios rows (up to 3):')
                for s in cur.execute('SELECT nome_socio, cnpj_cpf_socio, qualificacao_socio FROM socios WHERE cnpj_basico = ? LIMIT 3', (cnpj_basico,)).fetchall():
                    print('  ', s)
            count += 1
            if count >= 20:
                break

conn.close()
print('\nDone.')
