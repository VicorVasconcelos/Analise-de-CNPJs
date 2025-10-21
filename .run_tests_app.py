from importlib import import_module

app_mod = import_module('src.app')
app = app_mod.create_app()
client = app.test_client()
res = client.get('/')
print('GET / status:', res.status_code)
ct = res.headers.get('Content-Type','')
print('Content-Type:', ct)
body = res.get_data(as_text=True)
print('Body starts:', body[:400].replace('\n',' '))
res2 = client.get('/health')
print('/health', res2.status_code, res2.get_json())
