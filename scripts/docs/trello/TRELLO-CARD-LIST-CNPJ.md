# Trello cards: Lista para criar - CNPJ Exportação

Esta lista contém cartões sugeridos para organizar tarefas relacionadas ao projeto de exportação/filtragem de CNPJ.

- [ ] Documentar endpoints principais (GET /stats, POST /query, POST /export-async)
- [ ] Implementar worker de exportação e monitoramento de jobs (scripts/export_worker.py)
- [ ] UI: página de export (formulário + lista de jobs com download)
- [ ] Criar agregados compostos (uf+cnae) para queries compostas
- [ ] Testes automatizados para endpoints críticos (/query, /export-async)
- [ ] Atualizar README com instruções de deploy (Windows & Linux)
- [ ] Validar índices do DB em staging e monitorar tempo de queries
- [ ] Criar rotina de limpeza para data/exports (retenção e pruning)
- [ ] Integrar criação de cartões com script de automação (scripts/trello_create_cards.py)

Observações:
- Não execute o script de criação sem TRELLO_KEY, TRELLO_TOKEN e LIST_ID.
- Os cartões podem ser refinados em subtarefas durante a triagem.
📋 NOME: [DB] Validar `data/cnpj_database.db` e Git LFS
📋 DESCRIÇÃO: Verificar se o arquivo do banco está versionado via Git LFS e documentar como clonar.
📌 RESPONSÁVEL: Victor Vasconcelos
🎯 PASSOS:
1) Confirmar que `.gitattributes` contém `data/cnpj_database.db`.
2) Rodar `git lfs ls-files` e confirmar que `data/cnpj_database.db` aparece.
3) Escrever 2–3 linhas no README com instrução de clone via LFS.
📊 CRITÉRIOS:
- [ ] `.gitattributes` tem `data/cnpj_database.db`.
- [ ] `git lfs ls-files` mostra `data/cnpj_database.db`.
- [ ] README com instrução curta de clone.
🕒 TEMPO: 15 min
🏷️ LABELS: 🔴 Crítico · 🗄️ DB
📍 LISTA: A fazer

📋 NOME: [BACKEND] Monitorar e otimizar `/filters`
📋 DESCRIÇÃO: Garantir estabilidade da rota `/filters` e medir tempos para detectar regressões.
📌 RESPONSÁVEL: Victor Vasconcelos
🎯 PASSOS:
1) Executar chamadas de teste para `/filters` em staging/produção.
2) Criar alerta (ex.: tempo > 2s ou erro 5xx).
3) Adicionar no README um exemplo `{value,label,count}`.
📊 CRITÉRIOS:
- [ ] `/filters` retorna 200 nas amostras.
- [ ] Alerta configurado.
- [ ] README com exemplo.
- [ ] Métricas (média e p95) registradas.
🕒 TEMPO: 1 h
🏷️ LABELS: 🟠 Alto · 🧰 Backend · 🧪 Testes

📋 NOME: [DB] Criar índices para colunas de filtro
📋 DESCRIÇÃO: Criar índices nas colunas (uf, cnae, natureza, municipio) para acelerar consultas.
📌 RESPONSÁVEL: Victor Vasconcelos
🎯 PASSOS:
1) Atualizar `create_indexes.sql`.
2) Aplicar índices na base de teste.
3) Medir tempo antes/depois.
📊 CRITÉRIOS:
- [ ] `create_indexes.sql` atualizado.
- [ ] Índices aplicados sem erro.
- [ ] Tempo de consulta reduzido.
🕒 TEMPO: 45 min
🏷️ LABELS: 🔴 Crítico · 🗄️ DB

📋 NOME: [BACKEND] Paridade entre `/query` e `/export`
📋 DESCRIÇÃO: Garantir que o CSV gerado por `/export` contenha os mesmos registros que `/query`.
📌 RESPONSÁVEL: Victor Vasconcelos
🎯 PASSOS:
1) Implementar/confirmar `build_where_and_params(filtros)`.
2) Rodar teste que compara contagem e hash entre `/query` e `/export`.
3) Corrigir diferenças e documentar.
📊 CRITÉRIOS:
- [ ] Função central de WHERE presente e testada.
- [ ] Hash/contagem entre `/query` e `/export` coincidem.
🕒 TEMPO: 1 h
🏷️ LABELS: 🔴 Crítico · 🧰 Backend · 📊 Export

📋 NOME: [BACKEND] Cache TTL para `/filters`
📋 DESCRIÇÃO: Implementar cache em memória com TTL para reduzir latência.
📌 RESPONSÁVEL: Victor Vasconcelos
🎯 PASSOS:
1) Implementar cache configurável (TTL = 300s sugerido).
2) Adicionar opção de ligar/desligar via configuração.
3) Medir tempos antes/depois.
📊 CRITÉRIOS:
- [ ] Cache ativável por configuração.
- [ ] TTL documentado no README.
- [ ] Teste mostra redução de tempo.
🕒 TEMPO: 45 min
🏷️ LABELS: 🟠 Alto · 🧰 Backend

📋 NOME: [DB] Gerar aggregates
📋 DESCRIÇÃO: Gerar tabelas `aggregates_*` usadas pelos filtros para reduzir custo de consulta.
📌 RESPONSÁVEL: Victor Vasconcelos
🎯 PASSOS:
1) Rodar `create_aggregates.py` assegurando idempotência.
2) Garantir que script roda várias vezes sem erro.
3) Documentar no README.
📊 CRITÉRIOS:
- [ ] Scripts geram tabelas esperadas.
- [ ] Script idempotente.
- [ ] README atualizado.
🕒 TEMPO: 1 h
🏷️ LABELS: 🟠 Alto · 🗄️ DB · 📦 Importação

📋 NOME: [BACKEND] Export streaming / job background
📋 DESCRIÇÃO: Para exports grandes, gerar CSV sem travar o servidor (streaming ou job background).
📌 RESPONSÁVEL: Victor Vasconcelos
🎯 PASSOS:
1) Implementar streaming ou job.
2) Salvar arquivos em `exports/` e criar rota `/download/<file>`.
3) Adicionar limpeza automática.
📊 CRITÉRIOS:
- [ ] Export grande não bloqueia servidor.
- [ ] Arquivos acessíveis em `exports/`.
- [ ] Limpeza automática implementada.
🕒 TEMPO: 2 h
🏷️ LABELS: 🟠 Alto · 📊 Export

📋 NOME: [FRONTEND] Ajustar `script.js` para formatos múltiplos
📋 DESCRIÇÃO: Fazer o frontend aceitar diferentes formatos de filtros enviados pelo backend.
📌 RESPONSÁVEL: Samuel Carvalho
🎯 PASSOS:
1) Atualizar `loadFilters()` para `{value,label,count}` e `{uf,count}`.
2) Garantir ordenação alfabética das UFs.
3) Testar manualmente.
📊 CRITÉRIOS:
- [ ] `loadFilters()` aceita ambos formatos.
- [ ] UFs ordenadas.
- [ ] Teste manual OK.
🕒 TEMPO: 30 min
🏷️ LABELS: 🟡 Frontend

📋 NOME: [TESTES] Smoke tests endpoints
📋 DESCRIÇÃO: Escrever testes simples para evitar regressões (health, filters, query).
📌 RESPONSÁVEL: Victor Vasconcelos
🎯 PASSOS:
1) Criar `tests/smoke_tests.py` com 3 testes.
2) Documentar como rodar `pytest`.
3) Rodar e ajustar.
📊 CRITÉRIOS:
- [ ] 3 testes implementados.
- [ ] `pytest` roda localmente.
🕒 TEMPO: 45 min
🏷️ LABELS: 🟡 Testes

📋 NOME: [DOCS] Exemplos `/query` / `/export`
📋 DESCRIÇÃO: Colocar exemplos práticos no README para uso da equipe.
📌 RESPONSÁVEL: Victor Vasconcelos
🎯 PASSOS:
1) Adicionar 2 exemplos de payload no README.
2) Incluir instrução rápida para validar CSV.
📊 CRITÉRIOS:
- [ ] README com exemplos.
- [ ] Instrução de validação do CSV.
🕒 TEMPO: 30 min
🏷️ LABELS: 🟡 Docs

MODELO RÁPIDO DE CARD (copiar/colar no Trello):

📋 NOME: [TIPO] Título curto
📋 DESCRIÇÃO: Texto curto
📌 RESPONSÁVEL: Nome
🎯 PASSOS:
1) ...
2) ...
📊 CRITÉRIOS:
- [ ] Item 1
- [ ] Item 2

Fim do arquivo — o conteúdo acima contém apenas cartões no formato esperado pelo script.
