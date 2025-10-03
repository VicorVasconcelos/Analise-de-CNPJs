import sqlite3
import time
from database import CNPJDatabase

class CNPJQueryTester:
    """
    Classe para testar consultas filtradas no banco CNPJ
    Simula os filtros que serão usados na interface web
    """
    
    def __init__(self, db_path="cnpj_database.db"):
        self.db_path = db_path
        self.db = CNPJDatabase(db_path)
    
    def verificar_dados_disponiveis(self):
        """Verifica quais dados estão disponíveis no banco"""
        print("📊 VERIFICANDO DADOS DISPONÍVEIS NO BANCO")
        print("=" * 60)
        
        if not self.db.connect():
            print("❌ Erro ao conectar com banco")
            return False
        
        cursor = self.db.connection.cursor()
        
        # Verificar cada tabela
        tabelas = ['empresas', 'estabelecimentos', 'simples', 'cnaes', 'municipios', 'naturezas', 'motivos']
        
        dados_disponiveis = {}
        
        for tabela in tabelas:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
                count = cursor.fetchone()[0]
                dados_disponiveis[tabela] = count
                
                if count > 0:
                    print(f"   ✅ {tabela:<20}: {count:,} registros")
                else:
                    print(f"   ⚠️  {tabela:<20}: VAZIO")
            except Exception as e:
                print(f"   ❌ {tabela:<20}: Erro - {e}")
                dados_disponiveis[tabela] = 0
        
        self.db.disconnect()
        
        # Verificar se temos dados suficientes para testes
        tem_dados = any(count > 0 for count in dados_disponiveis.values())
        
        if tem_dados:
            print(f"\n✅ DADOS DISPONÍVEIS PARA TESTES!")
            return dados_disponiveis
        else:
            print(f"\n❌ BANCO VAZIO - Execute primeiro a importação")
            return None
    
    def teste_consulta_simples(self):
        """Testa consultas simples em cada tabela"""
        print("\n🔍 TESTE 1: CONSULTAS SIMPLES")
        print("-" * 50)
        
        if not self.db.connect():
            return False
        
        cursor = self.db.connection.cursor()
        
        try:
            # 1. Buscar CNAEs disponíveis
            print("📋 CNAEs disponíveis:")
            cursor.execute("SELECT codigo_cnae, descricao_cnae FROM cnaes LIMIT 5")
            cnaes = cursor.fetchall()
            for codigo, descricao in cnaes:
                print(f"   {codigo}: {descricao[:50]}...")
            
            # 2. Buscar UFs disponíveis
            print(f"\n🗺️  UFs com estabelecimentos:")
            cursor.execute("SELECT uf, COUNT(*) as total FROM estabelecimentos GROUP BY uf ORDER BY total DESC LIMIT 5")
            ufs = cursor.fetchall()
            for uf, total in ufs:
                print(f"   {uf}: {total:,} estabelecimentos")
            
            # 3. Buscar municípios
            print(f"\n🏙️  Municípios com mais estabelecimentos:")
            cursor.execute("""
                SELECT m.nome_municipio, e.uf, COUNT(*) as total 
                FROM estabelecimentos e 
                LEFT JOIN municipios m ON e.municipio = m.codigo_municipio 
                GROUP BY e.municipio, e.uf 
                ORDER BY total DESC 
                LIMIT 5
            """)
            municipios = cursor.fetchall()
            for nome, uf, total in municipios:
                print(f"   {nome or 'N/A'}/{uf}: {total:,} estabelecimentos")
            
            print("   ✅ Consultas simples funcionando!")
            return True
            
        except Exception as e:
            print(f"   ❌ Erro nas consultas simples: {e}")
            return False
        finally:
            self.db.disconnect()
    
    def teste_consulta_com_joins(self):
        """Testa consultas com JOINs entre tabelas"""
        print("\n🔗 TESTE 2: CONSULTAS COM JOINS")
        print("-" * 50)
        
        if not self.db.connect():
            return False
        
        cursor = self.db.connection.cursor()
        
        try:
            # Consulta complexa simulando a exportação
            print("🧪 Testando JOIN completo (estrutura de exportação):")
            
            sql = """
                SELECT 
                    e.cnpj_basico,
                    e.cnpj_ordem,
                    e.cnpj_dv,
                    emp.razao_social,
                    e.nome_fantasia,
                    nat.descricao_natureza,
                    emp.porte,
                    emp.capital_social,
                    c.descricao_cnae,
                    mot.descricao_motivo,
                    e.data_situacao,
                    e.logradouro,
                    e.numero,
                    e.bairro,
                    e.cep,
                    e.uf,
                    m.nome_municipio,
                    e.telefone1,
                    e.email,
                    s.opcao_simples,
                    s.opcao_mei,
                    e.matriz_filial
                FROM estabelecimentos e
                LEFT JOIN empresas emp ON e.cnpj_basico = emp.cnpj_basico
                LEFT JOIN simples s ON e.cnpj_basico = s.cnpj_basico
                LEFT JOIN cnaes c ON e.cnae_principal = c.codigo_cnae
                LEFT JOIN naturezas nat ON emp.natureza_juridica = nat.codigo_natureza
                LEFT JOIN municipios m ON e.municipio = m.codigo_municipio
                LEFT JOIN motivos mot ON e.situacao = mot.codigo_motivo
                LIMIT 5
            """
            
            inicio = time.time()
            cursor.execute(sql)
            resultados = cursor.fetchall()
            tempo = time.time() - inicio
            
            print(f"   📊 Resultados encontrados: {len(resultados)}")
            print(f"   ⏱️  Tempo de execução: {tempo:.3f}s")
            
            if resultados:
                print(f"   📋 Exemplo de resultado:")
                resultado = resultados[0]
                print(f"      CNPJ: {resultado[0]}{resultado[1]}{resultado[2]}")
                print(f"      Razão Social: {resultado[3] or 'N/A'}")
                print(f"      Nome Fantasia: {resultado[4] or 'N/A'}")
                print(f"      CNAE: {resultado[8] or 'N/A'}")
                print(f"      UF: {resultado[15] or 'N/A'}")
                print(f"      Município: {resultado[16] or 'N/A'}")
                
                print("   ✅ JOINs funcionando corretamente!")
                return True
            else:
                print("   ⚠️  Nenhum resultado encontrado")
                return False
                
        except Exception as e:
            print(f"   ❌ Erro nos JOINs: {e}")
            return False
        finally:
            self.db.disconnect()
    
    def teste_filtros_multiplos(self):
        """Testa filtros múltiplos como serão usados na interface"""
        print("\n🎯 TESTE 3: FILTROS MÚLTIPLOS")
        print("-" * 50)
        
        if not self.db.connect():
            return False
        
        cursor = self.db.connection.cursor()
        
        # Casos de teste simulando filtros da interface
        casos_teste = [
            {
                'nome': 'Filtro por UF',
                'filtros': {'uf': 'SP'},
                'sql_where': "e.uf = 'SP'"
            },
            {
                'nome': 'Filtro por UF + Situação Ativa',
                'filtros': {'uf': 'RJ', 'situacao': '02'},
                'sql_where': "e.uf = 'RJ' AND e.situacao = '02'"
            },
            {
                'nome': 'Filtro por Matriz/Filial',
                'filtros': {'matriz_filial': '1'},
                'sql_where': "e.matriz_filial = '1'"
            }
        ]
        
        try:
            for caso in casos_teste:
                print(f"\n🧪 {caso['nome']}:")
                
                # SQL base para contagem
                sql_count = f"""
                    SELECT COUNT(*) 
                    FROM estabelecimentos e
                    WHERE {caso['sql_where']}
                """
                
                inicio = time.time()
                cursor.execute(sql_count)
                total = cursor.fetchone()[0]
                tempo = time.time() - inicio
                
                print(f"   📊 Registros encontrados: {total:,}")
                print(f"   ⏱️  Tempo de consulta: {tempo:.3f}s")
                
                if total > 0:
                    # SQL para buscar amostra
                    sql_sample = f"""
                        SELECT e.cnpj_basico, e.nome_fantasia, e.uf, e.municipio
                        FROM estabelecimentos e
                        WHERE {caso['sql_where']}
                        LIMIT 3
                    """
                    
                    cursor.execute(sql_sample)
                    amostras = cursor.fetchall()
                    
                    print(f"   📋 Amostra dos resultados:")
                    for cnpj, nome, uf, municipio in amostras:
                        print(f"      {cnpj} - {nome or 'S/N'} - {uf}/{municipio}")
                    
                    print(f"   ✅ Filtro funcionando!")
                else:
                    print(f"   ⚠️  Nenhum resultado para este filtro")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Erro nos filtros: {e}")
            return False
        finally:
            self.db.disconnect()
    
    def teste_performance_indices(self):
        """Testa a performance dos índices criados"""
        print("\n⚡ TESTE 4: PERFORMANCE DOS ÍNDICES")
        print("-" * 50)
        
        if not self.db.connect():
            return False
        
        cursor = self.db.connection.cursor()
        
        # Consultas para testar cada índice
        consultas_teste = [
            {
                'nome': 'Índice UF',
                'sql': "SELECT COUNT(*) FROM estabelecimentos WHERE uf = 'SP'"
            },
            {
                'nome': 'Índice Município',
                'sql': "SELECT COUNT(*) FROM estabelecimentos WHERE municipio = '7107'"
            },
            {
                'nome': 'Índice CNAE',
                'sql': "SELECT COUNT(*) FROM estabelecimentos WHERE cnae_principal = '4711302'"
            },
            {
                'nome': 'Índice Bairro',
                'sql': "SELECT COUNT(*) FROM estabelecimentos WHERE bairro = 'CENTRO'"
            }
        ]
        
        try:
            tempos_execucao = []
            
            for consulta in consultas_teste:
                print(f"\n🏃 {consulta['nome']}:")
                
                # Executar 3 vezes para média
                tempos = []
                for i in range(3):
                    inicio = time.time()
                    cursor.execute(consulta['sql'])
                    resultado = cursor.fetchone()[0]
                    tempo = time.time() - inicio
                    tempos.append(tempo)
                
                tempo_medio = sum(tempos) / len(tempos)
                tempos_execucao.append(tempo_medio)
                
                print(f"   📊 Registros: {resultado:,}")
                print(f"   ⏱️  Tempo médio: {tempo_medio:.3f}s")
                
                if tempo_medio < 0.1:
                    print(f"   ✅ Performance excelente!")
                elif tempo_medio < 0.5:
                    print(f"   👍 Performance boa!")
                else:
                    print(f"   ⚠️  Performance pode melhorar")
            
            tempo_medio_geral = sum(tempos_execucao) / len(tempos_execucao)
            print(f"\n📊 RESUMO DE PERFORMANCE:")
            print(f"   ⏱️  Tempo médio geral: {tempo_medio_geral:.3f}s")
            
            if tempo_medio_geral < 0.1:
                print(f"   🚀 ÍNDICES OTIMIZADOS - Sistema pronto para produção!")
            else:
                print(f"   💡 Índices funcionando - Sistema pronto para testes!")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Erro nos testes de performance: {e}")
            return False
        finally:
            self.db.disconnect()
    
    def simular_consulta_exportacao(self, filtros=None):
        """Simula uma consulta de exportação com filtros personalizados"""
        print("\n📤 TESTE 5: SIMULAÇÃO DE EXPORTAÇÃO")
        print("-" * 50)
        
        if filtros:
            print(f"🎯 Filtros aplicados: {filtros}")
        else:
            print(f"🎯 Sem filtros (exportação completa)")
        
        if not self.db.connect():
            return False
        
        cursor = self.db.connection.cursor()
        
        try:
            # Construir WHERE dinâmico baseado nos filtros
            where_clauses = []
            params = []
            
            if filtros:
                if 'uf' in filtros:
                    where_clauses.append("e.uf = ?")
                    params.append(filtros['uf'])
                
                if 'municipio' in filtros:
                    where_clauses.append("e.municipio = ?")
                    params.append(filtros['municipio'])
                
                if 'cnae' in filtros:
                    where_clauses.append("e.cnae_principal = ?")
                    params.append(filtros['cnae'])
                
                if 'bairro' in filtros:
                    where_clauses.append("UPPER(e.bairro) LIKE UPPER(?)")
                    params.append(f"%{filtros['bairro']}%")
                
                if 'matriz_filial' in filtros:
                    where_clauses.append("e.matriz_filial = ?")
                    params.append(filtros['matriz_filial'])
            
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            # SQL de exportação completa
            sql_export = f"""
                SELECT 
                    (e.cnpj_basico || e.cnpj_ordem || e.cnpj_dv) as cnpj_completo,
                    e.cnpj_basico,
                    emp.razao_social,
                    e.nome_fantasia,
                    nat.descricao_natureza,
                    emp.porte,
                    emp.capital_social,
                    c.descricao_cnae,
                    mot.descricao_motivo,
                    e.data_situacao,
                    (COALESCE(e.tipo_logradouro,'') || ' ' || COALESCE(e.logradouro,'') || 
                     CASE WHEN e.numero IS NOT NULL AND e.numero != '' 
                          THEN ', nº ' || e.numero ELSE '' END ||
                     CASE WHEN e.complemento IS NOT NULL AND e.complemento != '' 
                          THEN ' (' || e.complemento || ')' ELSE '' END ||
                     CASE WHEN e.bairro IS NOT NULL AND e.bairro != '' 
                          THEN ' - ' || e.bairro ELSE '' END) as endereco_completo,
                    e.cep,
                    e.uf,
                    m.nome_municipio,
                    e.telefone1,
                    e.email,
                    COALESCE(s.opcao_simples, 'N') as opcao_simples,
                    COALESCE(s.opcao_mei, 'N') as opcao_mei,
                    e.matriz_filial
                FROM estabelecimentos e
                LEFT JOIN empresas emp ON e.cnpj_basico = emp.cnpj_basico
                LEFT JOIN simples s ON e.cnpj_basico = s.cnpj_basico
                LEFT JOIN cnaes c ON e.cnae_principal = c.codigo_cnae
                LEFT JOIN naturezas nat ON emp.natureza_juridica = nat.codigo_natureza
                LEFT JOIN municipios m ON e.municipio = m.codigo_municipio
                LEFT JOIN motivos mot ON e.situacao = mot.codigo_motivo
                WHERE {where_sql}
                LIMIT 10
            """
            
            print(f"🔍 Executando consulta de exportação...")
            
            inicio = time.time()
            cursor.execute(sql_export, params)
            resultados = cursor.fetchall()
            tempo = time.time() - inicio
            
            print(f"   📊 Registros retornados: {len(resultados)}")
            print(f"   ⏱️  Tempo de execução: {tempo:.3f}s")
            
            if resultados:
                print(f"\n📋 AMOSTRA DOS DADOS FORMATADOS:")
                for i, resultado in enumerate(resultados[:3], 1):
                    print(f"\n   📄 Registro {i}:")
                    print(f"      CNPJ: {resultado[0] or 'N/A'}")
                    print(f"      Razão Social: {resultado[2] or 'N/A'}")
                    print(f"      Nome Fantasia: {resultado[3] or 'N/A'}")
                    print(f"      CNAE: {resultado[7] or 'N/A'}")
                    print(f"      Endereço: {resultado[10] or 'N/A'}")
                    print(f"      UF/Município: {resultado[12]}/{resultado[13] or 'N/A'}")
                    print(f"      Simples: {resultado[15]}")
                    print(f"      MEI: {resultado[16]}")
                
                print(f"\n✅ EXPORTAÇÃO SIMULADA COM SUCESSO!")
                return True
            else:
                print(f"   ⚠️  Nenhum resultado encontrado com os filtros aplicados")
                return False
                
        except Exception as e:
            print(f"   ❌ Erro na simulação de exportação: {e}")
            return False
        finally:
            self.db.disconnect()

def main():
    """Executa todos os testes de consultas"""
    print("🧪 SISTEMA DE TESTES DE CONSULTAS CNPJ")
    print("=" * 60)
    
    tester = CNPJQueryTester()
    
    # 1. Verificar dados disponíveis
    dados = tester.verificar_dados_disponiveis()
    if not dados:
        print("\n❌ TESTES CANCELADOS - Banco vazio")
        print("💡 Execute primeiro: python import_data.py")
        return
    
    # 2. Executar testes sequencialmente
    testes = [
        ('Consultas Simples', tester.teste_consulta_simples),
        ('Consultas com JOINs', tester.teste_consulta_com_joins),
        ('Filtros Múltiplos', tester.teste_filtros_multiplos),
        ('Performance dos Índices', tester.teste_performance_indices)
    ]
    
    resultados = {}
    
    for nome, funcao_teste in testes:
        try:
            resultado = funcao_teste()
            resultados[nome] = resultado
        except Exception as e:
            print(f"❌ Erro no teste {nome}: {e}")
            resultados[nome] = False
    
    # 3. Simulação de exportação com diferentes filtros
    casos_exportacao = [
        {'uf': 'SP'},
        {'uf': 'RJ', 'matriz_filial': '1'},
        {'bairro': 'CENTRO'}
    ]
    
    for i, filtros in enumerate(casos_exportacao, 1):
        print(f"\n📤 CASO DE EXPORTAÇÃO {i}:")
        tester.simular_consulta_exportacao(filtros)
    
    # 4. Relatório final
    print(f"\n📊 RELATÓRIO FINAL DOS TESTES")
    print("=" * 60)
    
    total_testes = len(resultados)
    testes_passaram = sum(resultados.values())
    
    for nome, passou in resultados.items():
        status = "✅ PASSOU" if passou else "❌ FALHOU"
        print(f"   {nome:<25}: {status}")
    
    print(f"\n📈 RESULTADO GERAL: {testes_passaram}/{total_testes} testes passaram")
    
    if testes_passaram == total_testes:
        print("🎉 TODOS OS TESTES PASSARAM - SISTEMA PRONTO PARA BACKEND!")
    else:
        print("⚠️  ALGUNS TESTES FALHARAM - Revisar antes de prosseguir")

if __name__ == "__main__":
    main()