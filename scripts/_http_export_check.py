import time
import requests

payload = {
    "uf": "AM",
    "situacao_cadastral": "08",
}

start = time.time()
try:
    resp = requests.post("http://localhost:5000/export", json=payload, timeout=220)
    elapsed = time.time() - start
    print(f"STATUS={resp.status_code}")
    print(f"ELAPSED_S={elapsed:.2f}")
    try:
        print(resp.json())
    except Exception:
        print(resp.text[:2000])
except Exception as e:
    elapsed = time.time() - start
    print("STATUS=EXCEPTION")
    print(f"ELAPSED_S={elapsed:.2f}")
    print(str(e))
