"""
Create missing cards from the MD and update labels/descriptions/members for differing cards.
This runs real API calls (not dry-run). Use carefully.
"""
from pathlib import Path
import sys, json, re
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import trello_tool

key, token, board_id = trello_tool.load_creds()
if not (key and token and board_id):
    print('Missing Trello credentials; set env vars or .trello_credentials.json')
    sys.exit(1)

md_text = trello_tool.TRELLO_MD.read_text(encoding='utf-8')
blocks = trello_tool.extract_blocks(md_text)

base = 'https://api.trello.com/1'
session = trello_tool.api_session(key, token)

# Fetch board metadata
lists = trello_tool.safe_get_json(session, f'{base}/boards/{board_id}/lists', description='board lists')
labels = trello_tool.safe_get_json(session, f'{base}/boards/{board_id}/labels', params={'limit':1000}, description='board labels')
members = trello_tool.safe_get_json(session, f'{base}/boards/{board_id}/members', description='board members')
board_cards = trello_tool.safe_get_json(session, f'{base}/boards/{board_id}/cards', description='board cards')
if None in (lists, labels, members, board_cards):
    print('Failed to fetch board data; aborting.')
    sys.exit(1)

lists_map_name_to_id = {l['name']: l['id'] for l in lists}
labels_map_name_to_id = {l.get('name'): l['id'] for l in labels if l.get('name')}
labels_map_id_to_name = {l['id']: l.get('name') for l in labels}
members_map = {}
for m in members:
    if m.get('username'):
        members_map[m['username'].strip().lower()] = m['id']
    if m.get('fullName'):
        members_map[m['fullName'].strip().lower()] = m['id']

board_by_name = {c['name']: c for c in board_cards}
board_by_id = {c['id']: c for c in board_cards}

# Reuse compare logic to find missing and differences
missing = []
diffs = []
for title, block in blocks.items():
    # find card id preferring CARD_ID_MAP
    card_id = None
    if title in trello_tool.CARD_ID_MAP and trello_tool.CARD_ID_MAP[title]:
        card_id = trello_tool.CARD_ID_MAP[title]
    elif title in board_by_name:
        card_id = board_by_name[title]['id']
    else:
        # fuzzy
        def normalize(s):
            s = s or ''
            s = s.lower()
            s = s.replace('`','')
            s = re.sub(r'[^a-z0-9\s]', ' ', s)
            s = re.sub(r'\s+', ' ', s).strip()
            return s
        norm = normalize(title)
        for bname, card in board_by_name.items():
            if norm == normalize(bname) or norm in normalize(bname) or normalize(bname) in norm:
                card_id = card['id']
                trello_tool.CARD_ID_MAP[title] = card_id
                break
    if not card_id:
        missing.append({'title': title, 'block': block})
        continue
    card = board_by_id.get(card_id)
    if not card:
        missing.append({'title': title, 'block': block})
        continue
    # check labels difference
    responsible, md_labels, md_list = trello_tool.extract_metadata_from_block(block)
    card_label_names = [labels_map_id_to_name.get(lid) for lid in card.get('idLabels', [])]
    def normset(xs):
        return set([ (x or '').strip().lower() for x in xs if x ])
    label_diff = normset(md_labels) != normset(card_label_names)
    # also check desc
    md_desc = block.strip()
    trello_desc = card.get('desc','').strip()
    desc_diff = md_desc != trello_desc
    # members
    card_member_ids = card.get('idMembers', [])
    assigned = True
    if responsible:
        rnorm = responsible.strip().lower()
        assigned = False
        for m in members:
            if (m.get('username') and m.get('username').strip().lower() == rnorm) or (m.get('fullName') and m.get('fullName').strip().lower() == rnorm):
                if m['id'] in card_member_ids:
                    assigned = True
                    break
    if label_diff or desc_diff or not assigned:
        diffs.append({'title': title, 'card_id': card_id, 'block': block, 'md_labels': md_labels, 'md_desc': md_desc, 'responsible': responsible})

print(f'Found {len(missing)} missing cards and {len(diffs)} cards to update')

# Create missing cards
created = []
for item in missing:
    title = item['title']
    block = item['block']
    responsible, md_labels, md_list = trello_tool.extract_metadata_from_block(block)
    # determine list id
    list_name = md_list or 'To Do'
    idList = lists_map_name_to_id.get(list_name)
    if not idList:
        # try alternatives
        for alt in ['A fazer','A Fazer','To Do','To do','Todo','TODO']:
            if alt in lists_map_name_to_id:
                idList = lists_map_name_to_id[alt]
                break
        if not idList:
            print(f'List "{list_name}" not found on board; skipping creation of {title}')
            continue
    # members
    idMembers = []
    if responsible:
        mid = members_map.get(responsible.strip().lower())
        if mid:
            idMembers.append(mid)
    # labels: ensure exist or create
    idLabels = []
    for lb in md_labels:
        if not lb:
            continue
        lid = labels_map_name_to_id.get(lb)
        if not lid:
            # create label
            resp = trello_tool.ensure_label(base, session, board_id, lb)
            if resp:
                labels_map_name_to_id[lb] = resp
                lid = resp
        if lid:
            idLabels.append(lid)
    payload = {'name': title, 'desc': block.strip(), 'idList': idList}
    if idMembers:
        payload['idMembers'] = ','.join(idMembers)
    if idLabels:
        payload['idLabels'] = ','.join(idLabels)
    resp = trello_tool.create_card(session, base, payload)
    if resp.ok:
        created.append(title)
        jid = resp.json().get('id')
        trello_tool.CARD_ID_MAP[title] = jid
        print(f'Created: {title} -> {jid}')
    else:
        print(f'Failed to create {title}: {resp.status_code} {resp.text}')

# Update differing cards (labels, desc, members)
updated = []
for item in diffs:
    title = item['title']
    card_id = item['card_id']
    block = item['block']
    responsible = item['responsible']
    md_labels = item['md_labels']
    # update description
    r = session.put(f'{base}/cards/{card_id}', params={'desc': block.strip()})
    if not r.ok:
        print(f'Failed to update desc for {title}: {r.status_code} {r.text}')
    # labels: ensure and set
    idLabels = []
    for lb in md_labels:
        if not lb:
            continue
        lid = labels_map_name_to_id.get(lb)
        if not lid:
            resp = trello_tool.ensure_label(base, session, board_id, lb)
            if resp:
                labels_map_name_to_id[lb] = resp
                lid = resp
        if lid:
            idLabels.append(lid)
    if idLabels:
        resp = session.put(f'{base}/cards/{card_id}', params={'idLabels': ','.join(idLabels)})
        if not resp.ok:
            print(f'Failed to set labels for {title}: {resp.status_code} {resp.text}')
    # members
    if responsible:
        mid = members_map.get(responsible.strip().lower())
        if mid:
            resp = session.post(f'{base}/cards/{card_id}/idMembers', params={'value': mid})
            if resp.ok:
                print(f'Assigned member {responsible} to {title}')
    updated.append(title)

print(f'Created {len(created)} cards, Updated {len(updated)} cards')
# persist CARD_ID_MAP
try:
    ID_MAP_FILE = ROOT / '.trello_card_id_map.json'
    ID_MAP_FILE.write_text(json.dumps(trello_tool.CARD_ID_MAP, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Saved CARD_ID_MAP to', ID_MAP_FILE)
except Exception as e:
    print('Failed to save CARD_ID_MAP:', e)
