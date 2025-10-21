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

def time_request(path, method='GET', json=None, timeout=120):
    url = API_BASE + path
    start = time.time()
    try:
        if method == 'GET':
            r = requests.get(url, timeout=timeout)
        else:
            r = requests.post(url, json=json, timeout=timeout)
        elapsed = time.time() - start
        status = r.status_code
        body_snippet = r.text[:400]
        return {'ok': True, 'status': status, 'elapsed': elapsed, 'snippet': body_snippet}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'elapsed': None}

print('\nBenchmarking endpoints...')
# Warm up health
print('Warming up /health')
print(time_request('/health', timeout=30))

print('\nTesting /stats (3 runs):')
for i in range(1,4):
    res = time_request('/stats', timeout=180)
    if res['ok']:
        print(f"/stats run {i}: status={res['status']} elapsed={res['elapsed']:.3f}s")
    else:
        print(f"/stats run {i}: ERROR: {res['error']}")

print('\nTesting /filters (3 runs):')
for i in range(1,4):
    res = time_request('/filters', timeout=300)
    if res['ok']:
        print(f"/filters run {i}: status={res['status']} elapsed={res['elapsed']:.3f}s")
    else:
        print(f"/filters run {i}: ERROR: {res['error']}")

print('\nDone')
