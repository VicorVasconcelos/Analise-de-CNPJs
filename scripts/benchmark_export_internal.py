import os
import time
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.app import create_app


def run_export(payload):
    app = create_app(db_path='data/cnpj_database.db')
    client = app.test_client()

    t0 = time.perf_counter()
    resp = client.post('/export', json=payload)
    dt = time.perf_counter() - t0

    data = None
    try:
        data = resp.get_json()
    except Exception:
        pass

    print(f"status_code={resp.status_code}")
    print(f"elapsed_s={dt:.3f}")
    if isinstance(data, dict):
        print(f"success={data.get('success')}")
        print(f"total_registros={data.get('total_registros')}")
        print(f"execution_time={data.get('execution_time')}")
        print(f"filename={data.get('filename')}")
        print(f"warning={data.get('warning')}")
        fn = data.get('filename')
        if fn:
            print(f"file_exists={os.path.exists(fn)}")
            if os.path.exists(fn):
                print(f"file_size={os.path.getsize(fn)}")
    else:
        print("response_json=none")


if __name__ == '__main__':
    # filtro pequeno/moderado para validar se 1k demora anormal
    run_export({'uf': 'SE', 'situacao_cadastral': '02'})
