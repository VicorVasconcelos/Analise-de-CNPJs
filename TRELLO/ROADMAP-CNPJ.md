# 🗺️ ROADMAP - Sistema de Análise de CNPJs

## 🎯 Visão Geral do Projeto

O objetivo deste roadmap é planejar o desenvolvimento do sistema de análise de CNPJs: coleta, armazenamento, filtragem, análise e exportação de dados públicos de empresas. Stack principal: Python (Flask) + SQLite (`cnpj_database.db`) para análises locais; frontend em vanilla JS. Banco grande gerenciado com Git LFS quando necessário. Contato: Victor Vasconcelos — +55 61 98438-5187

## 📋 Labels Sugeridas (Trello)
- 🔴 CRÍTICO — Bloqueador
- 🟠 ALTO — Prioridade alta (filtros, export, índices)
- 🟡 MÉDIO — Melhorias e refatorações
- 🟢 BAIXO — UI/UX e documentação
- 🗄️ DB — Scripts e índices (`create_aggregates.py`, `create_indexes.sql`)
- 🧰 Backend — Flask (endpoints `/filters`, `/query`, `/export`, `/download`)
- 🧩 Frontend — vanilla JS (`index.html`, `script.js`)
- 📦 Import — Scripts de importação (`import_data.py`, `import_estabelecimentos.py`)
- 📊 Export — CSV/streaming/exports
- 🧪 Testes — Smoke tests e automações
- 🟤 Docs — README, guias de uso

---

## 🚀 FASE 1: INICIALIZAÇÃO & INGRESSO DE DADOS (Sprint 1-2)
Objetivo: preparar ambiente, importar dados, criar aggregates e garantir operações básicas.

Sprint 1 — Setup & Import (2 semanas)
- Validar Git LFS para `cnpj_database.db` e documentar (README)
- Rodar import de amostra (`python import_data.py --input path/to/file.csv`)
- Gerar `aggregates_*` com `python create_aggregates.py`
- Aplicar índices iniciais (`create_indexes.sql`) e rodar `ANALYZE`
- Testes básicos: `/health`, `/filters` (shape e latência)

Métrica de sucesso:
- Import concluído e aggregates gerados
- `/filters` responde com shape esperado e latência média aceitável

Riscos:
- Arquivo CSV corrompido/encoding errado — ter rotina de limpeza
- Git LFS sem quota suficiente

---

## 🚀 FASE 2: PARIDADE DE FILTROS E EXPORT (Sprint 3-4)
Objetivo: garantir que os filtros utilizados pela UI e a exportação apliquem exatamente a mesma lógica.

Sprint 2 — Paridade e Export (2 semanas)
- Centralizar `build_where_and_params(filtros)` em `app.py`
- Implementar `/export` que usa a mesma função de WHERE (streaming ou job background)
- Testes: comparar contagens/hashes entre `/query` (full) e `/export` CSV
- Adicionar exemplos de payload `/query` e `/export` no README/Trello

Métrica de sucesso:
- Export gera CSV com os mesmos registros filtrados por `/query`
- Export grande executado sem travar o servidor (job/streaming)

Riscos:
- Operação de export muito pesada em memória → preferir streaming ou offload

---

## 🚀 FASE 3: PERFORMANCE & AGGREGATES (Sprint 5-6)
Objetivo: otimizar consultas e criar infraestrutura de aggregates, caching e monitoramento.

Sprint 3 — Índices & Aggregates (2 semanas)
- Revisar `create_indexes.sql` e aplicar índices nas colunas de filtro (uf, cnae_fiscal_principal, natureza_juridica, municipio)
- Melhorar `create_aggregates.py` para ser incremental e idempotente
- Implementar cache TTL para `/filters` (ex.: 300s)
- Executar `analyze_db.py` e aplicar recomendações

Sprint 4 — Monitoramento e métricas (2 semanas)
- Adicionar instrumentação de tempos (p50/p95/p99) nos endpoints críticos
- Configurar alert rules (ex.: tempo médio > 1.5s, p95 > 3s, erro 5xx)
- Logs estruturados e rotação de logs

Métrica de sucesso:
- p95 da rota `/filters` abaixo do objetivo (ex.: 1s)
- Cache reduz tempos e carga do DB

---

## 🚀 FASE 4: TESTES, QA E EXPORTS (Sprint 7-8)
Objetivo: garantir confiabilidade via testes automatizados e validar o fluxo de exportação.

Sprint 5 — Testes e QA (2 semanas)
- Implementar `tests/smoke_tests.py` com: `/health`, `/filters` (shape), `/query` (amostra)
- Integrar `pytest` ao processo de desenvolvimento local
- Gerar CSV de amostra `exports/sample_500.csv` para QA

Sprint 6 — Polishing export (2 semanas)
- Implementar streaming CSV com headers configuráveis
- Criar rota `/download/<file>` para servir arquivos gerados
- Implementar limpeza automática de arquivos antigos em `exports/`

Métrica de sucesso:
- Smoke tests verdes em ambiente local
- Export amostral validado por QA

---

## 🚀 FASE 5: UI/UX E DOCUMENTAÇÃO (Sprint 9-10)
Objetivo: refinamento do frontend, usabilidade e documentação para novos usuários.

Sprint 7 — Frontend (2 semanas)
- Ajustar `script.js` para ordenar UFs alfabeticamente e tolerar formatos de filtro
- Melhorar formulários de filtros e feedback de carregamento
- Adicionar footer com contato e instruções rápidas

Sprint 8 — Docs & Onboarding (2 semanas)
- Finalizar `README.md` com exemplos de payloads `/query` e `/export`
- Incluir instruções de Git LFS e clonagem do repositório
- Criar guia rápido de troubleshooting (logs, onde buscar erros)

Métrica de sucesso:
- Usuário novo consegue rodar app local em menos de 1 hora com README

---

## 🚀 FASE 6: OPERAÇÕES E MANUTENÇÃO (Sprint 11-12)
Objetivo: preparar rotinas operacionais para manter a base de dados e os exports.

Sprint 9 — Operações (2 semanas)
- Criar `scripts/cleanup_exports.py` para remoção de arquivos antigos
- Script de backup local (zip + upload para Drive/OneDrive)
- Playbook de incidentes (o que fazer se o DB corromper ou export travar)

Sprint 10 — Planejamento LFS (2 semanas)
- Avaliar uso de Git LFS e alternativas (hosting do DB, snapshots)
- Política de versionamento para DB (amostras vs full)

Métrica de sucesso:
- Rotinas de backup/limpeza funcionando
- Política de LFS definida e documentada

---

## 🧭 Dependências e Riscos Gerais
- Git LFS quotas podem limitar versionamento do DB (mitigação: usar apenas amostras ou storage externo)
- Exports massivos podem travar o servidor (mitigação: streaming e jobs)
- Dados sujos/encodings — ter pipeline de limpeza antes do import

---

## 📅 Milestones sugeridos
- M1 (setup + import) — 2 semanas
- M2 (paridade query/export) — 4 semanas
- M3 (aggregates + cache) — 8 semanas
- M4 (tests + QA) — 10 semanas
- M5 (prod-ready docs + ops) — 12 semanas

---

## 📞 Contato
Victor Vasconcelos — +55 61 98438-5187


---

*Arquivo gerado automaticamente como base para o Trello do projeto de Análise de CNPJs.*