import requests, json
url='http://127.0.0.1:5000/query'
payloads=[{}, {'filtros':{'uf':'SP'}}, {'filtros':{'uf':'SP','cnae':'4781400'}}]
for p in payloads:
    try:
        r=requests.post(url, json=p, timeout=120)
        print('payload=',p,'status=',r.status_code)
        print('body:', r.text[:1000])
    except Exception as e:
        print('payload=',p,'exception=',e)
