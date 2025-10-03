import pandas as pd
import sqlite3
import os
from pathlib import Path
import time
from database import CNPJDatabase

class CNPJImporter:
    """
    Classe para importar dados dos CSVs da Receita Federal para o banco de dados
    Processa arquivos grandes em chunks para otimizar memória
    """
    
    def __init__(self, db_path="cnpj_database.db", data_dir="../PROJETO CNPJ"):
        self.db_path = db_path
        self.data_dir = Path(data_dir)
        self.db = CNPJDatabase(db_path)
        self.chunk_size = 10000  # Processar 10k registros por vez
        
    def find_csv_files(self):
        """Localiza todos os arquivos CSV nas subpastas"""
        print("🔍 LOCALIZANDO ARQUIVOS CSV...")
        
        arquivos_encontrados = {}
        
        # Mapear pastas para tipos de dados
        mapeamento_pastas = {
            'Empresas0': 'empresas',
            'Estabelecimentos0': 'estabelecimentos', 
            'Simples': 'simples',
            'Cnaes': 'cnaes',
            'Municipios': 'municipios',
            'Naturezas': 'naturezas',
            'Motivos': 'motivos',
            'Paises': 'paises',
            'Qualificacoes': 'qualificacoes'
        }
        
        for pasta, tabela in mapeamento_pastas.items():
            pasta_path = self.data_dir / pasta
            if pasta_path.exists():
                # Procurar arquivos CSV na pasta
                csv_files = list(pasta_path.glob("*.csv"))
                if csv_files:
                    arquivo = csv_files[0]  # Pegar o primeiro CSV encontrado
                    tamanho_mb = arquivo.stat().st_size / (1024*1024)
                    arquivos_encontrados[tabela] = {
                        'arquivo': arquivo,
                        'tamanho_mb': tamanho_mb
                    }
                    print(f"   ✅ {tabela:<20} - {arquivo.name} ({tamanho_mb:.1f} MB)")
                else:
                    print(f"   ❌ {tabela:<20} - Nenhum CSV encontrado")
            else:
                print(f"   ⚠️  {tabela:<20} - Pasta não encontrada: {pasta}")
        
        return arquivos_encontrados
    
    def import_table_reference(self, tabela, arquivo_info):
        """Importa tabelas de referência pequenas (completas)"""
        arquivo = arquivo_info['arquivo']
        tamanho_mb = arquivo_info['tamanho_mb']
        
        print(f"\n📥 IMPORTANDO: {tabela.upper()}")
        print(f"   📁 Arquivo: {arquivo.name}")
        print(f"   📊 Tamanho: {tamanho_mb:.1f} MB")
        
        try:
            # Definir colunas para cada tabela
            colunas_map = {
                'cnaes': ['codigo_cnae', 'descricao_cnae'],
                'municipios': ['codigo_municipio', 'nome_municipio'], 
                'naturezas': ['codigo_natureza', 'descricao_natureza'],
                'motivos': ['codigo_motivo', 'descricao_motivo'],
                'paises': ['codigo_pais', 'nome_pais'],
                'qualificacoes': ['codigo_qualificacao', 'descricao_qualificacao']
            }
            
            colunas = colunas_map.get(tabela, [])
            if not colunas:
                print(f"   ❌ Colunas não definidas para {tabela}")
                return False
            
            # Carregar dados
            df = pd.read_csv(arquivo, sep=';', encoding='latin-1', names=colunas)
            df = df.fillna('')  # Substituir NaN por string vazia
            
            print(f"   📊 Registros carregados: {len(df):,}")
            
            # Inserir no banco
            if self.db.connect():
                cursor = self.db.connection.cursor()
                
                # Preparar SQL de inserção
                placeholders = ','.join(['?' for _ in colunas])
                sql = f"INSERT OR REPLACE INTO {tabela} ({','.join(colunas)}) VALUES ({placeholders})"
                
                # Inserir dados
                dados = df.values.tolist()
                cursor.executemany(sql, dados)
                self.db.connection.commit()
                
                print(f"   ✅ {len(dados):,} registros inseridos com sucesso!")
                self.db.disconnect()
                return True
            else:
                print(f"   ❌ Erro ao conectar com banco")
                return False
                
        except Exception as e:
            print(f"   ❌ Erro na importação: {e}")
            return False
    
    def import_table_large(self, tabela, arquivo_info):
        """Importa tabelas grandes em chunks"""
        arquivo = arquivo_info['arquivo']
        tamanho_mb = arquivo_info['tamanho_mb']
        
        print(f"\n📥 IMPORTANDO (CHUNKS): {tabela.upper()}")
        print(f"   📁 Arquivo: {arquivo.name}")
        print(f"   📊 Tamanho: {tamanho_mb:.1f} MB")
        print(f"   🔄 Chunk size: {self.chunk_size:,} registros")
        
        try:
            # Definir colunas para tabelas grandes
            colunas_map = {
                'empresas': ['cnpj_basico', 'razao_social', 'natureza_juridica', 'porte', 
                           'capital_social', 'ente_federativo', 'campo7'],
                'estabelecimentos': ['cnpj_basico', 'cnpj_ordem', 'cnpj_dv', 'matriz_filial', 
                                   'nome_fantasia', 'situacao', 'data_situacao', 'motivo_situacao',
                                   'nome_cidade_exterior', 'pais', 'data_inicio', 'cnae_principal',
                                   'cnae_secundario', 'tipo_logradouro', 'logradouro', 'numero',
                                   'complemento', 'bairro', 'cep', 'uf', 'municipio', 'ddd1',
                                   'telefone1', 'ddd2', 'telefone2', 'fax_ddd', 'fax_numero',
                                   'email', 'situacao_especial', 'data_situacao_especial'],
                'simples': ['cnpj_basico', 'opcao_simples', 'data_opcao_simples', 'data_exclusao_simples',
                          'opcao_mei', 'data_opcao_mei', 'data_exclusao_mei']
            }
            
            colunas = colunas_map.get(tabela, [])
            if not colunas:
                print(f"   ❌ Colunas não definidas para {tabela}")
                return False
            
            # Conectar ao banco
            if not self.db.connect():
                print(f"   ❌ Erro ao conectar com banco")
                return False
            
            cursor = self.db.connection.cursor()
            
            # Preparar SQL de inserção
            if tabela == 'estabelecimentos':
                # Estabelecimentos tem ID auto-increment, não incluir na inserção
                colunas_insert = colunas
                placeholders = ','.join(['?' for _ in colunas_insert])
                sql = f"INSERT INTO {tabela} ({','.join(colunas_insert)}) VALUES ({placeholders})"
            else:
                placeholders = ','.join(['?' for _ in colunas])
                sql = f"INSERT OR REPLACE INTO {tabela} ({','.join(colunas)}) VALUES ({placeholders})"
            
            # Processar arquivo em chunks
            total_inseridos = 0
            chunk_num = 0
            inicio = time.time()
            
            for chunk_df in pd.read_csv(arquivo, sep=';', encoding='latin-1', 
                                      names=colunas, chunksize=self.chunk_size):
                chunk_num += 1
                chunk_df = chunk_df.fillna('')  # Substituir NaN por string vazia
                
                # Inserir chunk
                dados = chunk_df.values.tolist()
                cursor.executemany(sql, dados)
                self.db.connection.commit()
                
                total_inseridos += len(dados)
                
                # Mostrar progresso
                tempo_decorrido = time.time() - inicio
                taxa = total_inseridos / tempo_decorrido if tempo_decorrido > 0 else 0
                print(f"   📊 Chunk {chunk_num}: {len(dados):,} registros | Total: {total_inseridos:,} | Taxa: {taxa:.0f} reg/s")
            
            print(f"   ✅ CONCLUÍDO! {total_inseridos:,} registros inseridos em {tempo_decorrido:.1f}s")
            self.db.disconnect()
            return True
            
        except Exception as e:
            print(f"   ❌ Erro na importação: {e}")
            if self.db.connection:
                self.db.disconnect()
            return False
    
    def import_all(self):
        """Importa todos os arquivos CSV para o banco"""
        print("🚀 INICIANDO IMPORTAÇÃO COMPLETA DOS DADOS CNPJ")
        print("=" * 60)
        
        # Localizar arquivos
        arquivos = self.find_csv_files()
        
        if not arquivos:
            print("❌ Nenhum arquivo CSV encontrado!")
            return False
        
        print(f"\n📋 ENCONTRADOS {len(arquivos)} ARQUIVOS PARA IMPORTAR")
        
        # Separar tabelas por tamanho
        tabelas_pequenas = ['cnaes', 'municipios', 'naturezas', 'motivos', 'paises', 'qualificacoes']
        tabelas_grandes = ['empresas', 'estabelecimentos', 'simples']
        
        sucesso_total = True
        
        # 1. Importar tabelas de referência primeiro (pequenas)
        print(f"\n🏷️  FASE 1: IMPORTANDO TABELAS DE REFERÊNCIA")
        print("-" * 50)
        
        for tabela in tabelas_pequenas:
            if tabela in arquivos:
                sucesso = self.import_table_reference(tabela, arquivos[tabela])
                if not sucesso:
                    sucesso_total = False
                    print(f"⚠️  Falha na importação de {tabela}")
        
        # 2. Importar tabelas grandes
        print(f"\n📊 FASE 2: IMPORTANDO TABELAS PRINCIPAIS (GRANDES)")
        print("-" * 50)
        
        for tabela in tabelas_grandes:
            if tabela in arquivos:
                sucesso = self.import_table_large(tabela, arquivos[tabela])
                if not sucesso:
                    sucesso_total = False
                    print(f"⚠️  Falha na importação de {tabela}")
        
        # 3. Verificar resultados
        print(f"\n📈 VERIFICANDO DADOS IMPORTADOS...")
        print("-" * 50)
        
        if self.db.connect():
            cursor = self.db.connection.cursor()
            
            tabelas_verificar = ['empresas', 'estabelecimentos', 'simples', 'cnaes', 'municipios']
            for tabela in tabelas_verificar:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
                    count = cursor.fetchone()[0]
                    print(f"   📊 {tabela:<20}: {count:,} registros")
                except:
                    print(f"   ❌ {tabela:<20}: Erro ao contar")
            
            self.db.disconnect()
        
        if sucesso_total:
            print(f"\n🎉 IMPORTAÇÃO CONCLUÍDA COM SUCESSO!")
            print(f"💾 Banco: {self.db_path}")
        else:
            print(f"\n⚠️  IMPORTAÇÃO CONCLUÍDA COM ALGUNS ERROS")
        
        return sucesso_total

def main():
    """Função principal para executar a importação"""
    print("📥 SISTEMA DE IMPORTAÇÃO DE DADOS CNPJ")
    print("=" * 60)
    
    # Verificar se banco existe
    if not os.path.exists("cnpj_database.db"):
        print("❌ Banco de dados não encontrado!")
        print("💡 Execute primeiro: python database.py")
        return
    
    # Criar importador
    importer = CNPJImporter()
    
    # Verificar se diretório de dados existe
    if not importer.data_dir.exists():
        print(f"❌ Diretório de dados não encontrado: {importer.data_dir}")
        print("💡 Verifique se os dados estão no local correto")
        return
    
    print(f"📁 Diretório de dados: {importer.data_dir.absolute()}")
    print(f"💾 Banco de dados: {importer.db_path}")
    
    # Confirmar importação
    resposta = input("\n🤔 Deseja iniciar a importação? (s/n): ").lower()
    if resposta != 's':
        print("⏹️  Importação cancelada")
        return
    
    # Executar importação
    inicio = time.time()
    sucesso = importer.import_all()
    fim = time.time()
    
    tempo_total = fim - inicio
    print(f"\n⏱️  TEMPO TOTAL: {tempo_total:.1f} segundos")
    
    if sucesso:
        print("✅ IMPORTAÇÃO FINALIZADA - SISTEMA PRONTO PARA USO!")
    else:
        print("⚠️  IMPORTAÇÃO CONCLUÍDA COM ALERTAS")

if __name__ == "__main__":
    main()