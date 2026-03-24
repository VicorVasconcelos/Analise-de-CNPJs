"""
Teste de query simples
"""
import requests
import json

payload = {
    "page": 1,
    "per_page": 10
}

try:
    print("Fazendo POST para /query...")
    response = requests.post("http://localhost:5000/query", json=payload, timeout=60)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nTotal de resultados: {data.get('total', 0)}")
        print(f"Página: {data.get('page', 0)}")
        print(f"Total de páginas: {data.get('total_pages', 0)}")
        print(f"Registros retornados: {len(data.get('results', []))}")
        if data.get('results'):
            print(f"\nPrimeiro resultado: {json.dumps(data['results'][0], indent=2, ensure_ascii=False)}")
    else:
        print(f"Erro: {response.text}")
        
except requests.exceptions.Timeout:
    print("Timeout - requisição demorou mais de 60 segundos")
except Exception as e:
    print(f"Erro: {e}")
