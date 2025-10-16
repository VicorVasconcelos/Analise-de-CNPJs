import urllib.request, json
url='http://127.0.0.1:5000/export'
data = json.dumps({'uf':'DF','socios_present':True}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type':'application/json'})
with urllib.request.urlopen(req, timeout=600) as resp:
    print(resp.read().decode('utf-8'))
