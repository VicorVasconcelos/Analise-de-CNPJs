import sqlite3
import os
from pathlib import Path

class CNPJDatabase:
    """
    Classe para gerenciar o banco de dados do Sistema CNPJ
    Contém todas as tabelas necessárias para armazenar dados da Receita Federal
    """
    
    def __init__(self, db_path="cnpj_database.db"):
        self.db_path = db_path
        self.connection = None
        
    def connect(self):
        """Conecta ao banco de dados SQLite"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            # Desabilitar chaves estrangeiras temporariamente para importação
            self.connection.execute("PRAGMA foreign_keys = OFF")
            print(f"✅ Conectado ao banco: {self.db_path}")
            return True
        except Exception as e:
            print(f"❌ Erro ao conectar: {e}")
            return False
    
    def disconnect(self):
        """Desconecta do banco de dados"""
        if self.connection:
            self.connection.close()
            print("🔌 Desconectado do banco")
    
    def create_tables(self):
        """Cria todas as tabelas necessárias do sistema CNPJ"""
        print("🏗️  CRIANDO ESTRUTURA DO BANCO DE DADOS")
        print("=" * 60)
        
        if not self.connection:
            print("❌ Não conectado ao banco")
            return False
        
        try:
            cursor = self.connection.cursor()
            
            # 1. TABELA EMPRESAS (1.7GB)
            print("📊 Criando tabela: empresas")
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
            
            # 2. TABELA ESTABELECIMENTOS (5.4GB - Principal)
            print("📊 Criando tabela: estabelecimentos")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS estabelecimentos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cnpj_basico TEXT NOT NULL,
                    cnpj_ordem TEXT NOT NULL,
                    cnpj_dv TEXT NOT NULL,
                    matriz_filial TEXT,
                    nome_fantasia TEXT,
                    situacao TEXT,
                    data_situacao TEXT,
                    motivo_situacao TEXT,
                    nome_cidade_exterior TEXT,
                    pais TEXT,
                    data_inicio TEXT,
                    cnae_principal TEXT,
                    cnae_secundario TEXT,
                    tipo_logradouro TEXT,
                    logradouro TEXT,
                    numero TEXT,
                    complemento TEXT,
                    bairro TEXT,
                    cep TEXT,
                    uf TEXT,
                    municipio TEXT,
                    ddd1 TEXT,
                    telefone1 TEXT,
                    ddd2 TEXT,
                    telefone2 TEXT,
                    fax_ddd TEXT,
                    fax_numero TEXT,
                    email TEXT,
                    situacao_especial TEXT,
                    data_situacao_especial TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cnpj_basico) REFERENCES empresas(cnpj_basico)
                )
            """)
            
            # 3. TABELA SIMPLES (2.6GB)
            print("📊 Criando tabela: simples")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS simples (
                    cnpj_basico TEXT PRIMARY KEY,
                    opcao_simples TEXT,
                    data_opcao_simples TEXT,
                    data_exclusao_simples TEXT,
                    opcao_mei TEXT,
                    data_opcao_mei TEXT,
                    data_exclusao_mei TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cnpj_basico) REFERENCES empresas(cnpj_basico)
                )
            """)
            
            # 4. TABELA CNAES (88KB - Referência)
            print("📊 Criando tabela: cnaes")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cnaes (
                    codigo_cnae TEXT PRIMARY KEY,
                    descricao_cnae TEXT NOT NULL
                )
            """)
            
            # 5. TABELA MUNICÍPIOS (120KB - Referência)
            print("📊 Criando tabela: municipios")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS municipios (
                    codigo_municipio TEXT PRIMARY KEY,
                    nome_municipio TEXT NOT NULL
                )
            """)
            
            # 6. TABELA NATUREZAS JURÍDICAS (4KB - Referência)
            print("📊 Criando tabela: naturezas")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS naturezas (
                    codigo_natureza TEXT PRIMARY KEY,
                    descricao_natureza TEXT NOT NULL
                )
            """)
            
            # 7. TABELA MOTIVOS (3KB - Referência)
            print("📊 Criando tabela: motivos")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS motivos (
                    codigo_motivo TEXT PRIMARY KEY,
                    descricao_motivo TEXT NOT NULL
                )
            """)
            
            # 8. TABELA PAÍSES (5KB - Referência)
            print("📊 Criando tabela: paises")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paises (
                    codigo_pais TEXT PRIMARY KEY,
                    nome_pais TEXT NOT NULL
                )
            """)
            
            # 9. TABELA QUALIFICAÇÕES (2KB - Referência)
            print("📊 Criando tabela: qualificacoes")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS qualificacoes (
                    codigo_qualificacao TEXT PRIMARY KEY,
                    descricao_qualificacao TEXT NOT NULL
                )
            """)
            
            # 10. TABELA SÓCIOS (Grande - Relacionamentos)
            print("📊 Criando tabela: socios")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS socios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cnpj_basico TEXT NOT NULL,
                    identificador_socio TEXT,
                    nome_socio TEXT,
                    cnpj_cpf_socio TEXT,
                    qualificacao_socio TEXT,
                    data_entrada_sociedade TEXT,
                    pais TEXT,
                    representante_legal TEXT,
                    nome_representante TEXT,
                    qualificacao_representante TEXT,
                    faixa_etaria TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cnpj_basico) REFERENCES empresas(cnpj_basico)
                )
            """)
            
            # CRIAR ÍNDICES PARA PERFORMANCE
            print("\n🚀 Criando índices para otimização...")
            
            # Índices principais para filtros
            indices = [
                "CREATE INDEX IF NOT EXISTS idx_estabelecimentos_uf ON estabelecimentos(uf)",
                "CREATE INDEX IF NOT EXISTS idx_estabelecimentos_municipio ON estabelecimentos(municipio)",
                "CREATE INDEX IF NOT EXISTS idx_estabelecimentos_cnae ON estabelecimentos(cnae_principal)",
                "CREATE INDEX IF NOT EXISTS idx_estabelecimentos_bairro ON estabelecimentos(bairro)",
                "CREATE INDEX IF NOT EXISTS idx_estabelecimentos_situacao ON estabelecimentos(situacao)",
                "CREATE INDEX IF NOT EXISTS idx_estabelecimentos_matriz_filial ON estabelecimentos(matriz_filial)",
                "CREATE INDEX IF NOT EXISTS idx_empresas_natureza ON empresas(natureza_juridica)",
                "CREATE INDEX IF NOT EXISTS idx_empresas_porte ON empresas(porte)",
                "CREATE INDEX IF NOT EXISTS idx_simples_opcao ON simples(opcao_simples)",
                "CREATE INDEX IF NOT EXISTS idx_simples_mei ON simples(opcao_mei)",
                "CREATE INDEX IF NOT EXISTS idx_socios_cnpj_basico ON socios(cnpj_basico)",
                "CREATE INDEX IF NOT EXISTS idx_socios_qualificacao ON socios(qualificacao_socio)"
            ]
            
            for i, sql in enumerate(indices, 1):
                cursor.execute(sql)
                print(f"   ✅ Índice {i}/10 criado")
            
            self.connection.commit()
            print(f"\n✅ SUCESSO! Banco de dados criado com 10 tabelas e 12 índices")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao criar tabelas: {e}")
            self.connection.rollback()
            return False
    
    def get_table_info(self):
        """Retorna informações sobre as tabelas criadas"""
        if not self.connection:
            return None
        
        cursor = self.connection.cursor()
        
        # Listar todas as tabelas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tabelas = cursor.fetchall()
        
        print("\n📋 TABELAS CRIADAS:")
        for i, (tabela,) in enumerate(tabelas, 1):
            if tabela != 'sqlite_sequence':
                # Contar registros (será 0 no início)
                cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
                count = cursor.fetchone()[0]
                print(f"   {i}. {tabela:<20} - {count:,} registros")
        
        return tabelas
    
    def clear_database(self):
        """Remove todas as tabelas (usar com cuidado!)"""
        if not self.connection:
            print("❌ Não conectado ao banco")
            return False
        
        print("⚠️  REMOVENDO TODAS AS TABELAS...")
        cursor = self.connection.cursor()
        
        # Listar tabelas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tabelas = cursor.fetchall()
        
        # Remover cada tabela
        for (tabela,) in tabelas:
            if tabela != 'sqlite_sequence':
                cursor.execute(f"DROP TABLE IF EXISTS {tabela}")
                print(f"   🗑️  Tabela {tabela} removida")
        
        self.connection.commit()
        print("✅ Banco limpo!")
        return True

def main():
    """Função principal para criar o banco de dados"""
    print("🚀 INICIANDO CRIAÇÃO DO BANCO DE DADOS CNPJ")
    print("=" * 60)
    
    # Verificar se já existe
    db_path = "cnpj_database.db"
    if os.path.exists(db_path):
        print(f"⚠️  Banco {db_path} já existe!")
        resposta = input("Deseja recriar? (s/n): ").lower()
        if resposta == 's':
            os.remove(db_path)
            print("🗑️  Banco anterior removido")
        else:
            print("⏹️  Operação cancelada")
            return
    
    # Criar banco
    db = CNPJDatabase(db_path)
    
    if db.connect():
        if db.create_tables():
            db.get_table_info()
            print(f"\n🎉 BANCO PRONTO PARA IMPORTAÇÃO DOS DADOS!")
            print(f"📁 Localização: {Path(db_path).absolute()}")
        db.disconnect()
    else:
        print("❌ Falha na criação do banco")

if __name__ == "__main__":
    main()