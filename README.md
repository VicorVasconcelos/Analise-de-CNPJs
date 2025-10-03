# Sistema de Análise de Dados Abertos do CNPJ

## 📋 Descrição

Sistema completo para análise e exportação de dados do CNPJ da Receita Federal do Brasil. Permite filtrar estabelecimentos por UF, CNAE, município, bairro e outras características, gerando arquivos CSV personalizados conforme os filtros aplicados pelo usuário.

## 🚀 Funcionalidades

- **Interface Web Moderna**: Design responsivo com filtros intuitivos
- **Filtros Avançados**: UF, CNAE, município, bairro, situação cadastral, porte da empresa
- **Exportação Personalizada**: Gera CSV com dados formatados conforme filtros
- **Performance Otimizada**: Consultas rápidas com índices no banco de dados
- **Paginação**: Navegação eficiente pelos resultados
- **API REST**: Backend robusto com 7 endpoints

## 🛠️ Tecnologias Utilizadas

- **Backend**: Python 3.13, Flask, SQLite
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Processamento**: pandas para manipulação de dados
- **Interface**: Design moderno com Font Awesome

## 📁 Estrutura do Projeto

```
Dashboard/
├── app.py                          # Backend Flask com APIs
├── database.py                     # Estrutura do banco de dados
├── import_data.py                  # Script de importação dos CSVs
├── test_queries.py                 # Testes de consultas
├── test_api.py                     # Testes das APIs
├── index.html                      # Interface principal
├── styles.css                      # Estilos responsivos
├── script.js                       # JavaScript interativo
├── cnpj_database.db               # Banco SQLite (criado após import)
├── cnpj_consolidado_final.csv     # Arquivo de exemplo/template
└── README.md                      # Esta documentação
```

## 🏃‍♂️ Como Executar

### 1. Pré-requisitos

- Python 3.13 ou superior
- Ambiente virtual Python (recomendado)

### 2. Instalação

```bash
# Clone ou baixe o projeto
cd Dashboard

# Ative o ambiente virtual (se usar)
.venv\Scripts\activate

# Instale as dependências
pip install flask flask-cors pandas requests
```

### 3. Preparação dos Dados

1. **Baixe os dados do CNPJ** da Receita Federal:
   - Site: https://dadosabertos.rfb.gov.br/CNPJ/
   - Arquivos necessários (9 CSVs, ~9.8GB total):
     - Empresas.csv (5.4GB)
     - Estabelecimentos.csv (2.4GB)
     - Simples.csv (88KB)
     - Cnaes.csv (59KB)
     - Municipios.csv (228KB)
     - Naturezas.csv (3KB)
     - Motivos.csv (2KB)
     - Paises.csv (8KB)
     - Qualificacoes.csv (2KB)

2. **Coloque os arquivos** na pasta do projeto

3. **Execute a importação**:
```bash
python import_data.py
```
⚠️ **Nota**: A importação pode demorar várias horas devido ao tamanho dos dados.

### 4. Inicialização do Sistema

1. **Inicie o servidor Flask**:
```bash
python app.py
```

2. **Abra o navegador** em: `http://localhost:5000`

3. **Acesse a interface** em: `index.html` (abra diretamente no navegador)

## 🔧 Uso do Sistema

### Interface Web

1. **Status**: Verifica conexão com a API
2. **Estatísticas**: Mostra resumo dos dados
3. **Filtros**: Selecione critérios de busca:
   - **UF**: Estados (múltipla seleção)
   - **CNAE**: Atividades econômicas (múltipla seleção)
   - **Município**: Nome da cidade
   - **Bairro**: Nome do bairro
   - **Situação**: Ativa, Suspensa, Baixada, etc.
   - **Porte**: Micro, Pequena, etc.

4. **Resultados**: Tabela paginada com dados encontrados
5. **Exportação**: Download do CSV com todos os registros filtrados

### APIs Disponíveis

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/` | GET | Informações da API |
| `/health` | GET | Status da aplicação |
| `/stats` | GET | Estatísticas gerais |
| `/filters` | GET | Opções de filtros |
| `/query` | POST | Busca com filtros |
| `/export` | POST | Gera CSV para download |
| `/download/<filename>` | GET | Download de arquivo |

### Exemplo de Uso da API

```python
import requests

# Buscar empresas de SP do setor de tecnologia
filters = {
    "uf": ["SP"],
    "cnae_principal": ["6201-5", "6202-3"],
    "situacao_cadastral": "02",  # Ativa
    "page": 1,
    "per_page": 100
}

response = requests.post("http://localhost:5000/query", json=filters)
data = response.json()

print(f"Encontradas {data['total']} empresas")
for empresa in data['data']:
    print(f"{empresa['razao_social']} - {empresa['municipio']}")
```

## 📊 Estrutura do Banco de Dados

### Tabelas Principais

- **empresas**: Dados básicos das empresas (CNPJ, razão social, etc.)
- **estabelecimentos**: Filiais e matriz (endereço, CNAE, situação)
- **simples**: Empresas do Simples Nacional

### Tabelas de Referência

- **cnaes**: Códigos de atividade econômica
- **municipios**: Códigos e nomes dos municípios
- **naturezas**: Natureza jurídica
- **motivos**: Motivos de situação cadastral
- **paises**: Códigos de países
- **qualificacoes**: Qualificação dos responsáveis

### Índices para Performance

- `idx_estabelecimentos_uf`: Busca por UF
- `idx_estabelecimentos_cnae`: Busca por CNAE
- `idx_estabelecimentos_municipio`: Busca por município
- `idx_estabelecimentos_situacao`: Busca por situação

## 🧪 Testes

### Executar Testes das APIs

```bash
python test_api.py
```

### Executar Testes de Consultas

```bash
python test_queries.py
```

### Testes Esperados

- ✅ Conexão com API
- ✅ Carregamento de estatísticas
- ✅ Filtros funcionais
- ✅ Busca com múltiplos critérios
- ✅ Exportação de CSV
- ✅ Download de arquivos
- ✅ Paginação de resultados

## 📈 Performance

### Métricas Observadas (100 registros de teste)

- **Consultas simples**: ~0.001s
- **Consultas complexas**: ~0.002s
- **Exportação CSV**: ~0.002s
- **Carregamento de filtros**: ~0.001s

### Otimizações Implementadas

- Índices específicos para campos de filtro
- Paginação para grandes resultados
- Processamento em chunks para importação
- Cache de opções de filtros

## 🔍 Troubleshooting

### Problemas Comuns

1. **Erro de conexão com API**
   - Verifique se `python app.py` está rodando
   - Confirme que a porta 5000 está livre

2. **Banco de dados vazio**
   - Execute `python import_data.py`
   - Verifique se os arquivos CSV estão na pasta

3. **Erro ao importar dados**
   - Confirme que tem espaço em disco suficiente
   - Verifique se os CSVs estão no formato correto

4. **Interface não carrega dados**
   - Abra o console do navegador (F12)
   - Verifique erros de CORS ou conectividade

### Logs e Debug

```bash
# Executar Flask em modo debug
export FLASK_ENV=development
python app.py

# Ver logs de importação
python import_data.py > import.log 2>&1
```

## 📝 Formatos de Saída

### CSV Exportado

O arquivo CSV gerado contém as seguintes colunas formatadas:

- **CNPJ**: XX.XXX.XXX/XXXX-XX
- **Razão Social**: Nome da empresa
- **Nome Fantasia**: Nome comercial
- **UF**: Estado
- **Município**: Cidade
- **Bairro**: Bairro
- **Endereço Completo**: Logradouro formatado
- **CEP**: XXXXX-XXX
- **CNAE Principal**: Código da atividade
- **Situação Cadastral**: Texto descritivo
- **Porte da Empresa**: Texto descritivo
- **Data de Início**: DD/MM/AAAA

## 🤝 Contribuições

Para contribuir com o projeto:

1. Faça um fork do repositório
2. Crie uma branch para sua feature
3. Implemente e teste suas modificações
4. Abra um Pull Request

## 📄 Licença

Este projeto é destinado ao uso educacional e análise de dados públicos da Receita Federal do Brasil.

## 📞 Suporte

Para dúvidas ou problemas:

1. Verifique a seção de Troubleshooting
2. Execute os testes para validar a instalação
3. Consulte os logs de erro do Flask

---

**Desenvolvido para análise de dados abertos do CNPJ - Receita Federal do Brasil**