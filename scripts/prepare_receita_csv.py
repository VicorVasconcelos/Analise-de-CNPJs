import argparse
import re
import shutil
from pathlib import Path


def build_target_name(source_name: str) -> str:
    upper_name = source_name.upper()
    idx = upper_name.rfind('.CSV')

    if idx != -1:
        target = source_name[: idx + 4]
    else:
        stem = source_name.rsplit('.', 1)[0] if '.' in source_name else source_name
        target = f"{stem}.csv"

    target = re.sub(r"\.CSV$", ".csv", target, flags=re.IGNORECASE)
    if not target.lower().endswith('.csv'):
        target = f"{target}.csv"

    return target


def convert_tree(base_dir: Path, overwrite: bool = False) -> tuple[int, int, int]:
    converted = 0
    skipped = 0
    already_csv = 0

    for source in base_dir.rglob('*'):
        if not source.is_file():
            continue

        if source.name.lower().endswith('.csv'):
            already_csv += 1
            continue

        target_name = build_target_name(source.name)
        target_path = source.with_name(target_name)

        if target_path.exists() and not overwrite:
            skipped += 1
            continue

        shutil.copy2(source, target_path)
        converted += 1

    return converted, skipped, already_csv


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Padroniza arquivos da Receita para extensão .csv sem alterar conteúdo.'
    )
    parser.add_argument(
        'base_dir',
        help='Diretório base com as pastas de dados da Receita.'
    )
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Sobrescreve .csv já existentes.'
    )

    args = parser.parse_args()
    base_dir = Path(args.base_dir)

    if not base_dir.exists() or not base_dir.is_dir():
        raise SystemExit(f'Diretório inválido: {base_dir}')

    converted, skipped, already_csv = convert_tree(base_dir, overwrite=args.overwrite)

    print('Conversão concluída.')
    print(f'Base: {base_dir}')
    print(f'Arquivos convertidos: {converted}')
    print(f'Arquivos já em .csv: {already_csv}')
    print(f'Arquivos ignorados (csv existente): {skipped}')


if __name__ == '__main__':
    main()
