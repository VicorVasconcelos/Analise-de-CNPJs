import sqlite3, json, time, csv, os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB = os.path.join(ROOT, 'data', 'cnpj_database.db')
EXPORT_DIR = os.path.join(ROOT, 'data', 'exports')
os.makedirs(EXPORT_DIR, exist_ok=True)

def _conn():
    return sqlite3.connect(DB, timeout=30)

def next_job(conn):
    cur = conn.cursor()
    cur.execute("SELECT id, payload FROM export_jobs WHERE status='queued' ORDER BY created_at LIMIT 1")
    return cur.fetchone()

def process_job(job):
    job_id, payload_json = job
    payload = json.loads(payload_json)
    where = "1=1"
    params = []
    filtros = payload.get('filtros', {})
    if filtros.get('uf'):
        where += " AND uf=?"
        params.append(filtros['uf'])
    if filtros.get('cnae'):
        where += " AND cnae_fiscal_principal=?"
        params.append(filtros['cnae'])
    query = f"SELECT SUBSTR(cnpj_basico||cnpj_ordem||cnpj_dv,1,14) as cnpj, nome_fantasia, uf, municipio, cnae_fiscal_principal FROM estabelecimentos_completos WHERE {where}"
    out_path = os.path.join(EXPORT_DIR, f'export_{job_id}.csv')
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['cnpj','nome_fantasia','uf','municipio','cnae'])
        writer.writerows(rows)
    conn.close()
    return out_path

def run():
    conn = _conn()
    while True:
        job = next_job(conn)
        if not job:
            time.sleep(2)
            continue
        job_id, payload_json = job
        cur = conn.cursor()
        cur.execute("UPDATE export_jobs SET status='processing' WHERE id=?", (job_id,))
        conn.commit()
        try:
            out_path = process_job((job_id, payload_json))
            cur.execute("UPDATE export_jobs SET status='done', result_path=?, finished_at=? WHERE id=?", (out_path, time.time(), job_id))
            conn.commit()
        except Exception as e:
            cur.execute("UPDATE export_jobs SET status='failed', finished_at=? WHERE id=?", (time.time(), job_id))
            conn.commit()
        time.sleep(0.5)

if __name__ == '__main__':
    run()
