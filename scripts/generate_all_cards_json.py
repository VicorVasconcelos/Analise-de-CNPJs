#!/usr/bin/env python3
"""
Parse `TRELLO/TRELLO-CARD-LIST-CNPJ.md` and generate a full `cards.json` containing
all cards in priority order. Assign members by rule:
- If name contains [FRONTEND] or 'Responsável: Samuel' -> 'Samuel Carvalho'
- Else assign to 'Victor Vasconcelos'

"""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / 'TRELLO' / 'TRELLO-CARD-LIST-CNPJ.md'
OUT = ROOT / 'cards.json'


def normalize_list_field(s: str):
    if not s:
        return 'A fazer'
    s = s.strip()
    # map Portuguese tokens to board list names
    if 'CONCLUÍDO' in s or 'CONCLUIDO' in s or 'CONCLUÍDO' in s.upper():
        return 'Concluído'
    if 'EM DESENVOLVIMENTO' in s or 'EM DESENVOLVIMENTO' in s.upper():
        return 'A fazer'
    return s


def parse_md(md_path: Path):
    if not md_path.exists():
        return []
    text = md_path.read_text(encoding='utf-8')
    lines = text.splitlines()
    cards = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('📋 NOME:'):
            name = line.split('📋 NOME:')[-1].strip()
            desc = ''
            labels = []
            list_name = 'A fazer'
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
                        if nk.strip() == '' or nk.strip().startswith(('🎯','📊','🏷️','📍','📌','🔴','🟠','🟡','🟢','---')):
                            break
                        desc += nk + '\n'
                        k += 1
                    j = k
                    continue
                if l.strip().startswith('🏷️ LABELS:'):
                    lbls = l.split('🏷️ LABELS:')[-1].strip()
                    labels = [x.strip() for x in re.split('[,;]', lbls) if x.strip()]
                    j += 1
                    continue
                if l.strip().startswith('📍 LISTA:'):
                    list_name = normalize_list_field(l.split('📍 LISTA:')[-1].strip())
                    j += 1
                    continue
                if l.strip().startswith('📌 RESPONSÁVEL:'):
                    responsible = l.split('📌 RESPONSÁVEL:')[-1].strip()
                    j += 1
                    continue
                if l.strip().startswith('📊 ESTIMATIVA:') or l.strip().startswith('🎯 CRITÉRIOS DE ACEITE:'):
                    j += 1
                    continue
                if l.strip().startswith('📋 NOME:') or l.strip().startswith('🔴 Card') or l.strip().startswith('🟠 Card') or l.strip().startswith('---'):
                    break
                j += 1

            # assign responsible by heuristics if not present
            if not responsible:
                if '[FRONTEND]' in name or 'FRONTEND' in name.upper():
                    responsible = 'Samuel Carvalho'
                else:
                    # default to Victor for backend/db/docs/tests
                    responsible = 'Victor Vasconcelos'

            card = {
                'name': name,
                'desc': desc.strip(),
                'list_name': list_name,
                'labels': labels or [],
                'members': [responsible]
            }
            cards.append(card)
            i = j
        else:
            i += 1
    return cards


def main():
    cards = parse_md(MD)
    if not cards:
        print('No cards parsed')
        return
    OUT.write_text(json.dumps(cards, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote {len(cards)} cards to {OUT}')


if __name__ == '__main__':
    main()
