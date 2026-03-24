#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import json

# Teste simples de export
payload = {
    'page': 1,
    'limit': 50,
    'filtros': {}
}

try:
    print('Testando /export...')
    resp = requests.post('http://localhost:5000/export', json=payload, timeout=30)
    print(f'Status: {resp.status_code}')
    data = resp.json()
    if data.get('success'):
        print(f'✅ Exportação bem-sucedida!')
        print(f'   - Registros: {data.get("total_registros")}')
        print(f'   - Tempo: {data.get("execution_time")}s')
        print(f'   - Arquivo: {data.get("filename")}')
    else:
        print(f'❌ Erro: {data.get("error")}')
        print(f'   Mensagem: {data.get("message")}')
except Exception as e:
    print(f'❌ Erro na requisição: {e}')
