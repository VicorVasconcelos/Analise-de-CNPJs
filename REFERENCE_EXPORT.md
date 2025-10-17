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