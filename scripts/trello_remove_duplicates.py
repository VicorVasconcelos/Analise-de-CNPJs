#!/usr/bin/env python3
"""
Detect and remove duplicate Trello cards by normalized name.

Usage:
  python scripts\trello_remove_duplicates.py --board BOARD_ID [--apply]

By default the script runs in dry-run mode and writes a report to archive/trello_duplicates_<ts>.json
Use --apply to actually delete duplicates (keeps the oldest card in each duplicate group).
"""
import os
import sys
import json
import argparse
from pathlib import Path
import re
import time
import requests

ROOT = Path(__file__).resolve().parents[1]
CREDS_FILE = ROOT / '.trello_credentials.json'
ARCHIVE = ROOT / 'archive'
ARCHIVE.mkdir(exist_ok=True)


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


def normalize(s: str) -> str:
    if not s:
        return ''
    s = s.lower()
    s = s.replace('`', '')
    s = re.sub(r'[^a-z0-9\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--board', required=False)
    p.add_argument('--apply', action='store_true', help='Actually delete duplicates')
    p.add_argument('--keep', choices=['oldest', 'newest'], default='oldest', help='Which card to keep among duplicates (default: oldest)')
    args = p.parse_args()

    key, token, board_id = load_creds()
    if args.board:
        board_id = args.board
    if not key or not token or not board_id:
        print('Missing Trello credentials or board id')
        sys.exit(1)

    base = 'https://api.trello.com/1'
    session = requests.Session()
    session.params = {'key': key, 'token': token}

    cards = session.get(f'{base}/boards/{board_id}/cards').json()
    # group by normalized name
    groups = {}
    for c in cards:
        n = normalize(c.get('name'))
        groups.setdefault(n, []).append(c)

    duplicates = {k: v for k, v in groups.items() if len(v) > 1}
    ts = int(time.time())
    report = {'board_id': board_id, 'timestamp': ts, 'duplicates': []}

    if not duplicates:
        print('No duplicates found.')
        return

    for norm, items in duplicates.items():
        # sort by dateLastActivity ascending
        items_sorted = sorted(items, key=lambda x: x.get('dateLastActivity') or '')
        if args.keep == 'oldest':
            keep = items_sorted[0]
            remove = items_sorted[1:]
        else:
            # keep newest
            keep = items_sorted[-1]
            remove = items_sorted[:-1]
        report['duplicates'].append({
            'normalized_name': norm,
            'keep': {'id': keep['id'], 'name': keep['name'], 'shortUrl': keep.get('shortUrl')},
            'remove': [{'id': r['id'], 'name': r['name'], 'shortUrl': r.get('shortUrl')} for r in remove]
        })

    out = ARCHIVE / f'trello_duplicates_report_{ts}.json'
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Found {len(report["duplicates"])} duplicate groups. Report written to {out}')

    if args.apply:
        # perform deletions
        deletions = []
        for grp in report['duplicates']:
            for r in grp['remove']:
                cid = r['id']
                resp = session.delete(f'{base}/cards/{cid}')
                ok = resp.ok
                deletions.append({'id': cid, 'name': r['name'], 'shortUrl': r.get('shortUrl'), 'deleted': ok, 'status_code': resp.status_code if not ok else 200})
                print(f"Deleted card {r['name']} -> {ok}")
        rep2 = ARCHIVE / f'trello_duplicates_deleted_{ts}.json'
        rep2.write_text(json.dumps({'deleted': deletions}, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f'Deletion report written to {rep2}')


if __name__ == '__main__':
    main()
