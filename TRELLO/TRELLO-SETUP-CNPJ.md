
# 📋 GUIA DE CONFIGURAÇÃO DO TRELLO - Projeto Análise de CNPJ (versão detalhada)

Documento adaptado para organizar o board do Trello especificamente para o projeto "Análise de CNPJ". Contém:
- Setup do board
- Labels e listas recomendadas
- Templates de cards prontos para uso (import, backend, export, bugs, docs)
- Exemplos de payloads para `/query` e `/export` e comandos úteis para manutenção

> Nota: Não executar commits automáticos a partir deste arquivo. Este guia é de referência para o time.

## 🎯 Setup Inicial do Board

### 1. Criar Board Principal
**Nome**: `Análise de CNPJ — Dashboard`
**Tipo**: Kanban
**Visibilidade**: Privado (Desenvolvimento Solo / time pequeno)
**Descrição**: Sistema para coleta, análise e exportação de dados de CNPJ. Backend: Flask (Python 3.13). Banco: SQLite (`cnpj_database.db`) — use Git LFS para versionamento quando necessário. Frontend: vanilla JS (`index.html`, `script.js`).

**Responsável / contato**: Victor Vasconcelos — +55 61 98438-5187

### 2. Listas recomendadas

```
📋 BACKLOG → 🎯 SPRINT ATUAL → 🏗️ EM DESENVOLVIMENTO → 🧪 TESTANDO → ✅ CONCLUÍDO → 🚀 DEPLOY
```

Sugestão de uso rápido:
- Faça grooming semanal do backlog
- Sprint curto de 1 a 2 semanas
- Mova para `🧪 TESTANDO` apenas quando cobrir cenários de export/filtragem

### 3. Labels recomendadas

| Cor | Nome | Uso |
|-----|------|-----|
| 🔴 | Crítico | Bugs que bloqueiam uso da aplicação ou causam perda de dados |
| 🟠 | Alta | Funcionalidades de core (filtros, export, import) |
| 🟡 | Média | Melhorias e refatorações |
| 🟢 | Baixa | UI/UX, ajustes não críticos |
| 🗄️ | DB | Scripts/Índices/aggregates (`create_aggregates.py`, `create_indexes.sql`) |
| 🧰 | Backend | Flask — endpoints `/filters`, `/query`, `/export`, `/download` |
| 🧩 | Frontend | Vanilla JS — `index.html`, `script.js` |
| 📦 | Importação | `import_data.py`, `import_estabelecimentos.py` |
| 📊 | Export | CSVs, streaming, background jobs |
| 🧪 | Testes | Smoke tests, unit/integration |
| 🟤 | Docs | `README.md`, guias e exemplos |

---

## 📝 TEMPLATES DE CARDS (Prontos para colar)

Cole o template abaixo ao criar um card e preencha os campos.

### Template: Importação de Dados

```
📦 [IMPORT] Nome do Arquivo / Fonte

📋 DESCRIÇÃO:
Pequena descrição do CSV ou fonte de dados (ex: base da Receita/Periódica).

🎯 CRITÉRIOS DE ACEITE:
- [ ] Arquivo processado para `cnpj_database.db`
- [ ] Registros validados (UF, município, CNAE)
- [ ] Índices essenciais criados (ex: `uf`, `cnae_fiscal_principal`)

🛠️ TAREFAS TÉCNICAS:
- [ ] Validar encoding (UTF-8/ISO-8859-1) e remover linhas corrompidas
- [ ] Rodar `python import_data.py --input path/to/file.csv` e monitorar logs
- [ ] Executar `python create_aggregates.py` para atualizar aggregates
- [ ] Verificar `analyze_db.py` para sugestões de índices
- [ ] (Opcional) Adicionar `cnpj_database.db` ao Git LFS e subir

📊 ESTIMATIVA: Xh
👤 RESPONSÁVEL: <nome>

DEFINITION OF DONE:
- [ ] Import concluído sem erros
- [ ] Aggregates atualizados e validados
- [ ] CSV de exportação gerado e conferido (amostra)
```

### Template: Endpoint `/filters` (Backend)

```
🧰 [BACKEND] /filters

📋 DESCRIÇÃO:
Rota que retorna dados para popular os filtros do frontend: `ufs`, `cnaes`, `naturezas`, `portes`, `simples`, `situacoes`.

🎯 CRITÉRIOS DE ACEITE:
- [ ] Usa `aggregates_*` quando disponíveis
- [ ] Responde com objetos `{ "value": "XX", "label": "XX - Nome", "count": N }`
- [ ] TTL cache aplicado para reduzir carga

🛠️ TAREFAS TÉCNICAS:
- [ ] Garantir `ORDER BY uf ASC` no fallback
- [ ] Implementar `last_filters_response.json` somente em debug
- [ ] Adicionar logs de timing para cada bloco (ufs, cnaes, naturezas)
- [ ] Escrever smoke test que valide o shape da resposta

📊 ESTIMATIVA: Xh
👤 RESPONSÁVEL: <nome>
```

### Template: `/query` e `/export` (Paridade)

```
📊 [BACKEND] /query + /export

📋 DESCRIÇÃO:
As rotas `/query` (paginada) e `/export` (CSV) devem aceitar o mesmo JSON de filtros e aplicar exatamente a mesma lógica de WHERE.

🎯 CRITÉRIOS DE ACEITE:
- [ ] Existe `build_where_and_params(filtros)` central
- [ ] `/export` gera CSV com mesmas linhas que `/query` aplicada a toda paginação
- [ ] Export grande não trava o servidor (streaming ou job offload)

🛠️ TAREFAS TÉCNICAS:
- [ ] Refatorar `app.py` para compartilhar função de filtros
- [ ] Usar parâmetros seguros `?` com lista de `params`
- [ ] Implementar `LIMIT`/`OFFSET` em `/query`
- [ ] Implementar streaming CSV ou job background para `/export` (opcional)
- [ ] Teste que compara hashes/contagens entre `/query` (full) e `/export` CSV

📊 ESTIMATIVA: Xh
👤 RESPONSÁVEL: <nome>
```

### Template: Bug / Incidente

```
🐛 [BUG] Título curto

📋 DESCRIÇÃO:
Descreva o erro com clareza.

🔍 PASSOS PARA REPRODUZIR:
1. Passo 1
2. Passo 2
3. Resultado observado

🎯 RESULTADO ESPERADO:
O que deveria acontecer

❌ RESULTADO ATUAL:
O que está acontecendo

🛠️ INVESTIGAÇÃO:
- [ ] Verificar logs do Flask (`server.log` / `server.err`)
- [ ] Conferir `last_filters_response.json` (se existe)
- [ ] Rodar `python analyze_db.py` para verificar índices
- [ ] Tentar reproduzir localmente com `python app.py`

PRIORIDADE: Crítico/Alto/Médio/Baixo
RESPONSÁVEL: <nome>
```

### Template: Documentação / README

```
🟤 [DOCS] Atualizar README

📋 DESCRIÇÃO:
Melhorar instruções de setup, exportação e uso das rotas. Incluir exemplos de payloads e comandos.

TAREFAS:
- [ ] Documentar payloads `/query` e `/export` (exemplos abaixo)
- [ ] Incluir instruções de Git LFS para o DB
- [ ] Exemplos de import e geração de aggregates
- [ ] Contato (Victor) atualizado

RESPONSÁVEL: Victor
```

---

## 🔧 Exemplos e comandos úteis

Use os exemplos abaixo ao criar cards e para onboarding do repositório.

### Comandos locais (Windows / cmd)

```cmd
REM Criar e ativar venv (Windows PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

REM Instalar dependências (se houver requirements)
pip install -r requirements.txt

REM Rodar a aplicação localmente
python app.py

REM Importar dados exemplo
python import_data.py --input "path\to\file.csv"

REM Gerar aggregates
python create_aggregates.py
```

### Observações sobre Git LFS

- O arquivo `cnpj_database.db` pode ser grande (GBs). Se for necessário versionar o DB, usar Git LFS:

```cmd
git lfs install
git lfs track "cnpj_database.db"
git add .gitattributes
git add cnpj_database.db
git commit -m "track db with lfs"
git push origin master
```

- Atenção ao quota do Git LFS no repositório remoto.

---

## � Payloads de exemplo

Use estes exemplos ao preencher cards de integração, testes ou ao documentar a API.

Exemplo mínimo para `/query` (POST JSON):

```json
{
	"filters": {
		"uf": "DF",
		"natureza_juridica": ["2062", "2054"],
		"cnae": ["6201500", "6202900"],
		"simples": "S",
		"situacao": [2, 8]
	},
	"page": 1,
	"per_page": 50,
	"sort": { "col": "razao_social", "dir": "asc" }
}
```

Exemplo para `/export` (usa os mesmos filtros):

```json
{
	"filters": {
		"uf": "DF",
		"cnae": ["6201500"]
	},
	"columns": ["cnpj", "razao_social", "uf", "cnae_fiscal_principal"],
	"format": "csv"
}
```

---

## 🔄 Automações sugeridas (Trello)

1. Ao mover para `🏗️ EM DESENVOLVIMENTO`:
- Atribuir responsável padrão
- Adicionar checklist técnica (import/aggregates/tests)

2. Ao mover para `🧪 TESTANDO`:
- Anexar logs relevantes (server.log, last_filters_response.json)
- Adicionar label `🧪`

3. Ao mover para `✅ CONCLUÍDO`:
- Arquivar em 7 dias
- AtualizarCHANGELOG (opcional)

---

## � Boas práticas e observações

- Sempre gerar `create_aggregates.py` após grandes imports para acelerar `/filters`.
- Evitar expor o `cnpj_database.db` sem controle: prefira exportar CSVs e compartilhar amostras.
- Para exports grandes, prefira gerar o CSV em disco e disponibilizar via `/download/<file>`.
- Monitorar `server.log` e `server.err` para erros e tempos longos.

## 🧾 Checklists úteis (copiar/colar)

Import checklist:
- [ ] Validar encoding
- [ ] Rodar import
- [ ] Executar aggregates
- [ ] Testar filtros básicos

Release checklist:
- [ ] Atualizar README
- [ ] Testar endpoints `/filters`, `/query`, `/export`
- [ ] Gerar release notes

---

## 📞 Contato

Victor Vasconcelos — +55 61 98438-5187

