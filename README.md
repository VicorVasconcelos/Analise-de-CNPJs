# Sistema de Análise de Dados do CNPJ

Este repositório contém o backend (Flask), frontend (HTML/CSS/JS) e scripts auxiliares para importar, indexar e gerar agregados a partir dos dados do CNPJ.

📌 Resumo rápido
- Backend: Python 3.13, Flask, SQLite
- Frontend: `index.html`, `script.js`, `styles.css` (Vanilla JS)
- Scripts auxiliares: importadores, criação de índices e geração de `aggregates_*`

---

## 🗂️ Estrutura do repositório (arquivos principais)

Arquivos presentes na raiz do projeto (exemplo representativo):

```
.gitattributes
.gitignore
analyze_and_bench.py
analyze_and_bench_safe.py
analyze_db.py
app.py
cnpj_database.db
cnpj_exportacao_20251010_100841.csv
create_aggregates.py
create_indexes.sql
create_indexes_temp.sql
database.py
importador_estabelecimentos_completo.py
import_data.py
import_estabelecimentos.py
import_projeto_cnpj.py
import_projeto_cnpj_v2.py
index.html
inspect_db.py
last_filters_response.json
README.md
response.json
response_filters.json
script.js
server.err
server.log
styles.css
```

> Nota: a pasta `exports/` é usada pelas rotinas de exportação (pode ser criada automaticamente pelo servidor).

---

## ⚙️ Pré-requisitos

- Python 3.10+ (3.13 recomendado)
- Recomenda-se criar um ambiente virtual (venv)

## ▶️ Instalação (Windows - PowerShell)

```powershell
cd "C:\Users\victor.vasconcelos\Documents\Dashboard"
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install flask flask-cors pandas requests
```

---

## 📦 Preparação dos dados (resumo)

1) Backup do DB (sempre antes de alterações):

```powershell
Copy-Item cnpj_database.db cnpj_database.db.backup_$(Get-Date -Format yyyyMMdd_HHmmss).db
```

2) Executar importadores (quando necessário):

```powershell
python import_projeto_cnpj.py
python import_estabelecimentos.py
```

3) Criar índices (apenas uma vez ou após import):

```powershell
sqlite3 cnpj_database.db ".read create_indexes.sql"
```

4) Gerar aggregates para acelerar `/filters`:

```powershell
python create_aggregates.py
```

5) (Opcional) executar `ANALYZE;` no sqlite3 para atualizar estatísticas do otimizador.

---

## 🧭 Como rodar (desenvolvimento)

```powershell
python app.py
```

Abra no navegador: http://localhost:5000

---

## 🚀 Endpoints principais

- `/health` — checagem rápida
- `/stats` — estatísticas do banco
- `/filters` — lista de filtros pré-computados (ufs, cnaes, naturezas, etc.)
- `/query` — executa consulta com filtros e paginação
- `/export` — gera CSVs na pasta `exports/`

---

## 🎯 Destaques e mudanças recentes

- O backend foi otimizado com tabelas de agregados (`aggregates_*`) para acelerar `/filters` e `/stats`.
- O endpoint `/export` passou a respeitar os mesmos filtros aplicados em `/query`, garantindo consistência entre a UI e o CSV gerado.
- O dropdown de UFs agora é apresentado em ordem alfabética (backend + frontend).

---

## ⚠️ Observações importantes

- O arquivo `cnpj_database.db` pode ser muito grande. Considere usar Git LFS ou manter o arquivo em armazenamento externo.
- Exportações muito grandes podem demorar; o servidor gera CSVs em chunks, mas cargas grandes devem ser executadas como jobs de background para maior robustez.

---

## 📌 Exportação canônica (referência)

O arquivo de exportação que deve ser tomado como referência para formato, ordem de colunas e conteúdo está em:

`c:\Users\victor.vasconcelos\Documents\Dashboard\cnpj_exportacao_20251016_173832.csv`

A partir deste ponto vamos manter este layout como *contrato* de saída. Todas as alterações na aplicação (backend ou frontend) devem preservar esse formato de exportação.

Diretivas imediatas:
- Não alterar a ordem das colunas nem os nomes de cabeçalho usados no CSV de referência.
- Focar otimização na interface e no tempo de geração de export (performance do `/export`), sem mudar a estrutura definitiva do CSV.
- Remover scripts auxiliares que geram exports de teste que não são usados em produção.

Se quiser alterar o layout no futuro, o processo deve ser: definir nova versão do CSV, registrar mudança no README e atualizar o contrato de compatibilidade.

---

## 🧰 Dicas de manutenção

- Sempre faça backup antes de rodar importadores.
- Após criar índices, rode `ANALYZE;` no Sqlite.
- Para re-gerar agregados: `python create_aggregates.py`.

---

## 🛠️ VS Code - configurações recomendadas para este projeto

Se o VS Code estiver lento ao abrir ou indexar o repositório, crie/ative o arquivo de workspace em `.vscode/settings.json` (já incluído) que aplica as seguintes otimizações:

- Exclui a pasta `archive/`, binários e grandes CSVs do file watcher e das buscas.
- Define a análise do Python (Pylance) para modo `basic` e limita a análise a arquivos abertos.
- Desativa recomendações de extensão e telemetria para reduzir o ruído.

Essas alterações melhoram significativamente a responsividade em máquinas com I/O limitado ou quando há muitos artefatos grandes no repositório.


## 🧪 Testes

- Atualmente não há testes automatizados no repositório. Posso adicionar testes de smoke para `/health`, `/filters` e `/query` se desejar.

---

## � Expor uma interface rápida via Streamlit (para enviar ao seu amigo)

---
## �📞 Contato

- **Desenvolvedor principal:** Victor Vasconcelos — +55 61 98438-5187

---

Atualizado em: 2025-10-10

---

##  Repository cleanup (2025-10-15)

Uma limpeza controlada de artefatos (exports, logs e relatórios) foi executada. Mantivemos apenas o backup mais recente em rchive/:

- rchive/cnpj_database.db.bak_20251015_165130.db

Se precisar restaurar qualquer relatório removido, recupere-o do histórico do Git.
