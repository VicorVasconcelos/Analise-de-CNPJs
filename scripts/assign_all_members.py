#!/usr/bin/env python3
"""
Assign members to Trello cards based on `cards.json`.

For each card in `cards.json`, find the matching card on the board by name
and assign the listed members (matching by fullName, username or partial match).
"""
import os
import sys
import json
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
CREDS_FILE = ROOT / '.trello_credentials.json'
CARDS_FILE = ROOT / 'cards.json'
REPORT_FILE = ROOT / 'trello_created_cards.json'


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


def find_member_id(members_map, target):
    if not target:
        return None
    t = target.strip().lower()
    # exact match by username or fullname
    if t in members_map:
        return members_map[t]
    # try partial matching on full names
    for k, v in members_map.items():
        if t in k:
            return v
    return None


def main():
    key, token, board_id = load_creds()
    if not key or not token or not board_id:
        print('Missing Trello credentials or board id (env or .trello_credentials.json)')
        sys.exit(1)

    if not CARDS_FILE.exists():
        print('cards.json not found')
        sys.exit(1)

    cards = json.loads(CARDS_FILE.read_text(encoding='utf-8'))

    base = 'https://api.trello.com/1'
    session = requests.Session()
    session.params = {'key': key, 'token': token}

    # fetch board members and build map of searchable keys -> id
    r = session.get(f'{base}/boards/{board_id}/members')
    r.raise_for_status()
    members = r.json()
    members_map = {}
    for m in members:
        if m.get('username'):
            members_map[m['username'].strip().lower()] = m['id']
        if m.get('fullName'):
            members_map[m['fullName'].strip().lower()] = m['id']

    # fetch existing board cards
    r = session.get(f'{base}/boards/{board_id}/cards')
    r.raise_for_status()
    board_cards = r.json()
    board_by_name = {c['name']: c for c in board_cards}

    assigned = []
    for desired in cards:
        name = desired.get('name')
        desired_members = desired.get('members') or []
        bc = board_by_name.get(name)
        if not bc:
            print(f'Card not found on board: {name}')
            continue
        card_id = bc['id']
        for dm in desired_members:
            if not dm:
                continue
            # normalize variants like 'Samuel' -> try to expand
            target = dm
            # try full name first
            mid = find_member_id(members_map, target)
            if not mid:
                # try common expansions
                if target.lower().startswith('sam'):
                    mid = find_member_id(members_map, 'samuel carvalho')
                elif target.lower().startswith('vict'):
                    mid = find_member_id(members_map, 'victor vasconcelos')
            if not mid:
                print(f'Warning: member "{dm}" not found on board; skipping for card "{name}"')
                continue
            # add member to card
            resp = session.post(f'{base}/cards/{card_id}/idMembers', params={'value': mid})
            if resp.ok:
                print(f'Assigned {dm} -> card: {name}')
                assigned.append({'card_id': card_id, 'card_name': name, 'member': dm})
            else:
                print(f'Failed to assign {dm} to {name}: {resp.status_code} {resp.text}')

    # refresh report of created cards
    r = session.get(f'{base}/boards/{board_id}/cards')
    r.raise_for_status()
    out = [{'id': c['id'], 'name': c['name'], 'shortUrl': c.get('shortUrl')} for c in r.json()]
    REPORT_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Updated report {REPORT_FILE} with {len(out)} cards')


if __name__ == '__main__':
    main()
