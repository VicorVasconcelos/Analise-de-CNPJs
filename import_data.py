import pandas as pd
import sqlite3
import os
from pathlib import Path
import time
from database import CNPJDatabase
import argparse
import json
import glob
import re

class CNPJImporter:
    """
    Classe para importar dados dos CSVs da Receita Federal para o banco de dados
    Processa arquivos grandes em chunks para otimizar memória
    """
    
    def __init__(self, db_path="cnpj_database.db", data_dir=r"c:\Users\victor.vasconcelos\Documents\Projeto CNPJ"):
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
            'EMPRESAS': 'empresas',
            'ESTABELECIMENTOS': 'estabelecimentos', 
            'SIMPLES': 'simples',
            'CNAES': 'cnaes',
            'MUNICIPIOS': 'municipios',
            'NATUREZAS': 'naturezas',
            'MOTIVOS': 'motivos',
            'PAISES': 'paises',
            'QUALIFICACOES': 'qualificacoes',
            'SOCIOS': 'socios'
        }

        # discover available subfolders (case-insensitive, allow variants like 'Empresas0')
        existing_dirs = {d.name: d for d in self.data_dir.iterdir() if d.is_dir()} if self.data_dir.exists() else {}

        for pasta, tabela in mapeamento_pastas.items():
            # try exact match first (case-insensitive), then prefix/contains
            pasta_match = None
            for name, path in existing_dirs.items():
                if name.lower() == pasta.lower():
                    pasta_match = path
                    break
            if not pasta_match:
                for name, path in existing_dirs.items():
                    if name.lower().startswith(pasta.lower()) or pasta.lower() in name.lower():
                        pasta_match = path
                        break

            if pasta_match and pasta_match.exists():
                # Procurar arquivos CSV na pasta
                csv_files = list(pasta_match.glob("*.csv"))
                if csv_files:
                    arquivos_info = []
                    total_mb = 0.0
                    for arquivo in csv_files:
                        tamanho_mb = arquivo.stat().st_size / (1024*1024)
                        arquivos_info.append({'arquivo': arquivo, 'tamanho_mb': tamanho_mb})
                        total_mb += tamanho_mb
                    arquivos_encontrados[tabela] = {
                        'arquivos': arquivos_info,
                        'total_mb': total_mb,
                        'count': len(arquivos_info)
                    }
                    print(f"   ✅ {tabela:<20} - {len(arquivos_info)} arquivo(s) ({total_mb:.1f} MB) - pasta: {pasta_match.name}")
                else:
                    print(f"   ❌ {tabela:<20} - Nenhum CSV encontrado em {pasta_match.name}")
            else:
                print(f"   ⚠️  {tabela:<20} - Pasta não encontrada: {pasta} (nenhuma correspondência em {self.data_dir})")

        return arquivos_encontrados

    def import_table_reference(self, tabela, arquivo_info):
        """Importa tabelas de referência pequenas (completas)"""
        # arquivo_info may contain multiple files under 'arquivos'
        arquivos = arquivo_info.get('arquivos') if isinstance(arquivo_info, dict) else None
        if arquivos:
            arquivo_names = [a['arquivo'].name for a in arquivos]
            tamanho_mb = arquivo_info.get('total_mb', 0.0)
            print(f"   📁 Arquivos: {', '.join(arquivo_names)}")
        else:
            arquivo = arquivo_info.get('arquivo') if isinstance(arquivo_info, dict) else None
            tamanho_mb = arquivo_info.get('tamanho_mb', 0) if isinstance(arquivo_info, dict) else 0
        
        print(f"\n📥 IMPORTANDO: {tabela.upper()}")
        if arquivos:
            names = ', '.join([str(a['arquivo'].name) for a in arquivos])
            print(f"   📁 Arquivos: {names}")
        else:
            fname = arquivo.name if arquivo is not None else '<unknown>'
            print(f"   📁 Arquivo: {fname}")
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
            
            # Carregar e inserir todos os arquivos (se houver mais de um)
            total_loaded = 0
            if not self.db.connect():
                print(f"   ❌ Erro ao conectar com banco")
                return False
            cursor = self.db.connection.cursor()
            placeholders = ','.join(['?' for _ in colunas])
            sql = f"INSERT OR REPLACE INTO {tabela} ({','.join(colunas)}) VALUES ({placeholders})"

            def process_file(file_path, enc='latin-1'):
                nonlocal total_loaded
                try:
                    df = pd.read_csv(file_path, sep=';', encoding=enc, names=colunas)
                except Exception:
                    df = pd.read_csv(file_path, sep=None, engine='python', encoding=enc, names=colunas)
                df = df.fillna('')
                dados = df.values.tolist()
                if dados:
                    cursor.executemany(sql, dados)
                    self.db.connection.commit()
                    total_loaded += len(dados)
                    print(f"   📊 {len(dados):,} registros inseridos de {os.path.basename(file_path)}")

            if arquivos:
                for a in arquivos:
                    process_file(a['arquivo'])
            else:
                process_file(arquivo)

            print(f"   ✅ TOTAL: {total_loaded:,} registros inseridos em {tabela}!")
            self.db.disconnect()
            return True
                
        except Exception as e:
            print(f"   ❌ Erro na importação: {e}")
            return False

    def import_table_large(self, tabela, arquivo_info):
        """Importa tabelas grandes em chunks"""
        arquivos = arquivo_info.get('arquivos') if isinstance(arquivo_info, dict) else None
        arquivo = arquivo_info.get('arquivo') if isinstance(arquivo_info, dict) else None
        tamanho_mb = arquivo_info.get('total_mb', 0) if isinstance(arquivo_info, dict) else arquivo_info.get('tamanho_mb', 0)

        arquivo_label = ','.join([a['arquivo'].name for a in arquivos]) if arquivos else (arquivo.name if arquivo is not None else '<external or not provided>')

        print(f"\n📥 IMPORTANDO (CHUNKS): {tabela.upper()}")
        print(f"   📁 Arquivo: {arquivo_label}")
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
                          'opcao_mei', 'data_opcao_mei', 'data_exclusao_mei'],
                'socios': ['cnpj_basico', 'identificador_socio', 'nome_socio', 'cnpj_cpf_socio', 
                         'qualificacao_socio', 'data_entrada_sociedade', 'pais', 'representante_legal',
                         'nome_representante', 'qualificacao_representante', 'faixa_etaria']
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
            
            # Special-case: importar sócios a partir de pasta externa (se existir)
            if tabela == 'socios':
                # if there's a local socios folder in data_dir, use it, else external
                local_socios = self.data_dir / 'SOCIOS'
                external_folder = r"C:\Users\victor.vasconcelos\Documents\PROJETO CNPJ\Socios0"
                if local_socios.exists():
                    return self.import_socios_from_folder(str(local_socios))
                if os.path.exists(external_folder):
                    return self.import_socios_from_folder(external_folder)

            # Processar arquivo(s) em chunks (default behavior)
            total_inseridos = 0
            chunk_num = 0
            inicio = time.time()
            def process_csv_path(path_obj):
                nonlocal total_inseridos, chunk_num
                path = path_obj if isinstance(path_obj, str) else str(path_obj)
                try:
                    for chunk_df in pd.read_csv(path, sep=';', encoding='latin-1', names=colunas, chunksize=self.chunk_size):
                        chunk_num += 1
                        chunk_df = chunk_df.fillna('')
                        dados = chunk_df.values.tolist()
                        cursor.executemany(sql, dados)
                        self.db.connection.commit()
                        total_inseridos += len(dados)
                        tempo_decorrido = time.time() - inicio
                        taxa = total_inseridos / tempo_decorrido if tempo_decorrido > 0 else 0
                        print(f"   📊 Chunk {chunk_num}: {len(dados):,} registros | Total: {total_inseridos:,} | Taxa: {taxa:.0f} reg/s")
                except Exception as e:
                    # try flexible read if strict CSV parsing fails
                    try:
                        df = pd.read_csv(path, sep=None, engine='python', encoding='latin-1')
                        df = df.fillna('')
                        dados = df.values.tolist()
                        if dados:
                            cursor.executemany(sql, dados)
                            self.db.connection.commit()
                            total_inseridos += len(dados)
                    except Exception as e2:
                        print('   ❌ Falha ao processar', path, 'erro:', e)

            if arquivos:
                for a in arquivos:
                    process_csv_path(a['arquivo'])
            else:
                process_csv_path(arquivo)

            # ensure tempo_decorrido is defined even if no chunks were processed or an exception occurred
            try:
                tempo_decorrido
            except NameError:
                tempo_decorrido = time.time() - inicio

            print(f"   ✅ CONCLUÍDO! {total_inseridos:,} registros inseridos em {tempo_decorrido:.1f}s")
            self.db.disconnect()
            return True
            
        except Exception as e:
            print(f"   ❌ Erro na importação: {e}")
            if self.db.connection:
                self.db.disconnect()
            return False

    def import_all(self, selected_tables=None):
        """Importa todos os arquivos CSV para o banco"""
        print("🚀 INICIANDO IMPORTAÇÃO COMPLETA DOS DADOS CNPJ")
        print("=" * 60)
        
        # Localizar arquivos
        arquivos = self.find_csv_files()
        
        if not arquivos:
            # If user requested only socios, allow proceeding because socios can be imported
            # from an external folder even if data_dir CSVs are missing.
            if selected_tables is not None:
                sel = set([s.strip().lower() for s in selected_tables])
                if 'socios' in sel:
                    print("⚠️ Nenhum arquivo CSV nas pastas padrão, mas prosseguindo pois --only socios foi solicitado.")
                else:
                    print("❌ Nenhum arquivo CSV encontrado!")
                    return False
            else:
                print("❌ Nenhum arquivo CSV encontrado!")
                return False
        
        print(f"\n📋 ENCONTRADOS {len(arquivos)} ARQUIVOS PARA IMPORTAR")
        
        # Separate tables by size
        tabelas_pequenas = ['cnaes', 'municipios', 'naturezas', 'motivos', 'paises', 'qualificacoes']
        tabelas_grandes = ['empresas', 'estabelecimentos', 'simples', 'socios']
        
        sucesso_total = True
        
        # 1. Importar tabelas de referência primeiro (pequenas)
        print(f"\n🏷️  FASE 1: IMPORTANDO TABELAS DE REFERÊNCIA")
        print("-" * 50)
        
        # If selected_tables provided, filter which to run
        if selected_tables is not None:
            # Normalize to set
            sel = set([s.strip().lower() for s in selected_tables])
        else:
            sel = None

        for tabela in tabelas_pequenas:
            if sel is not None and tabela not in sel:
                print(f"   ⏭️ Pulando {tabela} (não selecionado)")
                continue
            if tabela in arquivos:
                sucesso = self.import_table_reference(tabela, arquivos[tabela])
                if not sucesso:
                    sucesso_total = False
                    print(f"⚠️  Falha na importação de {tabela}")
            else:
                print(f"   ⚠️  Arquivo para {tabela} não encontrado, pulando")
        
        # 2. Importar tabelas grandes
        print(f"\n📊 FASE 2: IMPORTANDO TABELAS PRINCIPAIS (GRANDES)")
        print("-" * 50)
        
        for tabela in tabelas_grandes:
            if sel is not None and tabela not in sel:
                print(f"   ⏭️ Pulando {tabela} (não selecionado)")
                continue
            if tabela in arquivos:
                sucesso = self.import_table_large(tabela, arquivos[tabela])
                if not sucesso:
                    sucesso_total = False
                    print(f"⚠️  Falha na importação de {tabela}")
            else:
                # allow socios to be imported from external folder even if not present in arquivos
                if tabela == 'socios':
                    sucesso = self.import_table_large(tabela, {'arquivo': None, 'tamanho_mb': 0})
                    if not sucesso:
                        sucesso_total = False
                        print(f"⚠️  Falha na importação de {tabela}")
                else:
                    print(f"   ⚠️  Arquivo para {tabela} não encontrado, pulando")
        
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

    def import_socios_from_folder(self, folder_path):
        """Importa arquivos de sócios de uma pasta externa e grava progresso em import_progress.json"""
        progress_path = Path('import_progress.json')
        out = {'folder': folder_path, 'files_processed': [], 'total_read': 0, 'total_inserted': 0}

        files = glob.glob(os.path.join(folder_path, '*.csv'))
        if not files:
            out['error'] = 'no_files_found'
            with open(progress_path, 'w', encoding='utf-8') as fh:
                json.dump(out, fh, ensure_ascii=False, indent=2)
            print(json.dumps(out, ensure_ascii=False))
            return False

        # connect to DB
        if not self.db.connect():
            out['error'] = 'db_connect_failed'
            with open(progress_path, 'w', encoding='utf-8') as fh:
                json.dump(out, fh, ensure_ascii=False, indent=2)
            print(json.dumps(out, ensure_ascii=False))
            return False

        cur = self.db.connection.cursor()
        # ensure table exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='socios'")
        if not cur.fetchone():
            cur.execute('''CREATE TABLE socios (
                cnpj_basico TEXT,
                cnpj_completo TEXT,
                nome_socio TEXT,
                cnpj_cpf_socio TEXT,
                qualificacao_socio TEXT
            )''')
            self.db.connection.commit()
        else:
            # ensure cnpj_completo column exists; SQLite doesn't have IF NOT EXISTS for ADD COLUMN
            cols = [row[1] for row in cur.execute("PRAGMA table_info(socios)")]
            if 'cnpj_completo' not in cols:
                try:
                    cur.execute('ALTER TABLE socios ADD COLUMN cnpj_completo TEXT')
                    self.db.connection.commit()
                except Exception:
                    # ignore if cannot add (older schema mismatch) and continue
                    pass
            self.db.connection.commit()

        # re-fetch current columns to build dynamic insert SQL and dedupe key
        db_cols = [row[1] for row in cur.execute("PRAGMA table_info(socios)")]
        # canonical desired columns (in preferred order)
        desired_cols = ['cnpj_basico','cnpj_completo','identificador_socio','nome_socio','cnpj_cpf_socio','qualificacao_socio','data_entrada_sociedade','pais','representante_legal','nome_representante','qualificacao_representante','faixa_etaria']
        insert_cols = [c for c in desired_cols if c in db_cols]
        if not insert_cols:
            # minimal fallback
            insert_cols = [c for c in ['cnpj_basico','cnpj_completo','nome_socio','cnpj_cpf_socio','qualificacao_socio'] if c in db_cols]
        placeholders = ','.join(['?' for _ in insert_cols])
        insert_sql = f"INSERT OR REPLACE INTO socios ({','.join(insert_cols)}) VALUES ({placeholders})"

        # fetch existing for dedupe using present key columns
        key_cols = ['cnpj_basico','nome_socio','cnpj_cpf_socio']
        present_key_cols = [c for c in key_cols if c in db_cols]
        if present_key_cols:
            sel = ','.join(present_key_cols)
            cur.execute(f"SELECT {sel} FROM socios")
            existing = set(cur.fetchall())
        else:
            existing = set()

        for fpath in files:
            filename = os.path.basename(fpath)
            try:
                # Try to detect encoding/delimiter using pandas/sniffer
                encs = ['latin-1', 'cp1252', 'utf-8-sig', 'utf-8']
                detected_enc = None
                detected_sep = None
                sample = ''
                for enc in encs:
                    try:
                        with open(fpath, 'r', encoding=enc, errors='replace') as fh:
                            sample = fh.read(8192)
                        detected_enc = enc
                        break
                    except Exception:
                        continue

                if sample:
                    # simple delimiter guess
                    for d in [';', ',', '\t', '|']:
                        if d in sample:
                            detected_sep = d
                            break

                # read with pandas in chunks
                if detected_sep:
                    it = pd.read_csv(fpath, sep=detected_sep, encoding=detected_enc, dtype=str, keep_default_na=False, chunksize=5000)
                else:
                    it = pd.read_csv(fpath, sep=None, engine='python', encoding=detected_enc or 'latin-1', dtype=str, keep_default_na=False, chunksize=5000)

                rows_read_file = 0
                rows_inserted_file = 0
                try:
                    # process each pandas chunk as it arrives
                    first_chunk = True
                    for df in it:
                        cols = list(df.columns)

                        # infer columns once using the first chunk's header
                        if first_chunk:
                            low = [c.lower() for c in cols]
                            def pick(preds):
                                for i,c in enumerate(low):
                                    for p in preds:
                                        if p in c:
                                            return cols[i]
                                return None

                            company = pick(['cnpj', 'empresa', 'cnpj_basico']) or cols[0]
                            nomecol = pick(['nome','socio'])
                            cpfcol = pick(['cpf','cnpj_cpf'])
                            qualcol = pick(['qual','qualificacao'])

                            # Fallback heuristics for headerless or odd files
                            if not nomecol and len(cols) >= 3:
                                nomecol = cols[2]
                            if not cpfcol and len(cols) >= 4:
                                cpfcol = cols[3]

                            # fallback further
                            if not nomecol:
                                for c in cols:
                                    if 'nome' in c.lower() or 'socio' in c.lower():
                                        nomecol = c
                                        break
                            if not cpfcol:
                                for c in cols:
                                    if 'cpf' in c.lower():
                                        cpfcol = c
                                        break
                            if not qualcol:
                                for c in cols:
                                    if 'qual' in c.lower():
                                        qualcol = c
                                        break

                            first_chunk = False

                        # Now process rows in this chunk
                        chunk_rows = []
                        for _, r in df.iterrows():
                            # Get possible CNPJ parts from multiple possible columns
                            cnpj_src = ''
                            if company in df.columns:
                                cnpj_src = r.get(company, '')
                            # try explicit parts
                            cnpj_bas_col = None
                            cnpj_ord_col = None
                            cnpj_dv_col = None
                            for c in cols:
                                lc = c.lower()
                                if 'cnpj_basico' in lc or (lc == 'cnpj' and len(str(r.get(c,'')))<=8):
                                    cnpj_bas_col = c
                                if 'ordem' in lc or 'cnpj_ordem' in lc:
                                    cnpj_ord_col = c
                                if 'dv' in lc or 'cnpj_dv' in lc or lc.endswith('_dv'):
                                    cnpj_dv_col = c

                            if not cnpj_src and cnpj_bas_col and cnpj_bas_col in df.columns:
                                cnpj_src = r.get(cnpj_bas_col, '')

                            nome = r.get(nomecol, '') if nomecol in df.columns else ''
                            cpf = r.get(cpfcol, '') if cpfcol in df.columns else ''
                            qual = r.get(qualcol, '') if qualcol in df.columns else ''
                            # extra optional fields mapping to DB columns (best-effort)
                            data_entrada = r.get('data_entrada_sociedade', '') if 'data_entrada_sociedade' in df.columns else r.get('data_entrada', '') if 'data_entrada' in df.columns else ''
                            identificador = r.get('identificador_socio', '') if 'identificador_socio' in df.columns else r.get('identificador', '') if 'identificador' in df.columns else ''
                            pais_val = r.get('pais', '') if 'pais' in df.columns else ''
                            representante = r.get('representante_legal', '') if 'representante_legal' in df.columns else ''
                            nome_representante = r.get('nome_representante', '') if 'nome_representante' in df.columns else ''
                            qual_rep = r.get('qualificacao_representante', '') if 'qualificacao_representante' in df.columns else ''
                            faixa = r.get('faixa_etaria', '') if 'faixa_etaria' in df.columns else ''

                            # Normalize and extract full CNPJ when possible
                            cnpj_completo = ''
                            cnpj_digits = re.sub(r'\D','',str(cnpj_src))
                            if len(cnpj_digits) >= 14:
                                cnpj_completo = cnpj_digits[:14]
                            else:
                                # try compose from separate columns
                                part_bas = ''
                                part_ord = ''
                                part_dv = ''
                                if cnpj_bas_col and cnpj_bas_col in df.columns:
                                    part_bas = re.sub(r'\D','',str(r.get(cnpj_bas_col, '')))
                                if cnpj_ord_col and cnpj_ord_col in df.columns:
                                    part_ord = re.sub(r'\D','',str(r.get(cnpj_ord_col, '')))
                                if cnpj_dv_col and cnpj_dv_col in df.columns:
                                    part_dv = re.sub(r'\D','',str(r.get(cnpj_dv_col, '')))
                                if part_bas and part_ord and part_dv:
                                    cnpj_completo = (part_bas + part_ord + part_dv)[:14]

                            cnpjb = ''
                            if cnpj_completo and len(cnpj_completo) >= 8:
                                cnpjb = cnpj_completo[:8]
                            else:
                                if len(cnpj_digits) == 8:
                                    cnpjb = cnpj_digits
                                else:
                                    # skip rows where we cannot determine cnpj_basic
                                    continue

                            nome_s = str(nome).strip()
                            cpf_s_raw = str(cpf).strip()
                            if '*' in cpf_s_raw:
                                cpf_s = cpf_s_raw
                            else:
                                cpf_s = re.sub(r'\D','',cpf_s_raw)
                            qual_s = str(qual).strip()

                            # map parsed values to insert_cols order
                            row_map = {
                                'cnpj_basico': cnpjb,
                                'cnpj_completo': cnpj_completo,
                                'identificador_socio': identificador,
                                'nome_socio': nome_s,
                                'cnpj_cpf_socio': cpf_s,
                                'qualificacao_socio': qual_s,
                                'data_entrada_sociedade': data_entrada,
                                'pais': pais_val,
                                'representante_legal': representante,
                                'nome_representante': nome_representante,
                                'qualificacao_representante': qual_rep,
                                'faixa_etaria': faixa
                            }
                            chunk_rows.append(tuple(row_map.get(c, '') for c in insert_cols))

                        # per-chunk bookkeeping and insert
                        rows_read_file += len(chunk_rows)

                        # dedupe for this chunk against existing
                        unique = []
                        seen = set()
                        try:
                            pos_cnpj = insert_cols.index('cnpj_basico')
                            pos_nome = insert_cols.index('nome_socio')
                            pos_cpf = insert_cols.index('cnpj_cpf_socio')
                        except ValueError:
                            pos_cnpj = pos_nome = pos_cpf = None

                        for t in chunk_rows:
                            if pos_cnpj is not None and pos_nome is not None and pos_cpf is not None:
                                key = (t[pos_cnpj], t[pos_nome], t[pos_cpf])
                            else:
                                key = (t[0],)
                            if key in existing or key in seen:
                                continue
                            seen.add(key)
                            unique.append(t)

                        if unique:
                            try:
                                cur.execute('BEGIN')
                                cur.executemany(insert_sql, unique)
                                self.db.connection.commit()
                                inserted = len(unique)
                                rows_inserted_file += inserted
                                out['total_inserted'] += inserted
                                for r in unique:
                                    if pos_cnpj is not None and pos_nome is not None and pos_cpf is not None:
                                        existing.add((r[pos_cnpj], r[pos_nome], r[pos_cpf]))
                                    else:
                                        existing.add((r[0],))
                            except Exception as e:
                                self.db.connection.rollback()
                                out.setdefault('errors', []).append({'file': filename, 'error': str(e)})

                except Exception as e:
                    # pandas chunk iteration failed or hung; fallback to streaming CSV reader
                    out.setdefault('warnings', []).append({'file': filename, 'warning': 'pandas_iter_failed, falling back to csv.reader', 'error': str(e)})
                    # call streaming fallback
                    s_read, s_insert = self._import_socios_csv_stream(fpath, cur, existing, progress_path, insert_cols, insert_sql)
                    rows_read_file += s_read
                    rows_inserted_file += s_insert

                out['files_processed'].append({'file': filename, 'rows_read': rows_read_file, 'rows_inserted': rows_inserted_file})
                out['total_read'] += rows_read_file

                # write progress after each file
                with open(progress_path, 'w', encoding='utf-8') as fh:
                    json.dump(out, fh, ensure_ascii=False, indent=2)

            except Exception as e:
                out.setdefault('errors', []).append({'file': filename, 'error': str(e)})
                with open(progress_path, 'w', encoding='utf-8') as fh:
                    json.dump(out, fh, ensure_ascii=False, indent=2)
                continue

        # close db
        self.db.disconnect()
        print(json.dumps(out, ensure_ascii=False))
        return True

    def _import_socios_csv_stream(self, fpath, cur, existing, progress_path, insert_cols, insert_sql, batch_size=5000):
        """Fallback streaming CSV reader for socios files. Returns (rows_read, rows_inserted)."""
        import csv
        rows_read = 0
        rows_inserted = 0
        batch = []
        filename = os.path.basename(fpath)

        # attempt to detect encoding and delimiter quickly
        encs = ['latin-1', 'cp1252', 'utf-8-sig', 'utf-8']
        detected_enc = None
        detected_sep = None
        sample = ''
        for enc in encs:
            try:
                with open(fpath, 'r', encoding=enc, errors='replace') as fh:
                    sample = fh.read(8192)
                detected_enc = enc
                break
            except Exception:
                continue

        if sample:
            for d in [';', ',', '\t', '|']:
                if d in sample:
                    detected_sep = d
                    break

        # open and stream
        with open(fpath, 'r', encoding=detected_enc or 'latin-1', errors='replace', newline='') as fh:
            if detected_sep:
                reader = csv.DictReader(fh, delimiter=detected_sep)
            else:
                reader = csv.DictReader(fh)

            # infer columns from fieldnames
            cols = reader.fieldnames or []
            low = [c.lower() for c in cols]
            def pick(preds):
                for i,c in enumerate(low):
                    for p in preds:
                        if p in c:
                            return cols[i]
                return None

            company = pick(['cnpj','empresa','cnpj_basico']) or (cols[0] if cols else None)
            nomecol = pick(['nome','socio'])
            cpfcol = pick(['cpf','cnpj_cpf'])
            qualcol = pick(['qual','qualificacao'])

            # Fallback heuristics for headerless files
            if not nomecol and len(cols) >= 3:
                nomecol = cols[2]
            if not cpfcol and len(cols) >= 4:
                cpfcol = cols[3]

            for row in reader:
                cnpj_src = row.get(company, '') if company else ''
                nome = row.get(nomecol, '') if nomecol else ''
                cpf = row.get(cpfcol, '') if cpfcol else ''
                qual = row.get(qualcol, '') if qualcol else ''

                cnpj_digits = re.sub(r'\D','',str(cnpj_src))
                cnpj_completo = ''
                cnpjb = ''
                if len(cnpj_digits) >= 14:
                    cnpj_completo = cnpj_digits[:14]
                    cnpjb = cnpj_completo[:8]
                elif len(cnpj_digits) == 8:
                    cnpjb = cnpj_digits
                else:
                    continue

                nome_s = str(nome).strip()
                cpf_s_raw = str(cpf)
                if '*' in cpf_s_raw:
                    cpf_s = cpf_s_raw
                else:
                    cpf_s = re.sub(r'\D','',cpf_s_raw)
                qual_s = str(qual).strip()

                # optional fields from CSV (best-effort)
                data_entrada = row.get('data_entrada_sociedade', '') or row.get('data_entrada', '')
                identificador = row.get('identificador_socio', '') or row.get('identificador', '')
                pais_val = row.get('pais', '')
                representante = row.get('representante_legal', '')
                nome_representante = row.get('nome_representante', '')
                qual_rep = row.get('qualificacao_representante', '')
                faixa = row.get('faixa_etaria', '')

                # build tuple aligned to insert_cols
                row_map = {
                    'cnpj_basico': cnpjb,
                    'cnpj_completo': cnpj_completo,
                    'identificador_socio': identificador,
                    'nome_socio': nome_s,
                    'cnpj_cpf_socio': cpf_s,
                    'qualificacao_socio': qual_s,
                    'data_entrada_sociedade': data_entrada,
                    'pais': pais_val,
                    'representante_legal': representante,
                    'nome_representante': nome_representante,
                    'qualificacao_representante': qual_rep,
                    'faixa_etaria': faixa
                }
                tup = tuple(row_map.get(c, '') for c in insert_cols)
                # dedupe key using present key columns if available
                try:
                    pos_cnpj = insert_cols.index('cnpj_basico')
                    pos_nome = insert_cols.index('nome_socio')
                    pos_cpf = insert_cols.index('cnpj_cpf_socio')
                    key = (tup[pos_cnpj], tup[pos_nome], tup[pos_cpf])
                except ValueError:
                    key = (tup[0],)
                if key in existing:
                    continue
                batch.append(tup)
                existing.add(key)
                rows_read += 1

                if len(batch) >= batch_size:
                    try:
                        cur.execute('BEGIN')
                        cur.executemany(insert_sql, batch)
                        cur.connection.commit()
                        rows_inserted += len(batch)
                        batch = []
                        # update progress file
                        try:
                            with open(progress_path, 'r', encoding='utf-8') as pf:
                                progress = json.load(pf)
                        except Exception:
                            progress = {'files_processed': []}
                        # naive update: append a checkpoint
                        progress.setdefault('checkpoints', []).append({'file': filename, 'rows_inserted': rows_inserted})
                        with open(progress_path, 'w', encoding='utf-8') as pf:
                            json.dump(progress, pf, ensure_ascii=False, indent=2)
                    except Exception:
                        cur.connection.rollback()
                        # continue

            # flush remaining
            # flush remaining
            if batch:
                    try:
                        cur.execute('BEGIN')
                        cur.executemany(insert_sql, batch)
                        cur.connection.commit()
                        rows_inserted += len(batch)
                    except Exception:
                        cur.connection.rollback()

        return rows_read, rows_inserted

def main():
    """Função principal para executar a importação"""
    print("📥 SISTEMA DE IMPORTAÇÃO DE DADOS CNPJ")
    print("=" * 60)
    
    # Verificar se banco existe
    if not os.path.exists("cnpj_database.db"):
        print("❌ Banco de dados não encontrado!")
        print("💡 Execute primeiro: python database.py")
        return
    
    # CLI options: --all or --only
    parser = argparse.ArgumentParser(description='Importador de dados CNPJ')
    parser.add_argument('--all', action='store_true', help='Importar tudo (padrão)')
    parser.add_argument('--only', type=str, help='Importar somente as tabelas listadas (vírgula separado), ex: --only empresas,socios')
    parser.add_argument('--list', action='store_true', help='Listar arquivos detectados e sair (não importa)')
    parser.add_argument('--data-dir', type=str, help='Diretório raiz dos dados (subpastas EMPRESAS, SOCIOS, etc). Ex: --data-dir "C:\\path\\to\\Projeto CNPJ"')
    args = parser.parse_args()

    # create importer with default data_dir; we may override it with args.data_dir
    importer = CNPJImporter()

    # override data_dir if provided (apply before existence checks)
    if args.data_dir:
        importer.data_dir = Path(args.data_dir)

    # Verificar se diretório de dados existe
    if not importer.data_dir.exists():
        # allow running only socios even if data_dir missing. We may not have 'selected' yet, so
        # inspect sys.argv to see if user requested --only socios
        import sys
        proceed = False
        if '--only' in sys.argv:
            try:
                idx = sys.argv.index('--only')
                if idx + 1 < len(sys.argv):
                    sel_str = sys.argv[idx + 1]
                    if 'socios' in sel_str.lower():
                        proceed = True
            except Exception:
                proceed = False

        if not proceed:
            print(f"❌ Diretório de dados não encontrado: {importer.data_dir}")
            print("💡 Verifique se os dados estão no local correto")
            return
        else:
            print(f"⚠️ Diretório de dados {importer.data_dir} não encontrado, mas prosseguindo porque --only socios foi solicitado.")
    
    print(f"📁 Diretório de dados: {importer.data_dir.absolute()}")
    print(f"💾 Banco de dados: {importer.db_path}")
    
    selected = None
    if args.only:
        selected = [s.strip().lower() for s in args.only.split(',') if s.strip()]

    # Executar importação
    inicio = time.time()
    if args.list:
        arquivos = importer.find_csv_files()
        print('\nArquivos detectados:')
        for tabela, info in arquivos.items():
            if 'arquivos' in info:
                for a in info['arquivos']:
                    print(f" - {tabela}: {a['arquivo']}")
            else:
                print(f" - {tabela}: {info.get('arquivo')}")
        return

    # Safety: do NOT import everything by default. Require explicit --all or --only.
    if not args.all and selected is None:
        print('\n⚠️  Ação não executada: é necessário informar --all para importar tudo ou --only para selecionar tabelas.')
        print('Use --list para ver os arquivos detectados.')
        return

    # Proceed with requested import
    if args.all:
        sucesso = importer.import_all(selected_tables=None)
    else:
        sucesso = importer.import_all(selected_tables=selected)
    fim = time.time()
    
    tempo_total = fim - inicio
    print(f"\n⏱️  TEMPO TOTAL: {tempo_total:.1f} segundos")
    
    if sucesso:
        print("✅ IMPORTAÇÃO FINALIZADA - SISTEMA PRONTO PARA USO!")
    else:
        print("⚠️  IMPORTAÇÃO CONCLUÍDA COM ALERTAS")

    # Relatório final: contagens reais por tabela
    try:
        db = CNPJDatabase('cnpj_database.db')
        if db.connect():
            cur = db.connection.cursor()
            tables = ['empresas','estabelecimentos','simples','cnaes','municipios','naturezas','motivos','paises','qualificacoes','socios']
            print('\nRelatório final (contagens reais):')
            for t in tables:
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {t}")
                    print(f" - {t}: {cur.fetchone()[0]:,}")
                except Exception:
                    print(f" - {t}: tabela não encontrada ou erro")
            db.disconnect()
    except Exception:
        pass

if __name__ == "__main__":
    main()