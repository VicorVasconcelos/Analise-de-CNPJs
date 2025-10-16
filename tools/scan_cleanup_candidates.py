import os, time, glob
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
keep_files = {'cnpj_database.db','cnpj_database.db-shm','cnpj_database.db-wal','README.md','app.py','index.html','styles.css','script.js'}
proposed = []
for dirpath, dirnames, filenames in os.walk(root):
    parts = set(dirpath.split(os.sep))
    if '.git' in parts or '.venv' in parts:
        continue
    for f in filenames:
        fp = os.path.join(dirpath,f)
        rel = os.path.relpath(fp, root)
        if f in keep_files:
            continue
        if fp.endswith('.py'):
            continue
        if f.startswith('cnpj_database.db'):
            continue
        if f.endswith('.csv') or f.endswith('.log') or f.endswith('.analysis.txt') or f.endswith('.normalized.csv') or f.endswith('.fixed_cnpj.csv') or (f.endswith('.db') and '.bak_' in f):
            try:
                sz = os.path.getsize(fp)
            except Exception:
                sz = 0
            mtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(fp))) if os.path.exists(fp) else ''
            proposed.append((rel, sz, mtime, fp))
    if '__pycache__' in dirnames:
        pc = os.path.join(dirpath,'__pycache__')
        total=0
        for root2,_,files2 in os.walk(pc):
            for ff in files2:
                try:
                    total += os.path.getsize(os.path.join(root2,ff))
                except:
                    pass
        proposed.append((os.path.relpath(pc,root), total, '', pc))
proposed_sorted = sorted(proposed, key=lambda x: x[1], reverse=True)
# write report
rep = os.path.join(root, 'tools', 'cleanup_report.txt')
with open(rep, 'w', encoding='utf-8') as fh:
    fh.write('Cleanup candidates report\n')
    fh.write('Project root: %s\n\n' % root)
    total_bytes = 0
    for rel,sz,mt,fp in proposed_sorted:
        fh.write('%-80s %12d bytes  %s\n' % (rel, sz, mt))
        total_bytes += sz
    fh.write('\nTotal candidates: %d\n' % len(proposed_sorted))
    fh.write('Total reclaimable size (approx): %.2f MB\n' % (total_bytes/1024.0/1024.0))
    # by extension
    cats = {}
    for rel,sz,mt,fp in proposed_sorted:
        ext = os.path.splitext(rel)[1].lower()
        cats.setdefault(ext,0)
        cats[ext]+=sz
    fh.write('\nBy extension:\n')
    for k,v in sorted(cats.items(), key=lambda x: x[1], reverse=True):
        fh.write('%-8s %.2f MB\n' % (k or '<noext>', v/1024.0/1024.0))
# also print archive listing
fh = open(rep, 'a', encoding='utf-8')
fh.write('\nArchive/ content:\n')
arch = os.path.join(root,'archive')
if os.path.isdir(arch):
    for f in sorted(os.listdir(arch)):
        fp = os.path.join(arch,f)
        try:
            sz=os.path.getsize(fp)
        except:
            sz=0
        fh.write('%s %d\n' % (f, sz))
else:
    fh.write('(no archive)\n')
fh.close()
print('Report written to', rep)
