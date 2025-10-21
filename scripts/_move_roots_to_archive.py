import os, shutil, time
root = r'c:\Users\victor.vasconcelos\Documents\Dashboard'
archive = os.path.join(root,'archive')
os.makedirs(archive, exist_ok=True)
for fname in ['script.js','styles.css','cards.json','README_TRELLO.md','REFERENCE_EXPORT.md']:
    src = os.path.join(root,fname)
    if os.path.exists(src):
        dst = os.path.join(archive, f'{fname}.bak_' + time.strftime('%Y%m%d_%H%M%S'))
        shutil.move(src, dst)
        print('moved', src, '->', dst)
    else:
        print('not found', src)
