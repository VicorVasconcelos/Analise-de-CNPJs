```markdown
Trello Tool
===========

Ferramenta unificada para operações com o Trello usadas neste projeto.

Arquivo principal: `trello_tool.py`

Credenciais
-----------

Defina as variáveis de ambiente no Windows (cmd.exe):

```bat
set TRELLO_KEY=seu_key
set TRELLO_TOKEN=seu_token
set TRELLO_BOARD_ID=seu_board_id
```

Ou crie um arquivo `config/.trello_credentials.json` com o conteúdo:

```json
{
  "key": "...",
  "token": "...",
  "board_id": "..."
}
```

Uso (exemplos)
---------------

Rodar menu interativo:

```bat
python scripts\trello_tool.py --interactive
```

Buscar todos os cards e salvar em `data/trello_created_cards.json`:

```bat
python scripts\trello_tool.py --fetch
```

Detectar duplicados e gerar relatório (arquivo em `archive/`):

```bat
python scripts\trello_tool.py --detect-duplicates
```

Criar cards em massa a partir de `cards.json` ou do markdown em `docs/trello/`:

```bat
python scripts\trello_tool.py --bulk-create
```

Notas
-----

- Os arquivos de credenciais **não devem** ser versionados (verifique que `config/.trello_credentials.json` está ignorado por `.gitignore`).
- Operações destrutivas (deleção) só ocorrem após confirmação explícita do usuário.
- Teste primeiro em um board de staging quando possível.

Instalar dependências
---------------------

Este script usa a biblioteca `requests`. Se ocorrer `ModuleNotFoundError: No module named 'requests'`, instale as dependências com:

```bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Se estiver usando o virtualenv do projeto (`.venv`), ative antes de instalar:

```bat
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

```
