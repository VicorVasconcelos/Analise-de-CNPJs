from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import sqlite3
import pandas as pd
import io
import time
import os
import sys
from datetime import datetime
# Import do módulo de database: quando o pacote `src` é usado como pacote, preferimos
# import relativo; quando o arquivo é executado diretamente como script (python src/app.py)
# a importação relativa falha. Tentamos o relativo e recuamos para um import absoluto.
try:
    from .database import CNPJDatabase
except Exception:
    try:
        from src.database import CNPJDatabase
    except Exception:
        # Último recurso: ajustar sys.path para permitir import a partir da raiz do repositório
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from src.database import CNPJDatabase
import threading
from functools import wraps
import json
import logging
import traceback
from werkzeug.exceptions import HTTPException

class CNPJApp:
    """
    Backend Flask para o Sistema de Análise de Dados CNPJ
    Provides APIs for filtering and exporting CNPJ data
    """

    def __init__(self, db_path="data/cnpj_database.db"):
        # Registrar a pasta web como pasta estática para servir index.html, JS, CSS diretamente
        web_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web'))
        self.web_dir = web_dir
        self.app = Flask(__name__, static_folder=web_dir, static_url_path='')
        CORS(self.app)  # Permitir requisições do frontend
        # Configurar logging para gravar erros no arquivo server.err
        log_handler = logging.FileHandler('server.err', encoding='utf-8')
        log_handler.setLevel(logging.ERROR)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        log_handler.setFormatter(formatter)
        # Adiciona também ao logger do Flask
        self.app.logger.addHandler(log_handler)
        logging.getLogger().addHandler(log_handler)
        self.db_path = db_path
        self.db = CNPJDatabase(db_path)

        # Configurar rotas
        self.setup_routes()

    def setup_routes(self):
        """Configura todas as rotas da API"""

        # Simple in-memory TTL cache for heavy endpoints
        class SimpleTTLCache:
            def __init__(self):
                self._data = {}
                self._lock = threading.Lock()

            def get(self, key):
                with self._lock:
                    entry = self._data.get(key)
                    if not entry:
                        return None
                    value, expires = entry
                    if time.time() > expires:
                        del self._data[key]
                        return None
                    return value

            def set(self, key, value, ttl=60):
                with self._lock:
                    self._data[key] = (value, time.time() + ttl)

        cache = SimpleTTLCache()

        def ttl_cache(ttl=60):
            def decorator(fn):
                @wraps(fn)
                def wrapper(*args, **kwargs):
                    cache_key = fn.__name__
                    cached = cache.get(cache_key)
                    if cached is not None:
                        return cached
                    result = fn(*args, **kwargs)
                    cache.set(cache_key, result, ttl=ttl)
                    return result
                return wrapper
            return decorator

        # Registrar um handler global para exceptions não tratadas
        @self.app.errorhandler(Exception)
        def _log_unhandled_exception(e):
            # Do not convert HTTP exceptions (404, 403, etc.) into 500
            if isinstance(e, HTTPException):
                return e
            tb = traceback.format_exc()
            try:
                self.app.logger.error("Unhandled exception: %s", tb)
            except Exception:
                pass
            try:
                with open('server.err', 'a', encoding='utf-8') as fh:
                    fh.write(f"\n[{datetime.now().isoformat()}] Unhandled exception:\n")
                    fh.write(tb)
                    fh.write('\n')
            except Exception:
                pass
            return jsonify({"error": str(e)}), 500

        def build_where_and_params(filtros):
            """Constrói where_clauses e params a partir do payload de filtros.
            Mesmo comportamento usado por /query para manter consistência com /export.
            """
            where_clauses = []
            params = []

            if filtros.get('razao_social'):
                where_clauses.append("(e.razao_social LIKE ? OR est.nome_fantasia LIKE ?)")
                termo = f"%{filtros['razao_social']}%"
                params.extend([termo, termo])

            if filtros.get('uf'):
                where_clauses.append("est.uf = ?")
                params.append(filtros['uf'])

            if filtros.get('cnae'):
                where_clauses.append("est.cnae_fiscal_principal = ?")
                params.append(filtros['cnae'])

            if filtros.get('natureza_juridica'):
                where_clauses.append("e.natureza_juridica = ?")
                params.append(filtros['natureza_juridica'])

            if filtros.get('porte'):
                # Normalize common human-readable labels (case-insensitive)
                porte_filtro = filtros['porte'].strip().upper()
                # Accept variants like 'GRANDE', 'GRANDE EMPRESA', 'Grande Empresa'
                if porte_filtro in ('MEI', 'MICRO-ENTIDADE', 'MICROEMPREENDEDOR') or porte_filtro == 'MEI':
                    where_clauses.append("s.opcao_mei = 'S'")
                elif porte_filtro in ('MICRO', 'MICROEMPRESA', 'ME'):
                    where_clauses.append("e.porte IN ('49', '50')")
                elif porte_filtro in ('PEQUENO', 'PEQUENA', 'EPP', 'EMPRESA DE PEQUENO PORTE'):
                    where_clauses.append("e.porte IN ('05', '16', '17', '19')")
                elif porte_filtro in ('MEDIO', 'MÉDIO', 'MEDIA', 'EMPRESA DE MÉDIO PORTE', 'EMPRESA DE MEDIO PORTE'):
                    where_clauses.append("e.porte IN ('43', '34', '65', '59')")
                elif porte_filtro in ('GRANDE', 'GRANDE EMPRESA', 'GRANDEEMPRESA'):
                    where_clauses.append("e.porte NOT IN ('49', '50', '05', '16', '17', '19', '43', '34', '65', '59') AND e.porte IS NOT NULL AND e.porte != ''")

            if filtros.get('situacao_cadastral'):
                where_clauses.append("est.situacao_cadastral = ?")
                params.append(filtros['situacao_cadastral'])

            # Filter to only include records that have socios in the socios table
            if filtros.get('socios_present'):
                # Use EXISTS to avoid relying on the aggregated join alias
                where_clauses.append("EXISTS (SELECT 1 FROM socios s2 WHERE s2.cnpj_basico = est.cnpj_basico)")

            if filtros.get('opcao_simples'):
                where_clauses.append("s.opcao_simples = ?")
                params.append(filtros['opcao_simples'])

            if filtros.get('municipio'):
                where_clauses.append("est.municipio = ?")
                params.append(filtros['municipio'])

            if filtros.get('bairro'):
                where_clauses.append("UPPER(est.bairro) LIKE UPPER(?)")
                params.append(f"%{filtros['bairro']}%")

            if filtros.get('matriz_filial'):
                where_clauses.append("est.identificador_matriz_filial = ?")
                params.append(filtros['matriz_filial'])

            return where_clauses, params

        @self.app.route('/')
        def home():
            """Servir a interface web do sistema a partir da pasta web/ (static_folder)."""
            try:
                return self.app.send_static_file('index.html')
            except Exception:
                self.app.logger.exception('Erro ao enviar index.html')
            return jsonify({
                "message": "🚀 API Sistema CNPJ - Dados Abertos da Receita Federal",
                "version": "1.0.0",
                "error": "Interface web (index.html) não encontrada",
                "timestamp": datetime.now().isoformat()
            }), 200

        @self.app.route('/api')
        def api_info():
            """Informações da API em formato JSON"""
            return jsonify({
                "message": "🚀 API Sistema CNPJ - Dados Abertos da Receita Federal",
                "version": "1.0.0",
                "endpoints": {
                    "GET /": "Interface web do sistema",
                    "GET /api": "Esta página",
                    "GET /health": "Status do sistema",
                    "GET /stats": "Estatísticas do banco de dados",
                    "GET /filters": "Opções disponíveis para filtros",
                    "POST /query": "Consultar dados com filtros",
                    "POST /export": "Exportar dados filtrados em CSV"
                },
                "timestamp": datetime.now().isoformat()
            })

        # (rota de diagnóstico temporária removida - revertida para o estado anterior)

        @self.app.route('/styles.css')
        def serve_css():
            """Servir o arquivo CSS (delegado ao static_folder)."""
            try:
                return self.app.send_static_file('styles.css')
            except Exception:
                return "/* CSS file not found */", 404

        @self.app.route('/script.js')
        def serve_js():
            """Servir o arquivo JavaScript (delegado ao static_folder)."""
            try:
                return self.app.send_static_file('script.js')
            except Exception:
                return "/* JavaScript file not found */", 404

        @self.app.route('/script-react.js')
        def serve_js_react():
            """Servir o arquivo JavaScript da versão React (delegado ao static_folder)."""
            try:
                return self.app.send_static_file('script-react.js')
            except Exception:
                return "/* React JavaScript file not found */", 404

        @self.app.route('/health')
        def health_check():
            """Verifica status do sistema"""
            # Check DB file existence first
            try:
                if not os.path.exists(self.db_path):
                    return jsonify({
                        "status": "no-db",
                        "database": "missing",
                        "db_path": self.db_path,
                        "timestamp": datetime.now().isoformat()
                    }), 200

                connected = self.db.connect()
                if not connected:
                    return jsonify({
                        "status": "disconnected",
                        "database": "cannot_connect",
                        "db_path": self.db_path,
                        "timestamp": datetime.now().isoformat()
                    }), 200

                cursor = self.db.connection.cursor()
                # Check if expected table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='empresas_completas'")
                if cursor.fetchone():
                    try:
                        cursor.execute("SELECT COUNT(*) FROM empresas_completas")
                        total_empresas = cursor.fetchone()[0]
                    except Exception:
                        total_empresas = None

                    return jsonify({
                        "status": "healthy",
                        "database": "connected",
                        "total_empresas": total_empresas,
                        "db_path": self.db_path,
                        "timestamp": datetime.now().isoformat()
                    }), 200
                else:
                    return jsonify({
                        "status": "uninitialized",
                        "database": "connected",
                        "message": "Tabelas esperadas não encontradas (ex: empresas_completas)",
                        "db_path": self.db_path,
                        "timestamp": datetime.now().isoformat()
                    }), 200
            finally:
                try:
                    self.db.disconnect()
                except Exception:
                    pass

        @self.app.route('/stats')
        @ttl_cache(ttl=120)
        def get_stats():
            """Retorna estatísticas do banco de dados"""
            try:
                if not self.db.connect():
                    return jsonify({"error": "Database connection failed"}), 500

                cursor = self.db.connection.cursor()

                # Prefer aggregated meta table when available (much faster)
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='aggregates_meta'")
                if cursor.fetchone():
                    cursor.execute("SELECT total_empresas, total_estabelecimentos, total_simples, total_cnaes FROM aggregates_meta LIMIT 1")
                    row = cursor.fetchone()
                    if row:
                        total_empresas, total_estabelecimentos, total_simples, total_cnaes = row
                    else:
                        total_empresas = total_estabelecimentos = total_simples = total_cnaes = 0
                else:
                    # Fallback to direct counts (slower)
                    cursor.execute("SELECT COUNT(*) FROM empresas_completas")
                    total_empresas = cursor.fetchone()[0]
                    cursor.execute("SELECT COUNT(*) FROM estabelecimentos_completos")
                    total_estabelecimentos = cursor.fetchone()[0]
                    cursor.execute("SELECT COUNT(*) FROM simples")
                    total_simples = cursor.fetchone()[0]
                    cursor.execute("SELECT COUNT(*) FROM cnaes")
                    total_cnaes = cursor.fetchone()[0]

                # Top UFs - use aggregates_ufs if present
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='aggregates_ufs'")
                if cursor.fetchone():
                    cursor.execute("SELECT uf, total_estabelecimentos as total FROM aggregates_ufs ORDER BY total DESC LIMIT 5")
                    top_ufs = [{"uf": uf, "total": total} for uf, total in cursor.fetchall()]
                else:
                    cursor.execute("""
                        SELECT uf, COUNT(*) as total
                        FROM estabelecimentos_completos
                        WHERE uf IS NOT NULL AND uf != ''
                        GROUP BY uf
                        ORDER BY total DESC
                        LIMIT 5
                    """)
                    top_ufs = [{"uf": uf, "total": total} for uf, total in cursor.fetchall()]

                # Top Naturezas - use aggregates_naturezas if present
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='aggregates_naturezas'")
                if cursor.fetchone():
                    cursor.execute("SELECT codigo_natureza, descricao_natureza, total FROM aggregates_naturezas ORDER BY total DESC LIMIT 10")
                    top_naturezas = [{"natureza": descricao or "N/A", "total": total} for _, descricao, total in cursor.fetchall()]
                else:
                    cursor.execute("""
                        SELECT n.descricao_natureza, COUNT(*) as total
                        FROM empresas_completas e
                        LEFT JOIN naturezas n ON e.natureza_juridica = n.codigo_natureza
                        GROUP BY e.natureza_juridica
                        ORDER BY total DESC
                        LIMIT 10
                    """)
                    top_naturezas = [{"natureza": natureza or "N/A", "total": total} for natureza, total in cursor.fetchall()]

                self.db.disconnect()

                return jsonify({
                    "tabelas": {
                        "empresas": total_empresas,
                        "estabelecimentos": total_estabelecimentos,
                        "simples": total_simples,
                        "cnaes": total_cnaes,
                        "naturezas": 91,
                        "qualificacoes": 68,
                        "motivos": 63
                    },
                    "top_ufs": top_ufs,
                    "top_naturezas": top_naturezas,
                    "timestamp": datetime.now().isoformat()
                })

            except Exception as e:
                import traceback
                # Print to console for immediate visibility
                traceback.print_exc()
                # Also append full traceback to server.err for later inspection
                try:
                    with open('server.err', 'a', encoding='utf-8') as fh:
                        fh.write(f"[{datetime.now().isoformat()}] Exception in /export:\n")
                        fh.write(traceback.format_exc())
                        fh.write("\n\n")
                except Exception as log_e:
                    print(f"[WARN] Failed to write server.err: {log_e}")

                return jsonify({"error": str(e)}), 500

        @self.app.route('/filters')
        @ttl_cache(ttl=300)
        def get_filter_options():
            """Retorna opções disponíveis para cada filtro"""
            import traceback
            try:
                start_total = time.time()
                if not self.db.connect():
                    print("[ERRO] Falha ao conectar ao banco de dados em /filters")
                    return jsonify({"error": "Database connection failed"}), 500

                cursor = self.db.connection.cursor()

                # Verificar se temos dados de estabelecimentos (fast check)
                t0 = time.time()
                cursor.execute("SELECT 1 FROM estabelecimentos_completos LIMIT 1")
                has_estabelecimentos = cursor.fetchone() is not None
                t_has_est = time.time() - t0
                print(f"[TIMING] /filters has_estabelecimentos: {t_has_est:.3f}s (fast check)")

                # Preferir tabelas de aggregates (pré-computadas) se existirem
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='aggregates_ufs'")
                t0 = time.time()
                if cursor.fetchone():
                    # aggregates_ufs existe - usamos os dados, ordenando por uf ASC para o dropdown
                    cursor.execute("SELECT uf, total_estabelecimentos as total FROM aggregates_ufs ORDER BY uf ASC")
                    ufs = [{"value": uf, "label": (uf or ''), "count": total} for uf, total in cursor.fetchall()]
                else:
                    # UFs disponíveis - usar estabelecimentos_completos e ordenar por uf ASC
                    cursor.execute("""
                        SELECT uf, COUNT(*) as total_estabelecimentos
                        FROM estabelecimentos_completos
                        WHERE uf IS NOT NULL AND uf != ''
                        GROUP BY uf
                        ORDER BY uf ASC
                    """)
                    ufs = [{"value": uf, "label": (uf or ''), "count": total} for uf, total in cursor.fetchall()]
                t_ufs = time.time() - t0
                print(f"[TIMING] /filters ufs: {t_ufs:.3f}s, found {len(ufs)} ufs")

                # CNAEs disponíveis - preferir aggregates
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='aggregates_cnaes'")
                t0 = time.time()
                if cursor.fetchone():
                    cursor.execute("SELECT codigo_cnae, descricao_cnae, total FROM aggregates_cnaes ORDER BY total DESC")
                    cnaes = [{"value": codigo, "label": f"{codigo} - {(descricao or 'Descrição não disponível')[:50]}...", "count": total} for codigo, descricao, total in cursor.fetchall()]
                else:
                    cursor.execute("""
                        SELECT DISTINCT e.cnae_fiscal_principal as codigo_cnae, c.descricao_cnae
                        FROM estabelecimentos_completos e
                        LEFT JOIN cnaes c ON e.cnae_fiscal_principal = c.codigo_cnae
                        WHERE e.cnae_fiscal_principal IS NOT NULL AND e.cnae_fiscal_principal != ''
                        ORDER BY e.cnae_fiscal_principal
                    """)
                    cnaes = [{"value": codigo, "label": f"{codigo} - {(descricao or 'Descrição não disponível')[:50]}...", "count": 0} for codigo, descricao in cursor.fetchall()]
                t_cnaes = time.time() - t0
                print(f"[TIMING] /filters cnaes: {t_cnaes:.3f}s, found {len(cnaes)} cnaes")

                # Naturezas Jurídicas disponíveis - prefer aggregates if present
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='aggregates_naturezas'")
                if cursor.fetchone():
                    cursor.execute("SELECT codigo_natureza, descricao_natureza, total FROM aggregates_naturezas ORDER BY total DESC LIMIT 50")
                    naturezas_juridicas = [{"value": codigo, "label": (descricao or ''), "count": total}
                               for codigo, descricao, total in cursor.fetchall()]
                else:
                    cursor.execute("""
                        SELECT n.codigo_natureza, n.descricao_natureza, COUNT(*) as total
                        FROM empresas_completas e
                        INNER JOIN naturezas n ON e.natureza_juridica = n.codigo_natureza
                        GROUP BY n.codigo_natureza, n.descricao_natureza
                        ORDER BY total DESC
                        LIMIT 50
                    """)
                    naturezas_juridicas = [{"value": codigo, "label": (descricao or ''), "count": total}
                               for codigo, descricao, total in cursor.fetchall()]

                # Portes de Empresa disponíveis - use aggregates_portes if present
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='aggregates_portes'")
                portes = []
                if cursor.fetchone():
                    cursor.execute("SELECT porte_key, total FROM aggregates_portes ORDER BY total DESC")
                    for porte_key, total in cursor.fetchall():
                        label = {
                            'MEI': 'Microempreendedor Individual (MEI)',
                            'MICRO': 'Microempresa (ME)',
                            'PEQUENO': 'Empresa de Pequeno Porte (EPP)',
                            'MEDIO': 'Empresa de Médio Porte',
                            'GRANDE': 'Grande Empresa',
                            'NAO_INFORMADO': 'Não Informado'
                        }.get(porte_key, porte_key)
                        portes.append({"value": porte_key, "label": label, "count": total})
                else:
                    # Fallback to slower counts
                    portes_classificacao = []
                    cursor.execute("""
                        SELECT COUNT(*) as total
                        FROM simples
                        WHERE opcao_mei = 'S'
                    """)
                    total_mei = cursor.fetchone()[0]
                    if total_mei > 0:
                        portes_classificacao.append({"value": "MEI", "label": "Microempreendedor Individual (MEI)", "count": total_mei})
                    cursor.execute("""
                        SELECT COUNT(*) as total
                        FROM empresas_completas
                        WHERE porte IN ('49', '50') AND porte IS NOT NULL AND porte != ''
                    """)
                    total_micro = cursor.fetchone()[0]
                    if total_micro > 0:
                        portes_classificacao.append({"value": "MICRO", "label": "Microempresa (ME)", "count": total_micro})
                    cursor.execute("""
                        SELECT COUNT(*) as total
                        FROM empresas_completas
                        WHERE porte IN ('05', '16', '17', '19') AND porte IS NOT NULL AND porte != ''
                    """)
                    total_pequeno = cursor.fetchone()[0]
                    if total_pequeno > 0:
                        portes_classificacao.append({"value": "PEQUENO", "label": "Empresa de Pequeno Porte (EPP)", "count": total_pequeno})
                    cursor.execute("""
                        SELECT COUNT(*) as total
                        FROM empresas_completas
                        WHERE porte IN ('43', '34', '65', '59') AND porte IS NOT NULL AND porte != ''
                    """)
                    total_medio = cursor.fetchone()[0]
                    if total_medio > 0:
                        portes_classificacao.append({"value": "MEDIO", "label": "Empresa de Médio Porte", "count": total_medio})
                    cursor.execute("""
                        SELECT COUNT(*) as total
                        FROM empresas_completas
                        WHERE porte NOT IN ('49', '50', '05', '16', '17', '19', '43', '34', '65', '59')
                        AND porte IS NOT NULL AND porte != ''
                    """)
                    total_grande = cursor.fetchone()[0]
                    if total_grande > 0:
                        portes_classificacao.append({"value": "GRANDE", "label": "Grande Empresa", "count": total_grande})
                    portes = portes_classificacao

                # Status Simples Nacional - use aggregates_simples if present
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='aggregates_simples'")
                simples_opcoes = []
                if cursor.fetchone():
                    cursor.execute("SELECT opcao, total FROM aggregates_simples ORDER BY total DESC")
                    for opcao, total in cursor.fetchall():
                        descricao = 'Optante pelo Simples' if opcao == 'S' else ('Não Optante' if opcao == 'N' else 'Não Informado')
                        simples_opcoes.append({"value": opcao, "label": descricao, "count": total})
                else:
                    cursor.execute("""
                        SELECT
                            opcao_simples,
                            CASE WHEN opcao_simples = 'S' THEN 'Optante pelo Simples'
                                 WHEN opcao_simples = 'N' THEN 'Não Optante'
                                 ELSE 'Não Informado' END as descricao,
                            COUNT(*) as total
                        FROM simples
                        GROUP BY opcao_simples
                        ORDER BY total DESC
                    """)
                    simples_opcoes = [{"value": opcao, "label": descricao, "count": total}
                                    for opcao, descricao, total in cursor.fetchall()]

                # Situações Cadastrais disponíveis
                situacoes_cadastrais = [
                    {"value": "01", "label": "Nulo"},
                    {"value": "02", "label": "Ativa"},
                    {"value": "03", "label": "Suspensa"},
                    {"value": "04", "label": "Inapta"},
                    {"value": "08", "label": "Baixada"}
                ]

                # Montar resposta
                response_obj = {
                    "ufs": ufs,
                    "cnaes": cnaes,
                    "naturezas_juridicas": naturezas_juridicas,
                    "portes": portes,
                    "simples_opcoes": simples_opcoes,
                    "situacoes_cadastrais": situacoes_cadastrais,
                    "has_estabelecimentos": has_estabelecimentos,
                    "timestamp": datetime.now().isoformat()
                }

                # Logs adicionais e dump para arquivo para diagnóstico front-end/back-end
                try:
                    print(f"[INFO] /filters counts -> ufs={len(ufs)}, cnaes={len(cnaes)}, naturezas={len(naturezas_juridicas)}, portes={len(portes)}, simples={len(simples_opcoes)}, situacoes={len(situacoes_cadastrais)}")
                    with open('last_filters_response.json', 'w', encoding='utf-8') as fh:
                        json.dump(response_obj, fh, ensure_ascii=False, indent=2)
                except Exception as dump_e:
                    print(f"[WARN] falha ao gravar last_filters_response.json: {dump_e}")

                self.db.disconnect()

                return jsonify(response_obj)

            except Exception as e:
                print("[ERRO] Exceção no handler /filters:")
                traceback.print_exc()
                return jsonify({"error": str(e)}), 500

        @self.app.route('/query', methods=['POST'])
        def query_data():
            """Consulta dados com filtros aplicados"""
            try:
                payload = request.get_json() or {}
                # suportar dois formatos: { ...filtros... } ou {"filtros": {...} }
                if isinstance(payload, dict) and 'filtros' in payload and isinstance(payload['filtros'], dict):
                    filtros = payload['filtros']
                    # permitir paginação no topo junto com filtros: suportar payload{"page":.., "per_page":.., "filtros":{}}
                    # caso page/per_page estejam no payload raiz, copie-os para filtros esperados
                    if 'page' in payload and 'page' not in filtros:
                        filtros['page'] = payload.get('page')
                    if 'per_page' in payload and 'per_page' not in filtros:
                        filtros['per_page'] = payload.get('per_page')
                else:
                    filtros = payload
                page = filtros.get('page', 1)
                per_page = min(filtros.get('per_page', 50), 1000)  # Máximo 1000 por página

                if not self.db.connect():
                    return jsonify({"error": "Database connection failed"}), 500

                # Construir consulta dinâmica - usando a função centralizada para consistência com /export
                where_clauses, params = build_where_and_params(filtros)
                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

                # helper: progress handler factory (define cedo para estar sempre disponível)
                def _make_progress_handler(start, max_seconds):
                    def handler():
                        return 1 if (time.time() - start) > max_seconds else 0
                    return handler

                # Detectar se podemos usar um caminho rápido (fast path) que evita JOINs pesados.
                # Fast path when filters do NOT reference empresa-level columns or socios/simples
                expensive_keys = {'razao_social', 'natureza_juridica', 'porte', 'opcao_simples', 'socios_present'}
                use_fast_path = not any(k in filtros for k in expensive_keys)

                # Contar total - tentar usar tabelas de agregados quando aplicável para evitar COUNTs pesados
                cursor = self.db.connection.cursor()

                total = None
                # marca tempo de início para medir execução mesmo quando total vier de agregados
                inicio = time.time()
                # Caso sem filtros (consulta global) podemos usar aggregates_meta
                if (not where_clauses):
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='aggregates_meta'")
                    if cursor.fetchone():
                        cursor.execute("SELECT total_estabelecimentos FROM aggregates_meta LIMIT 1")
                        row = cursor.fetchone()
                        if row:
                            total = row[0]

                # Caso com um único filtro simples (uf, cnae, natureza, porte, simples) tentar usar tabela específica
                if total is None:
                    simple_agg_map = {
                        'uf': ('aggregates_ufs', 'uf', 'total_estabelecimentos'),
                        'cnae': ('aggregates_cnaes', 'codigo_cnae', 'total'),
                        'natureza_juridica': ('aggregates_naturezas', 'codigo_natureza', 'total'),
                        'porte': ('aggregates_portes', 'porte_key', 'total'),
                        'opcao_simples': ('aggregates_simples', 'opcao', 'total')
                    }
                    # detect filters keys excluding pagination params
                    filter_keys = [k for k in filtros.keys() if k not in ('page', 'per_page')]
                    if len(filter_keys) == 1:
                        fk = filter_keys[0]
                        if fk in simple_agg_map:
                            agg_table, agg_col, agg_total_col = simple_agg_map[fk]
                            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (agg_table,))
                            if cursor.fetchone():
                                # Query the aggregates table for the matching value
                                val = filtros.get(fk)
                                try:
                                    cursor.execute(f"SELECT {agg_total_col} FROM {agg_table} WHERE {agg_col} = ? LIMIT 1", (val,))
                                    r = cursor.fetchone()
                                    if r:
                                        total = r[0]
                                except Exception:
                                    # If any problem occurs, fallback to regular count
                                    total = None

                # Se ainda não obtivemos total por agregados, executar o COUNT com proteção de progress handler
                if total is None:
                    if use_fast_path:
                        # Count only on estabelecimentos_completos (indexed on uf, cnae, municipio)
                        sql_count = f"SELECT COUNT(*) FROM estabelecimentos_completos est WHERE {where_sql}"
                    else:
                        # Full join path (slower) - needed when filters reference empresa/simples/socios
                        sql_count = f"""
                            SELECT COUNT(*)
                            FROM estabelecimentos_completos est
                            LEFT JOIN empresas_completas e ON est.cnpj_basico = e.cnpj_basico
                            LEFT JOIN simples s ON est.cnpj_basico = s.cnpj_basico
                            WHERE {where_sql}
                        """

                    inicio = time.time()
                    # safety: set a progress handler to abort long-running SQL (protect interactive use)
                    def _make_progress_handler(start, max_seconds):
                        def handler():
                            return 1 if (time.time() - start) > max_seconds else 0
                        return handler

                    try:
                        # abort count if longer than 30 seconds (increased temporarily for debugging)
                        self.db.connection.set_progress_handler(_make_progress_handler(inicio, 30), 1000)
                        cursor.execute(sql_count, params)
                        total = cursor.fetchone()[0]
                        # debug log: count executed
                        print(f"[DEBUG] count executed sql_count startswith: {sql_count.strip()[:60]}")
                    except sqlite3.OperationalError as oe:
                        # Query interrupted by progress handler
                        try:
                            self.db.disconnect()
                        except Exception:
                            pass
                        return jsonify({"error": "query_timeout", "message": "Count query timed out", "details": str(oe)}), 503
                    finally:
                        try:
                            self.db.connection.set_progress_handler(None, 0)
                        except Exception:
                            pass

                # Buscar dados paginados - baseado nos dados dos estabelecimentos
                offset = (page - 1) * per_page

                if use_fast_path:
                    # Simpler select primarily from estabelecimentos_completos, joining only small lookup tables
                    # choose order column: avoid expensive ORDER BY on large non-indexed columns for broad queries
                    # Use rowid ordering to avoid expensive sorts on large tables
                    order_col = 'est.rowid'
                    # Fast path: avoid heavy join to empresas_completas for broad queries.
                    # Returning a placeholder for razao_social keeps the result shape unchanged
                    # while eliminating the expensive join.
                    sql_data = f"""
                        SELECT
                            SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 1, 2) || '.' ||
                            SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 3, 3) || '.' ||
                            SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 6, 3) || '/' ||
                            SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 9, 4) || '-' ||
                            SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 13, 2) as cnpj_formatado,
                            COALESCE(est.nome_fantasia, 'N/A') as nome_fantasia,
                            CASE WHEN est.situacao_cadastral = '02' THEN 'ATIVA'
                                 WHEN est.situacao_cadastral = '03' THEN 'SUSPENSA'
                                 WHEN est.situacao_cadastral = '04' THEN 'INAPTA'
                                 WHEN est.situacao_cadastral = '08' THEN 'BAIXADA'
                                 ELSE 'NÃO INFORMADO' END as situacao,
                            est.uf,
                            COALESCE(m.nome_municipio, 'N/A') as municipio,
                            '' as porte,
                            '' as natureza_juridica,
                            '' as razao_social
                        FROM estabelecimentos_completos est
                        LEFT JOIN municipios m ON est.municipio = m.codigo_municipio
                        LEFT JOIN cnaes c ON est.cnae_fiscal_principal = c.codigo_cnae
                        WHERE {where_sql}
                        ORDER BY {order_col}
                        LIMIT ? OFFSET ?
                    """
                else:
                    # for heavy path, avoid ordering by empresa fields when no filters are applied
                    if not where_clauses:
                        order_clause = 'est.rowid'
                    else:
                        order_clause = 'e.razao_social, est.cnpj_ordem'
                    sql_data = f"""
                        SELECT
                            SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 1, 2) || '.' ||
                            SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 3, 3) || '.' ||
                            SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 6, 3) || '/' ||
                            SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 9, 4) || '-' ||
                            SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 13, 2) as cnpj_formatado,
                            COALESCE(e.razao_social, 'N/A') as razao_social,
                            COALESCE(est.nome_fantasia, 'N/A') as nome_fantasia,
                            CASE WHEN est.situacao_cadastral = '02' THEN 'ATIVA'
                                 WHEN est.situacao_cadastral = '03' THEN 'SUSPENSA'
                                 WHEN est.situacao_cadastral = '04' THEN 'INAPTA'
                                 WHEN est.situacao_cadastral = '08' THEN 'BAIXADA'
                                 ELSE 'NÃO INFORMADO' END as situacao,
                            est.uf,
                            COALESCE(m.nome_municipio, 'N/A') as municipio,
                            CASE WHEN s.opcao_mei = 'S' THEN 'Microempreendedor Individual (MEI)'
                                 WHEN e.porte IN ('49', '50') THEN 'Microempresa (ME)'
                                 WHEN e.porte IN ('05', '16', '17', '19') THEN 'Empresa de Pequeno Porte (EPP)'
                                 WHEN e.porte IN ('43', '34', '65', '59') THEN 'Empresa de Médio Porte'
                                 WHEN e.porte NOT IN ('49', '50', '05', '16', '17', '19', '43', '34', '65', '59')
                                      AND e.porte IS NOT NULL AND e.porte != '' THEN 'Grande Empresa'
                                 ELSE 'Não Informado' END as porte,
                            COALESCE(n.descricao_natureza, 'N/A') as natureza_juridica
                        FROM estabelecimentos_completos est
                        LEFT JOIN empresas_completas e ON est.cnpj_basico = e.cnpj_basico
                        LEFT JOIN naturezas n ON e.natureza_juridica = n.codigo_natureza
                        LEFT JOIN simples s ON est.cnpj_basico = s.cnpj_basico
                        LEFT JOIN cnaes c ON est.cnae_fiscal_principal = c.codigo_cnae
                        LEFT JOIN municipios m ON est.municipio = m.codigo_municipio
                        WHERE {where_sql}
                        ORDER BY {order_clause}
                        LIMIT ? OFFSET ?
                    """

                try:
                    # debug log: indicate which sql_data will be executed
                    print(f"[DEBUG] Executing data SQL (use_fast_path={use_fast_path}, where_clauses={len(where_clauses)})")
                    print(f"[DEBUG] sql_data preview: {sql_data.strip()[:200]}")
                    # allow slightly longer for data fetch (increased temporarily for debugging)
                    start_data = time.time()
                    self.db.connection.set_progress_handler(_make_progress_handler(start_data, 60), 1000)
                    cursor.execute(sql_data, params + [per_page, offset])
                except sqlite3.OperationalError as oe:
                    try:
                        self.db.disconnect()
                    except Exception:
                        pass
                    return jsonify({"error": "query_timeout", "message": "Data query timed out", "details": str(oe)}), 503
                finally:
                    try:
                        self.db.connection.set_progress_handler(None, 0)
                    except Exception:
                        pass
                resultados = cursor.fetchall()
                tempo = time.time() - inicio

                # Formatar resultados
                dados = []
                for row in resultados:
                    dados.append({
                        "cnpj_formatado": row[0],
                        "razao_social": row[1],
                        "nome_fantasia": row[2],
                        "situacao": row[3],
                        "uf": row[4],
                        "municipio": row[5],
                        "porte": row[6],
                        "natureza_juridica": row[7]
                    })

                self.db.disconnect()

                return jsonify({
                    "success": True,
                    "data": dados,
                    "pagination": {
                        "page": page,
                        "per_page": per_page,
                        "total": total,
                        "pages": (total + per_page - 1) // per_page
                    },
                    "query_info": {
                        "filters_applied": len(where_clauses),
                        "execution_time": round(tempo, 3)
                    },
                    "timestamp": datetime.now().isoformat()
                })

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route('/export', methods=['POST'])
        def export_data():
            """Exporta dados filtrados em CSV"""
            try:
                filtros = request.get_json() or {}

                if not self.db.connect():
                    return jsonify({"error": "Database connection failed"}), 500

                # Construir consulta dinâmica (igual ao query) usando helper centralizado
                where_clauses, params = build_where_and_params(filtros)
                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

                # Se tabela de socios não existir, tentar importar arquivos CSV da pasta externa (Socio0)
                cursor = self.db.connection.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='socios'")
                if not cursor.fetchone():
                    socio_dir = r"C:\Users\victor.vasconcelos\Documents\PROJETO CNPJ\Socio0"
                    try:
                        if os.path.isdir(socio_dir):
                            # Importar todos os CSVs da pasta para a tabela 'socios' (se possível)
                            for fname in os.listdir(socio_dir):
                                if fname.lower().endswith('.csv'):
                                    fpath = os.path.join(socio_dir, fname)
                                    try:
                                        df_soc = pd.read_csv(fpath, dtype=str, encoding='utf-8', error_bad_lines=False)
                                    except Exception:
                                        # tentar leitura com latin-1 como fallback
                                        df_soc = pd.read_csv(fpath, dtype=str, encoding='latin-1', engine='python')

                                    # Normalizar nomes de colunas esperados
                                    cols = {c.lower(): c for c in df_soc.columns}
                                    mapping = {}
                                    if 'nome_socio' in cols:
                                        mapping[cols['nome_socio']] = 'nome_socio'
                                    elif 'nome' in cols:
                                        mapping[cols['nome']] = 'nome_socio'
                                    if 'cnpj_cpf_socio' in cols:
                                        mapping[cols['cnpj_cpf_socio']] = 'cnpj_cpf_socio'
                                    elif 'cpf' in cols:
                                        mapping[cols['cpf']] = 'cnpj_cpf_socio'
                                    if 'qualificacao_socio' in cols:
                                        mapping[cols['qualificacao_socio']] = 'qualificacao_socio'
                                    elif 'qualificacao' in cols:
                                        mapping[cols['qualificacao']] = 'qualificacao_socio'
                                    if 'cnpj_basico' in cols:
                                        mapping[cols['cnpj_basico']] = 'cnpj_basico'

                                    if mapping:
                                        df_soc = df_soc.rename(columns=mapping)
                                    # Garantir colunas mínimas
                                    for expected in ['cnpj_basico', 'nome_socio', 'cnpj_cpf_socio', 'qualificacao_socio']:
                                        if expected not in df_soc.columns:
                                            df_soc[expected] = ''

                                    # Gravar na tabela sqlite 'socios'
                                    try:
                                        df_soc[['cnpj_basico', 'nome_socio', 'cnpj_cpf_socio', 'qualificacao_socio']].to_sql('socios', self.db.connection, if_exists='append', index=False)
                                        print(f"[INFO] importado socios de {fpath} para tabela 'socios'")
                                    except Exception as e:
                                        print(f"[WARN] falha ao importar socios de {fpath}: {e}")
                    except Exception as e:
                        print(f"[WARN] falha ao verificar/importar socios: {e}")

                # Consulta completa para exportação (baseada no melhorar_arquivo_consolidado.py)
                # Verificar se tabela 'socios' existe para incluir colunas de sócios
                cursor = self.db.connection.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='socios'")
                has_socios = cursor.fetchone() is not None

                # Build socios select/join: use placeholders when socios table missing to avoid SQL syntax errors
                socios_join = ""
                if has_socios:
                    # Select only the first socio per cnpj_basico (by MIN(rowid)), map qualificacao via qualificacoes
                    # and produce a masked CPF token (preserve masked tokens like '***560201**')
                    # Try to load optional proposals file (non-destructive) into a TEMP table
                    # so we can use proposed qualificacao values as a fallback during export.
                    try:
                        import csv as _csv, io
                        proposals_path = os.path.join('archive', 'socios_reimport_proposals_applied.csv')
                        if not os.path.exists(proposals_path):
                            proposals_path = os.path.join('archive', 'socios_reimport_proposals.csv')

                        cur = self.db.connection.cursor()
                        # Always create a TEMP table (possibly empty) so SQL can safely reference it
                        cur.execute('CREATE TEMP TABLE IF NOT EXISTS proposals_qual (cnpj_basico TEXT PRIMARY KEY, proposed_qual TEXT)')
                        # Ensure it's empty for this session unless the CSV provides rows
                        cur.execute('DELETE FROM proposals_qual')

                        if os.path.exists(proposals_path):
                            try:
                                with open(proposals_path, 'r', encoding='utf-8', errors='ignore') as pf:
                                    # detect delimiter (simple heuristic)
                                    sample = pf.read(8192)
                                    pf.seek(0)
                                    delim = ';' if ';' in sample else (',' if ',' in sample else ';')
                                    reader = _csv.DictReader(pf, delimiter=delim)
                                    rows = []
                                    for r in reader:
                                        # expect column cnpj_basico and proposed_qual (or variants in header)
                                        c = r.get('cnpj_basico') or r.get('cnpj') or r.get('cnpj_basic')
                                        q = r.get('proposed_qual') or r.get('proposed_qualificacao') or r.get('qual') or r.get('proposed')
                                        if c:
                                            rows.append((str(c).strip(), str(q).strip() if q is not None else ''))
                                    if rows:
                                        cur.executemany('INSERT OR REPLACE INTO proposals_qual (cnpj_basico, proposed_qual) VALUES (?,?)', rows)
                                        # do not commit; temp table is session-scoped and will be discarded when connection closes
                            except Exception:
                                # ignore proposals loading errors and proceed without them
                                pass
                    except Exception:
                        pass

                    socios_select = (
                        "COALESCE(socios_agg.nome_socio, '') as nome_socio, "
                        # effective code: prefer socios table value, fallback to proposals
                        "CASE WHEN (socios_agg.nome_socio IS NOT NULL AND TRIM(socios_agg.nome_socio) != '') AND (COALESCE(NULLIF(TRIM(socios_agg.qualificacao_socio),''), NULLIF(TRIM(proposals_qual.proposed_qual),''))) IS NOT NULL "
                        "THEN (COALESCE(NULLIF(TRIM(socios_agg.qualificacao_socio),''), NULLIF(TRIM(proposals_qual.proposed_qual),'')) || "
                        "COALESCE('' || (CASE WHEN q_map.descricao_qualificacao IS NOT NULL AND q_map.descricao_qualificacao != '' THEN ' - ' || q_map.descricao_qualificacao ELSE '' END), '')) "
                        "ELSE '' END as qualificacao_socio, "
                        "CASE WHEN socios_agg.cnpj_cpf_socio IS NULL THEN '' "
                        "WHEN instr(socios_agg.cnpj_cpf_socio, '*') > 0 THEN socios_agg.cnpj_cpf_socio "
                        "WHEN LENGTH(TRIM(socios_agg.cnpj_cpf_socio)) >= 11 THEN '***' || SUBSTR(socios_agg.cnpj_cpf_socio, 4, 6) || '**' "
                        "ELSE socios_agg.cnpj_cpf_socio END as cpf_mid6"
                    )
                    socios_join = (
                        "\n                    LEFT JOIN (\n                        SELECT s.cnpj_basico, s.nome_socio, s.qualificacao_socio, s.cnpj_cpf_socio\n                        FROM socios s\n                        INNER JOIN (SELECT cnpj_basico, COALESCE(MIN(CASE WHEN TRIM(nome_socio) != '' THEN rowid END), MIN(rowid)) as min_rowid FROM socios GROUP BY cnpj_basico) f\n                        ON f.cnpj_basico = s.cnpj_basico AND f.min_rowid = s.rowid\n                    ) as socios_agg ON socios_agg.cnpj_basico = e.cnpj_basico\n                    -- Ensure proposals are linked to the establishment so proposed values are available even when no socios row exists\n                    LEFT JOIN proposals_qual ON proposals_qual.cnpj_basico = e.cnpj_basico\n                    -- Map the effective code (socios.qualificacao_socio or proposals_qual.proposed_qual) to its description once\n                    LEFT JOIN qualificacoes q_map ON q_map.codigo_qualificacao = COALESCE(NULLIF(TRIM(socios_agg.qualificacao_socio),''), NULLIF(TRIM(proposals_qual.proposed_qual),''))"
                    )
                else:
                    # placeholders so CSV columns exist and SQL has no trailing comma
                    socios_select = "'' as nome_socio, '' as qualificacao_socio, '' as cpf_mid6"

                # Prepare bairro + optional socios fragment with deterministic comma placement
                bairro_and_socios = "COALESCE(est.bairro, '') as bairro"
                if socios_select:
                    bairro_and_socios = bairro_and_socios + ", " + socios_select
                sql_export = f"""
                    SELECT DISTINCT
                        CASE WHEN est.cnpj_basico IS NOT NULL AND est.cnpj_ordem IS NOT NULL AND est.cnpj_dv IS NOT NULL
                            THEN SUBSTR(est.cnpj_basico,1,2) || '.' || SUBSTR(est.cnpj_basico,3,3) || '.' || SUBSTR(est.cnpj_basico,6,3) || '/' || est.cnpj_ordem || '-' || est.cnpj_dv
                            ELSE est.cnpj_basico
                        END as cnpj,
                        COALESCE(e.razao_social, '') as razao_social,
                        COALESCE(est.nome_fantasia, '') as nome_fantasia,

                        -- Situação empresa
                        CASE
                            WHEN est.situacao_cadastral = '02' THEN 'ATIVA'
                            WHEN est.situacao_cadastral = '03' THEN 'SUSPENSA'
                            WHEN est.situacao_cadastral = '04' THEN 'INAPTA'
                            WHEN est.situacao_cadastral = '08' THEN 'BAIXADA'
                            ELSE 'NÃO INFORMADO'
                        END as situacao_empresa,

                        -- Data formatada
                        CASE
                            WHEN LENGTH(est.data_situacao_cadastral) = 8 THEN
                                SUBSTR(est.data_situacao_cadastral, 7, 2) || '/' ||
                                SUBSTR(est.data_situacao_cadastral, 5, 2) || '/' ||
                                SUBSTR(est.data_situacao_cadastral, 1, 4)
                            ELSE COALESCE(est.data_situacao_cadastral, '')
                        END as data_situacao,

                        -- motivo_situacao removido para manter compatibilidade com o layout de exportacao anterior

                    -- Endereço completo
                        TRIM(
                            COALESCE(est.tipo_logradouro || ' ', '') ||
                            COALESCE(est.logradouro, '') ||
                            CASE WHEN est.numero IS NOT NULL AND est.numero != ''
                                 THEN ', nº ' || est.numero ELSE '' END ||
                            CASE WHEN est.complemento IS NOT NULL AND est.complemento != ''
                                 THEN ' (' || est.complemento || ')' ELSE '' END
                        ) as endereco_completo,

                        -- CEP formatado
                        CASE
                            WHEN LENGTH(est.cep) >= 8 THEN
                                SUBSTR(est.cep, 1, 5) || '-' || SUBSTR(est.cep, 6, 3)
                            ELSE COALESCE(est.cep, '')
                        END as cep,

                        est.uf,
                        COALESCE(m.nome_municipio, '') as nome_municipio,

                        -- Telefone formatado
                        CASE
                            WHEN est.ddd_1 IS NOT NULL AND est.telefone_1 IS NOT NULL THEN
                                '(' || est.ddd_1 || ') ' ||
                                CASE
                                    WHEN LENGTH(est.telefone_1) = 9 THEN
                                        SUBSTR(est.telefone_1, 1, 5) || '-' || SUBSTR(est.telefone_1, 6, 4)
                                    WHEN LENGTH(est.telefone_1) = 8 THEN
                                        SUBSTR(est.telefone_1, 1, 4) || '-' || SUBSTR(est.telefone_1, 5, 4)
                                    ELSE est.telefone_1
                                END
                            ELSE ''
                        END as telefone_formatado,

                        COALESCE(est.correio_eletronico, '') as email,
                        COALESCE(c.descricao_cnae, '') as descricao_cnae,
                        COALESCE(nat.descricao_natureza, '') as descricao_natureza,
                        -- Bairro (moved to match reference export ordering)
                        COALESCE(est.bairro, '') as bairro,
                    CASE WHEN s.opcao_mei = 'S' THEN 'Microempreendedor Individual (MEI)'
                        WHEN e.porte IN ('49', '50') THEN 'Microempresa (ME)'
                        WHEN e.porte IN ('05', '16', '17', '19') THEN 'Empresa de Pequeno Porte (EPP)'
                        WHEN e.porte IN ('43', '34', '65', '59') THEN 'Empresa de Médio Porte'
                        WHEN e.porte NOT IN ('49', '50', '05', '16', '17', '19', '43', '34', '65', '59')
                            AND e.porte IS NOT NULL AND e.porte != '' THEN 'Grande Empresa'
                             ELSE 'Não Informado' END as porte,

                        -- Capital social corrigido - garantir que apareça
                        CASE
                            WHEN e.capital_social IS NOT NULL AND e.capital_social != '' AND e.capital_social != '0' THEN
                                'R$ ' || REPLACE(
                                    printf("%.2f", CAST(e.capital_social AS REAL) / 100.0),
                                    '.', ','
                                )
                            ELSE 'Não Informado'
                        END as capital_social,

                        CASE WHEN s.opcao_simples = 'S' THEN 'Sim'
                             WHEN s.opcao_simples = 'N' THEN 'Não'
                             ELSE 'N/A' END as opcao_simples,

                        CASE WHEN s.opcao_mei = 'S' THEN 'Sim'
                             WHEN s.opcao_mei = 'N' THEN 'Não'
                             ELSE 'N/A' END as opcao_mei,

                    CASE WHEN est.identificador_matriz_filial = '1' THEN 'Matriz'
                        WHEN est.identificador_matriz_filial = '2' THEN 'Filial'
                        ELSE 'N/A' END as matriz_filial,
                    {socios_select}

                    FROM estabelecimentos_completos est
                    LEFT JOIN empresas_completas e ON est.cnpj_basico = e.cnpj_basico
                    LEFT JOIN simples s ON est.cnpj_basico = s.cnpj_basico
                    LEFT JOIN cnaes c ON est.cnae_fiscal_principal = c.codigo_cnae
                    LEFT JOIN naturezas nat ON e.natureza_juridica = nat.codigo_natureza
                    LEFT JOIN municipios m ON est.municipio = m.codigo_municipio{socios_join}
                    WHERE {where_sql}
                    ORDER BY e.razao_social, est.cnpj_ordem
                """

                # Executar consulta
                cursor = self.db.connection.cursor()
                inicio = time.time()
                # DEBUG: write generated SQL and params to server.err to inspect syntax issues
                try:
                    with open('server.err', 'a', encoding='utf-8') as fh:
                        fh.write('\n--- SQL_EXPORT START ---\n')
                        fh.write(sql_export)
                        fh.write('\n--- SQL_EXPORT PARAMS: %s ---\n' % (str(params),))
                except Exception:
                    pass

                cursor.execute(sql_export, params)

                # Buscar resultados em chunks para economizar memória
                chunk_size = 10000
                dados_csv = []

                # Headers - canonical 22-column layout (CNPJ first, CPF_SOCIO last)
                headers = [
                    'CNPJ', 'RAZAO_SOCIAL', 'NOME_FANTASIA', 'SITUACAO_EMPRESA', 'DATA_SITUACAO',
                    'ENDERECO_COMPLETO', 'CEP', 'UF', 'NOME_MUNICIPIO', 'TELEFONE_FORMATADO',
                    'EMAIL', 'DESCRICAO_CNAE', 'DESCRICAO_NATUREZA', 'BAIRRO', 'PORTE',
                    'CAPITAL_SOCIAL', 'OPCAO_SIMPLES', 'OPCAO_MEI', 'MATRIZ_FILIAL',
                    'NOME_SOCIO', 'QUALIFICACAO_SOCIO', 'CPF_SOCIO'
                ]

                # Processar resultados
                total_registros = 0
                while True:
                    rows = cursor.fetchmany(chunk_size)
                    if not rows:
                        break

                    for row in rows:
                        dados_csv.append(row)
                        total_registros += 1

                tempo = time.time() - inicio
                self.db.disconnect()

                # Criar DataFrame e CSV
                df = pd.DataFrame(dados_csv, columns=headers)

                # Criar arquivo temporário
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"cnpj_exportacao_{timestamp}.csv"

                # Salvar arquivo CSV diretamente - evitando linhas em branco
                df.to_csv(filename, sep=';', index=False, encoding='utf-8-sig',
                         lineterminator='\n', quoting=1)

                # Retornar informações da exportação
                return jsonify({
                    "success": True,
                    "filename": filename,
                    "total_registros": total_registros,
                    "execution_time": round(tempo, 3),
                    "filters_applied": filtros,
                    "download_url": f"/download/{filename}",
                    "timestamp": datetime.now().isoformat()
                })

            except Exception as e:
                # Registrar traceback completo em server.err e no logger do Flask
                tb = traceback.format_exc()
                try:
                    # Imprimir no logger do Flask (gravado em server.err via handler)
                    self.app.logger.error("Exception in /export: %s", tb)
                except Exception:
                    pass
                # Garantir que o arquivo server.err contenha o traceback se o logger falhar
                try:
                    with open('server.err', 'a', encoding='utf-8') as fh:
                        fh.write(f"\n[{datetime.now().isoformat()}] Exception in /export:\n")
                        fh.write(tb)
                        fh.write('\n')
                except Exception:
                    pass
                return jsonify({"error": str(e)}), 500

        @self.app.route('/download/<filename>')
        def download_file(filename):
            """Download do arquivo CSV gerado"""
            try:
                if os.path.exists(filename):
                    return send_file(filename, as_attachment=True, download_name=filename)
                else:
                    return jsonify({"error": "File not found"}), 404
            except Exception as e:
                return jsonify({"error": str(e)}), 500

def create_app(db_path="data/cnpj_database.db"):
    """Factory function para criar a aplicação Flask"""
    cnpj_app = CNPJApp(db_path=db_path)
    return cnpj_app.app

def main():
    """Executa o servidor Flask"""
    print("INICIANDO SERVIDOR FLASK - SISTEMA CNPJ")
    print("=" * 60)
    # Calcular caminho do DB relativo ao diretório raiz do projeto (pai da pasta src)
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    db_path = os.path.join(repo_root, 'data', 'cnpj_database.db')
    if not os.path.exists(db_path):
        print(f"ERROR: Banco de dados não encontrado em {db_path}!")
        print("TIP: Coloque o arquivo data/cnpj_database.db ou execute import_data.py para gerar o DB")
        return

    # Criar aplicação apontando para o DB em data/
    app = create_app(db_path=db_path)

    print("Servidor configurado com sucesso!")
    print("Endpoints disponíveis:")
    print("   http://localhost:5000/          - Página inicial")
    print("   http://localhost:5000/health    - Status do sistema")
    print("   http://localhost:5000/stats     - Estatísticas")
    print("   http://localhost:5000/filters   - Opções de filtros")
    print("   http://localhost:5000/query     - Consultar dados (POST)")
    print("   http://localhost:5000/export    - Exportar CSV (POST)")

    print(f"\nINICIANDO SERVIDOR NA PORTA 5000...")
    print("   Para parar: Ctrl+C")

    # Executar servidor (debug desabilitado para evitar restarts durante operações longas)
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    main()