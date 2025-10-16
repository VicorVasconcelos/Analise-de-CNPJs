import csv
import re
import sqlite3
import os

IN = 'cnpj_exportacao_20251015_152740.normalized.csv'
OUT = 'cnpj_exportacao_20251015_152740.fixed_cnpj.csv'
REPORT = 'cnpj_exportacao_20251015_152740.cnpj_fix.report.txt'

def only_digits(s):
    return ''.join(re.findall(r"\d", s or ""))

conn = sqlite3.connect('cnpj_database.db')
cur = conn.cursor()

fixed = 0
unresolved = 0
examples = []

with open(IN, 'r', encoding='utf-8-sig', errors='replace') as inf, open(OUT, 'w', encoding='utf-8-sig', newline='') as outf:
    reader = csv.reader(inf, delimiter=';')
    writer = csv.writer(outf, delimiter=';')
    header = next(reader)
    writer.writerow(header)
    if 'CNPJ' in header:
        idx = header.index('CNPJ')
    else:
        idx = 0

    for i, row in enumerate(reader, start=2):
        if idx >= len(row):
            unresolved += 1
            examples.append((i, None, 'missing_column'))
            writer.writerow(row)
            continue
        raw = row[idx]
        digs = only_digits(raw)
        if len(digs) == 14:
            # OK
            writer.writerow(row)
            continue
        # if we have 8 digits (cnpj_basico), try to fetch ordem and dv
        if len(digs) == 8:
            cnpj_basico = digs
            # try estabelecimentos_completos first
            cur.execute("SELECT cnpj_ordem, cnpj_dv FROM estabelecimentos_completos WHERE cnpj_basico = ? LIMIT 1", (cnpj_basico,))
            r = cur.fetchone()
            if not r:
                cur.execute("SELECT cnpj_ordem, cnpj_dv FROM empresas_completas WHERE cnpj_basico = ? LIMIT 1", (cnpj_basico,))
                r = cur.fetchone()
            if r and r[0] and r[1]:
                ordem, dv = r[0], r[1]
                formatted = f"{cnpj_basico[:2]}.{cnpj_basico[2:5]}.{cnpj_basico[5:8]}/{ordem}-{dv}"
                row[idx] = formatted
                fixed += 1
                if len(examples) < 10:
                    examples.append((i, raw, formatted))
                writer.writerow(row)
                continue
        # fallback: leave as is, but note unresolved
        unresolved += 1
        if len(examples) < 10:
            examples.append((i, raw, None))
        writer.writerow(row)

conn.close()

with open(REPORT, 'w', encoding='utf-8') as rf:
    rf.write(f'input: {IN}\noutput: {OUT}\n')
    rf.write(f'fixed: {fixed}\nunresolved: {unresolved}\n')
    rf.write('examples:\n')
    for ex in examples:
        rf.write(str(ex) + '\n')

print('Finished CNPJ fix')
print('fixed:', fixed, 'unresolved:', unresolved)
print('report:', REPORT)
