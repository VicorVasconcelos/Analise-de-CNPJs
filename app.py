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
                tabelas = ['empresas', 'simples', 'cnaes', 'naturezas', 'qualificacoes', 'motivos']
                
                for tabela in tabelas:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
                        count = cursor.fetchone()[0]
                        stats[tabela] = count
                    except:
                        stats[tabela] = 0
                
                # Top Naturezas Jurídicas
                cursor.execute("""
                    SELECT n.descricao_natureza, COUNT(*) as total
                    FROM empresas e
                    LEFT JOIN naturezas n ON e.natureza_juridica = n.codigo_natureza
                    GROUP BY e.natureza_juridica
                    ORDER BY total DESC
                    LIMIT 10
                """)
                top_naturezas = [{"natureza": natureza or "N/A", "total": total} for natureza, total in cursor.fetchall()]
                
                # Distribuição Simples Nacional
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
                
                self.db.disconnect()
                
                return jsonify({
                    "tabelas": stats,
                    "top_naturezas": top_naturezas,
                    "simples_distribuicao": simples_dist,
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/filters')
        def get_filter_options():
            """Retorna opções disponíveis para cada filtro"""
            try:
                if not self.db.connect():
                    return jsonify({"error": "Database connection failed"}), 500
                
                cursor = self.db.connection.cursor()
                
                # Verificar se temos dados de estabelecimentos
                cursor.execute("SELECT COUNT(*) FROM estabelecimentos")
                has_estabelecimentos = cursor.fetchone()[0] > 0
                
                # UFs disponíveis na tabela estabelecimentos
                cursor.execute("""
                    SELECT DISTINCT uf, COUNT(*) as total 
                    FROM estabelecimentos 
                    WHERE uf IS NOT NULL AND uf != '' 
                    GROUP BY uf 
                    ORDER BY uf
                """)
                ufs = [{"value": row[0], "label": row[0], "count": row[1]} for row in cursor.fetchall()]
                
                # CNAEs disponíveis (temporariamente desabilitado - dados não disponíveis)
                cnaes = []
                
                # Naturezas Jurídicas disponíveis
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
                
                # Portes de Empresa disponíveis
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
                
                # Status Simples Nacional
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
                
                self.db.disconnect()
                
                return jsonify({
                    "ufs": ufs,
                    "cnaes": cnaes,
                    "naturezas": naturezas,
                    "portes": portes,
                    "simples_opcoes": simples_opcoes,
                    "has_estabelecimentos": has_estabelecimentos,
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
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
                needs_estabelecimentos_join = filtros.get('uf')
                
                # Definir FROM clause baseado nos filtros
                if needs_estabelecimentos_join:
                    from_clause = """
                        FROM empresas e
                        LEFT JOIN naturezas n ON e.natureza_juridica = n.codigo_natureza
                        LEFT JOIN simples s ON e.cnpj_basico = s.cnpj_basico
                        LEFT JOIN estabelecimentos est ON e.cnpj_basico = est.cnpj_basico
                    """
                else:
                    from_clause = """
                        FROM empresas e
                        LEFT JOIN naturezas n ON e.natureza_juridica = n.codigo_natureza
                        LEFT JOIN simples s ON e.cnpj_basico = s.cnpj_basico
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
                
                # Construir consulta dinâmica (igual ao query)
                where_clauses = []
                params = []
                
                if filtros.get('uf'):
                    where_clauses.append("est.uf = ?")
                    params.append(filtros['uf'])
                
                if filtros.get('cnae'):
                    where_clauses.append("est.cnae_fiscal_principal = ?")
                    params.append(filtros['cnae'])
                
                if filtros.get('municipio'):
                    where_clauses.append("est.municipio = ?")
                    params.append(filtros['municipio'])
                
                if filtros.get('bairro'):
                    where_clauses.append("UPPER(est.bairro) LIKE UPPER(?)")
                    params.append(f"%{filtros['bairro']}%")
                
                if filtros.get('matriz_filial'):
                    where_clauses.append("est.identificador_matriz_filial = ?")
                    params.append(filtros['matriz_filial'])
                
                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
                
                # Consulta completa para exportação (baseada no melhorar_arquivo_consolidado.py)
                sql_export = f"""
                    SELECT DISTINCT
                        -- CNPJ formatado
                        SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 1, 2) || '.' ||
                        SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 3, 3) || '.' ||
                        SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 6, 3) || '/' ||
                        SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 9, 4) || '-' ||
                        SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 13, 2) as cnpj_formatado,
                        
                        (est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv) as cnpj_completo,
                        est.cnpj_basico,
                        COALESCE(emp.razao_social, '') as razao_social,
                        COALESCE(est.nome_fantasia, '') as nome_fantasia,
                        COALESCE(nat.descricao_natureza, '') as descricao_natureza,
                        COALESCE(emp.porte, '') as porte,
                        COALESCE(emp.capital_social, '') as capital_social,
                        COALESCE(c.descricao_cnae, '') as descricao_cnae,
                        
                        -- Situação empresa
                        CASE 
                            WHEN est.situacao_cadastral = '02' THEN 'ATIVA'
                            WHEN est.situacao_cadastral = '03' THEN 'SUSPENSA'
                            WHEN est.situacao_cadastral = '04' THEN 'INAPTA'
                            WHEN est.situacao_cadastral = '08' THEN 'BAIXADA'
                            ELSE 'NÃO INFORMADO'
                        END as situacao_empresa,
                        
                        COALESCE(est.motivo_situacao_cadastral, '') as descricao_motivo,
                        
                        -- Data formatada
                        CASE 
                            WHEN LENGTH(est.data_situacao_cadastral) = 8 THEN
                                SUBSTR(est.data_situacao_cadastral, 7, 2) || '/' ||
                                SUBSTR(est.data_situacao_cadastral, 5, 2) || '/' ||
                                SUBSTR(est.data_situacao_cadastral, 1, 4)
                            ELSE COALESCE(est.data_situacao_cadastral, '')
                        END as data_situacao,
                        
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
                        COALESCE(s.opcao_simples, 'N') as opcao_simples,
                        COALESCE(s.opcao_mei, 'N') as opcao_mei,
                        est.identificador_matriz_filial as matriz_filial
                    FROM estabelecimentos est
                    LEFT JOIN empresas emp ON est.cnpj_basico = emp.cnpj_basico
                    LEFT JOIN simples s ON est.cnpj_basico = s.cnpj_basico
                    LEFT JOIN cnaes c ON est.cnae_fiscal_principal = c.codigo_cnae
                    LEFT JOIN naturezas nat ON emp.natureza_juridica = nat.codigo_natureza
                    LEFT JOIN municipios m ON est.municipio = m.codigo_municipio
                    WHERE {where_sql}
                    ORDER BY est.cnpj_basico, est.cnpj_ordem
                """
                
                # Executar consulta
                cursor = self.db.connection.cursor()
                inicio = time.time()
                cursor.execute(sql_export, params)
                
                # Buscar resultados em chunks para economizar memória
                chunk_size = 10000
                dados_csv = []
                
                # Headers
                headers = [
                    'CNPJ_FORMATADO', 'CNPJ_COMPLETO', 'CNPJ_BASICO', 'RAZAO_SOCIAL', 
                    'NOME_FANTASIA', 'DESCRICAO_NATUREZA', 'PORTE', 'CAPITAL_SOCIAL',
                    'DESCRICAO_CNAE', 'SITUACAO_EMPRESA', 'DESCRICAO_MOTIVO', 'DATA_SITUACAO',
                    'ENDERECO_COMPLETO', 'CEP', 'UF', 'NOME_MUNICIPIO', 'TELEFONE_FORMATADO',
                    'EMAIL', 'OPCAO_SIMPLES', 'OPCAO_MEI', 'MATRIZ_FILIAL'
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
                
                # Gerar arquivo CSV
                output = io.StringIO()
                df.to_csv(output, sep=';', index=False, encoding='utf-8')
                output.seek(0)
                
                # Criar arquivo temporário
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"cnpj_exportacao_{timestamp}.csv"
                
                # Salvar arquivo temporário
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(output.getvalue())
                
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