import os
import glob
import shutil
from datetime import datetime

root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
archive = os.path.join(root, 'archive')

deleted = []
kept = []

print('Project root:', root)

# Patterns in project root to delete
patterns_root = [
    os.path.join(root, 'cnpj_exportacao_*.csv'),
    os.path.join(root, '*.normalized.csv'),
    os.path.join(root, '*.analysis.txt'),
    os.path.join(root, '*fixed_cnpj.csv'),
    os.path.join(root, 'export_sample_*.csv'),
]

# Files in archive to delete (exports and proposals)
patterns_archive = [
    os.path.join(archive, 'cnpj_exportacao_*.csv'),
    os.path.join(archive, 'socios_*.csv'),
]

# Collect targets
targets = []
for p in patterns_root:
    targets.extend(glob.glob(p))
for p in patterns_archive:
    targets.extend(glob.glob(p))

# Also include archive/exports directory
exports_dir = os.path.join(archive, 'exports')
if os.path.isdir(exports_dir):
    # add all files under it
    for rootdir, dirs, files in os.walk(exports_dir):
        for f in files:
            targets.append(os.path.join(rootdir, f))

# Include server logs
for logf in ['server.err', 'server.log']:
    p = os.path.join(root, logf)
    if os.path.exists(p):
        targets.append(p)

# Backups: find all bak files and keep only the newest
backups = glob.glob(os.path.join(archive, 'cnpj_database.db.bak_*.db'))
if backups:
    backups_sorted = sorted(backups, key=lambda x: os.path.getmtime(x), reverse=True)
    keep_backup = backups_sorted[0]
    kept.append(keep_backup)
    # add other backups to targets for deletion
    for b in backups_sorted[1:]:
        targets.append(b)
else:
    keep_backup = None

# Remove duplicates and ensure we never delete main DB or WAL/SHM
unique_targets = []
for t in targets:
    t_abs = os.path.abspath(t)
    if t_abs in unique_targets:
        continue
    if os.path.basename(t_abs) in ('cnpj_database.db', 'cnpj_database.db-wal', 'cnpj_database.db-shm'):
        print('Skipping main DB file:', t_abs)
        continue
    unique_targets.append(t_abs)

# Print summary of what will be deleted and what will be kept
print('\nWill keep backup:')
if keep_backup:
    print(' ', keep_backup)
else:
    print('  (no backups found)')

print('\nFiles/dirs planned for deletion:')
for t in unique_targets:
    print(' ', t)

# Proceed to delete
print('\nDeleting...')
for t in unique_targets:
    try:
        if os.path.isdir(t):
            shutil.rmtree(t)
            deleted.append(t)
        else:
            os.remove(t)
            deleted.append(t)
    except Exception as e:
        print('  Failed to delete', t, '->', e)

print('\nDeleted files count:', len(deleted))
for d in deleted[:100]:
    print(' ', d)

print('\nKept files:')
for k in kept:
    print(' ', k)

print('\nCleanup completed at', datetime.now().isoformat())
