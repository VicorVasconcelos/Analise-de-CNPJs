import time
import requests

payload = {
    "uf": "DF",
    "situacao_cadastral": "08"
}

start = time.time()
try:
    resp = requests.post("http://localhost:5000/export", json=payload, timeout=480)
    elapsed = time.time() - start
    print(f"status={resp.status_code}")
    print(f"elapsed={elapsed:.2f}s")
    data = resp.json()
    print(f"error={data.get('error')}")
    print(f"message={data.get('message')}")
    print(f"total={data.get('total_registros')}")
    print(f"execution_time={data.get('execution_time')}")
except Exception as exc:
    elapsed = time.time() - start
    print("status=exception")
    print(f"elapsed={elapsed:.2f}s")
    print(str(exc))
