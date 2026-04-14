# Sistema de Análise de Dados do CNPJ

Este repositório contém o backend (Flask), frontend (HTML/CSS/JS) e scripts de operação para consulta, filtros e exportação de dados CNPJ.

📌 Resumo rápido
- Backend: Python, Flask, SQLite
- Frontend: `web/index.html`, `web/script.js`, `web/styles.css` (Vanilla JS)
- Execução recomendada: Waitress (`scripts/run_backend_waitress.py`)
- Operação diária: scripts `.cmd` em `scripts/`

---

## 🗂️ Estrutura do repositório (arquivos principais)

Estrutura principal atual:

```
src/                    # Backend Flask
web/                    # Frontend estático
scripts/                # Operação e manutenção
data/                   # Banco SQLite e arquivos de apoio
tests/                  # Testes
README.md
requirements.txt
```

## Estrutura mínima relevante
- `src/` - código fonte do backend
- `web/` - frontend
- `data/cnpj_database.db` - banco SQLite principal
- `scripts/start_backend.cmd` - sobe backend
- `scripts/start_tunnel.cmd` - sobe túnel público
- `scripts/start_cnpj_system.cmd` - sobe backend + túnel
- `scripts/monitor_health.cmd` - monitor de saúde
- `scripts/deep_clean_safe.ps1` - limpeza segura

---

- Recomenda-se usar ambiente virtual (`.venv`)

## ▶️ Instalação (Windows - PowerShell)

```powershell
cd "C:\Users\victor.vasconcelos\Documents\Projeto CNPJ"
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 📦 Preparação dos dados (resumo)

1) Backup do banco antes de alterações:

```powershell
Copy-Item data/cnpj_database.db data/cnpj_database.db.backup_$(Get-Date -Format yyyyMMdd_HHmmss).db
```

2) Regenerar agregados (quando necessário):

```powershell
.venv\Scripts\python.exe scripts\create_aggregates.py
```

---

## 🧭 Como rodar (desenvolvimento)

```powershell
.venv\Scripts\python.exe src\app.py
```

Abrir no navegador:
- `http://localhost:5000`
- `http://localhost:5000/health`

---

## 🚀 Execução recomendada (produção local)

Subir backend com auto-restart:

```powershell
scripts\start_backend.cmd
```

Subir túnel público:

```powershell
scripts\start_tunnel.cmd
```

Subir tudo (backend + túnel):

```powershell
scripts\start_cnpj_system.cmd
```

Parar tudo:

```powershell
scripts\stop_cnpj_system.cmd
```

Atualizar link público:

```powershell
scripts\refresh_public_link.cmd
```

Monitorar saúde da API:

```powershell
scripts\monitor_health.cmd
```

---

## 📌 Exportação canônica (contrato)

O export CSV deve manter este cabeçalho canônico:

`CNPJ;RAZAO_SOCIAL;NOME_FANTASIA;SITUACAO_EMPRESA;DATA_SITUACAO;ENDERECO_COMPLETO;CEP;UF;NOME_MUNICIPIO;TELEFONE;TELEFONE 2;EMAIL;DESCRICAO_CNAE;BAIRRO;PORTE;CAPITAL_SOCIAL;MEI;MATRIZ_FILIAL;NOME_SOCIO;QUALIFICACAO_SOCIO;CPF_SOCIO`

Regras atuais de ordenação no export:
- Empresas ativas primeiro
- Depois registros com telefone preenchido
- Depois registros com e-mail preenchido

---

## ⚠️ Observações importantes

- `data/cnpj_database.db` é grande; evite versionar backups pesados.
- Exportações grandes podem demorar; prefira filtros mais específicos.
- Logs e arquivos temporários podem crescer ao longo do tempo.

---

## 🧰 Dicas de manutenção

Limpeza segura da workspace:

```powershell
scripts\deep_clean_safe.ps1
```

Aplicar limpeza efetiva:

```powershell
scripts\deep_clean_safe.ps1 -Apply -KeepDbBackups 1
```

Limpeza mais agressiva (usar com cuidado):

```powershell
scripts\deep_clean_safe.ps1 -Apply -KeepDbBackups 0 -IncludePcTemp -AggressiveWorkspace
```

---

## 🧪 Testes

```powershell
.venv\Scripts\python.exe -m pytest
```

---

## 📞 Contato

- **Desenvolvedor principal:** Victor Vasconcelos — +55 61 98438-5187

---

Atualizado em: 2026-04-14
