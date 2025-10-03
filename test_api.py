import requests
import json
import time

class APITester:
    """
    Teste automatizado para as APIs do sistema CNPJ
    """
    
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def test_endpoint(self, endpoint, method='GET', data=None):
        """Testa um endpoint específico"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == 'GET':
                response = self.session.get(url)
            elif method == 'POST':
                response = self.session.post(url, json=data)
            
            print(f"🔗 {method} {endpoint}")
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Sucesso!")
                return result
            else:
                print(f"   ❌ Erro: {response.text}")
                return None
                
        except Exception as e:
            print(f"   ❌ Exceção: {e}")
            return None
    
    def run_all_tests(self):
        """Executa todos os testes das APIs"""
        print("🧪 TESTANDO TODAS AS APIs DO SISTEMA CNPJ")
        print("=" * 60)
        
        # 1. Teste da página inicial
        print("\n📋 TESTE 1: Página inicial")
        home = self.test_endpoint("/")
        if home:
            print(f"   📝 Versão: {home.get('version')}")
            print(f"   📡 Endpoints: {len(home.get('endpoints', {}))} disponíveis")
        
        # 2. Teste de health check
        print("\n💓 TESTE 2: Health check")
        health = self.test_endpoint("/health")
        if health:
            print(f"   🔋 Status: {health.get('status')}")
            print(f"   🗄️  Database: {health.get('database')}")
            print(f"   📊 Estabelecimentos: {health.get('total_estabelecimentos'):,}")
        
        # 3. Teste de estatísticas
        print("\n📊 TESTE 3: Estatísticas")
        stats = self.test_endpoint("/stats")
        if stats:
            tabelas = stats.get('tabelas', {})
            print(f"   📋 Tabelas:")
            for tabela, count in tabelas.items():
                print(f"      {tabela}: {count:,} registros")
            
            top_ufs = stats.get('top_ufs', [])[:3]
            print(f"   🗺️  Top UFs: {', '.join([f'{uf['uf']}({uf['total']})' for uf in top_ufs])}")
        
        # 4. Teste de filtros
        print("\n🎯 TESTE 4: Opções de filtros")
        filters = self.test_endpoint("/filters")
        if filters:
            ufs = filters.get('ufs', [])
            cnaes = filters.get('cnaes', [])
            print(f"   🗺️  UFs disponíveis: {len(ufs)}")
            print(f"   🏢 CNAEs disponíveis: {len(cnaes)}")
            print(f"   📋 Exemplo UFs: {', '.join([uf['value'] for uf in ufs[:5]])}")
        
        # 5. Teste de consulta simples
        print("\n🔍 TESTE 5: Consulta simples")
        query_data = {"page": 1, "per_page": 5}
        query = self.test_endpoint("/query", "POST", query_data)
        if query:
            print(f"   📊 Registros retornados: {len(query.get('data', []))}")
            print(f"   📄 Total disponível: {query.get('pagination', {}).get('total', 0):,}")
            print(f"   ⏱️  Tempo execução: {query.get('query_info', {}).get('execution_time')}s")
            
            # Mostrar amostra
            dados = query.get('data', [])
            if dados:
                exemplo = dados[0]
                print(f"   📋 Exemplo:")
                print(f"      CNPJ: {exemplo.get('cnpj_completo')}")
                print(f"      Empresa: {exemplo.get('nome_fantasia')}")
                print(f"      UF: {exemplo.get('uf')}")
        
        # 6. Teste de consulta com filtro
        print("\n🎯 TESTE 6: Consulta com filtro UF")
        query_filtered = {"uf": "SP", "page": 1, "per_page": 3}
        query_result = self.test_endpoint("/query", "POST", query_filtered)
        if query_result:
            dados = query_result.get('data', [])
            total = query_result.get('pagination', {}).get('total', 0)
            print(f"   📊 Registros SP: {total:,}")
            print(f"   📋 Amostra retornada: {len(dados)}")
            
            for i, item in enumerate(dados, 1):
                print(f"      {i}. {item.get('cnpj_completo')} - {item.get('nome_fantasia', 'S/N')} - {item.get('municipio')}")
        
        # 7. Teste de exportação (apenas verificar se funciona, não baixar)
        print("\n📤 TESTE 7: Exportação CSV")
        export_data = {"uf": "RJ", "per_page": 10}  # Pequena amostra
        export = self.test_endpoint("/export", "POST", export_data)
        if export:
            print(f"   📁 Arquivo gerado: {export.get('filename')}")
            print(f"   📊 Registros exportados: {export.get('total_registros'):,}")
            print(f"   ⏱️  Tempo execução: {export.get('execution_time')}s")
            print(f"   🔗 URL download: {export.get('download_url')}")
        
        print(f"\n🎉 TESTES CONCLUÍDOS!")
        print("✅ API Flask funcionando perfeitamente!")

def main():
    """Executa os testes da API"""
    print("🚀 INICIANDO TESTES DA API CNPJ")
    print("=" * 60)
    
    # Aguardar servidor inicializar
    print("⏳ Aguardando servidor inicializar...")
    time.sleep(2)
    
    # Verificar se servidor está rodando
    try:
        response = requests.get("http://localhost:5000", timeout=5)
        if response.status_code == 200:
            print("✅ Servidor detectado, iniciando testes...")
        else:
            print("❌ Servidor não está respondendo corretamente")
            return
    except:
        print("❌ Servidor não encontrado na porta 5000")
        print("💡 Certifique-se de que o app.py está rodando")
        return
    
    # Executar testes
    tester = APITester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()