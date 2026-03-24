import json
import time
import urllib.request

BASE = "http://127.0.0.1:5000"


def post(path, payload, timeout=120):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get(path, timeout=30):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    h = get("/health")
    print("health:", h.get("status"))

    candidates = [
        {"uf": "AC", "situacao_cadastral": "02"},
        {"uf": "AC", "situacao_cadastral": "08"},
        {"uf": "SE", "situacao_cadastral": "02"},
        {"uf": "RO", "situacao_cadastral": "02"},
        {"uf": "AM", "situacao_cadastral": "02"},
        {"uf": "TO", "situacao_cadastral": "02"},
    ]

    scored = []
    for f in candidates:
        q = dict(f)
        q.update({"page": 1, "per_page": 1, "fetch_all": False})
        t0 = time.perf_counter()
        r = post("/query", q, timeout=60)
        dt = time.perf_counter() - t0
        total = int(r.get("pagination", {}).get("total", 0))
        scored.append((abs(total - 17000), total, f))
        print("candidate:", f, "total=", total, "query_s=", round(dt, 3))

    scored.sort(key=lambda x: x[0])
    best_total = scored[0][1]
    best_filter = scored[0][2]
    print("best_filter:", best_filter, "best_total:", best_total)

    t0 = time.perf_counter()
    exp = post("/export", best_filter, timeout=900)
    dt = time.perf_counter() - t0

    print("export_http_s:", round(dt, 3))
    print("export_success:", exp.get("success"))
    print("export_total_registros:", exp.get("total_registros"))
    print("export_execution_time_backend_s:", exp.get("execution_time"))
    print("export_filename:", exp.get("filename"))
    print("export_warning:", exp.get("warning"))


if __name__ == "__main__":
    main()
