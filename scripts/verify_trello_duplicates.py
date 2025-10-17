#!/usr/bin/env python3
"""Verify duplicate normalized names on Trello board and print a summary."""
import json
import re
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CREDS = ROOT / '.trello_credentials.json'

def load_creds():
    data = json.loads(CREDS.read_text(encoding='utf-8'))
    return data.get('key'), data.get('token'), data.get('board_id')

def normalize(s):
    s = (s or '').lower()
    s = re.sub(r'[^a-z0-9\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def main():
    key, token, board = load_creds()
    if not key or not token or not board:
        print('Missing creds in .trello_credentials.json')
        return
    base = 'https://api.trello.com/1'
    params = {'key': key, 'token': token}
    cards = requests.get(f'{base}/boards/{board}/cards', params=params).json()
    mapping = {}
    for c in cards:
        n = normalize(c.get('name'))
        mapping.setdefault(n, []).append(c)
    dups = {k:v for k,v in mapping.items() if len(v)>1}
    print('Total cards on board:', len(cards))
    print('Duplicate groups remaining:', len(dups))
    if dups:
        import json
        print(json.dumps(dups, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
