
SPRINTS PLANEJADOS — versão simples

Objetivo: organizar trabalho em sprints de 2 semanas. Responsáveis principais: Victor (backend, DB, testes, docs) e Samuel (frontend, UI).

Capacidade sugerida por sprint:
- Ideal: ~60 horas

Prioridades (simples):
- 🔴 Crítico — estabilidade e correções importantes
- 🟠 Alto — performance e export
- 🟡 Médio — melhorias e testes
- 🟢 Baixo — UI e docs

Sprint 1 — Fundação (Victor)
- Validar Git LFS, rodar import de exemplo, gerar aggregates, aplicar índices e testar `/filters`.

Sprint 2 — Paridade query/export (Victor)
- Garantir que `/export` use mesma lógica do `/query`. Implementar export streaming ou job background.

Sprint 3 — Performance e monitoramento (Victor)
- Aplicar índices, rodar `analyze_db.py`, implementar cache TTL e criar alertas simples.

Sprint 4 — Testes e QA (Victor)
- Criar `tests/smoke_tests.py`, rodar `pytest`, gerar CSV de amostra `exports/sample_500.csv`.

Sprint 5 — Polimento e UI (Samuel + Victor)
- Samuel cuida do frontend (filtros, footer, CSS). Victor prepara exemplos e documentação.

Sprint 6 — Operações e manutenção (Victor)
- Scripts de limpeza, backups e playbook de incidentes.

Processo rápido:
- Segunda: planejar a semana (30min)
- Quinta: checkpoint rápido (30min)
- Sexta: review + retrospectiva (45min)

Template rápido de sprint (copiar e adaptar):
- SPRINT X — [Data início] a [Data fim]
- Objetivo: [texto curto]
- Backlog: copiar cards do `TRELLO-CARD-LIST-CNPJ.md`
- Critérios: 1-2 itens mensuráveis

Links úteis:
- README: `README.md`
- Scripts: `import_data.py`, `create_aggregates.py`, `analyze_db.py`
- Contato: Victor — +55 61 98438-5187
