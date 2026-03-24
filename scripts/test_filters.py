"""
Teste do endpoint /filters
"""
import requests
import json

try:
    print("Chamando /filters...")
    response = requests.get("http://localhost:5000/filters", timeout=120)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nChaves retornadas: {list(data.keys())}")
        for key, value in data.items():
            if isinstance(value, list):
                print(f"  {key}: {len(value)} itens")
            else:
                print(f"  {key}: {value}")
    else:
        print(f"Erro: {response.text}")
        
except requests.exceptions.Timeout:
    print("Timeout - requisição demorou mais de 120 segundos")
except Exception as e:
    print(f"Erro: {e}")
