```markdown
Trello Tool
===========

Ferramenta unificada para operações com Trello usadas neste projeto.

Arquivo principal: `trello_tool.py`

Credenciais
-----------

Defina as variáveis de ambiente no Windows (cmd.exe):

```bat
set TRELLO_KEY=your_key
set TRELLO_TOKEN=your_token
set TRELLO_BOARD_ID=your_board_id
```

Ou crie um arquivo `.trello_credentials.json` na raiz do projeto com:

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

Buscar todos os cards e gravar em `trello_created_cards.json`:

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

- Os arquivos de credenciais **não devem** ser versionados (há `.gitignore` para `.trello_credentials.json`).
- As operações de deleção só acontecem quando confirmadas pelo usuário no menu interativo ou usando o código que chama explicitamente a função de deleção.
- Teste primeiro com credenciais de um board de staging, se possível.

Instalar dependências
---------------------

Este script usa a biblioteca `requests`. Se você recebeu um erro `ModuleNotFoundError: No module named 'requests'`, instale as dependências com:

```bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Se estiver usando o virtualenv fornecido no repositório (`.venv`), ative antes de instalar:

```bat
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

```
