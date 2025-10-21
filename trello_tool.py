#!/usr/bin/env python3
"""
scripts/trello_tool.py

Ferramenta interativa unificada para operações com Trello.

Opções apresentadas ao usuário (quando em modo interativo):
 1 - Verificar duplicados (gera relatório) e opção para apagar
 2 - Baixar/atualizar lista de cards do board (trello_created_cards.json)
 3 - Criar cards em massa (usa cards.json ou parse do MD em TRELLO/)
 4 - Listar membros e labels do board
 5 - Detectar e relatar duplicados (salva em archive/)
 6 - Sair

Este arquivo consolida o comportamento de scripts antigos em scripts/ e archive/.

Credenciais: configure as variáveis de ambiente TRELLO_KEY, TRELLO_TOKEN e TRELLO_BOARD_ID
ou crie um arquivo local `.trello_credentials.json` com:
    {"key":"...","token":"...","board_id":"..."}
NÃO comite esse arquivo com credenciais reais.
"""

import os
import sys
import json
import time
import argparse
import re
from pathlib import Path
from typing import List, Dict, Optional
try:
    import requests
except Exception:
    print('\nO módulo Python "requests" não está instalado.')
    print('Instale-o antes de executar este script.')
    print('\nNo Windows (cmd.exe) execute:')
    print('  python -m pip install --upgrade pip')
    print('  python -m pip install requests')
    print('\nSe estiver usando um virtualenv, ative-o antes de instalar:')
    print('  .venv\\Scripts\\activate  # ou seu ambiente virtual')
    sys.exit(1)
import datetime

ROOT = Path(__file__).resolve().parent
CREDS_FILE = ROOT / '.trello_credentials.json'
OUT = ROOT / 'trello_created_cards.json'
CARDS_JSON = ROOT / 'cards.json'
TRELLO_MD = ROOT / 'docs' / 'trello' / 'TRELLO-CARD-LIST-CNPJ.md'
ARCHIVE = ROOT / 'archive'
ARCHIVE.mkdir(exist_ok=True)

# Mapeamento opcional de título do markdown -> id do card no Trello.
# Você pode preencher esse dicionário manualmente para que a sincronização use
# ids estáveis e não dependa do casamento por nome.
# Exemplo:
# CARD_ID_MAP = {
#     '[FRONTEND] Ajustar `script.js` para formatos múltiplos': '5f6d7c8b9a0e1d2c3b4a5f6e'
# }
# Se mantido vazio, o script tentará mapear nomes para ids buscando todos os
# cards do board e comparando nomes normalizados.
ID_MAP_FILE = ROOT / '.trello_card_id_map.json'


def load_card_id_map() -> Dict[str, str]:
    """Load CARD_ID_MAP from ID_MAP_FILE if present. If not present, create it
    with an empty dict (or seed it from the inline constants if desired).
    """
    if ID_MAP_FILE.exists():
        try:
            data = json.loads(ID_MAP_FILE.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    # Seed with an empty dict to avoid leaking environment-specific IDs
    try:
        ID_MAP_FILE.write_text(json.dumps({}, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass
    return {}


def save_card_id_map(m: Dict[str, str]):
    try:
        ID_MAP_FILE.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass


# Carrega o mapa de ids no momento da importação
CARD_ID_MAP: Dict[str, str] = load_card_id_map()


def load_creds():
    key = os.getenv('TRELLO_KEY')
    token = os.getenv('TRELLO_TOKEN')
    board = os.getenv('TRELLO_BOARD_ID')
    # Try local creds file
    if CREDS_FILE.exists():
        try:
            data = json.loads(CREDS_FILE.read_text(encoding='utf-8'))
            key = key or data.get('key')
            token = token or data.get('token')
            board = board or data.get('board_id')
        except Exception:
            pass

    # If any value missing and running interactively, prompt the user to enter them
    if (not key or not token or not board) and sys.stdin and sys.stdin.isatty():
        print('\nAlgumas credenciais do Trello estão faltando.')
        print('Você pode colar suas credenciais aqui (não serão enviadas ao Git).')
        try:
            if not key:
                k = input('TRELLO_KEY (enter para pular): ').strip()
                if k:
                    key = k
            if not token:
                t = input('TRELLO_TOKEN (enter para pular): ').strip()
                if t:
                    token = t
            if not board:
                b = input('TRELLO_BOARD_ID (enter para pular): ').strip()
                if b:
                    board = b
            # Offer to save
            if key and token and board:
                save = input('Salvar estas credenciais em `.trello_credentials.json`? (y/N): ').strip().lower()
                if save == 'y':
                    try:
                        CREDS_FILE.write_text(json.dumps({'key': key, 'token': token, 'board_id': board}, indent=2), encoding='utf-8')
                        print(f'Credenciais salvas em {CREDS_FILE} (não commitá-las).')
                    except Exception as e:
                        print('Falha ao salvar credenciais:', e)
        except Exception:
            # In non-interactive contexts, just return what we have
            pass

    return key, token, board


def require_creds():
    key, token, board = load_creds()
    if not key or not token or not board:
        print('Missing Trello credentials or board id. Set env vars or create .trello_credentials.json')
        sys.exit(1)
    return key, token, board


def api_session(key, token):
    s = requests.Session()
    s.params = {'key': key, 'token': token}
    return s


def safe_get_json(session: requests.Session, url: str, params: dict | None = None, description: str = ''):
    """Executa session.get e retorna o JSON parseado ou None em caso de erro.

    Imprime mensagens de diagnóstico úteis (código HTTP e trecho do corpo) quando
    a resposta não é JSON ou ocorre erro HTTP.
    """
    try:
        r = session.get(url, params=params)
    except Exception as e:
        print(f'Requisição HTTP falhou para {description or url}:', e)
        return None
    if not r.ok:
        # Non-2xx: show status and small body snippet
        body = (r.text or '')[:1000]
        print(f'Erro HTTP {r.status_code} ao acessar {description or url}. Corpo da resposta (truncado):')
        print(body)
        return None
    try:
        return r.json()
    except Exception as e:
        body = (r.text or '')[:2000]
        print(f'Falha ao decodificar JSON de {description or url}: {e}')
        print('Corpo da resposta (truncado):')
        print(body)
        return None


def fetch_cards(board_id: str, key: str, token: str, write_out: bool = True) -> List[Dict]:
    base = 'https://api.trello.com/1'
    s = api_session(key, token)
    r = s.get(f'{base}/boards/{board_id}/cards')
    r.raise_for_status()
    cards = r.json()
    out = [{'id': c['id'], 'name': c['name'], 'shortUrl': c.get('shortUrl'), 'dateLastActivity': c.get('dateLastActivity')} for c in cards]
    if write_out:
        OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'Wrote {len(out)} cards to {OUT}')
    return out


def get_board_lists(base, key, token, board_id):
    r = requests.get(f'{base}/boards/{board_id}/lists', params={'key': key, 'token': token})
    r.raise_for_status()
    return {item['name']: item['id'] for item in r.json()}


def get_board_members(base, key, token, board_id):
    r = requests.get(f'{base}/boards/{board_id}/members', params={'key': key, 'token': token})
    r.raise_for_status()
    out = {}
    for m in r.json():
        if m.get('username'):
            out[m['username'].lower()] = m['id']
        if m.get('fullName'):
            out[m['fullName'].lower()] = m['id']
    return out


def get_labels(base, key, token, board_id):
    r = requests.get(f'{base}/boards/{board_id}/labels', params={'key': key, 'token': token, 'limit': 1000})
    r.raise_for_status()
    return {l['name']: l['id'] for l in r.json() if l.get('name')}


def ensure_label(base, session, board_id, label_name):
    resp = session.post(f'{base}/labels', params={'idBoard': board_id, 'name': label_name, 'color': 'green'})
    if resp.ok:
        return resp.json()['id']
    return None


def create_card(session, base, payload):
    resp = session.post(f'{base}/cards', params=payload)
    return resp


def delete_card(session, base, card_id):
    resp = session.delete(f'{base}/cards/{card_id}')
    return resp


def normalize(s: str) -> str:
    if not s:
        return ''
    s = s.lower()
    s = s.replace('`', '')
    s = re.sub(r'[^a-z0-9\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def detect_duplicates(cards: List[Dict]) -> Dict:
    groups = {}
    for c in cards:
        n = normalize(c.get('name'))
        groups.setdefault(n, []).append(c)
    duplicates = {k: v for k, v in groups.items() if len(v) > 1}
    return duplicates


def write_duplicate_report(board_id: str, duplicates: Dict) -> Path:
    ts = int(time.time())
    report = {'board_id': board_id, 'timestamp': ts, 'duplicates': []}
    for norm, items in duplicates.items():
        items_sorted = sorted(items, key=lambda x: x.get('dateLastActivity') or '')
        keep = items_sorted[0]
        remove = items_sorted[1:]
        report['duplicates'].append({
            'normalized_name': norm,
            'keep': {'id': keep['id'], 'name': keep['name'], 'shortUrl': keep.get('shortUrl')},
            'remove': [{'id': r['id'], 'name': r['name'], 'shortUrl': r.get('shortUrl')} for r in remove]
        })
    out = ARCHIVE / f'trello_duplicates_report_{ts}.json'
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Report written to {out}')
    return out


def parse_cards_from_md(md_path: Path) -> List[Dict]:
    cards = []
    if not md_path.exists():
        return cards
    text = md_path.read_text(encoding='utf-8')
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('\ud83d\udccb NOME:'):
            name = line.split('\ud83d\udccb NOME:')[-1].strip()
            desc = ''
            responsible = None
            j = i + 1
            while j < len(lines):
                l = lines[j].strip()
                if l.startswith('\ud83d\udccb DESCRI\u00c7\u00c3O:'):
                    desc = l.split('\ud83d\udccb DESCRI\u00c7\u00c3O:')[-1].strip() + '\n'
                    k = j + 1
                    while k < len(lines):
                        nk = lines[k].rstrip()
                        if nk.strip() == '' or nk.strip().startswith('\ud83c\udfaf') or nk.strip().startswith('\ud83d\udcca') or nk.strip().startswith('\ud83c\udff7\ufe0f') or nk.strip().startswith('\ud83d\udccd') or nk.strip().startswith('\ud83d\udccc'):
                            break
                        desc += nk + '\n'
                        k += 1
                    j = k
                elif l.startswith('\ud83d\udccc RESPONS\u00c1VEL:'):
                    responsible = l.split('\ud83d\udccc RESPONS\u00c1VEL:')[-1].strip()
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


def load_cards_from_file() -> List[Dict]:
    if CARDS_JSON.exists():
        try:
            return json.loads(CARDS_JSON.read_text(encoding='utf-8'))
        except Exception as e:
            print('Falha ao analisar cards.json:', e)
            return []
    return parse_cards_from_md(TRELLO_MD)


def extract_blocks(md_text: str) -> Dict[str, str]:
    """Parse the markdown and return a dict mapping card title -> full block text."""
    lines = md_text.splitlines()
    blocks = {}
    current_name = None
    current_lines: List[str] = []

    def flush():
        nonlocal current_name, current_lines
        if current_name:
            blocks[current_name.strip()] = '\n'.join(current_lines).strip()
            current_name = None
            current_lines = []

    for line in lines:
        s = line.strip()
        if s.startswith('📋 NOME:'):
            flush()
            current_name = line.split('📋 NOME:')[-1].strip()
            current_lines = [line]
            continue
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


def extract_metadata_from_block(block_text: str):
    responsible = None
    labels = []
    list_name = None
    for line in block_text.splitlines():
        l = line.strip()
        if l.lower().startswith('📌 responsável:') or l.lower().startswith('responsável:') or l.lower().startswith('responsavel:'):
            parts = l.split(':', 1)
            if len(parts) > 1:
                responsible = parts[1].strip()
        if 'label' in l.lower() or 'labels' in l.lower() or '🏷️' in l:
            parts = l.split(':', 1)
            if len(parts) > 1:
                for lab in re.split('[,;]', parts[1]):
                    lab = lab.strip()
                    if lab:
                        labels.append(lab)
        if l.lower().startswith('📍 lista:') or l.lower().startswith('lista recomendada:') or l.lower().startswith('lista:'):
            parts = l.split(':', 1)
            if len(parts) > 1:
                list_name = parts[1].strip()
    return responsible, labels, list_name


def generate_cards_json(md_path: Path = TRELLO_MD, out_path: Path = CARDS_JSON) -> int:
    """Gera `cards.json` a partir dos cards FRONTEND presentes no markdown.

    Retorna o número de cards gravados.
    """
    if not md_path.exists():
        print(f'Markdown {md_path} not found')
        return 0
    text = md_path.read_text(encoding='utf-8')
    lines = text.splitlines()
    cards = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('📋 NOME:') and '[FRONTEND]' in line:
            name = line.split('📋 NOME:')[-1].strip()
            desc = ''
            responsible = None
            j = i + 1
            while j < len(lines):
                l = lines[j].rstrip()
                if l.strip().startswith('📋 DESCRIÇÃO:'):
                    desc_part = l.split('📋 DESCRIÇÃO:')[-1].strip()
                    desc += desc_part + '\n'
                    k = j + 1
                    while k < len(lines):
                        nk = lines[k].rstrip()
                        if nk.strip() == '' or nk.strip().startswith(('🎯','📊','🏷️','📍','📌','📋')):
                            break
                        desc += nk + '\n'
                        k += 1
                    j = k
                    continue
                if l.strip().startswith('📌 RESPONSÁVEL:'):
                    responsible = l.split('📌 RESPONSÁVEL:')[-1].strip()
                    j += 1
                    continue
                if l.strip().startswith('📋 NOME:'):
                    break
                j += 1
            card = {
                'name': name,
                'desc': desc.strip(),
                'list_name': 'To Do',
                'labels': ['Frontend'],
                'members': [responsible] if responsible else []
            }
            cards.append(card)
            i = j
        else:
            i += 1
    if not cards:
        print('No frontend cards found in markdown.')
        return 0
    out_path.write_text(json.dumps(cards, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote {len(cards)} cards to {out_path}')
    return len(cards)


def load_cards_names() -> List[str]:
    """Return list of card names from cards.json or all block keys from the markdown."""
    if CARDS_JSON.exists():
        try:
            data = json.loads(CARDS_JSON.read_text(encoding='utf-8'))
            return [c.get('name') for c in data if c.get('name')]
        except Exception:
            return []
    if TRELLO_MD.exists():
        blocks = extract_blocks(TRELLO_MD.read_text(encoding='utf-8'))
        return list(blocks.keys())
    return []


def sync_cards_from_md(board_id: str, key: str, token: str, dry_run: bool = False, force_all: bool = False) -> int:
    """Sincroniza os blocos do markdown com o board do Trello.

    Se dry_run for True, apenas imprime as ações pretendidas sem escrever na API.
    Retorna o número de cards processados (tentativas de atualização).
    """
    if not TRELLO_MD.exists():
        print('Markdown file not found:', TRELLO_MD)
        return 0
    md_text = TRELLO_MD.read_text(encoding='utf-8')
    blocks = extract_blocks(md_text)
    target_names = []
    if not force_all:
        target_names = load_cards_names()
    if not target_names:
        print('Using all blocks from markdown as target list')
        target_names = list(blocks.keys())

    base = 'https://api.trello.com/1'
    session = api_session(key, token)

    # buscar listas, membros, labels e cards do board (usar safe_get_json)
    lists = safe_get_json(session, f'{base}/boards/{board_id}/lists', description='listas do board')
    if lists is None:
        print('Falha ao obter listas do board; abortando sincronização.')
        return 0
    lists_map = {l['name']: l['id'] for l in lists}
    members = safe_get_json(session, f'{base}/boards/{board_id}/members', description='membros do board')
    members_map = {}
    if members is None:
        print('Falha ao obter membros do board; abortando sincronização.')
        return 0
    for m in members:
        if m.get('username'):
            members_map[m['username'].strip().lower()] = m['id']
        if m.get('fullName'):
            members_map[m['fullName'].strip().lower()] = m['id']
    labels = safe_get_json(session, f'{base}/boards/{board_id}/labels', params={'limit':1000}, description='labels do board')
    if labels is None:
        print('Falha ao obter labels do board; abortando sincronização.')
        return 0
    labels_map = {l['name']: l['id'] for l in labels if l.get('name')}
    board_cards = safe_get_json(session, f'{base}/boards/{board_id}/cards', description='cards do board')
    if board_cards is None:
        print('Falha ao obter cards do board; abortando sincronização.')
        return 0
    board_by_name = {c['name']: c for c in board_cards}
    # Build name->id map from board for fallback and for populating CARD_ID_MAP
    board_name_to_id = {c['name']: c['id'] for c in board_cards}
    # Try to fill CARD_ID_MAP with normalized matches if empty
    # CARD_ID_MAP is loaded at import time from ID_MAP_FILE; updates will be
    # persisted at the end of this function.

    created_count = 0
    for name in target_names:
        def normalize(s: str) -> str:
            s = s or ''
            s = s.lower()
            s = s.replace('`', '')
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

        # prefer explicit ID mapping when available
        card_id = None
        if name in CARD_ID_MAP and CARD_ID_MAP[name]:
            card_id = CARD_ID_MAP[name]
        else:
            # try exact name match
            card = board_by_name.get(name)
            if card:
                card_id = card['id']
            else:
                # try normalized fuzzy match by names
                norm_name = normalize(name)
                for bname, bid in board_name_to_id.items():
                    if norm_name == normalize(bname) or norm_name in normalize(bname) or normalize(bname) in norm_name:
                        card_id = bid
                        CARD_ID_MAP[name] = bid
                        break
        if not card_id:
            print(f'Card "{name}" not found on board; skipping')
            continue

        # update description
            if dry_run:
                print(f'[simulação] Irá atualizar descrição de "{name}" (tamanho {len(desc)}).')
        else:
            r = session.put(f'{base}/cards/{card_id}', params={'desc': desc})
            if not r.ok:
                print(f'Falha ao atualizar descrição de {name}:', r.status_code, r.text)
                continue

        # extract metadata
        responsible, mlabels, mlist = extract_metadata_from_block(desc)

        # assign list if provided
        if mlist:
            target_list = None
            for lname in lists_map.keys():
                if lname.lower() == mlist.lower() or mlist.lower() in lname.lower() or lname.lower() in mlist.lower():
                    target_list = lists_map[lname]
                    break
            if target_list:
                if dry_run:
                    print(f'[simulação] Irá mover "{name}" para a lista id {target_list} ({mlist}).')
                else:
                    session.put(f'{base}/cards/{card_id}', params={'idList': target_list})

        # ensure labels exist on board and set them
        idLabels = []
        for lb in mlabels:
            if not lb:
                continue
            ln = lb
            ln = re.sub(r'[\U0001F300-\U0001F6FF\u2600-\u26FF]', '', ln)
            ln = ln.strip()
            lid = labels_map.get(lb) or labels_map.get(ln)
            if not lid:
                if dry_run:
                    print(f'[simulação] Irá criar label "{ln}" no board.')
                    lid = f'dry-{ln}'
                else:
                    resp = session.post(f'{base}/labels', params={'idBoard': board_id, 'name': ln, 'color': 'green'})
                    if resp.ok:
                        lid = resp.json().get('id')
                        labels_map[ln] = lid
            if lid:
                idLabels.append(lid)
        if idLabels:
            if dry_run:
                print(f'[simulação] Irá definir labels {idLabels} no card "{name}".')
            else:
                session.put(f'{base}/cards/{card_id}', params={'idLabels': ','.join(idLabels)})

        # assign responsible
        if responsible:
            target = responsible.strip().lower()
            mid = members_map.get(target)
            if not mid:
                for k, v in members_map.items():
                    if target in k or k in target:
                        mid = v
                        break
            if mid:
                if dry_run:
                    print(f'[simulação] Irá atribuir membro id {mid} ao card "{name}".')
                else:
                    resp = session.post(f'{base}/cards/{card_id}/idMembers', params={'value': mid})
                    if resp.ok:
                        print(f'Assigned member {responsible} to {name}')

    created_count += 1
    print(f'Card atualizado: {name}')

    print(f'Total atualizados: {created_count}')
    # persist CARD_ID_MAP for future runs
    try:
        if CARD_ID_MAP:
            save_card_id_map(CARD_ID_MAP)
    except Exception:
        pass
    return created_count


def bulk_create(board_id: str, key: str, token: str):
    cards = load_cards_from_file()
    if not cards:
        print('Nenhum card encontrado (nenhum cards.json e nenhum card parseado no markdown em TRELLO).')
        return
    base = 'https://api.trello.com/1'
    session = api_session(key, token)
    try:
        lists_map = get_board_lists(base, key, token, board_id)
        members_map = get_board_members(base, key, token, board_id)
        labels_map = get_labels(base, key, token, board_id)
    except requests.HTTPError as e:
        print('Falha ao buscar metadata do board:', e)
        return
    created = 0
    for c in cards:
        name = c.get('name')
        desc = c.get('desc', '')
        list_name = c.get('list_name') or 'To Do'
        idList = lists_map.get(list_name)
        if not idList:
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
            mid = members_map.get(mn.lower())
            if not mid:
                keyn = mn.lower().strip()
                mid = members_map.get(keyn)
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
            print(f'Criado: {name}')
            created += 1
        else:
            print(f'Falha ao criar {name}: {resp.status_code} {resp.text}')
        time.sleep(0.6)
    print(f'Total criados: {created}/{len(cards)}')


def apply_md_to_board(board_id: str, key: str, token: str, dry_run: bool = True):
    """Criar cards faltantes a partir do markdown e atualizar cards existentes.

    Se dry_run for True, apenas imprime as ações sem aplicar alterações.
    """
    if not TRELLO_MD.exists():
        print('Arquivo markdown não encontrado:', TRELLO_MD)
        return 0
    md_text = TRELLO_MD.read_text(encoding='utf-8')
    blocks = extract_blocks(md_text)

    base = 'https://api.trello.com/1'
    session = api_session(key, token)

    lists = safe_get_json(session, f'{base}/boards/{board_id}/lists', description='listas do board')
    members = safe_get_json(session, f'{base}/boards/{board_id}/members', description='membros do board')
    labels = safe_get_json(session, f'{base}/boards/{board_id}/labels', params={'limit':1000}, description='labels do board')
    board_cards = safe_get_json(session, f'{base}/boards/{board_id}/cards', description='cards do board')
    if None in (lists, members, labels, board_cards):
        print('Falha ao obter dados do board; abortando operação de aplicação.')
        return 0

    lists_map = {l['name']: l['id'] for l in lists}
    labels_map = {l.get('name'): l['id'] for l in labels if l.get('name')}
    members_map = {}
    for m in members:
        if m.get('username'):
            members_map[m['username'].strip().lower()] = m['id']
        if m.get('fullName'):
            members_map[m['fullName'].strip().lower()] = m['id']

    board_by_name = {c['name']: c for c in board_cards}
    board_by_id = {c['id']: c for c in board_cards}

    created = 0
    updated = 0

    # Primeiro: criar cards que existem no markdown mas não existem no board
    for title, block in blocks.items():
        # find card id (prefer explicit map)
        card_id = None
        if title in CARD_ID_MAP and CARD_ID_MAP[title]:
            card_id = CARD_ID_MAP[title]
        elif title in board_by_name:
            card_id = board_by_name[title]['id']

        if not card_id:
            # create card from parsed block minimal fields
            parsed_responsible, parsed_labels, parsed_list = extract_metadata_from_block(block)
            list_id = None
            if parsed_list and parsed_list in lists_map:
                list_id = lists_map[parsed_list]
            else:
                # fallback to first list
                list_id = next(iter(lists_map.values()))

            payload = {'name': title, 'desc': block, 'idList': list_id}
            if dry_run:
                print(f'[simulação] Irá criar card: "{title}" na lista id {list_id}')
            else:
                resp = session.post(f'{base}/cards', params={**session.params, **payload})
                if resp.ok:
                    print(f'Card criado: {title}')
                    created += 1
                else:
                    print(f'Falha ao criar {title}:', resp.status_code, resp.text)
            continue

    # Second: ensure existing cards have correct desc/labels/list/members
    for title, block in blocks.items():
        # determine card id
        card_id = None
        if title in CARD_ID_MAP and CARD_ID_MAP[title]:
            card_id = CARD_ID_MAP[title]
        elif title in board_by_name:
            card_id = board_by_name[title]['id']
        else:
            # skip created ones above (they won't be present in board_by_name until next fetch)
            continue

        card = board_by_id.get(card_id)
        if not card:
            continue

        # update description
        if dry_run:
            print(f'[simulação] Irá atualizar descrição de "{title}" (tamanho {len(block)})')
        else:
            r = session.put(f'{base}/cards/{card_id}', params={'desc': block, **session.params})
            if not r.ok:
                print(f'Falha ao atualizar descrição de {title}:', r.status_code, r.text)

        # labels
        responsible, desired_labels, desired_list = extract_metadata_from_block(block)
        # ensure labels exist and collect ids
        desired_label_ids = []
        for lb in desired_labels:
            lid = labels_map.get(lb)
            if not lid and not dry_run:
                resp = session.post(f'{base}/labels', params={'idBoard': board_id, 'name': lb, 'color': 'green', **session.params})
                if resp.ok:
                    lid = resp.json().get('id')
                    labels_map[lb] = lid
            if lid:
                desired_label_ids.append(lid)
        if desired_label_ids:
            if dry_run:
                print(f'[simulação] Irá definir labels {desired_label_ids} em "{title}"')
            else:
                session.put(f'{base}/cards/{card_id}', params={'idLabels': ','.join(desired_label_ids), **session.params})

        # list
        if desired_list:
            # find matching list id
            target_list_id = None
            for lname, lid in lists_map.items():
                if lname.lower() == desired_list.lower() or desired_list.lower() in lname.lower():
                    target_list_id = lid
                    break
            if target_list_id:
                if dry_run:
                    print(f'[simulação] Irá mover "{title}" para a lista {target_list_id}')
                else:
                    session.put(f'{base}/cards/{card_id}', params={'idList': target_list_id, **session.params})

        # members
        if responsible:
            target = responsible.strip().lower()
            mid = members_map.get(target)
            if mid:
                if dry_run:
                    print(f'[simulação] Irá atribuir membro {target} a "{title}"')
                else:
                    resp = session.post(f'{base}/cards/{card_id}/idMembers', params={'value': mid, **session.params})
                    if resp.ok:
                        print(f'Assigned member {responsible} to {title}')

        updated += 1

    print(f'Aplicação concluída: criados={created} atualizados={updated}')
    return created + updated


def interactive_menu():
    key, token, board_id = load_creds()
    if not key or not token or not board_id:
        print('Missing credentials or board id. Configure env vars or .trello_credentials.json')
        return
    base = 'https://api.trello.com/1'
    session = api_session(key, token)

    while True:
        print('\nTrello Tool - opções:')
        print('1 - Baixar/atualizar lista de cards do board (fetch)')
        print('2 - Gerar cards.json a partir do markdown (generate)')
        print('3 - Sincronizar markdown para Trello (atualiza desc/labels/membros) (sync)')
        print('4 - Aplicar markdown ao board (criar faltantes e corrigir labels/members) (apply)')
        print('5 - Criar cards em massa (cards.json ou TRELLO MD) (bulk-create)')
        print('6 - Listar membros e labels do board')
        print('7 - Detectar duplicados e gerar relatório (com opção de apagar)')
        print('8 - Sair')
        choice = input('Escolha uma opção (1-8): ').strip()
        if choice == '1':
            fetch_cards(board_id, key, token, write_out=True)
        elif choice == '2':
            generate_cards_json()
        elif choice == '3':
            confirm = input('Executar sincronização (atualizar descrições/labels/membros)? (y/N, default dry-run): ').strip().lower()
            dry = True
            if confirm == 'y':
                dry = False
            sync_cards_from_md(board_id, key, token, dry_run=dry, force_all=True)
        elif choice == '4':
            confirm = input('Aplicar mudanças (criar faltantes e atualizar existentes). Executar de verdade? (y/N default: dry-run): ').strip().lower()
            dry = True
            if confirm == 'y':
                dry = False
            apply_md_to_board(board_id, key, token, dry_run=dry)
        elif choice == '5':
            confirm = input('Criar cards em massa no board especificado? (y/N): ').strip().lower()
            if confirm == 'y':
                bulk_create(board_id, key, token)
            else:
                print('Operação cancelada.')
        elif choice == '6':
            try:
                members = get_board_members(base, key, token, board_id)
                labels = get_labels(base, key, token, board_id)
                print('\nMembros (username/fullName -> id):')
                for k, v in members.items():
                    print(f' - {k}: {v}')
                print('\nLabels (name -> id):')
                for k, v in labels.items():
                    print(f' - {k}: {v}')
            except requests.HTTPError as e:
                print('Falha ao buscar metadata do board:', e)
        elif choice == '7':
            cards = fetch_cards(board_id, key, token, write_out=False)
            dups = detect_duplicates(cards)
            if not dups:
                print('Nenhum duplicado encontrado.')
            else:
                print(f'Encontradas {len(dups)} entradas duplicadas. Gerando relatório...')
                rep = write_duplicate_report(board_id, dups)
                ans = input('Deseja apagar os duplicados listados no relatório? (y/N): ').strip().lower()
                if ans == 'y':
                    # perform deletions keeping the oldest
                    deletions = []
                    for norm, items in dups.items():
                        items_sorted = sorted(items, key=lambda x: x.get('dateLastActivity') or '')
                        keep = items_sorted[0]
                        remove = items_sorted[1:]
                        for r in remove:
                            resp = delete_card(session, base, r['id'])
                            deletions.append({'id': r['id'], 'name': r['name'], 'shortUrl': r.get('shortUrl'), 'deleted': resp.ok, 'status_code': resp.status_code if not resp.ok else 200})
                            print(f"Deleted {r.get('name')} -> {resp.ok}")
                    rep2 = ARCHIVE / f'trello_duplicates_deleted_{int(time.time())}.json'
                    rep2.write_text(json.dumps({'deleted': deletions}, indent=2, ensure_ascii=False), encoding='utf-8')
                    print(f'Deletion report written to {rep2}')
                else:
                    print('Nenhuma alteração aplicada.')
        elif choice == '8':
            print('Saindo.')
            break
        else:
            print('Opção inválida, tente novamente.')


def main():
    parser = argparse.ArgumentParser(description='Ferramenta unificada para operações com Trello')
    parser.add_argument('--interactive', action='store_true', help='Executar menu interativo')
    parser.add_argument('--fetch', action='store_true', help='Baixar cards do board e salvar em trello_created_cards.json')
    parser.add_argument('--detect-duplicates', action='store_true', help='Detectar duplicados e salvar relatório')
    parser.add_argument('--bulk-create', action='store_true', help='Criar cards em massa a partir de cards.json ou do markdown em TRELLO/')
    parser.add_argument('--generate', action='store_true', help='Gerar cards.json a partir do markdown em TRELLO (cards FRONTEND)')
    parser.add_argument('--sync', action='store_true', help='Sincronizar markdown para o board do Trello (atualiza descrições/labels/membros)')
    parser.add_argument('--dry-run', action='store_true', help='Com --sync ou --apply: mostrar ações sem gravar (modo simulação)')
    parser.add_argument('--use-all', action='store_true', help='Com --sync: ignorar cards.json e usar todos os blocos do markdown')
    parser.add_argument('--apply', action='store_true', help='Criar cards faltantes e atualizar cards existentes a partir do markdown (usar --dry-run para simular)')
    parser.add_argument('--board', help='ID do board (substitui o configurado nas credenciais)')
    args = parser.parse_args()

    # If no arguments were provided, start in interactive mode by default.
    # This makes the script show all options when launched without flags.
    if len(sys.argv) == 1:
        interactive_menu()
        return

    key, token, board_id = load_creds()
    if args.board:
        board_id = args.board
    if args.interactive:
        interactive_menu()
        return
    if args.fetch:
        if not key or not token or not board_id:
            print('Credenciais ou board id ausentes')
            return
        fetch_cards(board_id, key, token, write_out=True)
        return
    if args.generate:
        generate_cards_json()
        return
    if args.sync:
        if not key or not token or not board_id:
            print('Credenciais ou board id ausentes')
            return
        sync_cards_from_md(board_id, key, token, dry_run=args.dry_run, force_all=args.use_all)
        return
    if args.apply:
        if not key or not token or not board_id:
            print('Credenciais ou board id ausentes')
            return
        print('Aplicando markdown no board (simulação=%s)...' % args.dry_run)
        apply_md_to_board(board_id, key, token, dry_run=args.dry_run)
        return
    if args.detect_duplicates:
        if not key or not token or not board_id:
            print('Missing credentials or board id')
            return
        cards = fetch_cards(board_id, key, token, write_out=False)
        dups = detect_duplicates(cards)
        if not dups:
            print('Nenhum duplicado encontrado.')
        else:
            write_duplicate_report(board_id, dups)
        return
    if args.bulk_create:
        if not key or not token or not board_id:
            print('Missing credentials or board id')
            return
        bulk_create(board_id, key, token)
        return
    parser.print_help()


if __name__ == '__main__':
    main()
