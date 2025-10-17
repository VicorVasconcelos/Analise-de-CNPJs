📋 TRELLO - LISTA DE CARTÕES PARA O PROJETO (VERSÃO EXPLICADA E SIMPLES)

Este arquivo traz cartões prontos para colar no Trello. Cada cartão tem:

- Nome do card
- Quem é o responsável
- Descrição curta e fácil de entender
- Passos práticos que você deve executar (1, 2, 3)
- Critérios de aceite (checáveis)
- Tempo estimado, labels e lista recomendada

Contato do projeto: Victor Vasconcelos — +55 61 98438-5187

Como usar este arquivo:

- Copie um bloco de cartão inteiro e cole no Trello para criar o card.
- Siga os passos (Passos para executar) e marque os critérios de aceite.
- Responsáveis: Victor (backend, DB, testes, docs); Samuel (frontend/UI).

---

SEÇÃO A — CARTÕES CRÍTICOS (FAZER PRIMEIRO)

1) [DB] Validar `cnpj_database.db` e Git LFS
   Responsável: Victor Vasconcelos
   Descrição curta: Verificar se o arquivo do banco está sendo versionado com Git LFS e documentar como clonar corretamente.
   Passos para executar:

1. Verificar `.gitattributes` contém `cnpj_database.db`.
2. Rodar `git lfs ls-files` e confirmar que `cnpj_database.db` aparece.
3. Escrever 3 linhas no README explicando como clonar com LFS (comando mínimo).
   Critérios de aceite:

- [ ] `.gitattributes` tem `cnpj_database.db`.
- [ ] `git lfs ls-files` mostra `cnpj_database.db`.
- [ ] README tem instrução curta de clone com LFS.
  Tempo estimado: 15 min
  Labels: 🔴 Crítico, 🗄️ DB
  Lista recomendada: A fazer

2) [BACKEND] Monitorar e otimizar `/filters`
   Responsável: Victor Vasconcelos
   Descrição curta: Garantir que a rota `/filters` continue estável e medir tempos para detectar regressões.
   Passos para executar:

1. Executar chamadas de teste para `/filters` em staging e produção (se disponível).
2. Criar alerta simples (ex.: se tempo > 2s ou erro 5xx) no sistema de logs/monitor.
3. Adicionar no README um pequeno exemplo do formato `{value,label,count}`.
   Critérios de aceite:

- [ ] `/filters` retorna 200 em staging/prod nas amostras testadas.
- [ ] Alerta configurado (tempo > 2s ou erro 5xx).
- [ ] README tem exemplo do formato de resposta.
- [ ] Métricas básicas (média e p95) coletadas e registradas.
  Tempo estimado: 1 h
  Labels: 🟠 Alto, 🧰 Backend, 🧪 Testes
  Lista recomendada: A fazer

3) [DB] Criar índices para colunas de filtro
   Responsável: Victor Vasconcelos
   Descrição curta: Adicionar índices nas colunas mais usadas nos filtros (uf, cnae, natureza, municipio) para acelerar consultas.
   Passos para executar:

1. Atualizar `create_indexes.sql` com os índices sugeridos.
2. Aplicar os índices na base de teste.
3. Medir tempo de `/filters` e `/query` antes e depois.
   Critérios de aceite:

- [ ] `create_indexes.sql` atualizado.
- [ ] Índices aplicados sem erro.
- [ ] Tempo de consulta reduzido (medir p95 ou média).
  Tempo estimado: 45 min
  Labels: 🔴 Crítico, 🗄️ DB
  Lista recomendada: A fazer

4) [BACKEND] Paridade entre `/query` e `/export`
   Responsável: Victor Vasconcelos
   Descrição curta: Garantir que o CSV gerado por `/export` contenha os mesmos registros que `/query` quando usado o mesmo filtro.
   Passos para executar:

1. Implementar (ou confirmar existência de) `build_where_and_params(filtros)` central.
2. Rodar um teste que compara contagem e hash entre `/query` (tudo) e `/export` (CSV).
3. Corrigir diferenças e documentar o procedimento.
   Critérios de aceite:

- [ ] Função central de WHERE existe e tem testes.
- [ ] Hash/contagem entre `/query` e `/export` coincidem nos testes.
  Tempo estimado: 1 h
  Labels: 🔴 Crítico, 🧰 Backend, 📊 Export
  Lista recomendada: A fazer

---

SEÇÃO B — PRIORIDADE ALTA

5) [BACKEND] Cache TTL para `/filters`
   Responsável: Victor Vasconcelos
   Descrição curta: Implementar cache em memória com tempo (TTL) para reduzir latência nas chamadas repetidas.
   Passos para executar:

1. Implementar cache configurável (p.ex. TTL = 300s por padrão).
2. Adicionar opção de ligar/desligar via configuração.
3. Medir tempos antes/depois para confirmar melhoria.
   Critérios de aceite:

- [ ] Cache ativável por configuração.
- [ ] TTL padrão documentado no README.
- [ ] Teste mostra redução de tempo após a primeira chamada.
  Tempo estimado: 45 min
  Labels: 🟠 Alto, 🧰 Backend
  Lista recomendada: A fazer

6) [DB] Gerar aggregates
   Responsável: Victor Vasconcelos
   Descrição curta: Script que gera tabelas `aggregates_*` usadas pelos filtros para reduzir custo das consultas.
   Passos para executar:

1. Rodar `create_aggregates.py` para gerenciar `aggregates_ufs`, `aggregates_cnaes`, `aggregates_naturezas`.
2. Garantir que o script é idempotente (pode rodar várias vezes).
3. Documentar peq. instrução no README.
   Critérios de aceite:

- [ ] Scripts geram as tabelas esperadas.
- [ ] Script é idempotente.
- [ ] README atualizado.
  Tempo estimado: 1 h
  Labels: 🟠 Alto, 🗄️ DB, 📦 Importação
  Lista recomendada: A fazer

7) [BACKEND] Export streaming / job background
   Responsável: Victor Vasconcelos
   Descrição curta: Para exports grandes, criar processo que gera CSV sem travar o servidor (streaming ou job em background com link de download).
   Passos para executar:

1. Implementar opção de streaming ou job (escolher uma estratégia).
2. Salvar arquivos em `exports/` e criar rota `/download/<file>`.
3. Adicionar limpeza automática de arquivos antigos.
   Critérios de aceite:

- [ ] Export grande não bloqueia o servidor.
- [ ] Arquivos salvos em `exports/` e acessíveis por `/download/<file>`.
- [ ] Limpeza automática implementada.
  Tempo estimado: 2 h
  Labels: 🟠 Alto, 📊 Export
  Lista recomendada: A fazer

---

SEÇÃO C — MÉDIA PRIORIDADE (FRONTEND / TESTES / DOCS)

8) [FRONTEND] Ajustar `script.js` para formatos múltiplos
   Responsável: Samuel Carvalho
   Descrição curta: Fazer o frontend aceitar diferentes formatos de filtros que o backend pode enviar.
   Passos para executar:

1. Atualizar `loadFilters()` para lidar com `{value,label,count}` e `{uf,count}`.
2. Garantir ordenação alfabética das UFs no dropdown.
3. Testar manualmente no browser.
   Critérios de aceite:

- [ ] `loadFilters()` aceita os dois formatos.
- [ ] UFs ordenadas no dropdown.
- [ ] Teste manual OK.
  Tempo estimado: 30 min
  Labels: 🟡, 🧩 Frontend
  Lista recomendada: A fazer

9) [TESTES] Smoke tests endpoints
   Responsável: Victor Vasconcelos
   Descrição curta: Escrever testes simples para evitar regressões (health, filters, query).
   Passos para executar:

1. Criar `tests/smoke_tests.py` com 3 testes básicos.
2. Instruir como rodar `pytest` no README.
3. Executar e corrigir eventuais falhas.
   Critérios de aceite:

- [ ] 3 testes implementados.
- [ ] `pytest` roda localmente e testes passam.
  Tempo estimado: 45 min
  Labels: 🟡, 🧪 Testes
  Lista recomendada: A fazer

10) [DOCS] Exemplos `/query` / `/export`
    Responsável: Victor Vasconcelos
    Descrição curta: Colocar exemplos práticos no README para facilitar uso pelas equipes.
    Passos para executar:

1. Adicionar 2 exemplos de payload no README (um para `/query` e outro para `/export`).
2. Incluir instrução rápida para baixar e validar CSV.
   Critérios de aceite:

- [ ] README com 2 exemplos práticos.
- [ ] Instrução de validação do CSV presente.
  Tempo estimado: 30 min
  Labels: 🟡, 🟤 Docs
  Lista recomendada: A fazer

---

SEÇÃO D — BAIXA PRIORIDADE / ITENS MENORES

11) [FRONTEND] Footer com contato
    Responsável: Samuel Carvalho
    Descrição curta: Adicionar footer com nome e telefone no `index.html`.
    Passos para executar:

1. Inserir markup simples no `index.html`.
2. Estilizar de forma discreta no `styles.css`.
   Critérios de aceite:

- [ ] Footer presente com contato.
- [ ] Estilo simples e não invasivo.
  Tempo estimado: 15 min
  Labels: 🟢, 🧩 Frontend
  Lista recomendada: Concluído

12) [FRONTEND] Ajustes visuais (CSS)
    Responsável: Samuel Carvalho
    Descrição curta: Pequenos ajustes no `styles.css` para legibilidade e consistência.
    Passos para executar:

1. Ajustar espaçamento e padding de botões.
2. Verificar fontes e tamanhos em telas comuns.
   Critérios de aceite:

- [ ] Espaçamentos e botões padronizados.
- [ ] Visual consistente.
  Tempo estimado: 20 min
  Labels: 🟢, 🧩 Frontend
  Lista recomendada: A fazer

---

ITENS TÉCNICOS ÚTEIS (copiar como cards quando precisar)

- Analisar performance do endpoint `/query` (rodar `analyze_db.py` e sugerir 3 índices).
- Gerar amostra CSV `exports/sample_500.csv` para QA.
- Criar script `scripts/cleanup_exports.py` para remover arquivos antigos em `exports/`.

MODELO RÁPIDO DE CARD (copiar/colar no Trello):

```
[TIPO] Título curto

DESCRIÇÃO: Texto curto
PASSOS: 1) ... 2) ...
CRITÉRIOS: - [ ] Item 1 - [ ] Item 2
RESPONSÁVEL: Nome
```

Fim do arquivo — copie o cartão que quiser e cole no Trello. Obrigado.
