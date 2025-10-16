import sys
import csv
import os
from collections import Counter

CANONICAL_HEADERS = [
    'CNPJ','RAZAO_SOCIAL','NOME_FANTASIA','SITUACAO_EMPRESA','DATA_SITUACAO',
    'ENDERECO_COMPLETO','CEP','UF','NOME_MUNICIPIO','TELEFONE_FORMATADO',
    'EMAIL','DESCRICAO_CNAE','DESCRICAO_NATUREZA','BAIRRO','PORTE',
    'CAPITAL_SOCIAL','OPCAO_SIMPLES','OPCAO_MEI','MATRIZ_FILIAL',
    'NOME_SOCIO','QUALIFICACAO_SOCIO','CPF_SOCIO'
]


def detect_dialect(path):
    with open(path, 'r', encoding='utf-8-sig', errors='replace') as f:
        sample = f.read(8192)
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample, delimiters=[',',';','\t','|'])
        except Exception:
            # fallback to semicolon
            class D:
                delimiter=';'
            dialect = D()
    return dialect


def normalize_file(path):
    dialect = detect_dialect(path)
    base, ext = os.path.splitext(path)
    out_path = base + '.normalized' + ext
    report_path = base + '.analysis.txt'

    total = 0
    mismatches = 0
    counts = Counter()
    examples = []

    with open(path, 'r', encoding='utf-8-sig', errors='replace') as inf:
        reader = csv.reader(inf, delimiter=dialect.delimiter)
        try:
            header = next(reader)
        except StopIteration:
            print('Arquivo vazio')
            return
        header_count = len(header)

        # prepare writer
        with open(out_path, 'w', encoding='utf-8-sig', newline='') as outf:
            writer = csv.writer(outf, delimiter=dialect.delimiter)
            writer.writerow(header)

            for i, row in enumerate(reader, start=2):
                total += 1
                rc = len(row)
                counts[rc] += 1
                if rc != header_count:
                    mismatches += 1
                    if len(examples) < 10:
                        examples.append((i, rc, row))
                    # normalize: if more columns, join extras into last column
                    if rc > header_count:
                        combined = row[:header_count-1] + [''.join(row[header_count-1:])]
                        writer.writerow(combined)
                    else:
                        # fewer columns: pad with empty strings
                        padded = row + [''] * (header_count - rc)
                        writer.writerow(padded)
                else:
                    writer.writerow(row)

    # write report
    with open(report_path, 'w', encoding='utf-8') as rf:
        rf.write(f'Input file: {path}\n')
        rf.write(f'Output file: {out_path}\n')
        rf.write(f'Total data rows: {total}\n')
        rf.write(f'Header columns: {header_count}\n')
        rf.write('Row counts frequency:\n')
        for k, v in counts.most_common():
            rf.write(f'  {k} columns: {v} rows\n')
        rf.write(f'Mismatched rows: {mismatches}\n')
        if examples:
            rf.write('\nExamples (line_number, columns_count):\n')
            for ln, rc, row in examples:
                rf.write(f'Line {ln}: {rc} columns -> {row[:5]}...\n')

        rf.write('\nCanonical headers suggestion (expected columns: {}):\n'.format(len(CANONICAL_HEADERS)))
        rf.write(','.join(CANONICAL_HEADERS) + '\n')

    print('Analysis complete')
    print('Output:', out_path)
    print('Report:', report_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python check_export_file.py <path-to-csv>')
        sys.exit(1)
    path = sys.argv[1]
    if not os.path.exists(path):
        print('File not found:', path)
        sys.exit(1)
    normalize_file(path)
