"""
Script para testar os endpoints e verificar erros
"""
import requests
import json

base_url = "http://localhost:5000"

print("=" * 80)
print("TESTE DE ENDPOINTS")
print("=" * 80)

# Test /health
print("\n1. Testando /health...")
try:
    response = requests.get(f"{base_url}/health")
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Resposta: {json.dumps(data, indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"   ERRO: {e}")

# Test /stats
print("\n2. Testando /stats...")
try:
    response = requests.get(f"{base_url}/stats")
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Resposta: {json.dumps(data, indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"   ERRO: {e}")

# Test /filters
print("\n3. Testando /filters...")
try:
    response = requests.get(f"{base_url}/filters")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Total de chaves na resposta: {len(data)}")
        for key in data.keys():
            if isinstance(data[key], list):
                print(f"   - {key}: {len(data[key])} itens")
            else:
                print(f"   - {key}: {data[key]}")
    else:
        print(f"   Erro: {response.text}")
except Exception as e:
    print(f"   ERRO: {e}")

print("\n" + "=" * 80)
