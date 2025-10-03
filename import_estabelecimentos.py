#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IMPORTADOR DE ESTABELECIMENTOS - DADOS CNPJ
Importa dados de estabelecimentos (UF, município, CNAE, endereço) para completar o sistema
"""

import pandas as pd
import sqlite3
import os
import time
import logging
from pathlib import Path

# Configurar logging sem emojis
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class EstabelecimentosImporter:
    def __init__(self, db_path='cnpj_database.db'):
        self.db_path = db_path
        self.conn = None
        
        # Configurações otimizadas para arquivo grande
        self.chunk_size = 100  # Reduzido para SQLite
        self.commit_every = 1000
        
    def connect_db(self):
        """Conectar ao banco SQLite com otimizações"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            
            # Otimizações SQLite para inserção em massa
            self.conn.execute("PRAGMA journal_mode = WAL")
            self.conn.execute("PRAGMA synchronous = NORMAL")
            self.conn.execute("PRAGMA cache_size = 100000")
            self.conn.execute("PRAGMA temp_store = memory")
            
            logging.info("Conectado ao banco com otimizações")
            return True
        except Exception as e:
            logging.error(f"Erro ao conectar: {e}")
            return False
    
    def create_estabelecimentos_table(self):
        """Criar tabela estabelecimentos otimizada"""
        try:
            cursor = self.conn.cursor()
            
            # Dropar tabela se existir
            cursor.execute("DROP TABLE IF EXISTS estabelecimentos")
            
            # Criar tabela com estrutura correta
            cursor.execute("""
                CREATE TABLE estabelecimentos (
                    cnpj_basico TEXT,
                    cnpj_ordem TEXT,
                    cnpj_dv TEXT,
                    identificador_matriz_filial TEXT,
                    nome_fantasia TEXT,
                    situacao_cadastral TEXT,
                    data_situacao_cadastral TEXT,
                    motivo_situacao_cadastral TEXT,
                    nome_cidade_exterior TEXT,
                    pais TEXT,
                    data_inicio_atividade TEXT,
                    cnae_fiscal_principal TEXT,
                    cnae_fiscal_secundaria TEXT,
                    tipo_logradouro TEXT,
                    logradouro TEXT,
                    numero TEXT,
                    complemento TEXT,
                    bairro TEXT,
                    cep TEXT,
                    uf TEXT,
                    municipio TEXT,
                    ddd_1 TEXT,
                    telefone_1 TEXT,
                    ddd_2 TEXT,
                    telefone_2 TEXT,
                    ddd_fax TEXT,
                    fax TEXT,
                    correio_eletronico TEXT,
                    situacao_especial TEXT,
                    data_situacao_especial TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Criar índices para performance
            cursor.execute("CREATE INDEX idx_estabelecimentos_cnpj ON estabelecimentos(cnpj_basico)")
            cursor.execute("CREATE INDEX idx_estabelecimentos_uf ON estabelecimentos(uf)")
            cursor.execute("CREATE INDEX idx_estabelecimentos_municipio ON estabelecimentos(municipio)")
            cursor.execute("CREATE INDEX idx_estabelecimentos_cnae ON estabelecimentos(cnae_fiscal_principal)")
            
            self.conn.commit()
            logging.info("Tabela estabelecimentos criada com sucesso")
            return True
            
        except Exception as e:
            logging.error(f"Erro ao criar tabela: {e}")
            return False
    
    def import_estabelecimentos(self):
        """Importar dados de estabelecimentos"""
        try:
            # Localizar arquivo
            estabelecimentos_path = r"C:\Users\victor.vasconcelos\Documents\PROJETO CNPJ\Estabelecimentos0"
            csv_files = list(Path(estabelecimentos_path).glob("*.CSV"))
            
            if not csv_files:
                logging.error("Arquivo de estabelecimentos não encontrado")
                return False
            
            csv_file = csv_files[0]
            file_size_gb = csv_file.stat().st_size / (1024**3)
            
            logging.info(f"Importando estabelecimentos de {csv_file.name}")
            logging.info(f"Tamanho do arquivo: {file_size_gb:.1f} GB")
            logging.info(f"Chunk size: {self.chunk_size}")
            
            total_imported = 0
            chunk_count = 0
            start_time = time.time()
            
            # Processar arquivo em chunks
            for chunk in pd.read_csv(
                csv_file,
                sep=';',
                encoding='latin1',
                chunksize=self.chunk_size,
                header=None,
                dtype=str,
                na_values=[''],
                keep_default_na=False
            ):
                # Definir nomes das colunas
                chunk.columns = [
                    'cnpj_basico', 'cnpj_ordem', 'cnpj_dv', 'identificador_matriz_filial',
                    'nome_fantasia', 'situacao_cadastral', 'data_situacao_cadastral',
                    'motivo_situacao_cadastral', 'nome_cidade_exterior', 'pais',
                    'data_inicio_atividade', 'cnae_fiscal_principal', 'cnae_fiscal_secundaria',
                    'tipo_logradouro', 'logradouro', 'numero', 'complemento', 'bairro',
                    'cep', 'uf', 'municipio', 'ddd_1', 'telefone_1', 'ddd_2', 'telefone_2',
                    'ddd_fax', 'fax', 'correio_eletronico', 'situacao_especial', 'data_situacao_especial'
                ]
                
                # Inserir no banco
                chunk.to_sql(
                    'estabelecimentos',
                    self.conn,
                    if_exists='append',
                    index=False,
                    method=None
                )
                
                chunk_count += 1
                total_imported += len(chunk)
                
                # Log de progresso a cada 1000 chunks
                if chunk_count % 1000 == 0:
                    elapsed = time.time() - start_time
                    rate = total_imported / elapsed if elapsed > 0 else 0
                    logging.info(f"Processados {chunk_count:,} chunks, {total_imported:,} registros... ({rate:.0f} reg/seg)")
                
                # Commit periodicamente
                if chunk_count % self.commit_every == 0:
                    self.conn.commit()
            
            # Commit final
            self.conn.commit()
            
            elapsed = time.time() - start_time
            logging.info(f"SUCESSO: {total_imported:,} estabelecimentos importados em {elapsed/60:.1f} minutos")
            return True
            
        except Exception as e:
            logging.error(f"Erro na importação: {e}")
            return False
    
    def import_municipios(self):
        """Importar dados de municípios"""
        try:
            municipios_path = r"C:\Users\victor.vasconcelos\Documents\PROJETO CNPJ\Municipios"
            csv_files = list(Path(municipios_path).glob("*.CSV"))
            
            if not csv_files:
                logging.warning("Arquivo de municípios não encontrado")
                return True  # Não é crítico
            
            csv_file = csv_files[0]
            logging.info(f"Importando municípios de {csv_file.name}")
            
            # Ler arquivo
            df = pd.read_csv(
                csv_file,
                sep=';',
                encoding='latin1',
                header=None,
                dtype=str,
                names=['codigo_municipio', 'nome_municipio']
            )
            
            # Criar tabela se não existir
            cursor = self.conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS municipios")
            cursor.execute("""
                CREATE TABLE municipios (
                    codigo_municipio TEXT PRIMARY KEY,
                    nome_municipio TEXT
                )
            """)
            
            # Inserir dados
            df.to_sql('municipios', self.conn, if_exists='append', index=False)
            self.conn.commit()
            
            logging.info(f"SUCESSO: {len(df):,} municípios importados")
            return True
            
        except Exception as e:
            logging.error(f"Erro ao importar municípios: {e}")
            return True  # Não é crítico

def main():
    """Função principal"""
    print("IMPORTANDO ESTABELECIMENTOS E MUNICIPIOS")
    print("=" * 60)
    
    importer = EstabelecimentosImporter()
    
    # Conectar ao banco
    if not importer.connect_db():
        return False
    
    # Criar tabela
    if not importer.create_estabelecimentos_table():
        return False
    
    # Importar municípios primeiro (mais rápido)
    print("\n1. Importando municípios...")
    importer.import_municipios()
    
    # Importar estabelecimentos (arquivo grande)
    print("\n2. Importando estabelecimentos...")
    print("ATENÇÃO: Este processo pode levar 30-60 minutos devido ao tamanho do arquivo (5.5GB)")
    
    success = importer.import_estabelecimentos()
    
    if success:
        print("\n" + "=" * 60)
        print("IMPORTAÇÃO CONCLUÍDA COM SUCESSO!")
        print("Agora temos dados completos: UF, municípios, CNAEs, endereços!")
        print("=" * 60)
    
    return success

if __name__ == "__main__":
    main()