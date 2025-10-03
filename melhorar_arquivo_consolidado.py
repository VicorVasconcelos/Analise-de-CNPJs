import pandas as pd
import re
from datetime import datetime

def melhorar_arquivo_consolidado():
    """
    Aplica melhorias de formatação no arquivo consolidado CNPJ
    """
    
    print("🔧 MELHORANDO ARQUIVO CONSOLIDADO - FORMATAÇÕES")
    print("=" * 60)
    
    # Carregar arquivo atual
    arquivo_entrada = "cnpj_consolidado_exemplo.csv"
    arquivo_saida = "cnpj_consolidado_final.csv"
    
    try:
        df = pd.read_csv(arquivo_entrada, sep=';', dtype=str)
        print(f"✅ Arquivo carregado: {len(df)} registros, {len(df.columns)} colunas")
        
        # 1. FORMATAR DATAS (AAAAMMDD → DD/MM/AAAA)
        print("\n📅 Formatando datas...")
        if 'DATA_SITUACAO' in df.columns:
            def formatar_data(data_str):
                if pd.isna(data_str) or data_str == '' or len(str(data_str)) != 8:
                    return ''
                try:
                    data_str = str(data_str)
                    ano = data_str[:4]
                    mes = data_str[4:6]
                    dia = data_str[6:8]
                    return f"{dia}/{mes}/{ano}"
                except:
                    return data_str
            
            df['DATA_SITUACAO'] = df['DATA_SITUACAO'].apply(formatar_data)
            print("   ✅ DATA_SITUACAO formatada (DD/MM/AAAA)")
        
        # 2. FORMATAR CEP (12345678 → 12345-678)
        print("\n📍 Formatando CEPs...")
        if 'CEP' in df.columns:
            def formatar_cep(cep):
                if pd.isna(cep) or cep == '':
                    return ''
                try:
                    # Remover decimais e converter para string
                    cep_str = str(int(float(cep))).zfill(8)
                    if len(cep_str) == 8:
                        return f"{cep_str[:5]}-{cep_str[5:]}"
                    return cep_str
                except:
                    return str(cep)
            
            df['CEP'] = df['CEP'].apply(formatar_cep)
            print("   ✅ CEP formatado (12345-678)")
        
        # 3. FORMATAR TELEFONES ((XX) XXXXX-XXXX)
        print("\n📞 Formatando telefones...")
        if 'DDD1' in df.columns and 'TELEFONE1' in df.columns:
            def formatar_telefone(ddd, telefone):
                if pd.isna(ddd) or pd.isna(telefone) or ddd == '' or telefone == '':
                    return ''
                try:
                    ddd_str = str(int(float(ddd))).zfill(2)
                    tel_str = str(int(float(telefone)))
                    
                    if len(tel_str) == 9:  # Celular
                        return f"({ddd_str}) {tel_str[:5]}-{tel_str[5:]}"
                    elif len(tel_str) == 8:  # Fixo
                        return f"({ddd_str}) {tel_str[:4]}-{tel_str[4:]}"
                    else:
                        return f"({ddd_str}) {tel_str}"
                except:
                    return ''
            
            df['TELEFONE_FORMATADO'] = df.apply(lambda row: formatar_telefone(row['DDD1'], row['TELEFONE1']), axis=1)
            print("   ✅ TELEFONE_FORMATADO criado ((XX) XXXXX-XXXX)")
        
        # 4. CRIAR ENDEREÇO COMPLETO FORMATADO
        print("\n🏠 Criando endereço completo...")
        def criar_endereco_completo(row):
            partes = []
            
            # Tipo + Logradouro
            if not pd.isna(row.get('TIPO_LOGRADOURO', '')) and row.get('TIPO_LOGRADOURO', '') != '':
                tipo = str(row['TIPO_LOGRADOURO']).strip()
                if not pd.isna(row.get('LOGRADOURO', '')) and row.get('LOGRADOURO', '') != '':
                    logradouro = str(row['LOGRADOURO']).strip()
                    partes.append(f"{tipo} {logradouro}")
            elif not pd.isna(row.get('LOGRADOURO', '')) and row.get('LOGRADOURO', '') != '':
                partes.append(str(row['LOGRADOURO']).strip())
            
            # Número
            if not pd.isna(row.get('NUMERO', '')) and row.get('NUMERO', '') != '':
                numero = str(row['NUMERO']).strip()
                if numero.upper() != 'S/N':
                    partes.append(f"nº {numero}")
                else:
                    partes.append("s/n")
            
            # Complemento
            if not pd.isna(row.get('COMPLEMENTO', '')) and row.get('COMPLEMENTO', '') != '':
                complemento = str(row['COMPLEMENTO']).strip()
                partes.append(f"({complemento})")
            
            # Bairro
            if not pd.isna(row.get('BAIRRO', '')) and row.get('BAIRRO', '') != '':
                bairro = str(row['BAIRRO']).strip()
                partes.append(f"- {bairro}")
            
            return ', '.join(partes) if partes else ''
        
        df['ENDERECO_COMPLETO'] = df.apply(criar_endereco_completo, axis=1)
        print("   ✅ ENDERECO_COMPLETO criado")
        
        # 5. FORMATAR CNPJ COMPLETO (XX.XXX.XXX/XXXX-XX)
        print("\n🆔 Formatando CNPJ...")
        if 'CNPJ_COMPLETO' in df.columns:
            def formatar_cnpj(cnpj):
                if pd.isna(cnpj) or cnpj == '':
                    return ''
                try:
                    cnpj_str = str(cnpj).zfill(14)
                    if len(cnpj_str) == 14:
                        return f"{cnpj_str[:2]}.{cnpj_str[2:5]}.{cnpj_str[5:8]}/{cnpj_str[8:12]}-{cnpj_str[12:]}"
                    return cnpj_str
                except:
                    return str(cnpj)
            
            df['CNPJ_FORMATADO'] = df['CNPJ_COMPLETO'].apply(formatar_cnpj)
            print("   ✅ CNPJ_FORMATADO criado (XX.XXX.XXX/XXXX-XX)")
        
        # 6. TRATAR SITUAÇÃO (ATIVA/INATIVA)
        print("\n📊 Criando situação simplificada...")
        def classificar_situacao(motivo):
            if pd.isna(motivo) or motivo == '':
                return 'NÃO INFORMADO'
            
            motivo_upper = str(motivo).upper()
            
            # Situações que indicam empresa inativa
            inativos = [
                'EXTINCAO', 'INCORPORACAO', 'FUSAO', 'CISAO', 'TRANSPASSE', 
                'ENCERRAMENTO', 'LIQUIDACAO', 'FALENCIA', 'BAIXA'
            ]
            
            for termo in inativos:
                if termo in motivo_upper:
                    return 'INATIVA'
            
            return 'ATIVA'
        
        if 'DESCRICAO_MOTIVO' in df.columns:
            df['SITUACAO_EMPRESA'] = df['DESCRICAO_MOTIVO'].apply(classificar_situacao)
            print("   ✅ SITUACAO_EMPRESA criada (ATIVA/INATIVA)")
        
        # 7. TRATAR CAMPOS VAZIOS
        print("\n🧹 Tratando campos vazios...")
        # Substituir valores NaN por strings vazias ou "Não informado"
        campos_texto = ['RAZAO_SOCIAL', 'NOME_FANTASIA', 'DESCRICAO_NATUREZA', 'EMAIL']
        for campo in campos_texto:
            if campo in df.columns:
                df[campo] = df[campo].fillna('').apply(lambda x: '' if x in ['nan', 'NaN', 'null'] else str(x))
        
        # Campos numéricos vazios
        campos_numericos = ['PORTE', 'CAPITAL_SOCIAL']
        for campo in campos_numericos:
            if campo in df.columns:
                df[campo] = df[campo].fillna('')
        
        # Campos Simples - Tratamento específico
        campos_simples = ['OPCAO_SIMPLES', 'OPCAO_MEI']
        for campo in campos_simples:
            if campo in df.columns:
                df[campo] = df[campo].fillna('').apply(lambda x: 'N' if x == '' else x)
        
        print("   ✅ Campos vazios tratados")
        
        # 8. REORGANIZAR COLUNAS PARA MELHOR VISUALIZAÇÃO
        print("\n📋 Reorganizando colunas...")
        colunas_ordenadas = [
            'CNPJ_FORMATADO',
            'CNPJ_COMPLETO',
            'CNPJ_BASICO',
            'RAZAO_SOCIAL',
            'NOME_FANTASIA',
            'DESCRICAO_NATUREZA',
            'PORTE',
            'CAPITAL_SOCIAL',
            'DESCRICAO_CNAE',
            'SITUACAO_EMPRESA',
            'DESCRICAO_MOTIVO',
            'DATA_SITUACAO',
            'ENDERECO_COMPLETO',
            'CEP',
            'UF',
            'NOME_MUNICIPIO',
            'TELEFONE_FORMATADO',
            'EMAIL',
            'OPCAO_SIMPLES',
            'OPCAO_MEI',
            'MATRIZ_FILIAL'
        ]
        
        # Filtrar apenas colunas que existem
        colunas_existentes = [col for col in colunas_ordenadas if col in df.columns]
        df_final = df[colunas_existentes].copy()
        
        # 9. SALVAR ARQUIVO MELHORADO
        print(f"\n💾 Salvando arquivo melhorado...")
        df_final.to_csv(arquivo_saida, sep=';', encoding='utf-8', index=False)
        
        print(f"\n✅ SUCESSO!")
        print(f"📁 Arquivo original: {arquivo_entrada}")
        print(f"📁 Arquivo melhorado: {arquivo_saida}")
        print(f"📊 Registros: {len(df_final)}")
        print(f"📈 Colunas: {len(df_final.columns)}")
        
        # Mostrar amostra melhorada
        print(f"\n🔍 AMOSTRA DOS DADOS MELHORADOS:")
        print("-" * 80)
        
        for i, row in df_final.head(3).iterrows():
            print(f"\n📋 Empresa {i+1}:")
            print(f"   CNPJ: {row.get('CNPJ_FORMATADO', 'N/A')}")
            print(f"   Razão Social: {row.get('RAZAO_SOCIAL', 'Não informado')}")
            print(f"   Nome Fantasia: {row.get('NOME_FANTASIA', 'Não informado')}")
            print(f"   Atividade: {row.get('DESCRICAO_CNAE', 'N/A')[:50]}...")
            print(f"   Situação: {row.get('SITUACAO_EMPRESA', 'N/A')}")
            print(f"   Data Situação: {row.get('DATA_SITUACAO', 'N/A')}")
            print(f"   Endereço: {row.get('ENDERECO_COMPLETO', 'N/A')[:60]}...")
            print(f"   CEP: {row.get('CEP', 'N/A')}")
            print(f"   Cidade/UF: {row.get('NOME_MUNICIPIO', 'N/A')}/{row.get('UF', 'N/A')}")
            print(f"   Telefone: {row.get('TELEFONE_FORMATADO', 'Não informado')}")
            print(f"   Email: {row.get('EMAIL', 'Não informado')}")
        
        print(f"\n📊 MELHORIAS APLICADAS:")
        print("   ✅ Datas formatadas (DD/MM/AAAA)")
        print("   ✅ CEPs formatados (12345-678)")
        print("   ✅ Telefones formatados ((XX) XXXXX-XXXX)")
        print("   ✅ CNPJs formatados (XX.XXX.XXX/XXXX-XX)")
        print("   ✅ Endereços completos organizados")
        print("   ✅ Situação da empresa classificada (ATIVA/INATIVA)")
        print("   ✅ Campos vazios tratados")
        print("   ✅ Colunas reorganizadas")
        
    except Exception as e:
        print(f"❌ Erro ao processar arquivo: {e}")

if __name__ == "__main__":
    melhorar_arquivo_consolidado()