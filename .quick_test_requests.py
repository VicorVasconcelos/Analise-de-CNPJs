from importlib import import_module
mod = import_module('src.app')
app = mod.create_app()
client = app.test_client()
print('GET / ->', client.get('/').status_code)
print('GET /favicon.ico ->', client.get('/favicon.ico').status_code)
