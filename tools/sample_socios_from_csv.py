import csv, re, sys
path = sys.argv[1]
cnpjs = []
with open(path, encoding='utf-8-sig') as f:
    r = csv.DictReader(f, delimiter=';')
    for row in r:
        nome = row.get('NOME_SOCIO','').strip()
        if nome:
            c = row.get('CNPJ','')
            digits = ''.join(re.findall(r'\d', c))
            cnpj_basico = digits[:8]
            cnpjs.append(cnpj_basico)
        if len(cnpjs) >= 10:
            break
print('sample_cnpj_basico:', cnpjs)
