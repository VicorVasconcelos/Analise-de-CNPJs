import shutil, time, os
src=r'c:\Users\victor.vasconcelos\Documents\Dashboard\index.html'
archive_dir=r'c:\Users\victor.vasconcelos\Documents\Dashboard\archive'
os.makedirs(archive_dir, exist_ok=True)
if os.path.exists(src):
    dst = os.path.join(archive_dir, 'index.html.bak_' + time.strftime('%Y%m%d_%H%M%S'))
    shutil.move(src, dst)
    print('moved', src, '->', dst)
else:
    print('src not found')
