"""
Script para importar dados reais do CNPJ da pasta PROJETO CNPJ
Versão corrigida - sem emojis e com chunks otimizados
"""

import pandas as pd
import sqlite3
from pathlib import Path
import os
from datetime import datetime
import logging

# Configurar logging simples (sem emojis)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('import_projeto_cnpj.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class CNPJProjectImporter:
    def __init__(self, db_path="data/cnpj_database.db", data_path="C:/Users/Victor/Documents/CNPJ"):
        self.db_path = db_path
        self.data_path = Path(data_path)
        self.connection = None
        
        # Mapeamento de pastas para tabelas e estruturas
        self.folder_mapping = {
            'Cnaes': {
                'table': 'cnaes',
                'columns': ['codigo_cnae', 'descricao_cnae'],
                'encoding': 'latin1'
            },
            'Empresas0': {
                'table': 'empresas',
                'columns': [
                    'cnpj_basico', 'razao_social', 'natureza_juridica', 
                    'porte', 'capital_social', 'ente_federativo',
                    'campo7'
                ],
                'encoding': 'latin1'
            },
            'Estabelecimentos0': {
                'table': 'estabelecimentos',
                'columns': [
                    'cnpj_basico', 'cnpj_ordem', 'cnpj_dv', 'identificador_matriz_filial',
                    'nome_fantasia', 'situacao_cadastral', 'data_situacao_cadastral',
                    'motivo_situacao_cadastral', 'nome_cidade_exterior', 'pais',
                    'data_inicio_atividade', 'cnae_fiscal_principal', 'cnae_fiscal_secundaria',
                    'tipo_logradouro', 'logradouro', 'numero', 'complemento', 'bairro',
                    'cep', 'uf', 'municipio', 'ddd_1', 'telefone_1', 'ddd_2', 'telefone_2',
                    'ddd_fax', 'fax', 'correio_eletronico', 'situacao_especial', 'data_situacao_especial'
                ],
                'encoding': 'latin1'
            },
            'Municipios': {
                'table': 'municipios',
                'columns': ['codigo_municipio', 'nome_municipio'],
                'encoding': 'latin1'
            },
            'Motivos': {
                'table': 'motivos',
                'columns': ['codigo_motivo', 'descricao_motivo'],
                'encoding': 'latin1'
            },
            'Naturezas': {
                'table': 'naturezas',
                'columns': ['codigo_natureza', 'descricao_natureza'],
                'encoding': 'latin1'
            },
            'Paises': {
                'table': 'paises',
                'columns': ['codigo_pais', 'nome_pais'],
                'encoding': 'latin1'
            },
            'Qualificacoes': {
                'table': 'qualificacoes',
                'columns': ['codigo_qualificacao', 'descricao_qualificacao'],
                'encoding': 'latin1'
            },
            'Simples': {
                'table': 'simples',
                'columns': [
                    'cnpj_basico', 'opcao_simples', 'data_opcao_simples', 'data_exclusao_simples',
                    'opcao_mei', 'data_opcao_mei', 'data_exclusao_mei'
                ],
                'encoding': 'latin1'
            },
            'Socios0': {
                'table': 'socios',
                'columns': [
                    'cnpj_basico', 'identificador_socio', 'nome_socio', 'cpf_cnpj_socio',
                    'qualificacao_socio', 'data_entrada_sociedade', 'pais', 'representante_legal',
                    'nome_representante', 'qualificacao_representante', 'faixa_etaria'
                ],
                'encoding': 'latin1'
            }
        }

    def connect_db(self):
        """Conecta ao banco de dados"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.execute("PRAGMA foreign_keys = OFF")  # Desabilitar FKs durante import
            self.connection.execute("PRAGMA journal_mode = WAL")  # Modo WAL para performance
            self.connection.execute("PRAGMA synchronous = NORMAL")
            self.connection.execute("PRAGMA cache_size = 10000")
            self.connection.execute("PRAGMA temp_store = MEMORY")
            logging.info("Conectado ao banco de dados")
            return True
        except Exception as e:
            logging.error(f"Erro ao conectar no banco: {e}")
            return False

    def find_csv_file(self, folder_name):
        """Encontra o arquivo CSV na pasta especificada"""
        folder_path = self.data_path / folder_name
        if not folder_path.exists():
            logging.warning(f"Pasta não encontrada: {folder_path}")
            return None
        
        csv_files = list(folder_path.glob("*.csv")) + list(folder_path.glob("*.CSV"))
        if not csv_files:
            logging.warning(f"Nenhum arquivo CSV encontrado em: {folder_path}")
            return None
        
        # Pega o primeiro arquivo CSV encontrado
        csv_file = csv_files[0]
        logging.info(f"Arquivo encontrado: {csv_file} ({csv_file.stat().st_size / (1024*1024):.1f} MB)")
        return csv_file

    def get_table_count(self, table_name):
        """Retorna o número de registros na tabela"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            return cursor.fetchone()[0]
        except:
            return 0

    def import_table(self, folder_name, config):
        """Importa dados de uma tabela específica"""
        csv_file = self.find_csv_file(folder_name)
        if not csv_file:
            return False
        
        table_name = config['table']
        columns = config['columns']
        encoding = config.get('encoding', 'utf-8')
        
        logging.info(f"Importando {table_name} de {csv_file.name}...")
        
        try:
            # Verificar se a tabela já tem dados
            current_count = self.get_table_count(table_name)
            if current_count > 0:
                logging.info(f"Tabela {table_name} já possui {current_count} registros. Pulando...")
                return True
            
            # Determinar tamanho do chunk baseado no número de colunas (SQLite limit)
            max_vars = 999  # SQLite limit
            max_rows_per_chunk = max_vars // len(columns)
            
            # Ajustar chunk size baseado no tamanho do arquivo
            file_size_mb = csv_file.stat().st_size / (1024 * 1024)
            if file_size_mb > 1000:  # > 1GB
                chunk_size = min(1000, max_rows_per_chunk)
            elif file_size_mb > 100:  # > 100MB
                chunk_size = min(5000, max_rows_per_chunk)
            else:
                chunk_size = min(10000, max_rows_per_chunk)
            
            logging.info(f"Arquivo: {file_size_mb:.1f} MB, Chunk size: {chunk_size}")
            
            # Ler e importar em chunks
            chunk_count = 0
            total_rows = 0
            
            for chunk in pd.read_csv(
                csv_file, 
                chunksize=chunk_size,
                encoding=encoding,
                sep=';',  # CSV da Receita Federal usa ';'
                header=None,  # Arquivos não têm header
                names=columns,
                dtype=str,  # Importar tudo como string inicialmente
                na_values=[''],
                keep_default_na=False
            ):
                chunk_count += 1
                
                # Limpar dados
                chunk = chunk.fillna('')
                
                # Inserir no banco usando método mais simples
                chunk.to_sql(
                    table_name, 
                    self.connection, 
                    if_exists='append', 
                    index=False,
                    method=None  # Usar método padrão ao invés de 'multi'
                )
                
                total_rows += len(chunk)
                
                # Log de progresso
                if chunk_count % 50 == 0:
                    logging.info(f"   Processados {chunk_count} chunks, {total_rows:,} registros...")
                    self.connection.commit()  # Commit periódico
            
            self.connection.commit()
            final_count = self.get_table_count(table_name)
            logging.info(f"SUCESSO {table_name}: {final_count:,} registros importados!")
            
            return True
            
        except Exception as e:
            logging.error(f"ERRO ao importar {table_name}: {e}")
            return False

    def create_indexes(self):
        """Criar índices para performance"""
        logging.info("Criando índices para performance...")
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_empresas_cnpj_basico ON empresas(cnpj_basico)",
            "CREATE INDEX IF NOT EXISTS idx_estabelecimentos_cnpj_basico ON estabelecimentos(cnpj_basico)",
            "CREATE INDEX IF NOT EXISTS idx_estabelecimentos_uf ON estabelecimentos(uf)",
            "CREATE INDEX IF NOT EXISTS idx_estabelecimentos_municipio ON estabelecimentos(municipio)",
            "CREATE INDEX IF NOT EXISTS idx_estabelecimentos_cnae ON estabelecimentos(cnae_fiscal_principal)",
            "CREATE INDEX IF NOT EXISTS idx_simples_cnpj_basico ON simples(cnpj_basico)"
        ]
        
        for index_sql in indexes:
            try:
                self.connection.execute(index_sql)
            except Exception as e:
                logging.warning(f"Erro ao criar índice: {e}")
        
        self.connection.commit()
        logging.info("Índices criados com sucesso!")

    def import_all_data(self):
        """Importa todos os dados do projeto CNPJ"""
        if not self.connect_db():
            return False
        
        start_time = datetime.now()
        logging.info("INICIANDO IMPORTAÇÃO DOS DADOS REAIS DO CNPJ")
        logging.info("=" * 60)
        
        # Ordem de importação (tabelas de referência primeiro, depois menores para maiores)
        import_order = [
            'Motivos', 'Naturezas', 'Paises', 'Qualificacoes', 
            'Cnaes', 'Municipios', 'Empresas0', 'Estabelecimentos0', 'Simples', 'Socios0'
        ]
        
        success_count = 0
        total_tables = len(import_order)
        
        for folder_name in import_order:
            if folder_name in self.folder_mapping:
                config = self.folder_mapping[folder_name]
                logging.info(f"\nTABELA {success_count + 1}/{total_tables}: {config['table'].upper()}")
                
                if self.import_table(folder_name, config):
                    success_count += 1
                else:
                    logging.error(f"FALHA ao importar {folder_name}")
        
        # Criar índices após importação
        if success_count > 0:
            self.create_indexes()
        
        # Reabilitar foreign keys
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.commit()
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        logging.info("\n" + "=" * 60)
        logging.info("IMPORTAÇÃO CONCLUÍDA!")
        logging.info(f"Tabelas importadas: {success_count}/{total_tables}")
        logging.info(f"Tempo total: {duration}")
        
        # Mostrar estatísticas finais
        self.show_final_stats()
        
        self.connection.close()
        return success_count >= (total_tables - 2)  # Permitir falha em até 2 tabelas grandes

    def show_final_stats(self):
        """Mostra estatísticas finais do banco"""
        logging.info("\nESTATÍSTICAS FINAIS:")
        
        tables = ['empresas', 'estabelecimentos', 'simples', 'cnaes', 'municipios', 'naturezas']
        
        for table in tables:
            try:
                cursor = self.connection.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                logging.info(f"   {table.capitalize():<15}: {count:,} registros")
            except:
                logging.info(f"   {table.capitalize():<15}: Erro ao contar")

def main():
    """Função principal"""
    importer = CNPJProjectImporter()
    
    # Verificar se a pasta existe
    if not importer.data_path.exists():
        logging.error(f"Pasta não encontrada: {importer.data_path}")
        logging.info("Verifique se o caminho está correto:")
        logging.info("   C:/Users/victor.vasconcelos/Documents/PROJETO CNPJ")
        return
    
    logging.info(f"Pasta de dados: {importer.data_path}")
    logging.info(f"Banco de dados: {importer.db_path}")
    
    success = importer.import_all_data()
    
    if success:
        logging.info("\nPROXIMOS PASSOS:")
        logging.info("   1. Reinicie o servidor Flask: python app.py")
        logging.info("   2. Acesse a interface web")
        logging.info("   3. Teste os filtros com os dados reais")
    else:
        logging.error("\nImportação falhou. Verifique os logs acima.")

if __name__ == "__main__":
    main()