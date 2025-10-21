import sqlite3
import time
import requests

DB = 'data/data/cnpj_database.db'
API_BASE = 'http://localhost:5000'

# Run ANALYZE on the DB
print('Running ANALYZE on', DB)
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute('ANALYZE')
conn.commit()
conn.close()
print('ANALYZE completed')

# Helper to time requests

def time_request(path, method='GET', json=None):
    url = API_BASE + path
    start = time.time()
    try:
        if method == 'GET':
            r = requests.get(url, timeout=120)
        else:
            r = requests.post(url, json=json, timeout=300)
        elapsed = time.time() - start
        status = r.status_code
        return status, elapsed, r.text[:200]
    except Exception as e:
        return 'ERR', None, str(e)

print('\nBenchmarking endpoints...')
# Warm up
print('Warming up /health')
print(time_request('/health'))

for i in range(1,4):
    status, elapsed, snippet = time_request('/stats')
    print(f'/stats run {i}: status={status} elapsed={elapsed:.3f}s')

for i in range(1,4):
    status, elapsed, snippet = time_request('/filters')
    print(f'/filters run {i}: status={status} elapsed={elapsed:.3f}s')

print('\nDone')
