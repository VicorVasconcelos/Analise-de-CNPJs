🎯 SPRINTS PLANEJADOS — Projeto Análise de CNPJ

Guia de planejamento de sprints adaptado ao projeto de análise de CNPJs. Estrutura pensada para um fluxo ágil (2 semanas por sprint) em desenvolvimento solo ou time pequeno.

Contato: Victor Vasconcelos — +55 61 98438-5187

---

1. CAPACIDADE E PRIORIDADES

Capacidade sugerida por sprint (2 semanas):
- Máximo: 80 horas
- Ideal: 60-70 horas
- Seguro (com buffer): 50-60 horas

Categoria de prioridade:
- 🔴 Crítico — bloqueadores e estabilidade do DB/backend
- 🟠 Alto — performance, export e automações
- 🟡 Médio — melhorias funcionais e testes
- 🟢 Baixo — UI/UX e documentação

---

2. SPRINT 1 — FUNDAÇÃO (Setup & Import)
Duração: 2 semanas | Capacidade alvo: 60 horas

Objetivo: Garantir ambiente local, importar dados e gerar aggregates.

Backlog sugerido:
- ✅ Validar Git LFS e `cnpj_database.db` (Card: Validar DB e Git LFS)
- ✅ Executar import exemplo (`python import_data.py --input ...`)
- ✅ Gerar `aggregates_*` (rodar `python create_aggregates.py`)
- ✅ Aplicar índices essenciais (`create_indexes.sql`)
- ✅ Testar endpoints básicos: `/health`, `/filters` (smoke)

Metas do sprint:
- DB import concluído e aggregates gerados
- Endpoints básicos respondendo com payloads corretos
- Documentação mínima no README para setup

Métricas de sucesso:
- Import completo sem falhas
- `/filters` latência média < 500ms (após aggregates)

---

3. SPRINT 2 — PARIDADE QUERY / EXPORT (Filtros e Export)
Duração: 2 semanas | Capacidade alvo: 65 horas

Objetivo: Garantir que `/query` e `/export` apliquem os mesmos filtros e oferecer export robusto.

Backlog sugerido:
- Refatorar `build_where_and_params(filtros)` para centralizar lógica
- Implementar `/export` usando a mesma lógica (streaming ou job)
- Teste que compara `/query` (full) com `/export` CSV (hash/contagem)
- Documentar payloads de `/query` e `/export` no README

Metas do sprint:
- `/export` gera CSV com os mesmos registros que `/query`
- Export de grande volume roda sem travar o servidor

Métricas de sucesso:
- Tempo de geração do CSV para 1M registros (estimativa/observação)
- Hash/contagem entre query/export conflit-free

---

4. SPRINT 3 — PERFORMANCE E MONITORAMENTO
Duração: 2 semanas | Capacidade alvo: 60 horas

Objetivo: Reduzir latências, adicionar cache, métricas e alertas.

Backlog sugerido:
- Implementar cache TTL para `/filters`
- Melhorar índices e reexecutar ANALYZE (usar `analyze_db.py`)
- Implementar logs e timings (P95, mediana)
- Criar alertas (ex.: tempo > 2s, erro 5xx)
- Automatizar geração de aggregates periódica (cron / scheduled task)

Metas do sprint:
- Reduzir p95 de `/filters` em X%
- Alertas configurados para regressões

Métricas de sucesso:
- p95 e p99 reduzidos
- Alert fired teste (simulado) funciona

---

5. SPRINT 4 — TESTES E QA
Duração: 2 semanas | Capacidade alvo: 50 horas

Objetivo: Cobertura mínima de smoke tests e automatização de verificações.

Backlog sugerido:
- Criar `tests/smoke_tests.py` (health, filters shape, query basic)
- Integrar `pytest` localmente
- Gerar amostra de CSVs para QA (`exports/sample_500.csv`)
- Documentar como rodar testes no README

Metas do sprint:
- Testes automáticos rodando localmente
- Processo de QA para validação de exports

Métricas de sucesso:
- 3 smoke tests verdes
- Amostra CSV validada por QA

---

6. SPRINT 5 — POLIMENTO & UI
Duração: 2 semanas | Capacidade alvo: 45 horas

Objetivo: Melhorias na interface, organização de filtros e usabilidade.

Backlog sugerido:
- Ajustar `script.js` para ordenar UFs e tolerar formatos
- Adicionar footer com contato
- Pequenas melhorias em `styles.css`
- Documentar fluxo de uso do frontend (passo-a-passo)

Metas do sprint:
- UI agradável e consistente
- Documentação UX mínima para usuários

---

7. SPRINT 6 — OPERAÇÕES & MANUTENÇÃO
Duração: 2 semanas | Capacidade alvo: 40 horas

Objetivo: Tarefas operacionais e scripts de manutenção.

Backlog sugerido:
- Escrever script de limpeza `scripts/cleanup_exports.py`
- Documentar processo de backup do DB (local/drive)
- Criar playbook de incidentes (o que fazer quando o DB falha)
- Revisar quotas de Git LFS e planejar estratégia de versionamento

Metas do sprint:
- Operações documentadas e scripts utilitários prontos

---

8. SPRINT PLANNING & REVIEW (CICLO SEMANAL)

Processo semanal sugerido:
- Segunda: Sprint planning rápido (30min) — selecionar cards da sprint
- Quinta: Checkpoint rápido (30min) — alinhar bloqueios
- Sexta: Review + Retrospectiva (45-60min)

Entregáveis semanais:
- Cards movidos para `✅ CONCLUÍDO`
- Logs e métricas atualizadas
- Notas de retrospectiva no Trello

---

9. TEMPLATE DE SPRINT (copiar e adaptar)

🏃‍♂️ SPRINT X - [NOME DO SPRINT]
📅 [Data Início] a [Data Fim] (2 semanas)

🎯 OBJETIVO PRINCIPAL:
[Descrição clara do objetivo principal deste sprint]

📊 CAPACIDADE PLANEJADA:
• Desenvolvedor: 50-70 horas

📋 BACKLOG DO SPRINT:
- [ ] Card A (Xh) — Prioridade
- [ ] Card B (Yh) — Prioridade

🎯 CRITÉRIOS DE SUCESSO:
- [ ] Critério 1
- [ ] Critério 2

---

10. LINKS E RECURSOS

- README: `README.md`
- Scripts: `import_data.py`, `create_aggregates.py`, `analyze_db.py`
- Pasta exports: `exports/`
- Contato: Victor Vasconcelos — +55 61 98438-5187
