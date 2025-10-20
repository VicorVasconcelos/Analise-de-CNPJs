import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import trello_tool

key, token, board = trello_tool.load_creds()
print('Creds:', bool(key), bool(token), board)
res = trello_tool.sync_cards_from_md(board, key, token, dry_run=True)
print('sync returned', res)
print('CARD_ID_MAP:', trello_tool.CARD_ID_MAP)
