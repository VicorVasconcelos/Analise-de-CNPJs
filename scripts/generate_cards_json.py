#!/usr/bin/env python3
"""
Generate cards.json by parsing TRELLO/TRELLO-CARD-LIST-CNPJ.md for frontend cards.
This creates a `cards.json` in the repo root that can be reviewed before creating cards.
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / 'TRELLO' / 'TRELLO-CARD-LIST-CNPJ.md'
OUT = ROOT / 'cards.json'


def parse_cards_from_md(md_path: Path):
    cards = []
    if not md_path.exists():
        return cards
    text = md_path.read_text(encoding='utf-8')
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # find frontend blocks by the card header containing [FRONTEND]
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
                if l.strip().startswith('📋 NOME:') or l.strip().startswith('🔴') or l.strip().startswith('🟠'):
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
    return cards


def main():
    cards = parse_cards_from_md(MD)
    if not cards:
        print('No frontend cards found in markdown.')
        return
    OUT.write_text(json.dumps(cards, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote {len(cards)} cards to {OUT}')


if __name__ == '__main__':
    main()
