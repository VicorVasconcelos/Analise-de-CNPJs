# ROADMAP - Sistema de Análise de CNPJs (resumo)

Objetivo: coletar, filtrar, analisar e exportar dados públicos de empresas.

Stack principal:
- Backend: Python (Flask)
- Banco: SQLite local (`data/cnpj_database.db`)
- Frontend: HTML/CSS/JavaScript simples

Contato: Victor Vasconcelos — +55 61 98438-5187

Observação importante (contrato de export):
- O arquivo `cnpj_exportacao_20251016_173832.csv` é a exportação canônica. Não altere a ordem ou os nomes das colunas sem atualizar o contrato de compatibilidade.

Fases e responsáveis (resumido):
- Fase 1 — Setup e import (Victor): validar Git LFS, rodar import de exemplo, gerar aggregates e aplicar índices.
- Fase 2 — Paridade query/export (Victor): garantir que `/export` use a mesma lógica do `/query` e produza export estável.
- Fase 3 — Performance e aggregates (Victor): aplicar índices, melhorar aggregates e implementar cache TTL para `/filters`.
- Fase 4 — Testes e QA (Victor): criar smoke tests e gerar CSV amostral para QA.
- Fase 5 — Frontend e documentação (Samuel + Victor): Samuel cuida do frontend e UX; Victor cuida dos exemplos e da documentação técnica.
- Fase 6 — Operações (Victor): backups, limpeza de exports e política de LFS.

Como usar este arquivo:
- Copie os cards importantes para o Trello seguindo a prioridade: Crítico → Alto → Médio → Baixo.
- Use o `cards.json` gerado pelos scripts para criar/atualizar o board automaticamente.

Métricas rápidas de sucesso (exemplos):
- `/filters` p95 abaixo de 1s.
- Exports retornam o mesmo número de registros que `/query` para a mesma carga.

Riscos principais e mitigação:
- Git LFS sem cota: manter apenas amostras no repositório e armazenar o DB completo em storage externo.
- Export muito grande: utilizar streaming ou jobs em background.

Milestones sugeridos:
- M1 (setup + import) — 2 semanas — responsável: Victor
- M2 (paridade + export) — 4 semanas — responsável: Victor
- M3 (aggregates + cache) — 8 semanas — responsável: Victor
- M4 (tests + QA) — 10 semanas — responsável: Victor
- M5 (docs + ops) — 12 semanas — responsável: Victor

---

Se desejar, atualizo também os arquivos de Sprints e Setup para a mesma linguagem e formatação. Diga se quer que eu prossiga.