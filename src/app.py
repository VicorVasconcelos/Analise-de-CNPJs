from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import sqlite3
import pandas as pd
import io
import time
import os
import sys
from datetime import datetime
import csv
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
# Optional export blueprint - import if available, but don't fail if not present
try:
    from .export_api import bp as export_bp
except Exception:
    try:
        from src.export_api import bp as export_bp
    except Exception:
        export_bp = None
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
        # Registrar blueprint de export assíncrono se disponível
        try:
            if export_bp is not None:
                self.app.register_blueprint(export_bp)
        except Exception:
            # não bloquear a inicialização caso o blueprint falhe
            pass
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
                # Aceitar tanto o schema "antigo" (view estabelecimentos_completos)
                # quanto o schema importado diretamente (table estabelecimentos).
                cursor.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE (type='table' OR type='view')
                      AND name IN ('estabelecimentos_completos', 'estabelecimentos')
                    ORDER BY CASE WHEN name='estabelecimentos_completos' THEN 0 ELSE 1 END
                    LIMIT 1
                    """
                )
                row = cursor.fetchone()
                if row:
                    source_name = row[0]
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {source_name}")
                        total_empresas = cursor.fetchone()[0]
                    except Exception:
                        total_empresas = None

                    return jsonify({
                        "status": "healthy",
                        "database": "connected",
                        "total_empresas": total_empresas,
                        "data_source": source_name,
                        "db_path": self.db_path,
                        "timestamp": datetime.now().isoformat()
                    }), 200
                return jsonify({
                    "status": "uninitialized",
                    "database": "connected",
                    "message": "Objetos esperados não encontrados (estabelecimentos_completos/estabelecimentos)",
                    "db_path": self.db_path,
                    "timestamp": datetime.now().isoformat()
                }), 200
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "database": "error",
                    "message": str(e),
                    "db_path": self.db_path,
                    "timestamp": datetime.now().isoformat()
                }), 500

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
                has_aggregates_meta = cursor.fetchone() is not None
                if has_aggregates_meta:
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
                has_aggregates_ufs = cursor.fetchone() is not None
                if has_aggregates_ufs:
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
                has_aggregates_naturezas = cursor.fetchone() is not None
                if has_aggregates_naturezas:
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
        @ttl_cache(ttl=1800)  # Cache por 30 minutos (era 5 minutos)
        def get_filter_options():
            """Retorna opções disponíveis para cada filtro"""
            import traceback
            try:
                start_total = time.time()
                print("[INFO] /filters - Iniciando carregamento de filtros...")
                
                if not self.db.connect():
                    print("[ERRO] Falha ao conectar ao banco de dados em /filters")
                    return jsonify({"error": "Database connection failed"}), 500

                cursor = self.db.connection.cursor()

                # Compatibilidade de schema: aceitar views *_completos (legado)
                # e tabelas base (import atual).
                cursor.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE (type='table' OR type='view')
                      AND name IN ('estabelecimentos_completos', 'estabelecimentos')
                    ORDER BY CASE WHEN name='estabelecimentos_completos' THEN 0 ELSE 1 END
                    LIMIT 1
                    """
                )
                est_row = cursor.fetchone()
                est_source = est_row[0] if est_row else None

                cursor.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE (type='table' OR type='view')
                      AND name IN ('empresas_completas', 'empresas')
                    ORDER BY CASE WHEN name='empresas_completas' THEN 0 ELSE 1 END
                    LIMIT 1
                    """
                )
                emp_row = cursor.fetchone()
                emp_source = emp_row[0] if emp_row else None

                # Verificar se temos dados de estabelecimentos (fast check)
                t0 = time.time()
                if est_source:
                    cursor.execute(f"SELECT 1 FROM {est_source} LIMIT 1")
                    has_estabelecimentos = cursor.fetchone() is not None
                else:
                    has_estabelecimentos = False
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
                    # Fallback ultrarrápido: lista fixa de UFs para evitar varredura grande.
                    ufs = [
                        {"value": "AC", "label": "AC", "count": None},
                        {"value": "AL", "label": "AL", "count": None},
                        {"value": "AM", "label": "AM", "count": None},
                        {"value": "AP", "label": "AP", "count": None},
                        {"value": "BA", "label": "BA", "count": None},
                        {"value": "CE", "label": "CE", "count": None},
                        {"value": "DF", "label": "DF", "count": None},
                        {"value": "ES", "label": "ES", "count": None},
                        {"value": "GO", "label": "GO", "count": None},
                        {"value": "MA", "label": "MA", "count": None},
                        {"value": "MG", "label": "MG", "count": None},
                        {"value": "MS", "label": "MS", "count": None},
                        {"value": "MT", "label": "MT", "count": None},
                        {"value": "PA", "label": "PA", "count": None},
                        {"value": "PB", "label": "PB", "count": None},
                        {"value": "PE", "label": "PE", "count": None},
                        {"value": "PI", "label": "PI", "count": None},
                        {"value": "PR", "label": "PR", "count": None},
                        {"value": "RJ", "label": "RJ", "count": None},
                        {"value": "RN", "label": "RN", "count": None},
                        {"value": "RO", "label": "RO", "count": None},
                        {"value": "RR", "label": "RR", "count": None},
                        {"value": "RS", "label": "RS", "count": None},
                        {"value": "SC", "label": "SC", "count": None},
                        {"value": "SE", "label": "SE", "count": None},
                        {"value": "SP", "label": "SP", "count": None},
                        {"value": "TO", "label": "TO", "count": None},
                    ]
                t_ufs = time.time() - t0
                print(f"[TIMING] /filters ufs: {t_ufs:.3f}s, found {len(ufs)} ufs")

                # CNAEs disponíveis - retornar TODOS os CNAEs para o usuário
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='aggregates_cnaes'")
                t0 = time.time()
                if cursor.fetchone():
                    # Aggregates já traz os códigos com contagem; ordenar por código para UX consistente
                    cursor.execute("SELECT codigo_cnae, descricao_cnae, total FROM aggregates_cnaes ORDER BY codigo_cnae ASC")
                    cnaes = [{"value": codigo, "label": f"{codigo} - {(descricao or 'Descrição não disponível')}", "count": total} for codigo, descricao, total in cursor.fetchall()]
                else:
                    # Fallback leve: usar tabela cnaes (lista completa) sem agregação pesada em estabelecimentos
                    cursor.execute("""
                        SELECT codigo_cnae, descricao_cnae
                        FROM cnaes
                        WHERE codigo_cnae IS NOT NULL AND codigo_cnae != ''
                        ORDER BY codigo_cnae ASC
                    """)
                    cnaes = [{"value": codigo, "label": f"{codigo} - {(descricao or 'Descrição não disponível')}", "count": None} for codigo, descricao in cursor.fetchall()]
                t_cnaes = time.time() - t0
                print(f"[TIMING] /filters cnaes: {t_cnaes:.3f}s, found {len(cnaes)} cnaes (all)")

                # Naturezas Jurídicas disponíveis - prefer aggregates if present
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='aggregates_naturezas'")
                if cursor.fetchone():
                    cursor.execute("SELECT codigo_natureza, descricao_natureza, total FROM aggregates_naturezas ORDER BY total DESC LIMIT 50")
                    naturezas_juridicas = [{"value": codigo, "label": (descricao or ''), "count": total}
                               for codigo, descricao, total in cursor.fetchall()]
                else:
                    # Fallback rápido: evita JOIN+GROUP pesado em empresas_completas.
                    # Para o filtro, a lista de naturezas é suficiente mesmo sem contagem exata.
                    cursor.execute("""
                        SELECT codigo_natureza, descricao_natureza
                        FROM naturezas
                        ORDER BY descricao_natureza ASC
                    """)
                    naturezas_juridicas = [{"value": codigo, "label": (descricao or ''), "count": None}
                               for codigo, descricao in cursor.fetchall()]

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
                    # Fallback ultrarrápido: evita múltiplos COUNT(*) full-scan em bases grandes.
                    portes = [
                        {"value": "MEI", "label": "Microempreendedor Individual (MEI)", "count": None},
                        {"value": "MICRO", "label": "Microempresa (ME)", "count": None},
                        {"value": "PEQUENO", "label": "Empresa de Pequeno Porte (EPP)", "count": None},
                        {"value": "MEDIO", "label": "Empresa de Médio Porte", "count": None},
                        {"value": "GRANDE", "label": "Grande Empresa", "count": None},
                    ]

                # Status Simples Nacional - use aggregates_simples if present
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='aggregates_simples'")
                simples_opcoes = []
                if cursor.fetchone():
                    cursor.execute("SELECT opcao, total FROM aggregates_simples ORDER BY total DESC")
                    for opcao, total in cursor.fetchall():
                        descricao = 'Optante pelo Simples' if opcao == 'S' else ('Não Optante' if opcao == 'N' else 'Não Informado')
                        simples_opcoes.append({"value": opcao, "label": descricao, "count": total})
                else:
                    simples_opcoes = [
                        {"value": "S", "label": "Optante pelo Simples", "count": None},
                        {"value": "N", "label": "Não Optante", "count": None},
                    ]

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
                    "municipios": [],
                    "cnaes": cnaes,
                    "naturezas_juridicas": naturezas_juridicas,
                    "portes": portes,
                    "simples_opcoes": simples_opcoes,
                    "situacoes_cadastrais": situacoes_cadastrais,
                    "has_estabelecimentos": has_estabelecimentos,
                    "timestamp": datetime.now().isoformat()
                }

                # Logs adicionais e dump para arquivo para diagnóstico front-end/back-end
                total_time = time.time() - start_total
                try:
                    print(f"[INFO] /filters counts -> ufs={len(ufs)}, cnaes={len(cnaes)}, naturezas={len(naturezas_juridicas)}, portes={len(portes)}, simples={len(simples_opcoes)}, situacoes={len(situacoes_cadastrais)}")
                    print(f"[TIMING] /filters TOTAL: {total_time:.3f}s - Resposta enviada com sucesso")
                    # Dump opcional para diagnóstico (desabilitado por padrão para reduzir I/O).
                    if os.environ.get('CNPJ_DEBUG_FILTERS_DUMP') == '1':
                        with open('last_filters_response.json', 'w', encoding='utf-8') as fh:
                            json.dump(response_obj, fh, ensure_ascii=False, indent=2)
                except Exception as dump_e:
                    print(f"[WARN] falha ao gravar last_filters_response.json: {dump_e}")

                return jsonify(response_obj)

            except Exception as e:
                print("[ERRO] Exceção no handler /filters:")
                traceback.print_exc()
                return jsonify({"error": str(e)}), 500

        @self.app.route('/municipios')
        def get_municipios_by_uf():
            """Retorna municípios da UF selecionada para filtro em cascata."""
            try:
                uf = (request.args.get('uf') or '').strip().upper()
                if not uf:
                    return jsonify({"uf": "", "municipios": [], "timestamp": datetime.now().isoformat()})

                if not self.db.connect():
                    return jsonify({"error": "Database connection failed"}), 500

                cursor = self.db.connection.cursor()

                cursor.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE (type='table' OR type='view')
                      AND name IN ('estabelecimentos_completos', 'estabelecimentos')
                    ORDER BY CASE WHEN name='estabelecimentos_completos' THEN 0 ELSE 1 END
                    LIMIT 1
                    """
                )
                row = cursor.fetchone()
                est_source = row[0] if row else None
                if not est_source:
                    return jsonify({"uf": uf, "municipios": [], "timestamp": datetime.now().isoformat()})

                start = time.time()
                cursor.execute(
                    f"""
                    SELECT
                        d.codigo_municipio as value,
                        COALESCE(NULLIF(TRIM(m.nome_municipio), ''), d.codigo_municipio) as label
                    FROM (
                        SELECT DISTINCT est.municipio as codigo_municipio
                        FROM {est_source} est
                        WHERE est.uf = ?
                          AND est.municipio IS NOT NULL
                          AND TRIM(est.municipio) != ''
                    ) d
                    LEFT JOIN municipios m ON m.codigo_municipio = d.codigo_municipio
                    ORDER BY label ASC
                    """,
                    [uf],
                )

                municipios = [{"value": value, "label": label, "uf": uf} for value, label in cursor.fetchall()]
                elapsed = time.time() - start
                print(f"[TIMING] /municipios uf={uf}: {elapsed:.3f}s, found {len(municipios)} municipios")

                return jsonify({
                    "uf": uf,
                    "municipios": municipios,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
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

                # Buscar todos os resultados quando solicitado pelo frontend.
                fetch_all = filtros.get('fetch_all', False)
                if isinstance(fetch_all, str):
                    fetch_all = fetch_all.strip().lower() in ('1', 'true', 'yes', 'sim', 's')
                else:
                    fetch_all = bool(fetch_all)

                ids_only = filtros.get('ids_only', False)
                if isinstance(ids_only, str):
                    ids_only = ids_only.strip().lower() in ('1', 'true', 'yes', 'sim', 's')
                else:
                    ids_only = bool(ids_only)

                # Normalizar paginação para evitar erros quando o frontend envia strings
                try:
                    page = int(filtros.get('page', 1))
                except (TypeError, ValueError):
                    page = 1
                page = max(page, 1)

                try:
                    per_page_raw = int(filtros.get('per_page', 50))
                except (TypeError, ValueError):
                    per_page_raw = 50
                per_page = max(1, min(per_page_raw, 1000))  # Máximo 1000 por página

                if fetch_all:
                    page = 1

                if not self.db.connect():
                    return jsonify({"error": "Database connection failed"}), 500

                # Construir consulta dinâmica - usando a função centralizada para consistência com /export
                where_clauses, params = build_where_and_params(filtros)
                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

                if fetch_all and not where_clauses:
                    return jsonify({
                        "error": "missing_filters_for_fetch_all",
                        "message": "Para evitar sobrecarga, fetch_all exige ao menos um filtro"
                    }), 400

                # Modo leve para export: retorna somente cnpj_basicos filtrados.
                if ids_only:
                    if not where_clauses:
                        return jsonify({
                            "error": "missing_filters_for_ids_only",
                            "message": "ids_only exige ao menos um filtro"
                        }), 400

                    cursor = self.db.connection.cursor()
                    inicio_ids = time.time()

                    def _make_progress_handler(start, max_seconds):
                        def handler():
                            return 1 if (time.time() - start) > max_seconds else 0
                        return handler

                    try:
                        self.db.connection.set_progress_handler(_make_progress_handler(inicio_ids, 60), 1000)
                        cursor.execute(
                            f"""
                            SELECT DISTINCT est.cnpj_basico
                            FROM estabelecimentos_completos est
                            WHERE {where_sql}
                            LIMIT 100000
                            """,
                            params,
                        )
                    except sqlite3.OperationalError as oe:
                        return jsonify({
                            "error": "ids_only_timeout",
                            "message": "Consulta de IDs excedeu 60s. Tente filtros mais específicos.",
                            "details": str(oe)
                        }), 503
                    finally:
                        try:
                            self.db.connection.set_progress_handler(None, 0)
                        except Exception:
                            pass

                    basicos = [r[0] for r in cursor.fetchall() if r and r[0]]
                    response_obj = {
                        "success": True,
                        "cnpj_basicos": basicos,
                        "total": len(basicos),
                        "execution_time": round(time.time() - inicio_ids, 3)
                    }
                    if len(basicos) >= 100000:
                        response_obj["warning"] = "Resultado limitado a 100.000 CNPJs básicos para exportação."
                    return jsonify(response_obj)

                # helper: progress handler factory (define cedo para estar sempre disponível)
                def _make_progress_handler(start, max_seconds):
                    def handler():
                        return 1 if (time.time() - start) > max_seconds else 0
                    return handler

                # Detectar se podemos usar um caminho rápido (fast path) que evita JOINs pesados.
                # Fast path when filters do NOT reference empresa-level columns or socios/simples
                expensive_keys = {'razao_social', 'natureza_juridica', 'porte', 'opcao_simples', 'socios_present'}
                use_fast_path = not any(k in filtros for k in expensive_keys)

                # Em fetch_all: retornar TODOS os resultados sem limite (para buscas/consultas)
                # Em paginação normal: usar agregates se disponível, senão fazer COUNT rápido.
                cursor = self.db.connection.cursor()
                total = None
                inicio = time.time()
                
                if not fetch_all:
                    # Tentar aggregates para não fazer COUNT em paginação normal
                    if not where_clauses:
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='aggregates_meta'")
                        if cursor.fetchone():
                            cursor.execute("SELECT total_estabelecimentos FROM aggregates_meta LIMIT 1")
                            row = cursor.fetchone()
                            if row:
                                total = row[0]
                    # Se ainda não temos total, fazer COUNT rápido sem JOINs em fast_path
                    if total is None and use_fast_path:
                        # where_sql referencia est.*, então o COUNT também precisa do alias est.
                        sql_count = f"SELECT COUNT(*) FROM estabelecimentos_completos est WHERE {where_sql}"
                        try:
                            cursor.execute(sql_count, params)
                            r = cursor.fetchone()
                            if r:
                                total = r[0]
                        except Exception:
                            total = None

                # Buscar dados paginados - baseado nos dados dos estabelecimentos
                offset = (page - 1) * per_page
                # Em fetch_all: sem LIMIT SQL para retornar tudo, MAS avisar que há limite prático (~100K)
                # para evitar serialização JSON lenta. Para obter > 100K, usar paginação.
                # Em paginação: aplicar LIMIT e OFFSET para browsing
                FETCH_ALL_MAX_FOR_JSON = 100000  # Limite prático para serialização JSON
                if fetch_all:
                    limit_offset_sql = f"LIMIT {FETCH_ALL_MAX_FOR_JSON}"  # Limite de segurança para JSON
                else:
                    limit_offset_sql = "LIMIT ? OFFSET ?"

                if use_fast_path:
                    # Fast path optimizado: sem LEFT JOIN a municipios (muito lento)
                    # Em fetch_all sem ORDER BY: máxima velocidade
                    order_clause_fast = ""
                    if not fetch_all and not where_clauses:
                        order_clause_fast = "ORDER BY est.cnpj_basico"
                    
                    sql_data = f"""
                        SELECT
                            SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 1, 2) || '.' ||
                            SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 3, 3) || '.' ||
                            SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 6, 3) || '/' ||
                            SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 9, 4) || '-' ||
                            SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 13, 2) as cnpj_formatado,
                            '' as razao_social,
                            COALESCE(est.nome_fantasia, 'N/A') as nome_fantasia,
                            CASE WHEN est.situacao_cadastral = '02' THEN 'ATIVA'
                                 WHEN est.situacao_cadastral = '03' THEN 'SUSPENSA'
                                 WHEN est.situacao_cadastral = '04' THEN 'INAPTA'
                                 WHEN est.situacao_cadastral = '08' THEN 'BAIXADA'
                                 ELSE 'NÃO INFORMADO' END as situacao,
                            est.uf,
                            '' as municipio,
                            '' as porte,
                            '' as natureza_juridica
                        FROM estabelecimentos_completos est
                        WHERE {where_sql}
                        {order_clause_fast}
                        {limit_offset_sql}
                    """
                else:
                    # for heavy path, avoid ordering by empresa fields when no filters are applied
                    # Ordenar por chave primária do estabelecimento para reduzir custo de sort.
                    order_clause = 'est.cnpj_basico, est.cnpj_ordem'
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
                        {limit_offset_sql}
                    """

                try:
                    start_data = time.time()
                    # Em fetch_all sem ORDER: 10s timeout. Com ORDER ou paginação: 60s
                    data_timeout = 10 if (fetch_all and not order_clause_fast) else 60
                    self.db.connection.set_progress_handler(_make_progress_handler(start_data, data_timeout), 1000)
                    sql_params = params if fetch_all else (params + [per_page, offset])
                    cursor.execute(sql_data, sql_params)
                except sqlite3.OperationalError as oe:
                    return jsonify({"error": "query_timeout", "message": "Data query timed out after 10s (verifique se filtros estão muito genéricos)", "details": str(oe)}), 503
                finally:
                    try:
                        self.db.connection.set_progress_handler(None, 0)
                    except Exception:
                        pass
                resultados = cursor.fetchall()
                tempo = time.time() - inicio

                # Formatar resultados
                dados = []
                fetch_all_limit_reached = False
                for i, row in enumerate(resultados):
                    if fetch_all and i >= FETCH_ALL_MAX_FOR_JSON:
                        # SQL LIMIT já força isso, mas marcar por segurança
                        fetch_all_limit_reached = True
                        break
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

                # Se fetch_all, usar o total do COUNT; senão, contar os dados retornados
                if fetch_all:
                    # total já tem o valor do COUNT se use_fast_path; senão usar len(dados)
                    if total is None:
                        total = len(dados)
                    per_page = len(dados)
                elif total is None:
                    # Total aproximado para manter paginação funcional quando COUNT expira.
                    total = offset + len(dados)

                response_obj = {
                    "success": True,
                    "data": dados,
                    "pagination": {
                        "page": page,
                        "per_page": per_page,
                        "total": total,
                        "pages": (total + per_page - 1) // per_page if per_page else 1
                    },
                    "query_info": {
                        "filters_applied": len(where_clauses),
                        "execution_time": round(tempo, 3)
                    },
                    "timestamp": datetime.now().isoformat()
                }
                
                # Se fetch_all atingiu limite de 100K, avisar cliente
                if fetch_all and (fetch_all_limit_reached or len(dados) >= FETCH_ALL_MAX_FOR_JSON):
                    response_obj["warning"] = f"Resultado limitado a {FETCH_ALL_MAX_FOR_JSON:,} registros (limite de segurança JSON). Use paginação (page/per_page) para visualizar mais dados."
                
                return jsonify(response_obj)

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route('/export', methods=['POST'])
        def export_data():
            """Exporta dados filtrados em CSV"""
            conn = None
            try:
                payload = request.get_json() or {}
                if isinstance(payload, dict) and isinstance(payload.get('filtros'), dict):
                    filtros = payload.get('filtros') or {}
                else:
                    filtros = payload if isinstance(payload, dict) else {}

                # Usa conexão dedicada para export para evitar contenção com requisições paralelas.
                conn = sqlite3.connect(self.db_path, timeout=60, check_same_thread=False)
                try:
                    conn.execute("PRAGMA journal_mode = WAL")
                    conn.execute("PRAGMA synchronous = NORMAL")
                    conn.execute("PRAGMA temp_store = MEMORY")
                    conn.execute("PRAGMA cache_size = 100000")
                    conn.execute("PRAGMA foreign_keys = OFF")
                except Exception:
                    pass

                # Construir consulta dinâmica (igual ao query) usando helper centralizado
                where_clauses, params = build_where_and_params(filtros)
                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

                # Materializa o subconjunto filtrado para evitar varreduras repetidas da tabela base.
                # Isso reduz contenção e estabiliza o tempo de export no frontend.
                cursor = conn.cursor()
                cursor.execute('DROP TABLE IF EXISTS temp.export_estab')
                cnpj_basicos = payload.get('cnpj_basicos') if isinstance(payload, dict) else None
                if isinstance(cnpj_basicos, list) and len(cnpj_basicos) > 0:
                    cleaned_basicos = []
                    for b in cnpj_basicos:
                        bstr = ''.join(ch for ch in str(b or '') if ch.isdigit())
                        if len(bstr) >= 8:
                            cleaned_basicos.append(bstr[:8])
                    if not cleaned_basicos:
                        return jsonify({
                            "error": "invalid_cnpj_basicos",
                            "message": "Nenhum cnpj_basico válido foi informado para exportação."
                        }), 400

                    cursor.execute('DROP TABLE IF EXISTS temp.export_basicos_input')
                    cursor.execute('CREATE TEMP TABLE export_basicos_input (cnpj_basico TEXT PRIMARY KEY)')
                    cursor.executemany(
                        'INSERT OR IGNORE INTO export_basicos_input (cnpj_basico) VALUES (?)',
                        [(b,) for b in cleaned_basicos[:100000]],
                    )
                    cursor.execute(
                        f"""
                        CREATE TEMP TABLE export_estab AS
                        SELECT est.*
                        FROM estabelecimentos_completos est
                        LEFT JOIN empresas_completas e ON est.cnpj_basico = e.cnpj_basico
                        LEFT JOIN simples s ON est.cnpj_basico = s.cnpj_basico
                        INNER JOIN export_basicos_input bi ON bi.cnpj_basico = est.cnpj_basico
                        WHERE {where_sql}
                        LIMIT 100000
                        """,
                        params,
                    )
                else:
                    cursor.execute(
                        f"""
                        CREATE TEMP TABLE export_estab AS
                        SELECT *
                        FROM estabelecimentos_completos est
                        WHERE {where_sql}
                        LIMIT 100000
                        """,
                        params,
                    )

                # Se tabela de socios não existir, tentar importar arquivos CSV da pasta externa (Socio0)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='socios'")
                if not cursor.fetchone() and os.environ.get('CNPJ_EXPORT_AUTO_IMPORT_SOCIOS', '0') == '1':
                    socio_dir = r"C:\Users\victor.vasconcelos\Documents\PROJETO CNPJ\Socio0"
                    try:
                        if os.path.isdir(socio_dir):
                            # Importar todos os CSVs da pasta para a tabela 'socios' (se possível)
                            for fname in os.listdir(socio_dir):
                                if fname.lower().endswith('.csv'):
                                    fpath = os.path.join(socio_dir, fname)
                                    try:
                                        # Use on_bad_lines for modern pandas to skip malformed rows
                                        df_soc = pd.read_csv(fpath, dtype=str, encoding='utf-8', on_bad_lines='skip')
                                    except Exception:
                                        # tentar leitura com latin-1 como fallback (engine python)
                                        df_soc = pd.read_csv(fpath, dtype=str, encoding='latin-1', engine='python', on_bad_lines='skip')

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
                                        df_soc[['cnpj_basico', 'nome_socio', 'cnpj_cpf_socio', 'qualificacao_socio']].to_sql('socios', conn, if_exists='append', index=False)
                                        print(f"[INFO] importado socios de {fpath} para tabela 'socios'")
                                    except Exception as e:
                                        print(f"[WARN] falha ao importar socios de {fpath}: {e}")
                    except Exception as e:
                        print(f"[WARN] falha ao verificar/importar socios: {e}")

                # Consulta completa para exportação (baseada no melhorar_arquivo_consolidado.py)
                # Verificar se tabela 'socios' existe para incluir colunas de sócios
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='socios'")
                has_socios = cursor.fetchone() is not None

                # Requisito funcional: exportação não deve seguir sem base de sócios disponível.
                if not has_socios:
                    return jsonify({
                        "error": "socios_required",
                        "message": "A exportação exige os campos de sócio. Tabela 'socios' não encontrada."
                    }), 503

                cursor.execute("SELECT 1 FROM socios LIMIT 1")
                if cursor.fetchone() is None:
                    return jsonify({
                        "error": "socios_required",
                        "message": "A exportação exige os campos de sócio. A tabela 'socios' está vazia."
                    }), 503

                # Build socios select/join
                socios_join = ""
                if has_socios:
                    # Índice essencial para acelerar agrupamento/join por cnpj_basico durante export.
                    try:
                        cur = conn.cursor()
                        cur.execute("CREATE INDEX IF NOT EXISTS idx_socios_cnpj_basico ON socios(cnpj_basico)")
                    except Exception:
                        pass

                    # Basicos somente do subconjunto de export já filtrado.
                    cur = conn.cursor()
                    cur.execute('DROP TABLE IF EXISTS temp.export_basicos')
                    cur.execute('CREATE TEMP TABLE export_basicos (cnpj_basico TEXT PRIMARY KEY)')
                    cur.execute(
                        """
                        INSERT OR IGNORE INTO export_basicos (cnpj_basico)
                        SELECT cnpj_basico
                        FROM export_estab
                        WHERE cnpj_basico IS NOT NULL AND TRIM(cnpj_basico) != ''
                        """
                    )

                    socios_select = (
                        "COALESCE(NULLIF(TRIM(socios_agg.nome_socio), ''), 'Não Informado') as nome_socio, "
                        "CASE WHEN NULLIF(TRIM(socios_agg.qualificacao_socio),'') IS NOT NULL "
                        "THEN (NULLIF(TRIM(socios_agg.qualificacao_socio),'') || "
                        "COALESCE('' || (CASE WHEN q_map.descricao_qualificacao IS NOT NULL AND q_map.descricao_qualificacao != '' THEN ' - ' || q_map.descricao_qualificacao ELSE '' END), '')) "
                        "ELSE 'Não Informado' END as qualificacao_socio, "
                        "CASE WHEN socios_agg.cpf_socio IS NULL OR TRIM(socios_agg.cpf_socio) = '' THEN 'Não Informado' "
                        "WHEN instr(socios_agg.cpf_socio, '*') > 0 THEN socios_agg.cpf_socio "
                        "WHEN LENGTH(TRIM(socios_agg.cpf_socio)) >= 11 THEN '***' || SUBSTR(socios_agg.cpf_socio, 4, 6) || '**' "
                        "ELSE socios_agg.cpf_socio END as cpf_socio"
                    )
                    socios_join = (
                        "\n                    LEFT JOIN (\n                        SELECT soc.cnpj_basico, soc.nome_socio, soc.qualificacao_socio, soc.cpf_cnpj_socio as cpf_socio\n                        FROM socios soc\n                        INNER JOIN (\n                            SELECT s2.cnpj_basico,\n                                   COALESCE(MIN(CASE WHEN TRIM(COALESCE(s2.nome_socio,'')) != '' THEN s2.rowid END), MIN(s2.rowid)) as min_rowid\n                            FROM socios s2\n                            INNER JOIN export_basicos eb ON eb.cnpj_basico = s2.cnpj_basico\n                            GROUP BY s2.cnpj_basico\n                        ) f\n                        ON f.cnpj_basico = soc.cnpj_basico AND f.min_rowid = soc.rowid\n                    ) as socios_agg ON socios_agg.cnpj_basico = est.cnpj_basico\n                    LEFT JOIN qualificacoes q_map ON q_map.codigo_qualificacao = NULLIF(TRIM(socios_agg.qualificacao_socio),'')"
                    )


                # Prepare bairro + optional socios fragment with deterministic comma placement
                bairro_and_socios = "COALESCE(est.bairro, '') as bairro"
                if socios_select:
                    bairro_and_socios = bairro_and_socios + ", " + socios_select
                sql_export = f"""
                    SELECT
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

                    FROM export_estab est
                    LEFT JOIN empresas_completas e ON est.cnpj_basico = e.cnpj_basico
                    LEFT JOIN simples s ON est.cnpj_basico = s.cnpj_basico
                    LEFT JOIN cnaes c ON est.cnae_fiscal_principal = c.codigo_cnae
                    LEFT JOIN naturezas nat ON e.natureza_juridica = nat.codigo_natureza
                    LEFT JOIN municipios m ON est.municipio = m.codigo_municipio{socios_join}
                """

                # Executar consulta
                cursor = conn.cursor()
                inicio = time.time()
                # DEBUG opcional de SQL (desabilitado por padrão para evitar I/O extra)
                if os.environ.get('CNPJ_EXPORT_DEBUG_SQL') == '1':
                    try:
                        with open('server.err', 'a', encoding='utf-8') as fh:
                            fh.write('\n--- SQL_EXPORT START ---\n')
                            fh.write(sql_export)
                            fh.write('\n--- SQL_EXPORT PARAMS: %s ---\n' % (str(params),))
                    except Exception:
                        pass

                # Evitar travamento indefinido em queries pesadas de export.
                export_timeout = int(os.environ.get('CNPJ_EXPORT_SQL_TIMEOUT', '120'))
                def _export_progress_handler():
                    return 1 if (time.time() - inicio) > export_timeout else 0

                try:
                    conn.set_progress_handler(_export_progress_handler, 1000)
                    cursor.execute(sql_export)
                except sqlite3.OperationalError as oe:
                    try:
                        conn.set_progress_handler(None, 0)
                    except Exception:
                        pass
                    return jsonify({
                        "error": "export_timeout",
                        "message": f"Export query excedeu {export_timeout}s. Aplique filtros mais específicos.",
                        "details": str(oe)
                    }), 503
                finally:
                    try:
                        conn.set_progress_handler(None, 0)
                    except Exception:
                        pass

                # Headers - canonical 22-column layout (CNPJ first, CPF_SOCIO last)
                headers = [
                    'CNPJ', 'RAZAO_SOCIAL', 'NOME_FANTASIA', 'SITUACAO_EMPRESA', 'DATA_SITUACAO',
                    'ENDERECO_COMPLETO', 'CEP', 'UF', 'NOME_MUNICIPIO', 'TELEFONE_FORMATADO',
                    'EMAIL', 'DESCRICAO_CNAE', 'DESCRICAO_NATUREZA', 'BAIRRO', 'PORTE',
                    'CAPITAL_SOCIAL', 'OPCAO_SIMPLES', 'OPCAO_MEI', 'MATRIZ_FILIAL',
                    'NOME_SOCIO', 'QUALIFICACAO_SOCIO', 'CPF_SOCIO'
                ]

                # Criar arquivo temporário
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"cnpj_exportacao_{timestamp}.csv"

                # Escrever CSV em streaming (mais rápido e com menor uso de memória)
                chunk_size = 10000
                total_registros = 0
                with open(filename, 'w', newline='', encoding='utf-8-sig') as fh:
                    writer = csv.writer(fh, delimiter=';', quoting=csv.QUOTE_ALL, lineterminator='\n')
                    writer.writerow(headers)
                    while True:
                        rows = cursor.fetchmany(chunk_size)
                        if not rows:
                            break
                        writer.writerows(rows)
                        total_registros += len(rows)

                tempo = time.time() - inicio

                # Retornar informações da exportação
                response_data = {
                    "success": True,
                    "filename": filename,
                    "total_registros": total_registros,
                    "execution_time": round(tempo, 3),
                    "filters_applied": filtros,
                    "download_url": f"/download/{filename}",
                    "timestamp": datetime.now().isoformat()
                }
                
                # Se atingiu limite de 100K, avisar cliente
                if total_registros >= 100000:
                    response_data["warning"] = "Exportação limitada a 100.000 registros. Aplique filtros mais específicos para obter resultados menores."
                
                return jsonify(response_data)

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
            finally:
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass

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