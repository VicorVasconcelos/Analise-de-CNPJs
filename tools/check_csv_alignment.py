import sys
import csv

def main():
    if len(sys.argv) < 2:
        print('Usage: python tools/check_csv_alignment.py <csv_file>')
        return 2
    path = sys.argv[1]
    max_examples = 20
    try:
        with open(path, 'r', encoding='utf-8-sig', newline='') as fh:
            reader = csv.reader(fh, delimiter=';')
            try:
                header = next(reader)
            except StopIteration:
                print('Empty file')
                return 0
            expected = len(header)
            print(f'Header columns: {expected} -> {header}')
            total = 0
            mismatches = []
            for i, row in enumerate(reader, start=2):
                total += 1
                if len(row) != expected:
                    mismatches.append((i, len(row), row))
                    if len(mismatches) >= max_examples:
                        break
            print(f'Total data rows scanned: {total}')
            print(f'Mismatching rows found: {len(mismatches)}')
            if mismatches:
                print('First mismatches (row, cols_count):')
                for rnum, cnt, row in mismatches:
                    print(f'  Row {rnum}: {cnt} cols; sample: {row[:5]}')
            else:
                print('All rows match header column count.')
    except Exception as e:
        print('Error while checking CSV:', e)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
