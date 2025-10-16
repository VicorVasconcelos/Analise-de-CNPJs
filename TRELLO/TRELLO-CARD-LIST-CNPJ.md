📋 TRELLO - CARD LIST (KANBAN) — Projeto Análise de CNPJ

Este arquivo contém cartões prontos para colar no Trello, organizados por prioridade (Crítico → Alto → Médio → Baixo). Cada cartão tem título, descrição, critérios de aceite, estimativa, labels e lista alvo. Use-o para montar um board Scrum e seguir a ordem de execução.

Contato do projeto: Victor Vasconcelos — +55 61 98438-5187

---

🚨 TAREFAS CRÍTICAS (🔴 Crítico)

🔴 Card 1: Validar `cnpj_database.db` e Git LFS

📋 NOME: [DB] Validar DB e Git LFS
📋 DESCRIÇÃO: Verificar se `cnpj_database.db` está corretamente trackeado em Git LFS, checar tamanho e instruir sobre quotas.

🎯 CRITÉRIOS DE ACEITE:
- [ ] `.gitattributes` contém `cnpj_database.db` em LFS
- [ ] `git lfs ls-files` mostra o arquivo
- [ ] Procedimento documentado no README/Trello para clonar com LFS

📊 ESTIMATIVA: 15min
🏷️ LABELS: 🔴 Crítico, 🗄️ DB
📍 LISTA: 🏗️ EM DESENVOLVIMENTO

🔴 Card 2: Monitorar e otimizar `/filters` (500s resolvidos)

📋 NOME: [BACKEND] Monitorar e otimizar /filters
📋 DESCRIÇÃO: Os erros 500 na rota `/filters` foram resolvidos e atualmente todas as chamadas retornam 200. Este card foca em monitoramento contínuo, melhorias de performance e garantia de formato de resposta.

🎯 CRITÉRIOS DE ACEITE:
- [ ] Confirmação que `/filters` retorna 200 em ambiente de produção e staging
- [ ] Alerts/configuração de logs para detectar regressões (ex.: quando tempo de resposta > 2s ou erro 5xx)
- [ ] Revisão do formato de resposta (confirmar `{value,label,count}`) e exemplos no README
- [ ] Métricas coletadas (tempo médio, p95) para o endpoint

📊 ESTIMATIVA: 1h
🏷️ LABELS: 🟠 Alto, 🧰 Backend, 🧪 Testes
📍 LISTA: 🏗️ EM DESENVOLVIMENTO

🔴 Card 3: Agregar índices essenciais

📋 NOME: [DB] Criar índices para colunas de filtro
📋 DESCRIÇÃO: Criar/atualizar índices sugeridos (UF, cnae_fiscal_principal, natureza_juridica, municipio) para acelerar queries.

🎯 CRITÉRIOS DE ACEITE:
- [ ] `create_indexes.sql` atualizado ou novo migration
- [ ] Índices aplicados com sucesso
- [ ] Melhora mensurável no tempo de `/filters` e `/query`

📊 ESTIMATIVA: 45min
🏷️ LABELS: 🔴 Crítico, 🗄️ DB
📍 LISTA: 🏗️ EM DESENVOLVIMENTO

🔴 Card 4: Garantir paridade `/query` ↔ `/export`

📋 NOME: [BACKEND] Paridade entre query e export
📋 DESCRIÇÃO: Fazer com que `/export` receba o mesmo payload que `/query` e aplique identical WHERE.

🎯 CRITÉRIOS DE ACEITE:
- [ ] Existe `build_where_and_params` central e testado
- [ ] `/export` retorna exatamente os mesmos registros que `/query` full
- [ ] Teste de hash/contagem criado

📊 ESTIMATIVA: 1h
🏷️ LABELS: 🔴 Crítico, 🧰 Backend, 📊 Export
📍 LISTA: 🏗️ EM DESENVOLVIMENTO

---

🟠 TAREFAS DE ALTA PRIORIDADE (🟠 Alto)

🟠 Card 5: Implementar TTL cache para `/filters`

📋 NOME: [BACKEND] Cache TTL para /filters
📋 DESCRIÇÃO: Implementar cache em memória com TTL para reduzir carga nas primeiras chamadas.

🎯 CRITÉRIOS DE ACEITE:
- [ ] Cache habilitável via configuração
- [ ] TTL padrão documentado (ex.: 300s)
- [ ] Teste demonstrando redução de tempo em chamadas subsequentes

📊 ESTIMATIVA: 45min
🏷️ LABELS: 🟠 Alto, 🧰 Backend
📍 LISTA: 🏗️ EM DESENVOLVIMENTO

🟠 Card 6: Criar aggregates (`create_aggregates.py`)

📋 NOME: [DB] Gerar Aggregates
📋 DESCRIÇÃO: Script para criação/atualização de tabelas `aggregates_*` usadas por `/filters`.

🎯 CRITÉRIOS DE ACEITE:
- [ ] Script gera `aggregates_ufs`, `aggregates_cnaes`, `aggregates_naturezas`
- [ ] Script é idempotente e rápido o suficiente
- [ ] Documentado no README

📊 ESTIMATIVA: 1h
🏷️ LABELS: 🟠 Alto, 🗄️ DB, 📦 Importação
📍 LISTA: 🏗️ EM DESENVOLVIMENTO

🟠 Card 7: Export streaming / job background

📋 NOME: [BACKEND] Export streaming / background job
📋 DESCRIÇÃO: Para exports grandes, implementar streaming de CSV ou job que gera o arquivo em disco e retorna link `/download`.

🎯 CRITÉRIOS DE ACEITE:
- [ ] Export grande não bloqueia worker
- [ ] Arquivo salvo em `exports/` e link gerado
- [ ] Limpeza de arquivos antigos automatizada

📊 ESTIMATIVA: 2h
🏷️ LABELS: 🟠 Alto, 📊 Export
📍 LISTA: 🏗️ EM DESENVOLVIMENTO

---

🟡 TAREFAS DE MÉDIA PRIORIDADE (🟡 Médio)

🟡 Card 8: Frontend: Validar formato de filtros

📋 NOME: [FRONTEND] Ajustar `script.js` para formatos múltiplos
📋 DESCRIÇÃO: Tornar o frontend tolerante a diferentes shapes de `ufs` e `naturezas` vindo do backend.

🎯 CRITÉRIOS DE ACEITE:
- [ ] `loadFilters()` suporta `{value,label,count}` e `{uf,count}`
- [ ] UFs ordenados alfabeticamente no dropdown
- [ ] Teste manual no browser OK

📊 ESTIMATIVA: 30min
🏷️ LABELS: 🟡, 🧩 Frontend
📍 LISTA: 🏗️ EM DESENVOLVIMENTO

🟡 Card 9: Escrever smoke tests básicos

📋 NOME: [TESTES] Smoke tests endpoints
📋 DESCRIÇÃO: Criar testes simples que verificam `/health`, `/filters` e `/query` para evitar regressões.

🎯 CRITÉRIOS DE ACEITE:
- [ ] Arquivo `tests/smoke_tests.py` com 3 testes
- [ ] Tests podem ser rodados localmente com `pytest`
- [ ] Resultado quick-check documentado

📊 ESTIMATIVA: 45min
🏷️ LABELS: 🟡, 🧪 Testes
📍 LISTA: 🏗️ EM DESENVOLVIMENTO

🟡 Card 10: Documentar payloads e exemplos no README

📋 NOME: [DOCS] Exemplos `/query` / `/export`
📋 DESCRIÇÃO: Incluir exemplos JSON de payloads e como gerar exports no README.

🎯 CRITÉRIOS DE ACEITE:
- [ ] README atualizado com 2 exemplos práticos
- [ ] Incluir comando para download e verificação do CSV

📊 ESTIMATIVA: 30min
🏷️ LABELS: 🟡, 🟤 Docs
📍 LISTA: 🏗️ EM DESENVOLVIMENTO

---

🟢 TAREFAS DE BAIXA PRIORIDADE (🟢 Baixo)

🟢 Card 11: UI: adicionar footer com contato

📋 NOME: [FRONTEND] Footer com contato
📋 DESCRIÇÃO: Adicionar pequeno footer no `index.html` com nome e telefone do responsável.

🎯 CRITÉRIOS DE ACEITE:
- [ ] Footer adicionado
- [ ] Estilização simples e não invasiva

📊 ESTIMATIVA: 15min
🏷️ LABELS: 🟢, 🧩 Frontend
📍 LISTA: ✅ CONCLUÍDO

🟢 Card 12: Pequenas melhorias CSS

📋 NOME: [FRONTEND] Ajustes visuais
📋 DESCRIÇÃO: Pequenos ajustes em `styles.css` para melhorar legibilidade

🎯 CRITÉRIOS DE ACEITE:
- [ ] Espaçamento ajustado
- [ ] Botões com tamanho consistente

📊 ESTIMATIVA: 20min
🏷️ LABELS: 🟢, 🧩 Frontend
📍 LISTA: 🏗️ EM DESENVOLVIMENTO

---

📦 CARDS TÉCNICOS ADICIONAIS (úteis para fluxo)

Card: Analisar performance do endpoint `/query`

📋 DESCRIÇÃO: Rodar `analyze_db.py` e verificar planos de execução para queries pesadas. Sugerir índices.

CRITÉRIOS:
- [ ] Executado `analyze_db.py`
- [ ] Relatório com 3 recomendações de índice

Card: Gerar amostra CSV para QA

📋 DESCRIÇÃO: Gerar CSV com 500 registros amostrais para testes manuais no Excel/PowerBI.

CRITÉRIOS:
- [ ] CSV `exports/sample_500.csv` criado
- [ ] Compartilhar via Google Drive/OneDrive

Card: Limpeza de arquivos temporários `exports/`

📋 DESCRIÇÃO: Implementar script que remove arquivos mais antigos que X dias em `exports/`.

CRITÉRIOS:
- [ ] Script `scripts/cleanup_exports.py` criado
- [ ] Agendamento sugerido (cron/windows task)

---

🧾 MODELO RÁPIDO DE CARD (copiar e colar)

```
[TIPO] Título curto

📋 DESCRIÇÃO:
Breve descrição.

🎯 CRITÉRIOS DE ACEITE:
- [ ] Item 1
- [ ] Item 2

📊 ESTIMATIVA: Xmin
🏷️ LABELS: ..., ...
📍 LISTA: 🏗️ EM DESENVOLVIMENTO
```

---

🔄 SUGESTÕES DE SPRINT (exemplos)

Sprint 1 (setup inicial):
- Validar DB e Git LFS
- Rodar import exemplo
- Gerar aggregates
- Testar `/filters` e `/query`

Sprint 2 (paridade e export):
- Refatorar `build_where_and_params`
- Implementar export streaming/job
- Escrever smoke tests

Sprint 3 (polimento):
- Melhorar frontend (filtros e UX)
- Documentação e README
- Limpeza e automações

---

🔗 Links úteis (colar nos cards)

- README: `README.md`
- Scripts principais: `import_data.py`, `create_aggregates.py`, `analyze_db.py`
- Pasta exports: `exports/`
- Contato: Victor Vasconcelos — +55 61 98438-5187

---

Fim do arquivo — copie os cards que quiser e cole no seu Trello.
