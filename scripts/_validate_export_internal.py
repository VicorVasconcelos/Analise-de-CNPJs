import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.app import create_app


def run_test(payload: dict, label: str) -> None:
    app = create_app("data/cnpj_database.db")
    client = app.test_client()

    start = time.time()
    resp = client.post("/export", json=payload)
    elapsed = time.time() - start

    data = resp.get_json(silent=True) or {}
    print(f"[{label}] status={resp.status_code} elapsed={elapsed:.2f}s")
    if isinstance(data, dict):
        print(f"[{label}] error={data.get('error')} message={data.get('message')}")
        print(f"[{label}] total={data.get('total_registros')} execution_time={data.get('execution_time')}")


if __name__ == "__main__":
    print("Iniciando validação interna...", flush=True)
    # Caso parecido com o print enviado (AM e situação BAIXADA)
    run_test({"uf": "AM", "situacao_cadastral": "08"}, "AM+BAIXADA")
