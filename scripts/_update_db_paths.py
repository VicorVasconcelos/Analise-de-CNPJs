import io, os
root = r'c:\Users\victor.vasconcelos\Documents\Dashboard'
for dirpath, dirnames, filenames in os.walk(root):
    # skip .git and .venv
    if '.git' in dirpath or '\\.venv' in dirpath:
        continue
    for fname in filenames:
        if fname.endswith(('.py', '.md', '.txt', '.sql')):
            path = os.path.join(dirpath, fname)
            try:
                with open(path, 'r', encoding='utf-8') as fh:
                    txt = fh.read()
            except Exception:
                continue
            if 'data/cnpj_database.db' in txt:
                new = txt.replace('data/cnpj_database.db', 'data/data/cnpj_database.db')
                with open(path, 'w', encoding='utf-8') as fh:
                    fh.write(new)
                print('updated', path)
print('done')
