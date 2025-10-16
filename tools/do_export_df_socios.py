import requests
import os
import json
import time

API_URL = 'http://127.0.0.1:5000/export'
PAYLOAD = {'uf': 'DF', 'socios_present': True}
REFERENCE = 'cnpj_exportacao_20251010_165816.csv'

print('Posting to', API_URL, PAYLOAD)
try:
    r = requests.post(API_URL, json=PAYLOAD, timeout=600)
except Exception as e:
    print('Request failed:', e)
    raise

print('Status code:', r.status_code)
try:
    data = r.json()
    print('Response JSON:', json.dumps(data, ensure_ascii=False))
except Exception:
    print('Non-JSON response; first 1000 chars:')
    print(r.text[:1000])
    raise SystemExit(1)

if 'filename' in data:
    fname = data['filename']
    if not os.path.isabs(fname):
        fname = os.path.join(os.getcwd(), fname)
    print('\nGenerated file:', fname)
    if os.path.exists(fname):
        print('\n--- First 10 lines of generated CSV ---')
        with open(fname, 'r', encoding='utf-8-sig', errors='replace') as fh:
            for i, line in enumerate(fh):
                print(line.rstrip('\n'))
                if i >= 10:
                    break
    else:
        print('File not found at', fname)

# Compare headers with reference file if present
if os.path.exists(REFERENCE):
    print('\nReference file found:', REFERENCE)
    with open(REFERENCE, 'r', encoding='utf-8-sig', errors='replace') as fh:
        ref_header = fh.readline().strip()
    print('\nReference header:')
    print(ref_header)
else:
    print('\nReference file not present in current folder:', REFERENCE)

print('\nDone.')
