import json
import os
import sys
import time
import traceback

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.app import create_app

out = {
    "query": {"ok": False},
    "export": {"ok": False},
}

try:
    app = create_app(db_path='data/cnpj_database.db')
    client = app.test_client()

    q_payload = {"uf": "DF", "cnae": "9602501", "page": 1, "per_page": 1, "fetch_all": False}
    t0 = time.perf_counter()
    q_resp = client.post('/query', json=q_payload)
    q_dt = time.perf_counter() - t0
    out["query"]["status_code"] = q_resp.status_code
    out["query"]["elapsed_s"] = round(q_dt, 3)
    try:
        q_json = q_resp.get_json() or {}
    except Exception:
        q_json = {}
    out["query"]["ok"] = q_resp.status_code == 200
    out["query"]["total"] = q_json.get("pagination", {}).get("total")
    out["query"]["error"] = q_json.get("error")
    out["query"]["message"] = q_json.get("message")

    e_payload = {"uf": "DF", "cnae": "9602501"}
    t1 = time.perf_counter()
    e_resp = client.post('/export', json=e_payload)
    e_dt = time.perf_counter() - t1
    out["export"]["status_code"] = e_resp.status_code
    out["export"]["elapsed_s"] = round(e_dt, 3)
    try:
        e_json = e_resp.get_json() or {}
    except Exception:
        e_json = {}
    out["export"]["ok"] = e_resp.status_code == 200 and bool(e_json.get("success"))
    out["export"]["success"] = e_json.get("success")
    out["export"]["total_registros"] = e_json.get("total_registros")
    out["export"]["execution_time"] = e_json.get("execution_time")
    out["export"]["filename"] = e_json.get("filename")
    out["export"]["warning"] = e_json.get("warning")
    out["export"]["error"] = e_json.get("error")
    out["export"]["message"] = e_json.get("message")
    out["export"]["details"] = e_json.get("details")
except Exception as ex:
    out["fatal_exception"] = repr(ex)
    out["traceback"] = traceback.format_exc()

with open('temp_export_case_df_9602501.json', 'w', encoding='utf-8') as fh:
    json.dump(out, fh, ensure_ascii=False, indent=2)

print('wrote temp_export_case_df_9602501.json')
