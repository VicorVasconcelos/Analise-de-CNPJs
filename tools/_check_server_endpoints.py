import requests
import time

urls = ['http://127.0.0.1:5000/', 'http://127.0.0.1:5000/health']
# give server a few seconds to start
for i in range(10):
    try:
        r = requests.get('http://127.0.0.1:5000/health', timeout=2)
        break
    except Exception:
        time.sleep(0.5)

for u in urls:
    try:
        r = requests.get(u, timeout=5)
        print(u, r.status_code)
        print('Content-Type:', r.headers.get('Content-Type'))
        print('Body preview:', r.text[:200].replace('\n',' '))
    except Exception as e:
        print(u, 'ERROR', str(e))
