import requests
for path in ('/stats','/filters'):
    url='http://127.0.0.1:5000'+path
    try:
        r=requests.get(url, timeout=20)
        print(path, 'status=', r.status_code)
        text=r.text
        print('body preview:', text[:800])
    except Exception as e:
        print(path, 'error=', e)
