#!/usr/bin/env python3
"""
Assign a Trello member (by full name) to cards on a board.
Reads `.trello_credentials.json` or env vars, reads `cards.json` to know target card names,
finds the member by fullName (or username) and adds them to the matching cards.

Usage (Windows cmd):
  python scripts\trello_assign_member.py --member "Samuel Caravalho"

"""
import os
import json
import sys
import argparse
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


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--member', required=True, help='Full name of the member to assign (e.g. "Samuel Caravalho")')
    p.add_argument('--board', help='Board id (overrides creds file)')
    args = p.parse_args()

    key, token, board_id = load_creds()
    if args.board:
        board_id = args.board
    if not key or not token or not board_id:
        print('Trello credentials or board id missing. Set env vars or .trello_credentials.json')
        sys.exit(1)

    member_name = args.member.strip().lower()

    base = 'https://api.trello.com/1'
    session = requests.Session()
    session.params = {'key': key, 'token': token}

    # fetch members
    r = session.get(f'{base}/boards/{board_id}/members')
    r.raise_for_status()
    members = r.json()
    member_id = None
    for m in members:
        full = (m.get('fullName') or '').strip().lower()
        uname = (m.get('username') or '').strip().lower()
        if full == member_name or uname == member_name:
            member_id = m['id']
            break

    if not member_id:
        print(f'Member "{args.member}" not found on board. Available members:')
        for m in members:
            print(' -', m.get('fullName'), '(', m.get('username'), ')')
        sys.exit(1)

    # fetch board cards
    r = session.get(f'{base}/boards/{board_id}/cards')
    r.raise_for_status()
    board_cards = r.json()

    # load desired card names
    if not CARDS_FILE.exists():
        print('cards.json not found')
        sys.exit(1)
    try:
        desired = json.loads(CARDS_FILE.read_text(encoding='utf-8'))
    except Exception as e:
        print('Failed to read cards.json:', e)
        sys.exit(1)

    name_map = {c['name']: c for c in desired}
    created = []

    for bc in board_cards:
        name = bc.get('name')
        if name in name_map:
            card_id = bc['id']
            # add member to card
            resp = session.post(f'{base}/cards/{card_id}/idMembers', params={'value': member_id})
            if resp.ok:
                print(f'Assigned {args.member} to card: {name}')
                created.append({'id': card_id, 'name': name, 'shortUrl': bc.get('shortUrl')})
            else:
                print(f'Failed to assign member to {name}:', resp.status_code, resp.text)

    # update report with real shortUrls
    if created:
        # merge with existing report or overwrite
        REPORT_FILE.write_text(json.dumps(created, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'Wrote {len(created)} items to {REPORT_FILE}')
    else:
        print('No matching cards found to update.')


if __name__ == '__main__':
    main()
