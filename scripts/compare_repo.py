import subprocess, sys

def run(cmd):
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if p.returncode != 0:
        print(f"ERROR running: {cmd}\n", p.stderr)
        sys.exit(1)
    return p.stdout.splitlines()

print('Gathering tracked files (local)...')
tracked = set(run('git ls-files'))
print(f'  tracked local: {len(tracked)} files')

print('Gathering files on origin/master (remote)...')
remote = set(run('git ls-tree -r origin/master --name-only'))
print(f'  remote origin/master: {len(remote)} files')

print('Gathering untracked files (local)...')
untracked = set(run('git ls-files --others --exclude-standard'))
print(f'  untracked local: {len(untracked)} files')

only_local_tracked = sorted(tracked - remote)
only_remote = sorted(remote - tracked)

print('\nSummary:')
print(f'  Files tracked locally but NOT present in origin/master: {len(only_local_tracked)}')
print(f'  Files present in origin/master but not tracked locally: {len(only_remote)}')
print(f'  Files untracked locally (not in git): {len(untracked)}')

if only_local_tracked:
    print('\nFiles tracked locally but missing on remote (examples up to 200):')
    for p in only_local_tracked[:200]:
        print('  ', p)

if only_remote:
    print('\nFiles on remote but not tracked locally (examples up to 200):')
    for p in only_remote[:200]:
        print('  ', p)

if untracked:
    print('\nUntracked files (not committed, examples up to 200):')
    for p in sorted(list(untracked))[:200]:
        print('  ', p)

# exit status 0
