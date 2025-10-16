import sys, csv, re, json

if len(sys.argv) < 2:
    print('Usage: python report_export_summary.py <path-to-normalized-csv>')
    sys.exit(1)

path = sys.argv[1]

def only_digits(s):
    return ''.join(re.findall(r"\d", s or ""))

total = 0
cnpj_bad = 0
cnpj_examples = []
nome_count = 0
qual_count = 0
cpf_count = 0
samples = []

with open(path, 'r', encoding='utf-8-sig', errors='replace') as f:
    reader = csv.DictReader(f, delimiter=';')
    headers = reader.fieldnames
    for i,row in enumerate(reader, start=1):
        total += 1
        cnpj = row.get('CNPJ','')
        digits = only_digits(cnpj)
        if len(digits) != 14:
            cnpj_bad += 1
            if len(cnpj_examples) < 10:
                cnpj_examples.append((i+1, cnpj, digits))
        nome = row.get('NOME_SOCIO','')
        qual = row.get('QUALIFICACAO_SOCIO','')
        cpf = row.get('CPF_SOCIO','')
        if nome and nome.strip():
            nome_count += 1
        if qual and qual.strip():
            qual_count += 1
        if cpf and cpf.strip():
            cpf_count += 1
        if len(samples) < 10:
            samples.append({
                'line': i+1,
                'CNPJ': cnpj,
                'NOME_SOCIO': nome,
                'QUALIFICACAO_SOCIO': qual,
                'CPF_SOCIO': cpf
            })

print('File:', path)
print('Headers detected:', headers)
print('Total rows:', total)
print('CNPJs malformed (not 14 digits):', cnpj_bad)
if cnpj_examples:
    print('CNPJ examples (line, raw, digits):')
    print(json.dumps(cnpj_examples, ensure_ascii=False, indent=2))
print('NOME_SOCIO filled:', nome_count)
print('QUALIFICACAO_SOCIO filled:', qual_count)
print('CPF_SOCIO filled:', cpf_count)
print('\nSample rows (first 10):')
print(json.dumps(samples, ensure_ascii=False, indent=2))
