from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import sqlite3
import pandas as pd
import io
import time
import os
from datetime import datetime
from database import CNPJDatabase
import threading
from functools import wraps
import json

class CNPJApp:
    """
    Backend Flask para o Sistema de Análise de Dados CNPJ
    Provides APIs for filtering and exporting CNPJ data
    """
    
    def __init__(self, db_path="cnpj_database.db"):
        self.app = Flask(__name__)
        CORS(self.app)  # Permitir requisições do frontend
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
                porte_filtro = filtros['porte']
                if porte_filtro == 'MEI':
                    where_clauses.append("s.opcao_mei = 'S'")
                elif porte_filtro == 'MICRO':
                    where_clauses.append("e.porte IN ('49', '50')")
                elif porte_filtro == 'PEQUENO':
                    where_clauses.append("e.porte IN ('05', '16', '17', '19')")
                elif porte_filtro == 'MEDIO':
                    where_clauses.append("e.porte IN ('43', '34', '65', '59')")
                elif porte_filtro == 'GRANDE':
                    where_clauses.append("e.porte NOT IN ('49', '50', '05', '16', '17', '19', '43', '34', '65', '59') AND e.porte IS NOT NULL AND e.porte != ''")

            if filtros.get('situacao_cadastral'):
                where_clauses.append("est.situacao_cadastral = ?")
                params.append(filtros['situacao_cadastral'])

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
            """Servir a interface web do sistema"""
            try:
                with open('index.html', 'r', encoding='utf-8') as f:
                    return f.read()
            except FileNotFoundError:
                return jsonify({
                    "message": "🚀 API Sistema CNPJ - Dados Abertos da Receita Federal",
                    "version": "1.0.0",
                    "error": "Interface web (index.html) não encontrada",
                    "endpoints": {
                        "GET /api": "Informações da API",
                        "GET /health": "Status do sistema",
                        "GET /stats": "Estatísticas do banco de dados",
                        "GET /filters": "Opções disponíveis para filtros",
                        "POST /query": "Consultar dados com filtros",
                        "POST /export": "Exportar dados filtrados em CSV"
                    },
                    "timestamp": datetime.now().isoformat()
                })
        
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
        
        @self.app.route('/styles.css')
        def serve_css():
            """Servir o arquivo CSS"""
            try:
                with open('styles.css', 'r', encoding='utf-8') as f:
                    content = f.read()
                response = self.app.response_class(
                    content,
                    mimetype='text/css'
                )
                return response
            except FileNotFoundError:
                return "/* CSS file not found */", 404
        
        @self.app.route('/script.js')
        def serve_js():
            """Servir o arquivo JavaScript"""
            try:
                with open('script.js', 'r', encoding='utf-8') as f:
                    content = f.read()
                response = self.app.response_class(
                    content,
                    mimetype='application/javascript'
                )
                return response
            except FileNotFoundError:
                return "/* JavaScript file not found */", 404

        @self.app.route('/script-react.js')
        def serve_js_react():
            """Servir o arquivo JavaScript da versão React (script-react.js)"""
            try:
                with open('script-react.js', 'r', encoding='utf-8') as f:
                    content = f.read()
                response = self.app.response_class(
                    content,
                    mimetype='application/javascript'
                )
                return response
            except FileNotFoundError:
                return "/* React JavaScript file not found */", 404
        
        @self.app.route('/health')
        def health_check():
            """Verifica status do sistema"""
            try:
                # Testar conexão com banco
                if self.db.connect():
                    cursor = self.db.connection.cursor()
                    cursor.execute("SELECT COUNT(*) FROM empresas_completas")
                    total_empresas = cursor.fetchone()[0]
                    self.db.disconnect()
                    
                    return jsonify({
                        "status": "healthy",
                        "database": "connected",
                        "total_empresas": total_empresas,
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    return jsonify({
                        "status": "unhealthy",
                        "database": "disconnected",
                        "error": "Cannot connect to database"
                    }), 500
                    
            except Exception as e:
                return jsonify({
                    "status": "unhealthy",
                    "database": "error",
                    "error": str(e)
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
                filtros = request.get_json() or {}
                page = filtros.get('page', 1)
                per_page = min(filtros.get('per_page', 50), 1000)  # Máximo 1000 por página

                if not self.db.connect():
                    return jsonify({"error": "Database connection failed"}), 500

                # Construir consulta dinâmica - usando a função centralizada para consistência com /export
                where_clauses, params = build_where_and_params(filtros)
                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

                # Contar total - baseado nos dados dos estabelecimentos
                cursor = self.db.connection.cursor()
                sql_count = f"""
                    SELECT COUNT(*) 
                    FROM estabelecimentos_completos est
                    LEFT JOIN empresas_completas e ON est.cnpj_basico = e.cnpj_basico
                    LEFT JOIN simples s ON est.cnpj_basico = s.cnpj_basico
                    WHERE {where_sql}
                """

                inicio = time.time()
                cursor.execute(sql_count, params)
                total = cursor.fetchone()[0]

                # Buscar dados paginados - baseado nos dados dos estabelecimentos
                offset = (page - 1) * per_page

                sql_data = f"""
                    SELECT 
                        -- CNPJ formatado
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
                    ORDER BY e.razao_social, est.cnpj_ordem
                    LIMIT ? OFFSET ?
                """

                cursor.execute(sql_data, params + [per_page, offset])
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
                
                # Consulta completa para exportação (baseada no melhorar_arquivo_consolidado.py)
                sql_export = f"""
                    SELECT DISTINCT
                        -- CNPJ formatado (renomeado para apenas CNPJ)
                        SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 1, 2) || '.' ||
                        SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 3, 3) || '.' ||
                        SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 6, 3) || '/' ||
                        SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 9, 4) || '-' ||
                        SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 13, 2) as cnpj,
                        
                        COALESCE(emp.razao_social, '') as razao_social,
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
                        
                        COALESCE(est.motivo_situacao_cadastral, '') as descricao_motivo,
                        
                        -- Endereço completo
                        TRIM(
                            COALESCE(est.tipo_logradouro || ' ', '') ||
                            COALESCE(est.logradouro, '') ||
                            CASE WHEN est.numero IS NOT NULL AND est.numero != '' 
                                 THEN ', nº ' || est.numero ELSE '' END ||
                            CASE WHEN est.complemento IS NOT NULL AND est.complemento != '' 
                                 THEN ' (' || est.complemento || ')' ELSE '' END ||
                            CASE WHEN est.bairro IS NOT NULL AND est.bairro != '' 
                                 THEN ' - ' || est.bairro ELSE '' END
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
                        
                        CASE WHEN s.opcao_mei = 'S' THEN 'Microempreendedor Individual (MEI)'
                             WHEN emp.porte IN ('49', '50') THEN 'Microempresa (ME)'
                             WHEN emp.porte IN ('05', '16', '17', '19') THEN 'Empresa de Pequeno Porte (EPP)'
                             WHEN emp.porte IN ('43', '34', '65', '59') THEN 'Empresa de Médio Porte'
                             WHEN emp.porte NOT IN ('49', '50', '05', '16', '17', '19', '43', '34', '65', '59') 
                                  AND emp.porte IS NOT NULL AND emp.porte != '' THEN 'Grande Empresa'
                             ELSE 'Não Informado' END as porte,
                        
                        -- Capital social corrigido - garantir que apareça
                        CASE 
                            WHEN emp.capital_social IS NOT NULL AND emp.capital_social != '' AND emp.capital_social != '0' THEN
                                'R$ ' || REPLACE(
                                    printf("%.2f", CAST(emp.capital_social AS REAL) / 100.0),
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
                             ELSE 'N/A' END as matriz_filial
                             
                    FROM estabelecimentos_completos est
                    LEFT JOIN empresas_completas emp ON est.cnpj_basico = emp.cnpj_basico
                    LEFT JOIN simples s ON est.cnpj_basico = s.cnpj_basico
                    LEFT JOIN cnaes c ON est.cnae_fiscal_principal = c.codigo_cnae
                    LEFT JOIN naturezas nat ON emp.natureza_juridica = nat.codigo_natureza
                    LEFT JOIN municipios m ON est.municipio = m.codigo_municipio
                    WHERE {where_sql}
                    ORDER BY emp.razao_social, est.cnpj_ordem
                """
                
                # Executar consulta
                cursor = self.db.connection.cursor()
                inicio = time.time()
                cursor.execute(sql_export, params)
                
                # Buscar resultados em chunks para economizar memória
                chunk_size = 10000
                dados_csv = []
                
                # Headers - SEM CNPJ_BASICO e CNPJ_COMPLETO, CNPJ_FORMATADO renomeado para CNPJ
                headers = [
                    'CNPJ', 'RAZAO_SOCIAL', 'NOME_FANTASIA', 
                    'SITUACAO_EMPRESA', 'DATA_SITUACAO', 'DESCRICAO_MOTIVO',
                    'ENDERECO_COMPLETO', 'CEP', 'UF', 'NOME_MUNICIPIO', 
                    'TELEFONE_FORMATADO', 'EMAIL', 
                    'DESCRICAO_CNAE', 'DESCRICAO_NATUREZA', 'PORTE', 'CAPITAL_SOCIAL',
                    'OPCAO_SIMPLES', 'OPCAO_MEI', 'MATRIZ_FILIAL'
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

def create_app():
    """Factory function para criar a aplicação Flask"""
    cnpj_app = CNPJApp()
    return cnpj_app.app

def main():
    """Executa o servidor Flask"""
    print("INICIANDO SERVIDOR FLASK - SISTEMA CNPJ")
    print("=" * 60)
    
    # Verificar se banco existe
    if not os.path.exists("cnpj_database.db"):
        print("❌ Banco de dados não encontrado!")
        print("💡 Execute primeiro: python import_data.py")
        return
    
    # Criar aplicação
    app = create_app()
    
    print("Servidor configurado com sucesso!")
    print("📡 Endpoints disponíveis:")
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