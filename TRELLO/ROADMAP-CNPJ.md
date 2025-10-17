# ROADMAP - Sistema de Análise de CNPJs (versão curta)

Objetivo rápido: coletar, filtrar, analisar e exportar dados públicos de empresas. Backend em Python (Flask), DB local em SQLite (`cnpj_database.db`), frontend em JS simples.

Contato: Victor Vasconcelos — +55 61 98438-5187

Observação importante (contrato de export):
- O arquivo `cnpj_exportacao_20251016_173832.csv` é a exportação canônica. Não mudar ordem/nomes de colunas enquanto trabalhamos nas otimizações.

Fases resumidas e responsáveis (texto simples)
- Fase 1 — Setup e import (Victor): validar Git LFS, rodar import exemplo, gerar aggregates e aplicar índices.
- Fase 2 — Paridade query/export (Victor): garantir que `/export` use a mesma lógica do `/query` e produzir export estável.
- Fase 3 — Performance e aggregates (Victor): aplicar índices, melhorar aggregates e implementar cache TTL para `/filters`.
- Fase 4 — Testes e QA (Victor): criar smoke tests e gerar CSV amostral para QA.
- Fase 5 — Frontend e documentação (Samuel + Victor): Samuel cuida do frontend e UX; Victor cuida de exemplos e docs técnicos.
- Fase 6 — Operações (Victor): backups, limpeza de exports e política de LFS.

Como usamos este arquivo:
- Copie os cards importantes para o Trello seguindo as prioridades: Críticos → Alto → Médio → Baixo.
- Use `cards.json` gerado pelos scripts para criar/atualizar o board automaticamente.

Métricas rápidas de sucesso (exemplos fáceis de medir):
- `/filters` p95 abaixo de 1s.
- Exports geram o mesmo número de registros que `/query` para o mesmo payload.

Riscos principais e mitigação direta:
- Git LFS sem quota: manter apenas amostras no repositório e armazenar o DB completo em storage externo.
- Export muito pesado: usar streaming ou job background.

Milestones curtos (sugestão):
- M1 (setup + import) — 2 semanas — responsável: Victor
- M2 (paridade e export) — 4 semanas — responsável: Victor
- M3 (aggregates + cache) — 8 semanas — responsável: Victor
- M4 (tests + QA) — 10 semanas — responsável: Victor
- M5 (docs + ops) — 12 semanas — responsável: Victor

---

Se quiser, eu atualizo também os arquivos de Sprints e Setup para a mesma linguagem clara. Diga se quer que eu prossiga com isso.