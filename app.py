from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import sqlite3
import pandas as pd
import io
import time
import os
from datetime import datetime
from database import CNPJDatabase

class CNPJApp:
    """
    Backend Flask para o Sistema de Análise de Dados CNPJ
    Provides APIs for filtering and exporting CNPJ data
    Sistema otimizado com cache e performance melhorada
    """
    
    def __init__(self, db_path="cnpj_database.db"):
        self.app = Flask(__name__)
        CORS(self.app)  # Permitir requisições do frontend
        self.db_path = db_path
        self.cache = {}  # Cache simples para filtros
        self.cache_timeout = 300  # 5 minutos
        self.db = CNPJDatabase(db_path)
        
        # Configurar rotas
        self.setup_routes()
    
    def setup_routes(self):
        """Configura todas as rotas da API"""
        
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
        
        @self.app.route('/health')
        def health_check():
            """Verifica status do sistema"""
            try:
                # Testar conexão com banco
                if self.db.connect():
                    cursor = self.db.connection.cursor()
                    cursor.execute("SELECT COUNT(*) FROM empresas")
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
        def get_stats():
            """Retorna estatísticas do banco de dados"""
            try:
                if not self.db.connect():
                    return jsonify({"error": "Database connection failed"}), 500
                
                cursor = self.db.connection.cursor()
                
                # Estatísticas por tabela
                stats = {}
                tabelas = ['empresas', 'simples', 'cnaes', 'naturezas', 'qualificacoes', 'motivos', 'estabelecimentos', 'socios']
                
                for tabela in tabelas:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
                        count = cursor.fetchone()[0]
                        stats[tabela] = count
                    except Exception as e:
                        stats[tabela] = 0
                
                # Top Naturezas Jurídicas (apenas se temos dados)
                top_naturezas = []
                try:
                    cursor.execute("""
                        SELECT n.descricao_natureza, COUNT(*) as total
                        FROM empresas e
                        LEFT JOIN naturezas n ON e.natureza_juridica = n.codigo_natureza
                        GROUP BY e.natureza_juridica
                        ORDER BY total DESC
                        LIMIT 10
                    """)
                    top_naturezas = [{"natureza": natureza or "N/A", "total": total} for natureza, total in cursor.fetchall()]
                except:
                    top_naturezas = []
                
                # Distribuição Simples Nacional (apenas se temos dados)
                simples_dist = []
                try:
                    cursor.execute("""
                        SELECT 
                            CASE WHEN opcao_simples = 'S' THEN 'Simples Nacional' 
                                 ELSE 'Não Optante' END as tipo,
                            COUNT(*) as total
                        FROM simples
                        GROUP BY opcao_simples
                        ORDER BY total DESC
                    """)
                    simples_dist = [{"tipo": tipo, "total": total} for tipo, total in cursor.fetchall()]
                except:
                    simples_dist = []
                
                self.db.disconnect()
                
                return jsonify({
                    "tabelas": stats,
                    "top_naturezas": top_naturezas,
                    "simples_distribuicao": simples_dist,
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                if self.db.connection:
                    self.db.disconnect()
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/filters')
        def get_filter_options():
            """Retorna opções disponíveis para cada filtro com cache"""
            cache_key = "filter_options"
            current_time = time.time()
            
            # Verificar cache
            if (cache_key in self.cache and 
                current_time - self.cache[cache_key]['timestamp'] < self.cache_timeout):
                print("🚀 Usando cache para filtros")
                return jsonify(self.cache[cache_key]['data'])
            
            print("🔍 Carregando filtros do banco de dados...")
            try:
                if not self.db.connect():
                    return jsonify({"error": "Database connection failed"}), 500
                
                cursor = self.db.connection.cursor()
                
                # Verificar se temos dados de estabelecimentos
                try:
                    cursor.execute("SELECT COUNT(*) FROM estabelecimentos")
                    has_estabelecimentos = cursor.fetchone()[0] > 0
                except:
                    has_estabelecimentos = False
                
                # UFs disponíveis na tabela estabelecimentos
                ufs = []
                try:
                    cursor.execute("""
                        SELECT DISTINCT uf, COUNT(*) as total 
                        FROM estabelecimentos 
                        WHERE uf IS NOT NULL AND uf != '' 
                        GROUP BY uf 
                        ORDER BY uf
                    """)
                    ufs = [{"value": row[0], "label": row[0], "count": row[1]} for row in cursor.fetchall()]
                except:
                    ufs = []
                
                # CNAEs disponíveis
                cnaes = []
                try:
                    cursor.execute("""
                        SELECT c.codigo_cnae, c.descricao_cnae, COUNT(*) as total 
                        FROM cnaes c
                        LEFT JOIN estabelecimentos e ON c.codigo_cnae = e.cnae_principal
                        WHERE c.codigo_cnae IS NOT NULL AND c.codigo_cnae != ''
                        GROUP BY c.codigo_cnae, c.descricao_cnae
                        HAVING total > 0
                        ORDER BY total DESC
                        LIMIT 50
                    """)
                    cnaes = [{"value": codigo, "label": f"{codigo} - {descricao[:50]}...", "count": total} 
                            for codigo, descricao, total in cursor.fetchall()]
                except:
                    # Se não conseguir fazer JOIN, pelo menos mostrar CNAEs cadastrados
                    try:
                        cursor.execute("""
                            SELECT codigo_cnae, descricao_cnae 
                            FROM cnaes 
                            WHERE codigo_cnae IS NOT NULL AND codigo_cnae != ''
                            ORDER BY codigo_cnae
                            LIMIT 50
                        """)
                        cnaes = [{"value": codigo, "label": f"{codigo} - {descricao[:50]}...", "count": 0} 
                                for codigo, descricao in cursor.fetchall()]
                    except:
                        cnaes = []
                
                # Naturezas Jurídicas disponíveis
                naturezas = []
                try:
                    cursor.execute("""
                        SELECT n.codigo_natureza, n.descricao_natureza, COUNT(*) as total 
                        FROM empresas e
                        INNER JOIN naturezas n ON e.natureza_juridica = n.codigo_natureza
                        GROUP BY n.codigo_natureza, n.descricao_natureza
                        ORDER BY total DESC
                        LIMIT 20
                    """)
                    naturezas = [{"value": codigo, "label": f"{codigo} - {descricao[:60]}...", "count": total} 
                               for codigo, descricao, total in cursor.fetchall()]
                except:
                    naturezas = []
                
                # Portes de Empresa disponíveis
                portes = []
                try:
                    cursor.execute("""
                        SELECT 
                            porte,
                            CASE WHEN porte = '01' THEN 'Micro Empresa'
                                 WHEN porte = '03' THEN 'Empresa de Pequeno Porte'
                                 WHEN porte = '05' THEN 'Demais'
                                 ELSE 'Não Informado' END as descricao,
                            COUNT(*) as total
                        FROM empresas
                        WHERE porte IS NOT NULL AND porte != ''
                        GROUP BY porte
                        ORDER BY total DESC
                    """)
                    portes = [{"value": porte, "label": descricao, "count": total} 
                             for porte, descricao, total in cursor.fetchall()]
                except:
                    portes = []
                
                # Status Simples Nacional
                simples_opcoes = []
                try:
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
                except:
                    simples_opcoes = []
                
                self.db.disconnect()
                
                # Preparar dados para retorno e cache
                filter_data = {
                    "ufs": ufs,
                    "cnaes": cnaes,
                    "naturezas": naturezas,
                    "portes": portes,
                    "simples_opcoes": simples_opcoes,
                    "has_estabelecimentos": has_estabelecimentos,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Salvar no cache
                self.cache[cache_key] = {
                    'data': filter_data,
                    'timestamp': current_time
                }
                print(f"✅ Filtros carregados e salvos no cache")
                
                return jsonify(filter_data)
                
            except Exception as e:
                if self.db.connection:
                    self.db.disconnect()
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
                
                # Construir consulta dinâmica
                where_clauses = []
                params = []
                
                if filtros.get('razao_social'):
                    where_clauses.append("UPPER(e.razao_social) LIKE UPPER(?)")
                    params.append(f"%{filtros['razao_social']}%")
                
                if filtros.get('uf'):
                    # Usar JOIN com estabelecimentos para filtrar por UF
                    where_clauses.append("est.uf = ?")
                    params.append(filtros['uf'])
                
                if filtros.get('cnae'):
                    where_clauses.append("est.cnae_principal = ?")
                    params.append(filtros['cnae'])
                
                if filtros.get('natureza_juridica'):
                    where_clauses.append("e.natureza_juridica = ?")
                    params.append(filtros['natureza_juridica'])
                
                if filtros.get('porte'):
                    where_clauses.append("e.porte = ?")
                    params.append(filtros['porte'])
                
                if filtros.get('opcao_simples'):
                    where_clauses.append("s.opcao_simples = ?")
                    params.append(filtros['opcao_simples'])
                
                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
                
                # Sempre usar JOIN completo para todos os filtros funcionarem
                from_clause = """
                    FROM empresas e
                    LEFT JOIN naturezas n ON e.natureza_juridica = n.codigo_natureza
                    LEFT JOIN simples s ON e.cnpj_basico = s.cnpj_basico
                    LEFT JOIN estabelecimentos est ON e.cnpj_basico = est.cnpj_basico
                """
                
                # Contar total
                cursor = self.db.connection.cursor()
                sql_count = f"""
                    SELECT COUNT(DISTINCT e.cnpj_basico) 
                    {from_clause}
                    WHERE {where_sql}
                """
                
                inicio = time.time()
                cursor.execute(sql_count, params)
                total = cursor.fetchone()[0]
                
                # Buscar dados paginados
                offset = (page - 1) * per_page
                
                sql_data = f"""
                    SELECT DISTINCT
                        e.cnpj_basico,
                        e.razao_social,
                        n.descricao_natureza,
                        CASE WHEN e.porte = '01' THEN 'Micro Empresa'
                             WHEN e.porte = '03' THEN 'Empresa de Pequeno Porte'
                             WHEN e.porte = '05' THEN 'Demais'
                             WHEN e.porte = '34' THEN 'Micro Empresa'
                             WHEN e.porte = '50' THEN 'Micro Empresa'
                             ELSE 'Não Informado' END as porte,
                        CASE WHEN s.opcao_simples = 'S' THEN 'Sim' 
                             WHEN s.opcao_simples = 'N' THEN 'Não'
                             ELSE 'N/A' END as simples_nacional,
                        s.data_opcao_simples
                    {from_clause}
                    WHERE {where_sql}
                    ORDER BY e.razao_social
                    LIMIT ? OFFSET ?
                """
                
                cursor.execute(sql_data, params + [per_page, offset])
                resultados = cursor.fetchall()
                tempo = time.time() - inicio
                
                # Formatar resultados
                dados = []
                for row in resultados:
                    dados.append({
                        "cnpj_basico": row[0],
                        "razao_social": row[1],
                        "natureza_juridica": row[2] or "N/A",
                        "porte": row[3] or "N/A", 
                        "simples_nacional": row[4],
                        "data_opcao_simples": row[5] or "N/A"
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
                
                # Construir consulta simples para exportação
                where_clauses = []
                params = []
                
                if filtros.get('razao_social'):
                    where_clauses.append("UPPER(e.razao_social) LIKE UPPER(?)")
                    params.append(f"%{filtros['razao_social']}%")
                
                if filtros.get('uf'):
                    where_clauses.append("est.uf = ?")
                    params.append(filtros['uf'])
                
                if filtros.get('cnae'):
                    where_clauses.append("est.cnae_principal = ?")
                    params.append(filtros['cnae'])
                
                if filtros.get('natureza_juridica'):
                    where_clauses.append("e.natureza_juridica = ?")
                    params.append(filtros['natureza_juridica'])
                
                if filtros.get('porte'):
                    where_clauses.append("e.porte = ?")
                    params.append(filtros['porte'])
                
                if filtros.get('opcao_simples'):
                    where_clauses.append("s.opcao_simples = ?")
                    params.append(filtros['opcao_simples'])
                
                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
                
                # Determinar se precisa do JOIN com estabelecimentos
                needs_estabelecimentos_join = filtros.get('uf') or filtros.get('cnae')
                
                # Consulta COMPLETA para exportação com todos os dados
                if needs_estabelecimentos_join:
                    sql_export = f"""
                        SELECT 
                            substr('00000000' || e.cnpj_basico, -8) || substr('0000' || COALESCE(est.cnpj_ordem, '0001'), -4) || substr('00' || COALESCE(est.cnpj_dv, '00'), -2) as cnpj_completo,
                            e.razao_social,
                            COALESCE(est.nome_fantasia, '') as nome_fantasia,
                            COALESCE(n.descricao_natureza, '') as natureza_juridica,
                            CASE WHEN e.porte = '01' THEN 'Micro Empresa'
                                 WHEN e.porte = '03' THEN 'Empresa de Pequeno Porte'
                                 WHEN e.porte = '05' THEN 'Demais'
                                 ELSE 'Não Informado' END as porte,
                            CASE WHEN s.opcao_simples = 'S' THEN 'Sim' 
                                 WHEN s.opcao_simples = 'N' THEN 'Não'
                                 ELSE 'N/A' END as simples_nacional,
                            COALESCE(s.data_opcao_simples, '') as data_opcao_simples,
                            COALESCE(est.situacao, '') as situacao,
                            COALESCE(est.data_situacao, '') as data_situacao,
                            COALESCE(cnae.descricao_cnae, '') as cnae_principal_desc,
                            COALESCE(est.cnae_principal, '') as cnae_principal,
                            COALESCE(est.tipo_logradouro, '') as tipo_logradouro,
                            COALESCE(est.logradouro, '') as logradouro,
                            COALESCE(est.numero, '') as numero,
                            COALESCE(est.complemento, '') as complemento,
                            COALESCE(est.bairro, '') as bairro,
                            COALESCE(est.cep, '') as cep,
                            COALESCE(est.uf, '') as uf,
                            COALESCE(mun.nome_municipio, '') as municipio,
                            COALESCE(est.ddd1, '') as ddd1,
                            COALESCE(est.telefone1, '') as telefone1,
                            COALESCE(est.ddd2, '') as ddd2,
                            COALESCE(est.telefone2, '') as telefone2,
                            COALESCE(est.email, '') as email,
                            COALESCE(e.capital_social, '') as capital_social,
                            GROUP_CONCAT(COALESCE(soc.nome_socio, '') || CASE WHEN COALESCE(qual.descricao_qualificacao, '') != '' THEN ' (' || qual.descricao_qualificacao || ')' ELSE '' END || CASE WHEN COALESCE(soc.cnpj_cpf_socio, '') != '' THEN ' - ' || soc.cnpj_cpf_socio ELSE '' END, '; ') as socios
                        FROM empresas e
                        LEFT JOIN naturezas n ON e.natureza_juridica = n.codigo_natureza
                        LEFT JOIN simples s ON e.cnpj_basico = s.cnpj_basico
                        LEFT JOIN estabelecimentos est ON e.cnpj_basico = est.cnpj_basico
                        LEFT JOIN cnaes cnae ON est.cnae_principal = cnae.codigo_cnae
                        LEFT JOIN municipios mun ON est.municipio = mun.codigo_municipio
                        LEFT JOIN socios soc ON e.cnpj_basico = soc.cnpj_basico
                        LEFT JOIN qualificacoes qual ON soc.qualificacao_socio = qual.codigo_qualificacao
                        WHERE {where_sql}
                        GROUP BY e.cnpj_basico, est.cnpj_ordem, est.cnpj_dv
                        ORDER BY e.razao_social
                        LIMIT 5000
                    """
                    headers = ['CNPJ_COMPLETO', 'RAZAO_SOCIAL', 'NOME_FANTASIA', 'NATUREZA_JURIDICA', 'PORTE', 
                              'SIMPLES_NACIONAL', 'DATA_OPCAO_SIMPLES', 'SITUACAO', 'DATA_SITUACAO', 
                              'CNAE_PRINCIPAL_DESC', 'CNAE_PRINCIPAL', 'TIPO_LOGRADOURO', 'LOGRADOURO', 'NUMERO', 
                              'COMPLEMENTO', 'BAIRRO', 'CEP', 'UF', 'MUNICIPIO', 'DDD1', 'TELEFONE1', 'DDD2', 
                              'TELEFONE2', 'EMAIL', 'CAPITAL_SOCIAL', 'SOCIOS']
                else:
                    # Consulta sem JOIN - pegar dados da matriz de cada empresa
                    sql_export = f"""
                        SELECT 
                            substr('00000000' || e.cnpj_basico, -8) || substr('0000' || COALESCE(est.cnpj_ordem, '0001'), -4) || substr('00' || COALESCE(est.cnpj_dv, '00'), -2) as cnpj_completo,
                            e.razao_social,
                            COALESCE(est.nome_fantasia, '') as nome_fantasia,
                            COALESCE(n.descricao_natureza, '') as natureza_juridica,
                            CASE WHEN e.porte = '01' THEN 'Micro Empresa'
                                 WHEN e.porte = '03' THEN 'Empresa de Pequeno Porte'
                                 WHEN e.porte = '05' THEN 'Demais'
                                 ELSE 'Não Informado' END as porte,
                            CASE WHEN s.opcao_simples = 'S' THEN 'Sim' 
                                 WHEN s.opcao_simples = 'N' THEN 'Não'
                                 ELSE 'N/A' END as simples_nacional,
                            COALESCE(s.data_opcao_simples, '') as data_opcao_simples,
                            COALESCE(est.situacao, '') as situacao,
                            COALESCE(est.data_situacao, '') as data_situacao,
                            COALESCE(cnae.descricao_cnae, '') as cnae_principal_desc,
                            COALESCE(est.cnae_principal, '') as cnae_principal,
                            COALESCE(est.tipo_logradouro, '') as tipo_logradouro,
                            COALESCE(est.logradouro, '') as logradouro,
                            COALESCE(est.numero, '') as numero,
                            COALESCE(est.complemento, '') as complemento,
                            COALESCE(est.bairro, '') as bairro,
                            COALESCE(est.cep, '') as cep,
                            COALESCE(est.uf, '') as uf,
                            COALESCE(mun.nome_municipio, '') as municipio,
                            COALESCE(est.ddd1, '') as ddd1,
                            COALESCE(est.telefone1, '') as telefone1,
                            COALESCE(est.ddd2, '') as ddd2,
                            COALESCE(est.telefone2, '') as telefone2,
                            COALESCE(est.email, '') as email,
                            COALESCE(e.capital_social, '') as capital_social,
                            GROUP_CONCAT(COALESCE(soc.nome_socio, '') || CASE WHEN COALESCE(qual.descricao_qualificacao, '') != '' THEN ' (' || qual.descricao_qualificacao || ')' ELSE '' END || CASE WHEN COALESCE(soc.cnpj_cpf_socio, '') != '' THEN ' - ' || soc.cnpj_cpf_socio ELSE '' END, '; ') as socios
                        FROM empresas e
                        LEFT JOIN naturezas n ON e.natureza_juridica = n.codigo_natureza
                        LEFT JOIN simples s ON e.cnpj_basico = s.cnpj_basico
                        LEFT JOIN estabelecimentos est ON e.cnpj_basico = est.cnpj_basico AND est.matriz_filial = '1'
                        LEFT JOIN cnaes cnae ON est.cnae_principal = cnae.codigo_cnae
                        LEFT JOIN municipios mun ON est.municipio = mun.codigo_municipio
                        LEFT JOIN socios soc ON e.cnpj_basico = soc.cnpj_basico
                        LEFT JOIN qualificacoes qual ON soc.qualificacao_socio = qual.codigo_qualificacao
                        WHERE {where_sql}
                        GROUP BY e.cnpj_basico, est.cnpj_ordem, est.cnpj_dv
                        ORDER BY e.razao_social
                        LIMIT 5000
                    """
                    headers = ['CNPJ_COMPLETO', 'RAZAO_SOCIAL', 'NOME_FANTASIA', 'NATUREZA_JURIDICA', 'PORTE', 
                              'SIMPLES_NACIONAL', 'DATA_OPCAO_SIMPLES', 'SITUACAO', 'DATA_SITUACAO', 
                              'CNAE_PRINCIPAL_DESC', 'CNAE_PRINCIPAL', 'TIPO_LOGRADOURO', 'LOGRADOURO', 'NUMERO', 
                              'COMPLEMENTO', 'BAIRRO', 'CEP', 'UF', 'MUNICIPIO', 'DDD1', 'TELEFONE1', 'DDD2', 
                              'TELEFONE2', 'EMAIL', 'CAPITAL_SOCIAL', 'SOCIOS']
                
                # Executar consulta
                cursor = self.db.connection.cursor()
                inicio = time.time()
                print(f"🔍 Executando consulta de exportação...")
                cursor.execute(sql_export, params)
                
                # Buscar resultados
                dados_csv = cursor.fetchall()
                tempo = time.time() - inicio
                self.db.disconnect()
                
                print(f"✅ Consulta executada em {tempo:.2f}s - {len(dados_csv)} registros encontrados")
                
                if not dados_csv:
                    return jsonify({
                        "success": False,
                        "error": "Nenhum dado encontrado com os filtros aplicados",
                        "total_registros": 0
                    })
                
                # Criar DataFrame otimizado
                print(f"🔧 Criando DataFrame otimizado com {len(dados_csv)} registros e {len(headers)} colunas")
                print(f"🔧 Headers: {headers}")
                try:
                    # Criar DataFrame e remover registros vazios
                    df = pd.DataFrame(dados_csv, columns=headers)
                    
                    # Otimizações de performance e limpeza
                    df = df.dropna(how='all')  # Remove linhas completamente vazias
                    df = df.drop_duplicates()  # Remove duplicatas
                    
                    print(f"✅ DataFrame otimizado criado: {df.shape} (removidas linhas vazias/duplicadas)")
                except Exception as e:
                    print(f"❌ ERRO ao criar DataFrame: {e}")
                    raise e
                
                # Aplicar formatações específicas aos dados
                print(f"🔧 Aplicando formatações...")
                try:
                    # Formatação do CNPJ completo (com pontos, barras e hífen)
                    if 'CNPJ_COMPLETO' in df.columns:
                        def format_cnpj_completo(x):
                            if pd.isna(x) or str(x).strip() == '' or str(x) == 'None':
                                return ''
                            # Extrair apenas números e garantir 14 dígitos
                            clean = ''.join(filter(str.isdigit, str(x)))
                            if len(clean) >= 8:  # CNPJ básico de 8 dígitos mínimo
                                # Completar com zeros se necessário
                                clean = clean.zfill(14)
                                return f"{clean[:2]}.{clean[2:5]}.{clean[5:8]}/{clean[8:12]}-{clean[12:14]}"
                            return str(x)
                        df['CNPJ_COMPLETO'] = df['CNPJ_COMPLETO'].apply(format_cnpj_completo)
                    
                    # Formatação do CEP (com hífen e remoção de .0)
                    if 'CEP' in df.columns:
                        def format_cep(x):
                            if pd.isna(x) or str(x).strip() == '' or str(x) == 'None':
                                return ''
                            # Remover .0 e extrair apenas números
                            clean_str = str(x).replace('.0', '').replace('.', '')
                            clean = ''.join(filter(str.isdigit, clean_str))
                            if len(clean) == 8:
                                return f"{clean[:5]}-{clean[5:]}"
                            elif len(clean) > 0:
                                return clean
                            return ''
                        df['CEP'] = df['CEP'].apply(format_cep)
                    
                    # Formatação dos telefones (melhorada para remover .0 e aplicar hífen)
                    phone_fields = ['TELEFONE1', 'TELEFONE2']
                    for field in phone_fields:
                        if field in df.columns:
                            def format_phone(x):
                                if pd.isna(x) or str(x).strip() == '' or str(x) == 'None' or str(x) == '0.0' or str(x) == '0':
                                    return ''
                                # Remover .0 e extrair apenas números
                                clean_str = str(x).replace('.0', '').replace('.', '')
                                clean = ''.join(filter(str.isdigit, clean_str))
                                if len(clean) == 8:
                                    return f"{clean[:4]}-{clean[4:]}"
                                elif len(clean) == 9:
                                    return f"{clean[:5]}-{clean[5:]}"
                                elif len(clean) > 0:
                                    return clean
                                return ''
                            df[field] = df[field].apply(format_phone)
                    
                    # Formatação dos DDDs (remover .0)
                    ddd_fields = ['DDD1', 'DDD2']
                    for field in ddd_fields:
                        if field in df.columns:
                            def format_ddd(x):
                                if pd.isna(x) or str(x).strip() == '' or str(x) == 'None' or str(x) == '0.0' or str(x) == '0':
                                    return ''
                                # Remover .0 e extrair apenas números
                                clean_str = str(x).replace('.0', '').replace('.', '')
                                clean = ''.join(filter(str.isdigit, clean_str))
                                return clean if clean else ''
                            df[field] = df[field].apply(format_ddd)
                    
                    # Formatação do capital social (como moeda brasileira)
                    if 'CAPITAL_SOCIAL' in df.columns:
                        def format_capital(x):
                            if pd.isna(x) or str(x).strip() == '' or str(x) == 'None' or str(x) == '0':
                                return 'R$ 0,00'
                            try:
                                # Tentar converter para float
                                clean_value = str(x).replace(',', '.')
                                value = float(clean_value)
                                return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                            except:
                                return str(x)
                        df['CAPITAL_SOCIAL'] = df['CAPITAL_SOCIAL'].apply(format_capital)
                    
                    # Padronização de campos de texto (title case aprimorado)
                    text_fields = ['RAZAO_SOCIAL', 'NOME_FANTASIA', 'TIPO_LOGRADOURO', 'LOGRADOURO', 'BAIRRO', 'MUNICIPIO']
                    for field in text_fields:
                        if field in df.columns:
                            def format_text(x):
                                if pd.isna(x) or str(x).strip() == '' or str(x) == 'None':
                                    return ''
                                # Aplicar title case mas manter algumas palavras em minúsculo
                                text = str(x).strip()
                                if text.isupper() or text.islower():
                                    return text.title()
                                return text
                            df[field] = df[field].apply(format_text)
                    
                    # Formatação de datas (formato brasileiro DD/MM/AAAA)
                    date_fields = ['DATA_OPCAO_SIMPLES', 'DATA_SITUACAO']
                    for field in date_fields:
                        if field in df.columns:
                            def format_date(x):
                                if pd.isna(x) or str(x).strip() == '' or str(x) == 'None':
                                    return ''
                                clean = ''.join(filter(str.isdigit, str(x)))
                                if len(clean) == 8:
                                    return f"{clean[6:8]}/{clean[4:6]}/{clean[:4]}"
                                return str(x)
                            df[field] = df[field].apply(format_date)
                    
                    # Formatação do CNAE (código estruturado)
                    if 'CNAE_PRINCIPAL' in df.columns:
                        def format_cnae(x):
                            if pd.isna(x) or str(x).strip() == '' or str(x) == 'None':
                                return ''
                            clean = ''.join(filter(str.isdigit, str(x)))
                            if len(clean) == 7:
                                return f"{clean[:2]}.{clean[2:4]}-{clean[4]}-{clean[5:7]}"
                            return str(x)
                        df['CNAE_PRINCIPAL'] = df['CNAE_PRINCIPAL'].apply(format_cnae)
                    
                    # Formatação da coluna SOCIOS (limpeza e organização aprimorada)
                    if 'SOCIOS' in df.columns:
                        def format_socios(x):
                            if pd.isna(x) or str(x).strip() == '' or str(x) == 'None':
                                return ''
                            # Limpar formatação problemática
                            text = str(x)
                            # Remover entradas vazias ou mal formatadas
                            text = text.replace(' - ; ', '; ').replace('()', '').replace(' () ', ' ')
                            text = text.replace(' - ', ' - ')
                            # Limpar múltiplos separadores
                            parts = [part.strip() for part in text.split(';') if part.strip() and part.strip() != '-' and part.strip() != '()']
                            return '; '.join(parts) if parts else ''
                        df['SOCIOS'] = df['SOCIOS'].apply(format_socios)
                    
                    print(f"✅ Formatações aplicadas com sucesso")
                    
                except Exception as e:
                    print(f"⚠️ Erro nas formatações (continuando sem formatação): {e}")
                
                # Gerar arquivo CSV otimizado
                print(f"🔧 Gerando arquivo CSV otimizado...")
                try:
                    # Remover linhas vazias e otimizar DataFrame
                    df_clean = df.dropna(how='all')  # Remove linhas completamente vazias
                    df_clean = df_clean.fillna('')   # Substitui NaN por string vazia
                    
                    # Gerar CSV sem linhas vazias
                    output = io.StringIO()
                    df_clean.to_csv(output, sep=';', index=False, encoding='utf-8', 
                                   lineterminator='\n')  # Força terminador de linha único
                    
                    # Limpar linhas vazias adicionais
                    csv_content = output.getvalue()
                    csv_lines = [line for line in csv_content.split('\n') if line.strip()]
                    csv_content = '\n'.join(csv_lines)
                    
                    output = io.StringIO(csv_content)
                    output.seek(0)
                    print(f"✅ CSV otimizado gerado: {len(csv_content)} caracteres, {len(csv_lines)} linhas")
                except Exception as e:
                    print(f"❌ ERRO ao gerar CSV: {e}")
                    raise e
                
                # Criar arquivo temporário
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"cnpj_exportacao_{timestamp}.csv"
                
                # Salvar arquivo temporário
                print(f"🔧 Salvando arquivo: {filename}")
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(output.getvalue())
                    print(f"✅ Arquivo salvo com sucesso: {filename}")
                except Exception as e:
                    print(f"❌ ERRO ao salvar arquivo: {e}")
                    raise e
                
                # Retornar informações da exportação
                return jsonify({
                    "success": True,
                    "filename": filename,
                    "total_registros": len(dados_csv),
                    "execution_time": round(tempo, 3),
                    "filters_applied": filtros,
                    "download_url": f"/download/{filename}",
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                print(f"❌ ERRO na exportação: {str(e)}")
                print(f"❌ Tipo do erro: {type(e).__name__}")
                import traceback
                print(f"❌ Traceback: {traceback.format_exc()}")
                if self.db.connection:
                    self.db.disconnect()
                return jsonify({"error": f"Erro na exportação: {str(e)}"}), 500
        
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
    print("🚀 INICIANDO SERVIDOR FLASK - SISTEMA CNPJ")
    print("=" * 60)
    
    # Verificar se banco existe
    if not os.path.exists("cnpj_database.db"):
        print("❌ Banco de dados não encontrado!")
        print("💡 Execute primeiro: python import_data.py")
        return
    
    # Criar aplicação
    app = create_app()
    
    print("✅ Servidor configurado com sucesso!")
    print("📡 Endpoints disponíveis:")
    print("   http://localhost:5000/          - Página inicial")
    print("   http://localhost:5000/health    - Status do sistema")
    print("   http://localhost:5000/stats     - Estatísticas")
    print("   http://localhost:5000/filters   - Opções de filtros")
    print("   http://localhost:5000/query     - Consultar dados (POST)")
    print("   http://localhost:5000/export    - Exportar CSV (POST)")
    
    print(f"\n🌐 INICIANDO SERVIDOR NA PORTA 5000...")
    print("   Para parar: Ctrl+C")
    
    # Executar servidor
    app.run(host='0.0.0.0', port=5000, debug=True)

if __name__ == "__main__":
    main()