import requests
import json
url = 'http://127.0.0.1:5000/query'
payload = {'uf':'SP','page':1,'per_page':10}
try:
    r = requests.post(url, json=payload, timeout=20)
    print('status', r.status_code)
    try:
        print(json.dumps(r.json(), indent=2, ensure_ascii=False)[:2000])
    except Exception as e:
        print('no-json', e)
except Exception as e:
    print('request error', e)
