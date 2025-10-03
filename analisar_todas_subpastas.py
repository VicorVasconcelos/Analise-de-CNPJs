import os

# Estrutura das subpastas e arquivos do CNPJ
base_path = r'C:\Users\victor.vasconcelos\Documents\PROJETO CNPJ'

subpastas = [
    'Cnaes',
    'Empresas0', 
    'Estabelecimentos0',
    'Motivos',
    'Municipios',
    'Naturezas',
    'Paises',
    'Qualificacoes',
    'Simples'
]

print("🔍 ANÁLISE COMPLETA DOS ARQUIVOS CSV - PROJETO CNPJ")
print("=" * 70)

for subpasta in subpastas:
    pasta_path = os.path.join(base_path, subpasta)
    
    print(f"\n📁 SUBPASTA: {subpasta}")
    print(f"📂 Caminho: {pasta_path}")
    
    try:
        # Listar arquivos CSV na subpasta
        arquivos = [f for f in os.listdir(pasta_path) if f.endswith('.csv') or f.endswith('.CSV')]
        
        if not arquivos:
            print("❌ Nenhum arquivo CSV encontrado")
            continue
            
        for arquivo in arquivos:
            arquivo_path = os.path.join(pasta_path, arquivo)
            
            print(f"\n  📄 ARQUIVO: {arquivo}")
            
            # Verificar tamanho
            tamanho_bytes = os.path.getsize(arquivo_path)
            tamanho_mb = tamanho_bytes / (1024 * 1024)
            tamanho_gb = tamanho_bytes / (1024 * 1024 * 1024)
            limite_1mb = 1024 * 1024  # 1MB em bytes
            
            if tamanho_gb >= 1:
                print(f"  📊 Tamanho: {tamanho_gb:.2f} GB ({tamanho_bytes:,} bytes)")
            else:
                print(f"  📊 Tamanho: {tamanho_mb:.2f} MB ({tamanho_bytes:,} bytes)")
            
            # Determinar estratégia de análise baseada no tamanho
            linhas = []
            
            if tamanho_bytes <= limite_1mb:
                # Arquivo pequeno (≤1MB) - analisar completamente
                print(f"  🔍 Arquivo pequeno - analisando TODAS as linhas:")
                try:
                    with open(arquivo_path, 'r', encoding='latin-1', errors='ignore') as f:
                        linhas = [linha.strip() for linha in f]
                    
                    print(f"  📊 Total de linhas: {len(linhas)}")
                    
                    # Mostrar linhas conforme quantidade
                    if len(linhas) <= 30:
                        # Arquivo muito pequeno - mostrar todas
                        print(f"  📋 Todas as {len(linhas)} linhas:")
                        for i, linha in enumerate(linhas, 1):
                            linha_display = linha[:150] + "..." if len(linha) > 150 else linha
                            print(f"    {i:2d}: {linha_display}")
                    else:
                        # Mostrar primeiras 15 e últimas 15
                        print("  📋 Primeiras 15 linhas:")
                        for i, linha in enumerate(linhas[:15], 1):
                            linha_display = linha[:150] + "..." if len(linha) > 150 else linha
                            print(f"    {i:2d}: {linha_display}")
                        
                        print("  📋 Últimas 15 linhas:")
                        for i, linha in enumerate(linhas[-15:], len(linhas)-14):
                            linha_display = linha[:150] + "..." if len(linha) > 150 else linha
                            print(f"    {i:2d}: {linha_display}")
                            
                except Exception as e:
                    print(f"  ❌ Erro ao ler arquivo completo: {e}")
                    linhas = []
            else:
                # Arquivo grande (>1MB) - apenas primeiras 20 linhas
                print(f"  🔍 Arquivo grande - analisando apenas as PRIMEIRAS 20 linhas:")
                try:
                    with open(arquivo_path, 'r', encoding='latin-1', errors='ignore') as f:
                        for i, linha in enumerate(f):
                            if i >= 20:
                                break
                            linhas.append(linha.strip())
                    
                    print(f"  📋 Primeiras 20 linhas:")
                    for i, linha in enumerate(linhas, 1):
                        linha_display = linha[:150] + "..." if len(linha) > 150 else linha
                        print(f"    {i:2d}: {linha_display}")
                        
                except Exception as e:
                    print(f"  ❌ Erro ao ler arquivo: {e}")
                    linhas = []
            
            # Analisar estrutura das colunas
            if linhas:
                primeira_linha = linhas[0]
                separador = ';' if ';' in primeira_linha else (',' if ',' in primeira_linha else '|')
                colunas = primeira_linha.split(separador)
                
                print(f"  🔧 Separador detectado: '{separador}'")
                print(f"  📊 Número de colunas: {len(colunas)}")
                print(f"  📝 Estrutura das colunas:")
                for i, col in enumerate(colunas, 1):
                    col_clean = col.strip('"').strip()
                    # Limitar tamanho da coluna
                    col_display = col_clean[:40] + "..." if len(col_clean) > 40 else col_clean
                    print(f"       Col {i:2d}: '{col_display}'")
                
                # Analisar algumas linhas para entender os dados
                if len(linhas) > 1:
                    print(f"  🔍 Análise dos dados (linha 2):")
                    segunda_linha = linhas[1]
                    valores = segunda_linha.split(separador)
                    for i, valor in enumerate(valores[:min(10, len(valores))], 1):
                        valor_clean = valor.strip('"').strip()
                        valor_display = valor_clean[:30] + "..." if len(valor_clean) > 30 else valor_clean
                        print(f"       Val {i:2d}: '{valor_display}'")
                
    except Exception as e:
        print(f"❌ Erro ao acessar subpasta {subpasta}: {e}")
    
    print("-" * 70)

print("\n✅ Análise de todas as subpastas concluída!")
print("\n📋 RESUMO DOS TIPOS DE DADOS ENCONTRADOS:")
print("  • CNAES - Códigos de atividade econômica")
print("  • EMPRESAS - Dados das empresas (razão social, capital, etc.)")
print("  • ESTABELECIMENTOS - Dados dos estabelecimentos (endereços, filiais)")
print("  • MOTIVOS - Motivos de situação cadastral")
print("  • MUNICIPIOS - Códigos e nomes dos municípios")
print("  • NATUREZAS - Naturezas jurídicas")
print("  • PAISES - Códigos e nomes dos países")
print("  • QUALIFICACOES - Qualificações dos responsáveis")
print("  • SIMPLES - Dados do Simples Nacional")
print("\n🔗 Próximo passo: Identificar chaves de relacionamento para junção dos dados")
print("\n📏 REGRA APLICADA:")
print("  • Arquivos ≤ 1MB: Análise completa")
print("  • Arquivos > 1MB: Apenas primeiras 20 linhas")