
## Guia rápido de setup (versão curta)

Este arquivo tem os passos essenciais para alguém novo configurar o projeto e o board do Trello. Objetivo: ser curto, prático e direto.

Responsáveis principais: Victor (backend/DB/tests/docs) e Samuel (frontend/UI)

1) Preparar ambiente (Windows - PowerShell)

```cmd
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt  # se existir
```

2) Rodar a aplicação local

```cmd
python app.py
```

3) Importar dados de exemplo

```cmd
python import_data.py --input "caminho\para\arquivo.csv"
python create_aggregates.py
```

4) Git LFS (quando for necessário versionar `data/cnpj_database.db`)

```cmd
git lfs install
git lfs track "data/cnpj_database.db"
git add .gitattributes
git add data/cnpj_database.db
git commit -m "track db with lfs"
git push origin master
```

Nota: prefira compartilhar amostras (`exports/sample_500.csv`) em vez do DB completo quando possível.

Templates curtos de card (copiar e colar)

- Importação:

```
[IMPORT] Nome do arquivo

DESCRIÇÃO: breve descrição da fonte
CRITÉRIOS: importar para DB; validar colunas; gerar aggregates
RESPONSÁVEL: Victor Vasconcelos
```

- Endpoint `/filters`:

```
[BACKEND] /filters

DESCRIÇÃO: retorna dados para os filtros do frontend
CRITÉRIOS: usa aggregates quando disponíveis; format {value,label,count}
RESPONSÁVEL: Victor Vasconcelos
```

- Frontend (exemplo):

```
[FRONTEND] Ajustar script.js

DESCRIÇÃO: tornar loadFilters() tolerante a diferentes formatos
CRITÉRIOS: aceita {value,label,count} e {uf,count}
RESPONSÁVEL: Samuel Carvalho
```

Automações rápidas sugeridas no Trello:
- Ao mover para "Em desenvolvimento": atribuir responsável padrão e adicionar checklist técnico.
- Ao mover para "Testando": anexar logs relevantes.

Boas práticas:
- Gerar aggregates após grandes imports.
- Para exports grandes, gerar arquivo e servir via `/download`.

Contatos:
- Victor Vasconcelos — +55 61 98438-5187 (backend/DB)
- Samuel Carvalho — (frontend)
