#!/usr/bin/env python3
"""
scripts/trello_bulk_create.py

Creates Trello cards in bulk for a given board. Credentials must be provided via
environment variables: TRELLO_KEY and TRELLO_TOKEN. Optionally set TRELLO_BOARD_ID.

Behavior:
- If a `cards.json` file exists in the current directory, it will be used (see format below).
- Otherwise the script will try to parse frontend cards from
  `TRELLO/TRELLO-CARD-LIST-CNPJ.md` (cards annotated with [FRONTEND] and '📌 RESPONSÁVEL').

cards.json example format:
[
  {
    "name": "[FRONTEND] Ajustar script.js para filtros",
    "desc": "Tornar o frontend tolerante a diferentes shapes...\nResponsável: Samuel",
    "list_name": "To Do",
    "labels": ["Frontend"],
    "members": ["samuel"]
  }
]

Usage (Windows cmd):
  set TRELLO_KEY=your_key
  set TRELLO_TOKEN=your_token
  set TRELLO_BOARD_ID=your_board_id
  python scripts\trello_bulk_create.py

This script will NOT hardcode or save your credentials. Use environment variables or a
local `.trello_credentials.json` if you prefer (but do NOT commit it).
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import List, Dict


ROOT = Path(__file__).resolve().parents[1]
CARDS_JSON = ROOT / 'cards.json'
TRELLO_MD = ROOT / 'TRELLO' / 'TRELLO-CARD-LIST-CNPJ.md'


def load_credentials():
    key = os.getenv('TRELLO_KEY')
    token = os.getenv('TRELLO_TOKEN')
    board = os.getenv('TRELLO_BOARD_ID')
    # optionally read local creds file if env not present
    creds_file = ROOT / '.trello_credentials.json'
    if (not key or not token) and creds_file.exists():
        try:
            data = json.loads(creds_file.read_text(encoding='utf-8'))
            key = key or data.get('key')
            token = token or data.get('token')
            board = board or data.get('board_id')
        except Exception:
            pass
    return key, token, board


def parse_cards_from_md(md_path: Path) -> List[Dict]:
    """Simple parser: extracts cards that mention [FRONTEND] in the 'NOME' line.
    It captures name, description (lines after '📋 DESCRIÇÃO:'), responsible (📌 RESPONSÁVEL)
    and default list 'To Do'."""
    cards = []
    if not md_path.exists():
        return cards
    text = md_path.read_text(encoding='utf-8')
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('📋 NOME:') and '[FRONTEND]' in line:
            # extract name
            name = line.split('📋 NOME:')[-1].strip()
            # description may be on next lines; find '📋 DESCRIÇÃO:'
            desc = ''
            responsible = None
            j = i + 1
            while j < len(lines):
                l = lines[j].strip()
                if l.startswith('📋 DESCRIÇÃO:'):
                    desc = l.split('📋 DESCRIÇÃO:')[-1].strip() + '\n'
                    k = j + 1
                    # capture following lines until a line that starts with an emoji field or blank
                    while k < len(lines):
                        nk = lines[k].rstrip()
                        if nk.strip() == '' or nk.strip().startswith('🎯') or nk.strip().startswith('📊') or nk.strip().startswith('🏷️') or nk.strip().startswith('📍') or nk.strip().startswith('📌'):
                            break
                        desc += nk + '\n'
                        k += 1
                    j = k
                elif l.startswith('📌 RESPONSÁVEL:'):
                    responsible = l.split('📌 RESPONSÁVEL:')[-1].strip()
                    j += 1
                elif l == '':
                    break
                else:
                    j += 1
            card = {
                'name': name,
                'desc': desc.strip() or '',
                'list_name': 'To Do',
                'labels': ['Frontend'],
                'members': [responsible] if responsible else []
            }
            cards.append(card)
            i = j
        else:
            i += 1
    return cards


def load_cards() -> List[Dict]:
    if CARDS_JSON.exists():
        try:
            return json.loads(CARDS_JSON.read_text(encoding='utf-8'))
        except Exception as e:
            print('Failed to parse cards.json:', e)
            return []
    # fallback to md parser
    return parse_cards_from_md(TRELLO_MD)


def get_board_lists(base, key, token, board_id):
    r = requests.get(f'{base}/boards/{board_id}/lists', params={'key': key, 'token': token})
    r.raise_for_status()
    return {item['name']: item['id'] for item in r.json()}


def get_board_members(base, key, token, board_id):
    r = requests.get(f'{base}/boards/{board_id}/members', params={'key': key, 'token': token})
    r.raise_for_status()
    # map both username and fullName lowercased to id
    out = {}
    for m in r.json():
        if m.get('username'):
            out[m['username'].lower()] = m['id']
        if m.get('fullName'):
            out[m['fullName'].lower()] = m['id']
    return out


def get_labels(base, key, token, board_id):
    r = requests.get(f'{base}/boards/{board_id}/labels', params={'key': key, 'token': token, 'limit':1000})
    r.raise_for_status()
    return {l['name']: l['id'] for l in r.json() if l.get('name')}


def ensure_label(base, session, board_id, label_name):
    # create label with default color green if not present
    resp = session.post(f'{base}/labels', params={'idBoard': board_id, 'name': label_name, 'color': 'green'})
    if resp.ok:
        return resp.json()['id']
    return None


def create_card(session, base, payload):
    resp = session.post(f'{base}/cards', params=payload)
    return resp


def main():
    key, token, board_id = load_credentials()
    if not key or not token:
        print('TRELLO_KEY and TRELLO_TOKEN must be set in environment (or .trello_credentials.json)')
        sys.exit(1)

    if not board_id:
        board_id = os.getenv('TRELLO_BOARD_ID')
    if not board_id:
        print('Set TRELLO_BOARD_ID environment variable (or pass via .trello_credentials.json)')
        sys.exit(1)

    cards = load_cards()
    if not cards:
        print('No cards found (no cards.json and no parsed cards in TRELLO md). Create cards.json or check TRELLO markdown file.')
        sys.exit(1)

    base = 'https://api.trello.com/1'
    session = requests.Session()
    session.params = {'key': key, 'token': token}

    try:
        lists_map = get_board_lists(base, key, token, board_id)
        members_map = get_board_members(base, key, token, board_id)
        labels_map = get_labels(base, key, token, board_id)
    except requests.HTTPError as e:
        print('Failed to fetch board metadata:', e)
        sys.exit(1)

    created = 0
    for c in cards:
        name = c.get('name')
        desc = c.get('desc', '')
        list_name = c.get('list_name') or 'To Do'
        idList = lists_map.get(list_name)
        if not idList:
            # try common alternatives (Portuguese board lists)
            alternatives = ['A fazer', 'A Fazer', 'To Do', 'To do', 'Todo', 'TODO']
            found = None
            for alt in alternatives:
                if alt in lists_map:
                    found = lists_map[alt]
                    break
            if not found:
                print(f'List "{list_name}" not found on board; available lists: {list(lists_map.keys())}')
                continue
            idList = found

        idMembers = []
        for mn in c.get('members', []) or []:
            if not mn:
                continue
            # try matching by username or full name, case-insensitive
            mid = members_map.get(mn.lower())
            if not mid:
                # try stripping accents/spaces
                key = mn.lower().strip()
                mid = members_map.get(key)
            if mid:
                idMembers.append(mid)
            else:
                print(f'Warning: member "{mn}" not found on board; skipping assignment')

        idLabels = []
        for lb in c.get('labels', []) or []:
            if not lb:
                continue
            lid = labels_map.get(lb)
            if not lid:
                # create
                nid = ensure_label(base, session, board_id, lb)
                if nid:
                    labels_map[lb] = nid
                    lid = nid
            if lid:
                idLabels.append(lid)

        payload = {
            'name': name,
            'desc': desc,
            'idList': idList
        }
        if idMembers:
            payload['idMembers'] = ','.join(idMembers)
        if idLabels:
            payload['idLabels'] = ','.join(idLabels)

        resp = create_card(session, base, payload)
        if resp.ok:
            print(f'Created: {name}')
            created += 1
        else:
            print(f'Failed to create {name}: {resp.status_code} {resp.text}')
        time.sleep(0.6)

    print(f'Created total: {created}/{len(cards)}')


if __name__ == '__main__':
    main()
