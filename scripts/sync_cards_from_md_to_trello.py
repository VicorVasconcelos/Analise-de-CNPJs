#!/usr/bin/env python3
"""
Sync cards from TRELLO/TRELLO-CARD-LIST-CNPJ.md to the Trello board.

For each card defined in the markdown, find the card on the board by name
and update its description with the full block from the markdown. Also ensure
the card is in the recommended list, has the labels present (creating labels
if needed) and members assigned.

Usage: python scripts\sync_cards_from_md_to_trello.py --board BOARD_ID
"""
import os
import re
import json
import sys
from pathlib import Path
import requests
import argparse

ROOT = Path(__file__).resolve().parents[1]
MD_PATH = ROOT / 'TRELLO' / 'TRELLO-CARD-LIST-CNPJ.md'
CARDS_JSON = ROOT / 'cards.json'
CREDS_FILE = ROOT / '.trello_credentials.json'


def load_creds():
    key = os.getenv('TRELLO_KEY')
    token = os.getenv('TRELLO_TOKEN')
    board = os.getenv('TRELLO_BOARD_ID')
    if CREDS_FILE.exists():
        try:
            data = json.loads(CREDS_FILE.read_text(encoding='utf-8'))
            key = key or data.get('key')
            token = token or data.get('token')
            board = board or data.get('board_id')
        except Exception:
            pass
    return key, token, board


def extract_blocks(md_text):
    # Parser that recognizes two patterns:
    # 1) Lines starting with '📋 NOME: <name>'
    # 2) Numbered blocks like '1) [DB] Nome...'
    lines = md_text.splitlines()
    blocks = {}
    current_name = None
    current_lines = []
    def flush():
        nonlocal current_name, current_lines
        if current_name:
            blocks[current_name.strip()] = '\n'.join(current_lines).strip()
            current_name = None
            current_lines = []

    for line in lines:
        s = line.strip()
        if s.startswith('📋 NOME:'):
            # new block
            flush()
            current_name = line.split('📋 NOME:')[-1].strip()
            current_lines = [line]
            continue
        # numbered pattern: e.g. '1) [DB] Validar ...' or '1) [FRONTEND] Ajustar ...'
        m = re.match(r'^\s*\d+\)\s*(\[.*\].*)', line)
        if m:
            flush()
            current_name = m.group(1).strip()
            current_lines = [line]
            continue
        if current_name is not None:
            current_lines.append(line)
    flush()
    return blocks


def extract_metadata_from_block(block_text):
    # extract responsible, labels and list from block text
    responsible = None
    labels = []
    list_name = None
    for line in block_text.splitlines():
        l = line.strip()
        # responsible markers
        if l.lower().startswith('📌 responsável:') or l.lower().startswith('responsável:') or l.lower().startswith('responsavel:'):
            parts = l.split(':', 1)
            if len(parts) > 1:
                responsible = parts[1].strip()
        # labels markers (many variants)
        if 'label' in l.lower() or 'labels' in l.lower() or '🏷️' in l:
            parts = l.split(':', 1)
            if len(parts) > 1:
                for lab in re.split('[,;]', parts[1]):
                    lab = lab.strip()
                    if lab:
                        labels.append(lab)
        # list markers
        if l.lower().startswith('📍 lista:') or l.lower().startswith('lista recomendada:') or l.lower().startswith('lista:'):
            parts = l.split(':', 1)
            if len(parts) > 1:
                list_name = parts[1].strip()
    return responsible, labels, list_name


def load_cards_list():
    # read cards.json to get the list of card names we created earlier
    if CARDS_JSON.exists():
        try:
            return [c['name'] for c in json.loads(CARDS_JSON.read_text(encoding='utf-8'))]
        except Exception:
            return []
    return []


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--board', required=False, help='Trello board id (overrides creds file)')
    args = p.parse_args()

    key, token, board_id = load_creds()
    if args.board:
        board_id = args.board
    if not key or not token or not board_id:
        print('Missing Trello credentials or board id. Set env vars or .trello_credentials.json')
        sys.exit(1)

    md_text = MD_PATH.read_text(encoding='utf-8')
    blocks = extract_blocks(md_text)
    target_names = load_cards_list()
    if not target_names:
        print('cards.json not found or empty; will try to use all blocks found in markdown')
        target_names = list(blocks.keys())

    base = 'https://api.trello.com/1'
    session = requests.Session()
    session.params = {'key': key, 'token': token}

    # fetch board lists, members, labels, cards
    lists = session.get(f'{base}/boards/{board_id}/lists').json()
    lists_map = {l['name']: l['id'] for l in lists}
    members = session.get(f'{base}/boards/{board_id}/members').json()
    members_map = {}
    for m in members:
        if m.get('username'):
            members_map[m['username'].strip().lower()] = m['id']
        if m.get('fullName'):
            members_map[m['fullName'].strip().lower()] = m['id']
    labels = session.get(f'{base}/boards/{board_id}/labels', params={'limit':1000}).json()
    labels_map = {l['name']: l['id'] for l in labels if l.get('name')}
    board_cards = session.get(f'{base}/boards/{board_id}/cards').json()
    board_by_name = {c['name']: c for c in board_cards}

    created_count = 0
    for name in target_names:
        # find matching block by normalized comparison (allow small name differences)
        def normalize(s: str) -> str:
            s = s or ''
            s = s.lower()
            s = s.replace('`', '')
            # remove punctuation except spaces
            s = re.sub(r'[^a-z0-9\s]', ' ', s)
            s = re.sub(r'\s+', ' ', s).strip()
            return s

        block_key = None
        norm_name = normalize(name)
        for k in blocks.keys():
            if not k:
                continue
            if norm_name == normalize(k) or norm_name in normalize(k) or normalize(k) in norm_name:
                block_key = k
                break
        if not block_key:
            # try fuzzy: check each word
            for k in blocks.keys():
                kn = normalize(k)
                common = sum(1 for w in norm_name.split() if w and w in kn)
                if common >= max(1, len(norm_name.split())//2):
                    block_key = k
                    break
        if not block_key:
            print(f'Warning: no block found for card "{name}" in markdown')
            continue
        desc = blocks[block_key]

        # find card on board
        card = board_by_name.get(name)
        if not card:
            print(f'Card "{name}" not found on board; skipping')
            continue
        card_id = card['id']

        # update description
        r = session.put(f'{base}/cards/{card_id}', params={'desc': desc})
        if not r.ok:
            print(f'Failed to update desc for {name}:', r.status_code, r.text)
            continue
        # extract metadata: responsible, labels, list
        responsible, mlabels, mlist = extract_metadata_from_block(desc)

        # assign list if provided
        if mlist:
            target_list = None
            for lname in lists_map.keys():
                if lname.lower() == mlist.lower() or mlist.lower() in lname.lower() or lname.lower() in mlist.lower():
                    target_list = lists_map[lname]
                    break
            if target_list:
                session.put(f'{base}/cards/{card_id}', params={'idList': target_list})

        # ensure labels exist on board and set them (normalize emoji labels by removing emoji)
        idLabels = []
        for lb in mlabels:
            if not lb:
                continue
            ln = lb
            # remove emoji-like characters
            ln = re.sub(r'[\U0001F300-\U0001F6FF\u2600-\u26FF]', '', ln)
            ln = ln.strip()
            lid = labels_map.get(lb) or labels_map.get(ln)
            if not lid:
                # create label
                resp = session.post(f'{base}/labels', params={'idBoard': board_id, 'name': ln, 'color': 'green'})
                if resp.ok:
                    lid = resp.json().get('id')
                    labels_map[ln] = lid
            if lid:
                idLabels.append(lid)
        if idLabels:
            session.put(f'{base}/cards/{card_id}', params={'idLabels': ','.join(idLabels)})

        # assign responsible if present
        if responsible:
            # try exact match on fullName or username
            target = responsible.strip().lower()
            mid = members_map.get(target)
            if not mid:
                # try partial matches
                for k, v in members_map.items():
                    if target in k or k in target:
                        mid = v
                        break
            if mid:
                resp = session.post(f'{base}/cards/{card_id}/idMembers', params={'value': mid})
                if resp.ok:
                    print(f'Assigned member {responsible} to {name}')
                else:
                    # ignore if already assigned
                    pass

        created_count += 1
        print(f'Updated card: {name}')

    print(f'Updated total: {created_count}')


if __name__ == '__main__':
    main()
