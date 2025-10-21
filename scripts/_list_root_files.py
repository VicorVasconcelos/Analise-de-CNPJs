from pathlib import Path
root = Path(__file__).resolve().parents[1]
all_files = [p for p in root.rglob('*') if p.is_file()]
by_name = {}
for p in all_files:
    name = p.name
    by_name.setdefault(name, []).append(p)

root_files = [p for p in root.iterdir() if p.is_file()]
dups = {name: paths for name, paths in by_name.items() if len(paths) > 1}
print('Files at root:', len(root_files))
print('Duplicate basenames across tree (count):', len(dups))
for name, paths in sorted(dups.items()):
    print('\n===', name)
    for p in paths:
        print(' -', p)

print('\nLoose root files:')
for p in sorted(root_files):
    if p.name.startswith('.') or p.name in ('README.md', 'requirements.txt'):
        continue
    print('-', p.name)
