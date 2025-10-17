#!/usr/bin/env python3
"""
Fetch all cards from a Trello board and write a report file `trello_created_cards.json`.
"""
import os
import json
import sys
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
CREDS_FILE = ROOT / '.trello_credentials.json'
OUT = ROOT / 'trello_created_cards.json'


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
    key, token, board_id = load_creds()
    if not key or not token or not board_id:
        print('Missing credentials or board id')
        sys.exit(1)

    base = 'https://api.trello.com/1'
    session = requests.Session()
    session.params = {'key': key, 'token': token}

    r = session.get(f'{base}/boards/{board_id}/cards')
    r.raise_for_status()
    cards = r.json()
    out = [{'id': c['id'], 'name': c['name'], 'shortUrl': c.get('shortUrl')} for c in cards]
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote {len(out)} cards to {OUT}')


if __name__ == '__main__':
    main()
