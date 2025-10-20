"""
Compare TRELLO/TRELLO-CARD-LIST-CNPJ.md with Trello board cards and report differences.
This script uses trello_tool module helpers (safe_get_json, extract_blocks, extract_metadata_from_block, CARD_ID_MAP).
"""
from pathlib import Path
import sys, json
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import trello_tool

key, token, board_id = trello_tool.load_creds()
if not (key and token and board_id):
    print('Missing Trello credentials; set env vars or .trello_credentials.json')
    sys.exit(1)

md_path = trello_tool.TRELLO_MD
if not md_path.exists():
    print('Markdown file not found:', md_path)
    sys.exit(1)

md_text = md_path.read_text(encoding='utf-8')
blocks = trello_tool.extract_blocks(md_text)

base = 'https://api.trello.com/1'
session = trello_tool.api_session(key, token)

lists = trello_tool.safe_get_json(session, f'{base}/boards/{board_id}/lists', description='board lists')
labels = trello_tool.safe_get_json(session, f'{base}/boards/{board_id}/labels', params={'limit':1000}, description='board labels')
members = trello_tool.safe_get_json(session, f'{base}/boards/{board_id}/members', description='board members')
board_cards = trello_tool.safe_get_json(session, f'{base}/boards/{board_id}/cards', description='board cards')

if None in (lists, labels, members, board_cards):
    print('Failed to fetch board data; aborting comparison.')
    sys.exit(1)

lists_map = {l['id']: l['name'] for l in lists}
labels_map_id_to_name = {l['id']: l.get('name') for l in labels}
labels_map_name_to_id = {l.get('name'): l['id'] for l in labels if l.get('name')}
members_map = {}
for m in members:
    if m.get('username'):
        members_map[m['username'].strip().lower()] = m['id']
    if m.get('fullName'):
        members_map[m['fullName'].strip().lower()] = m['id']

board_by_id = {c['id']: c for c in board_cards}
board_by_name = {c['name']: c for c in board_cards}

# Helper to find card id (prefer CARD_ID_MAP)
def find_card_id_for_name(name):
    if name in trello_tool.CARD_ID_MAP and trello_tool.CARD_ID_MAP[name]:
        return trello_tool.CARD_ID_MAP[name]
    # exact match
    if name in board_by_name:
        return board_by_name[name]['id']
    # fuzzy
    def normalize(s):
        s = s or ''
        s = s.lower()
        s = s.replace('`','')
        import re
        s = re.sub(r'[^a-z0-9\s]', ' ', s)
        s = re.sub(r'\s+', ' ', s).strip()
        return s
    norm = normalize(name)
    for bname, card in board_by_name.items():
        if norm == normalize(bname) or norm in normalize(bname) or normalize(bname) in norm:
            return card['id']
    return None

report = {
    'missing_on_trello': [],
    'differences': [],
    'extra_on_trello': []
}

# Check each md block
for title, block in blocks.items():
    card_id = find_card_id_for_name(title)
    if not card_id:
        report['missing_on_trello'].append(title)
        continue
    card = board_by_id.get(card_id)
    if not card:
        # maybe id map points to non-existing card
        report['missing_on_trello'].append(title)
        continue
    diffs = []
    # compare description (block vs card.desc)
    md_desc = block.strip()
    trello_desc = card.get('desc','').strip()
    if md_desc != trello_desc:
        diffs.append('desc')
    # metadata
    responsible, md_labels, md_list = trello_tool.extract_metadata_from_block(block)
    # list
    card_list_id = card.get('idList')
    card_list_name = lists_map.get(card_list_id)
    if md_list:
        if not card_list_name or md_list.lower() not in card_list_name.lower():
            diffs.append('list')
    # labels: convert card label ids to names
    card_label_names = [labels_map_id_to_name.get(lid) for lid in card.get('idLabels', [])]
    # simplify comparison by lowercasing and stripping
    def normset(xs):
        return set([ (x or '').strip().lower() for x in xs if x ])
    if normset(md_labels) != normset(card_label_names):
        diffs.append('labels')
    # responsible / members
    card_member_ids = card.get('idMembers', [])
    # try to match responsible to any member
    assigned = False
    if responsible:
        rnorm = responsible.strip().lower()
        for m in members:
            if (m.get('username') and m.get('username').strip().lower() == rnorm) or (m.get('fullName') and m.get('fullName').strip().lower() == rnorm):
                if m['id'] in card_member_ids:
                    assigned = True
                    break
        if not assigned:
            diffs.append('members')
    # collect diffs
    if diffs:
        report['differences'].append({'title': title, 'card_id': card_id, 'diffs': diffs})

# Find extras on Trello not present in markdown
md_titles_norm = set([t.strip().lower() for t in blocks.keys()])
for c in board_cards:
    if c['name'].strip().lower() not in md_titles_norm:
        report['extra_on_trello'].append({'name': c['name'], 'id': c['id']})

print(json.dumps(report, ensure_ascii=False, indent=2))
