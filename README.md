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
data/cnpj_database.db
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
server.log
## Estrutura mínima relevante
- `src/` - código fonte do backend (Flask)
- `web/` - frontend (arquivos estáticos)
- `data/cnpj_database.db` - arquivo SQLite com os dados (não comitar arquivos grandes)
- `create_aggregates.py` - script que gera tabelas `aggregates_*` para acelerar consultas
- `create_indexes.sql` / `create_indexes_temp.sql` - scripts SQL para criar índices importantes


---

- Recomenda-se criar um ambiente virtual (venv)

## ▶️ Instalação (Windows - PowerShell)

```powershell
cd "C:\Users\victor.vasconcelos\Documents\Dashboard"
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install flask flask-cors pandas requests

---

## 📦 Preparação dos dados (resumo)

1) Backup do DB (sempre antes de alterações):

```powershell
Copy-Item data/cnpj_database.db data/cnpj_database.db.backup_$(Get-Date -Format yyyyMMdd_HHmmss).db
```

2) Executar importadores (quando necessário):

```powershell
python import_projeto_cnpj.py
python import_estabelecimentos.py
```

3) Criar índices (apenas uma vez ou após import):

```powershell
sqlite3 data/cnpj_database.db ".read create_indexes.sql"
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

Abra no navegador: http://localhost:5000
- `/health` — checagem rápida
- `/filters` — lista de filtros pré-computados (ufs, cnaes, naturezas, etc.)
- `/query` — executa consulta com filtros e paginação


- O backend foi otimizado com tabelas de agregados (`aggregates_*`) para acelerar `/filters` e `/stats`.


## ⚠️ Observações importantes

- O arquivo `data/cnpj_database.db` pode ser muito grande. Considere usar Git LFS ou manter o arquivo em armazenamento externo.
- Exportações muito grandes podem demorar; o servidor gera CSVs em chunks, mas cargas grandes devem ser executadas como jobs de background para maior robustez.

---

## 📌 Exportação canônica (referência)
`c:\Users\victor.vasconcelos\Documents\Dashboard\cnpj_exportacao_20251016_173832.csv`

A partir deste ponto vamos manter este layout como *contrato* de saída. Todas as alterações na aplicação (backend ou frontend) devem preservar esse formato de exportação.
Diretivas imediatas:
- Não alterar a ordem das colunas nem os nomes de cabeçalho usados no CSV de referência.
Se quiser alterar o layout no futuro, o processo deve ser: definir nova versão do CSV, registrar mudança no README e atualizar o contrato de compatibilidade.
---

## 🧰 Dicas de manutenção


---

## 🛠️ VS Code - configurações recomendadas para este projeto


- Define a análise do Python (Pylance) para modo `basic` e limita a análise a arquivos abertos.
- Desativa recomendações de extensão e telemetria para reduzir o ruído.
Essas alterações melhoram significativamente a responsividade em máquinas com I/O limitado ou quando há muitos artefatos grandes no repositório.

## 🧪 Testes

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

- rchive/data/cnpj_database.db.bak_20251015_165130.db

Se precisar restaurar qualquer relatório removido, recupere-o do histórico do Git.
