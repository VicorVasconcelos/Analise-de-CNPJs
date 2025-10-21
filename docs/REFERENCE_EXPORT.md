<!-- Copied from root REFERENCE_EXPORT.md -->

Documentação sobre o formato de exportação de CNPJ.
```markdown
Canonical export reference

Path (kept in place as you requested):

c:\Users\victor.vasconcelos\Documents\Dashboard\cnpj_exportacao_20251016_173832.csv

Purpose:
- This file is the canonical CSV layout and sample for exported spreadsheets.
- Use this file as the authoritative column order, headers and formatting for all exports.

How to validate an export locally:
- Generate an export using the project's test exporter:

    python tools\generate_export_with_socios.py

- Compare with the reference using the included validator:

    python tools\validate_export_against_reference.py

The validator checks header order and the first 10 rows for exact equality (field-by-field) and prints any differences.
````markdown
<!-- Copiado do REFERENCE_EXPORT.md raiz -->

Documentação sobre o formato canônico de exportação do CNPJ.

Path (armazenamento canônico):

c:\Users\victor.vasconcelos\Documents\Dashboard\cnpj_exportacao_20251016_173832.csv

Propósito:
- Este arquivo é o layout CSV canônico e o exemplo para as planilhas exportadas.
- Use este arquivo como referência autoritativa para a ordem das colunas, cabeçalhos e formatação de todas as exportações.

Como validar uma exportação localmente:
1) Gere uma exportação usando o exportador de teste do projeto:

    python tools\generate_export_with_socios.py

2) Compare com a referência usando o validador incluído:

    python tools\validate_export_against_reference.py

O validador verifica a ordem dos cabeçalhos e as primeiras 10 linhas para igualdade exata (campo a campo) e imprime quaisquer diferenças.

Diretrizes rápidas:
- Não altere a ordem das colunas nem os nomes dos cabeçalhos sem atualizar este documento.
- Para mudanças no layout, crie uma nova versão do CSV, registre a alteração no README e atualize o contrato de compatibilidade.

````
