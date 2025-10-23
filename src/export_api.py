from flask import Blueprint, request, jsonify, current_app
import sqlite3, json, os, time

bp = Blueprint('export_api', __name__)

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'cnpj_database.db'))
EXPORT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'exports'))
os.makedirs(EXPORT_DIR, exist_ok=True)

from flask import Blueprint, request, jsonify, current_app
import sqlite3, json, os, time

bp = Blueprint('export_api', __name__)

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'cnpj_database.db'))
EXPORT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'exports'))
os.makedirs(EXPORT_DIR, exist_ok=True)

def _get_conn():
    return sqlite3.connect(DB_PATH, timeout=30)

@bp.route('/export-async', methods=['POST'])
def create_export():
    payload = request.get_json() or {}
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS export_jobs (id INTEGER PRIMARY KEY, payload TEXT, status TEXT, result_path TEXT, created_at REAL, finished_at REAL)')
    now = time.time()
    cur.execute('INSERT INTO export_jobs (payload, status, created_at) VALUES (?,?,?)', (json.dumps(payload), 'queued', now))
    job_id = cur.lastrowid
    conn.commit()
    conn.close()
    return jsonify({'job_id': job_id}), 202

@bp.route('/export-status/<int:job_id>', methods=['GET'])
def export_status(job_id):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute('SELECT id, status, result_path, created_at, finished_at FROM export_jobs WHERE id=?', (job_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return jsonify({'error':'not_found'}), 404
    id, status, result_path, created_at, finished_at = row
    return jsonify({'id':id,'status':status,'result_path':result_path,'created_at':created_at,'finished_at':finished_at})
