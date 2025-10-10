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
# Sistema de Análise CNPJ

Um projeto para analisar, filtrar e exportar os dados abertos do CNPJ (Receita Federal). Este repositório contém o backend em Flask, o frontend em HTML/CSS/vanilla JS e scripts de importação/otimização para o banco SQLite.

Principais pontos
- Backend: Flask + SQLite (arquivo: `cnpj_database.db`)
- Frontend: `index.html`, `script.js`, `styles.css`
- Tabelas de referência e agregados para acelerar filtros: `aggregates_*`

Estrutura relevante
- `app.py` — servidor Flask com endpoints: `/health`, `/stats`, `/filters`, `/query`, `/export`
- `database.py` — conexão com SQLite e PRAGMA de performance
- `import_*` scripts — importadores para empresas, estabelecimentos e tabelas de referência
- `create_aggregates.py` — monta as tabelas `aggregates_*` para acelerar `/filters`
- `create_indexes.sql` — instruções para criar índices importantes
- `script.js`, `index.html`, `styles.css` — frontend
- `exports/` — pasta onde arquivos CSV exportados são salvos

Requisitos
- Python 3.10+ (3.13 recomendado)
- Dependências: `flask`, `flask-cors`, `pandas`, `requests` (instale via `pip`)

Como rodar (desenvolvimento)
1. No diretório do projeto, ative o venv (opcional):
   `.venv\Scripts\activate`
2. Instale dependências se necessário:
   `pip install flask flask-cors pandas requests`
3. Inicie o servidor:
   `python app.py`
4. Abra no navegador: `http://localhost:5000`

Backup do banco (sempre antes de alterações)
- Faça uma cópia do arquivo: `Copy-Item cnpj_database.db cnpj_database.db.backup_$(Get-Date -Format yyyyMMdd_HHmmss).db`

Índices e aggregates
- Crie índices (uma vez) com `create_indexes.sql` ou via sqlite3:
  `sqlite3 cnpj_database.db ".read create_indexes.sql"`
- Gere/atualize as tabelas de agregados:
  `python create_aggregates.py`
  Essas tabelas (`aggregates_ufs`, `aggregates_cnaes`, `aggregates_naturezas`, `aggregates_portes`, `aggregates_simples`) reduzem consultas demoradas no `/filters`.

Cache
- `/stats` e `/filters` usam cache TTL em memória (em `app.py`).
- Se atualizar aggregates, reinicie o servidor ou force refresh do cache.

Fluxo de atualização da base
1. Backup do DB
2. Parar servidor
3. Executar importadores (empresas, estabelecimentos, referências)
4. Criar índices
5. Rodar `create_aggregates.py`
6. Executar `ANALYZE;` no sqlite3
7. Reiniciar servidor

Testes
- `test_api.py` e `test_queries.py` — scripts de verificação. Execute com `python` ou `pytest`.

Dicas de troubleshooting rápido
- Se dropdowns aparecerem vazios, abra DevTools → Network → verifique `/filters` e confirme que o JSON tem `value`/`label` (o frontend já é tolerante a variações).
- Se `/filters` estiver lento, verifique se `aggregates_*` existem.

Git — commit e push
```powershell
cd "C:\Users\victor.vasconcelos\Documents\Dashboard"
git add README.md
git commit -m "docs: atualizar README com processo de atualização, índices e aggregates"
git push origin perf-improvements
```

Contato
- Para dúvidas ou testes locais, inicie o servidor (`python app.py`) e acesse `http://localhost:5000`.

---
Atualizado em: 2025-10-10
**Desenvolvido para análise de dados abertos do CNPJ - Receita Federal do Brasil**