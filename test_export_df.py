#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import json
import time

# Teste com filtro específico (DF)
payload = {
    'filtros': {
        'uf': 'DF',
        'situacao_cadastral': ['02']  # Ativa
    }
}

try:
    print('Testando /export com filtro DF + ATIVA...')
    start = time.time()
    resp = requests.post('http://localhost:5000/export', json=payload, timeout=120)
    elapsed = time.time() - start
    print(f'Status: {resp.status_code} (tempo de requisição: {elapsed:.2f}s)')
    data = resp.json()
    if data.get('success'):
        print(f'✅ Exportação bem-sucedida!')
        print(f'   - Registros: {data.get("total_registros")}')
        print(f'   - Tempo backend: {data.get("execution_time")}s')
        print(f'   - Arquivo: {data.get("filename")}')
    else:
        print(f'❌ Erro: {data.get("error")}')
        print(f'   Mensagem: {data.get("message")}')
        print(f'   JSON: {json.dumps(data, indent=2, ensure_ascii=False)}')
except Exception as e:
    print(f'❌ Erro na requisição: {e}')
