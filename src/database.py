import sqlite3
import os
from pathlib import Path

class CNPJDatabase:
    """
    Classe para gerenciar o banco de dados do Sistema CNPJ
    Contém todas as tabelas necessárias para armazenar dados da Receita Federal
    """

    def __init__(self, db_path="data/cnpj_database.db"):
        self.db_path = db_path
        self.connection = None

    def connect(self):
        """Conecta ao banco de dados SQLite"""
        try:
            # Conectar com timeout e permitir uso de objetos em múltiplas threads
            self.connection = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
            # Performance pragmas: journaling WAL, menor sync e cache em memória
            try:
                self.connection.execute("PRAGMA journal_mode = WAL")
                self.connection.execute("PRAGMA synchronous = NORMAL")
                self.connection.execute("PRAGMA temp_store = MEMORY")
                # cache_size em páginas (p.ex. 100k) - ajuste conforme memória disponível
                self.connection.execute("PRAGMA cache_size = 100000")
            except Exception:
                # Alguns pragmas podem não estar disponíveis em builds específicos; ignorar falhas
                pass
            # Desabilitar chaves estrangeiras temporariamente para importação
            self.connection.execute("PRAGMA foreign_keys = OFF")
            print(f"OK - Conectado ao banco: {self.db_path}")
            return True
        except Exception as e:
            print(f"ERRO - Erro ao conectar: {e}")
            return False

    def disconnect(self):
        """Desconecta do banco de dados"""
        if self.connection:
            self.connection.close()
            print("Desconectado do banco")

    def create_tables(self):
        """Cria todas as tabelas necessárias do sistema CNPJ"""
        print("CRIANDO ESTRUTURA DO BANCO DE DADOS")
        print("=" * 60)

        if not self.connection:
            print("ERRO - Nao conectado ao banco")
            return False

        try:
            cursor = self.connection.cursor()

            # 1. TABELA EMPRESAS
            print("Criando tabela: empresas")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS empresas (
                    cnpj_basico TEXT PRIMARY KEY,
                    razao_social TEXT,
                    natureza_juridica TEXT,
                    porte TEXT,
                    capital_social TEXT,
                    ente_federativo TEXT,
                    campo7 TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. TABELA ESTABELECIMENTOS
            print("Criando tabela: estabelecimentos")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS estabelecimentos (
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (cnpj_basico, cnpj_ordem, cnpj_dv)
                )
            """)

            # 3. TABELA SOCIOS
            print("Criando tabela: socios")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS socios (
                    cnpj_basico TEXT,
                    identificador_socio TEXT,
                    nome_socio TEXT,
                    cpf_cnpj_socio TEXT,
                    qualificacao_socio TEXT,
                    data_entrada_sociedade TEXT,
                    pais TEXT,
                    representante_legal TEXT,
                    nome_representante TEXT,
                    qualificacao_representante TEXT,
                    faixa_etaria TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 4. TABELA CNAES
            print("Criando tabela: cnaes")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cnaes (
                    codigo_cnae TEXT PRIMARY KEY,
                    descricao_cnae TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 5. TABELA MUNICIPIOS
            print("Criando tabela: municipios")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS municipios (
                    codigo_municipio TEXT PRIMARY KEY,
                    nome_municipio TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 6. TABELA NATUREZAS
            print("Criando tabela: naturezas")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS naturezas (
                    codigo_natureza TEXT PRIMARY KEY,
                    descricao_natureza TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 7. TABELA QUALIFICACOES
            print("Criando tabela: qualificacoes")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS qualificacoes (
                    codigo_qualificacao TEXT PRIMARY KEY,
                    descricao_qualificacao TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 8. TABELA PAISES
            print("Criando tabela: paises")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paises (
                    codigo_pais TEXT PRIMARY KEY,
                    nome_pais TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 9. TABELA MOTIVOS
            print("Criando tabela: motivos")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS motivos (
                    codigo_motivo TEXT PRIMARY KEY,
                    descricao_motivo TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 10. TABELA SIMPLES
            print("Criando tabela: simples")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS simples (
                    cnpj_basico TEXT PRIMARY KEY,
                    opcao_simples TEXT,
                    data_opcao_simples TEXT,
                    data_exclusao_simples TEXT,
                    opcao_mei TEXT,
                    data_opcao_mei TEXT,
                    data_exclusao_mei TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ÍNDICES PARA MELHOR PERFORMANCE
            print("\nCriando índices...")
            
            # Índices para estabelecimentos
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_estabelecimentos_cnpj_basico ON estabelecimentos(cnpj_basico)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_estabelecimentos_uf ON estabelecimentos(uf)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_estabelecimentos_municipio ON estabelecimentos(municipio)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_estabelecimentos_cnae ON estabelecimentos(cnae_fiscal_principal)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_estabelecimentos_situacao ON estabelecimentos(situacao_cadastral)")
            
            # Índices para empresas
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_empresas_natureza ON empresas(natureza_juridica)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_empresas_porte ON empresas(porte)")
            
            # Índices para sócios
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_socios_cnpj_basico ON socios(cnpj_basico)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_socios_cpf_cnpj ON socios(cpf_cnpj_socio)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_socios_nome ON socios(nome_socio)")
            
            # Índice para simples
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_simples_opcao_simples ON simples(opcao_simples)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_simples_opcao_mei ON simples(opcao_mei)")

            self.connection.commit()
            print(f"\n✅ SUCESSO! Banco de dados criado com 10 tabelas e 12 índices")
            return True
        except Exception as e:
            print(f"❌ Erro ao criar tabelas: {e}")
            self.connection.rollback()
            return False
