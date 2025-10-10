import os
import zipfile
import csv
import sqlite3
from io import TextIOWrapper
import time

class ImportadorEstabelecimentosCompleto:
    def __init__(self):
        self.db_path = 'cnpj_database.db'
        self.projeto_path = r"C:\Users\victor.vasconcelos\Documents\PROJETO CNPJ"
        self.zip_path = os.path.join(self.projeto_path, "Estabelecimentos0.zip")
        
    def conectar_db(self):
        """Conectar ao banco SQLite"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
    def criar_tabela_completa(self):
        """Criar tabela para estabelecimentos completos"""
        print("🏗️ Criando tabela estabelecimentos_completos...")
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS estabelecimentos_completos (
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
        print("📊 Criando índices...")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_est_comp_cnpj_basico ON estabelecimentos_completos(cnpj_basico)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_est_comp_uf ON estabelecimentos_completos(uf)")
        
        self.conn.commit()
        print("✅ Tabela estabelecimentos_completos criada com sucesso!")
        
    def verificar_existencia(self):
        """Verificar se já temos dados na tabela"""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM estabelecimentos_completos")
            count = self.cursor.fetchone()[0]
            return count
        except sqlite3.OperationalError:
            # Tabela não existe ainda
            return 0
        
    def importar_estabelecimentos(self):
        """Importar todos os estabelecimentos do arquivo ZIP"""
        print(f"📁 Abrindo arquivo: {self.zip_path}")
        
        if not os.path.exists(self.zip_path):
            print(f"❌ Arquivo não encontrado: {self.zip_path}")
            return False
            
        total_importados = 0
        total_com_uf = 0
        batch_size = 10000
        batch_data = []
        
        try:
            with zipfile.ZipFile(self.zip_path, 'r') as zip_file:
                arquivo = zip_file.namelist()[0]
                print(f"📄 Processando: {arquivo}")
                
                with zip_file.open(arquivo) as csv_file:
                    text_file = TextIOWrapper(csv_file, encoding='latin-1')
                    reader = csv.reader(text_file, delimiter=';')
                    
                    inicio = time.time()
                    
                    for i, linha in enumerate(reader):
                        if len(linha) >= 30:  # Garantir que temos todas as colunas
                            # Preparar dados para inserção
                            dados = [
                                linha[0],   # cnpj_basico
                                linha[1],   # cnpj_ordem
                                linha[2],   # cnpj_dv
                                linha[3],   # identificador_matriz_filial
                                linha[4],   # nome_fantasia
                                linha[5],   # situacao_cadastral
                                linha[6],   # data_situacao_cadastral
                                linha[7],   # motivo_situacao_cadastral
                                linha[8],   # nome_cidade_exterior
                                linha[9],   # pais
                                linha[10],  # data_inicio_atividade
                                linha[11],  # cnae_fiscal_principal
                                linha[12],  # cnae_fiscal_secundaria
                                linha[13],  # tipo_logradouro
                                linha[14],  # logradouro
                                linha[15],  # numero
                                linha[16],  # complemento
                                linha[17],  # bairro
                                linha[18],  # cep
                                linha[19],  # uf
                                linha[20],  # municipio
                                linha[21],  # ddd_1
                                linha[22],  # telefone_1
                                linha[23],  # ddd_2
                                linha[24],  # telefone_2
                                linha[25],  # ddd_fax
                                linha[26],  # fax
                                linha[27],  # correio_eletronico
                                linha[28],  # situacao_especial
                                linha[29],  # data_situacao_especial
                            ]
                            
                            batch_data.append(dados)
                            total_importados += 1
                            
                            # Contar UFs válidas
                            if linha[19] and len(linha[19].strip()) == 2:
                                total_com_uf += 1
                            
                            # Inserir em lotes
                            if len(batch_data) >= batch_size:
                                self._inserir_batch(batch_data)
                                batch_data = []
                                
                                # Progresso
                                if total_importados % 50000 == 0:
                                    tempo_decorrido = time.time() - inicio
                                    velocidade = total_importados / tempo_decorrido
                                    print(f"   ⚡ {total_importados:,} processados ({velocidade:.0f} reg/seg)")
                    
                    # Inserir último lote
                    if batch_data:
                        self._inserir_batch(batch_data)
                    
                    self.conn.commit()
                    
                    tempo_total = time.time() - inicio
                    print(f"\n🎉 IMPORTAÇÃO CONCLUÍDA!")
                    print(f"   📊 Total importado: {total_importados:,} estabelecimentos")
                    print(f"   🗺️ Com UF válida: {total_com_uf:,} ({(total_com_uf/total_importados)*100:.1f}%)")
                    print(f"   ⏱️ Tempo total: {tempo_total:.1f} segundos")
                    print(f"   🚀 Velocidade média: {total_importados/tempo_total:.0f} registros/segundo")
                    
                    return True
                    
        except Exception as e:
            print(f"❌ Erro durante importação: {e}")
            self.conn.rollback()
            return False
    
    def _inserir_batch(self, batch_data):
        """Inserir um lote de dados"""
        self.cursor.executemany("""
            INSERT INTO estabelecimentos_completos (
                cnpj_basico, cnpj_ordem, cnpj_dv, identificador_matriz_filial,
                nome_fantasia, situacao_cadastral, data_situacao_cadastral,
                motivo_situacao_cadastral, nome_cidade_exterior, pais,
                data_inicio_atividade, cnae_fiscal_principal, cnae_fiscal_secundaria,
                tipo_logradouro, logradouro, numero, complemento, bairro, cep,
                uf, municipio, ddd_1, telefone_1, ddd_2, telefone_2, ddd_fax,
                fax, correio_eletronico, situacao_especial, data_situacao_especial
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, batch_data)
    
    def verificar_resultados(self):
        """Verificar resultados da importação"""
        print("\n📈 VERIFICANDO RESULTADOS:")
        
        # Total geral
        self.cursor.execute("SELECT COUNT(*) FROM estabelecimentos_completos")
        total = self.cursor.fetchone()[0]
        print(f"   Total estabelecimentos: {total:,}")
        
        # Por UF
        self.cursor.execute("""
            SELECT uf, COUNT(*) as total, COUNT(DISTINCT cnpj_basico) as empresas_distintas
            FROM estabelecimentos_completos 
            WHERE uf IS NOT NULL AND uf != ''
            GROUP BY uf 
            ORDER BY total DESC
            LIMIT 10
        """)
        
        print(f"   Top 10 UFs:")
        for uf, estabelecimentos, empresas in self.cursor.fetchall():
            print(f"     {uf}: {estabelecimentos:,} estabelecimentos ({empresas:,} empresas)")
    
    def executar(self):
        """Executar importação completa"""
        print("🚀 INICIANDO IMPORTAÇÃO COMPLETA DE ESTABELECIMENTOS")
        print("=" * 60)
        
        self.conectar_db()
        
        # Verificar se já existe
        count_existente = self.verificar_existencia()
        if count_existente > 0:
            print(f"⚠️ Tabela já contém {count_existente:,} registros")
            resposta = input("Deseja recriar a tabela? (s/N): ").lower()
            if resposta == 's':
                self.cursor.execute("DROP TABLE IF EXISTS estabelecimentos_completos")
                self.conn.commit()
            else:
                print("❌ Importação cancelada")
                return
        
        self.criar_tabela_completa()
        
        if self.importar_estabelecimentos():
            self.verificar_resultados()
            print("\n✅ Importação concluída com sucesso!")
        else:
            print("\n❌ Falha na importação")
        
        self.conn.close()

if __name__ == "__main__":
    importador = ImportadorEstabelecimentosCompleto()
    importador.executar()