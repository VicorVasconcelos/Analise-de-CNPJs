import csv, re, json, sys
path='cnpj_exportacao_20251015_152740.normalized.csv'
with open(path, 'r', encoding='utf-8-sig', errors='replace') as f:
    r = csv.reader(f, delimiter=';')
    hdr = next(r)
    if 'CNPJ' in hdr:
        idx = hdr.index('CNPJ')
    else:
        idx = 0
    total=0
    bad=0
    examples=[]
    for i,row in enumerate(r, start=2):
        total+=1
        if idx>=len(row):
            bad+=1
            if len(examples)<10:
                examples.append((i, None, None))
            continue
        val = row[idx]
        digits = ''.join(re.findall(r'\d', val))
        if len(digits)!=14:
            bad+=1
            if len(examples)<10:
                examples.append((i, val, digits))
print('checked_rows:', total)
print('malformed_count:', bad)
print('examples:')
print(json.dumps(examples, ensure_ascii=False, indent=2))
