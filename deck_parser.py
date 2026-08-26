"""
Deck List Parser for MTG Deck Visualizer.
Supports:
- Text formats with set codes and collector numbers:
    '3 Cabal Therapy (WC03) we62sb'
    '16 Swamp (ONS) 341'
    '4 Withered Wretch (PLST) LGN-86'
- Text formats without set codes:
    '3 Cabal Therapy'
    '16 Swamp'
- Sideboard markers: 'SIDEBOARD:', 'Sideboard:', 'SB:', '// Sideboard'
- Moxfield JSON deck data (mainboard & sideboard)
"""

import re
import urllib.request
import json

# Premodern set codes for fast validation/prioritization
PREMODERN_SETS = {
    '4ed', 'ice', 'chr', 'ren', 'hml', 'all', 'mir', 'vis', '5ed', 'por', 'wth',
    'tmp', 'sth', 'exo', 'usg', 'ath', 'ulg', '6ed', 'uds', 's99', 'p02', 'mmq',
    'brb', 'nem', 's00', 'pcy', 'btd', 'inv', 'pls', '7ed', 'apc', 'ody', 'dkm',
    'tor', 'jud', 'ons', 'lgn', 'scg',
    # World Champ & special sets of the era
    'wc97', 'wc98', 'wc99', 'wc00', 'wc01', 'wc02', 'wc03',
    'ptc', 'prm', 'fbb', '4bb', 'rqs', 'drk', 'atq', 'arn', 'leg', '3ed', '2ed', 'leb', 'lea'
}

def parse_decklist_text(text: str):
    """
    Parses deck list text into mainboard and sideboard lists of card items.
    Each item:
    {
        'name': str,
        'quantity': int,
        'set': str or None,
        'collector_number': str or None,
        'is_sideboard': bool
    }
    """
    mainboard = []
    sideboard = []
    
    lines = text.strip().splitlines()
    in_sideboard = False
    
    # Regex patterns for line parsing:
    pattern_with_set = re.compile(
        r'^\s*(\d+)x?\s+(.+?)\s+\(([A-Za-z0-9_]+)\)\s*([A-Za-z0-9_\-\*]*)\s*$'
    )
    pattern_bracket_set = re.compile(
        r'^\s*(\d+)x?\s+(.+?)\s+\[([A-Za-z0-9_]+)\]\s*([A-Za-z0-9_\-\*]*)\s*$'
    )
    pattern_simple = re.compile(
        r'^\s*(\d+)x?\s+(.+?)\s*$'
    )
    
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
            
        lower_line = line.lower()
        if (lower_line.startswith('sideboard') or 
            lower_line.startswith('// sideboard') or 
            lower_line.startswith('sb:') or 
            lower_line == '//' or
            lower_line == 'sideboard:'):
            in_sideboard = True
            if lower_line.startswith('sb:') and len(line) > 3:
                card_part = line[3:].strip()
                if card_part:
                    line = card_part
                else:
                    continue
            else:
                continue

        if (lower_line.startswith('//') or 
            lower_line == 'deck' or 
            lower_line == 'main' or 
            lower_line == 'mainboard' or
            lower_line.startswith('about') or
            lower_line.startswith('format:')):
            continue

        m1 = pattern_with_set.match(line)
        if m1:
            qty = int(m1.group(1))
            name = m1.group(2).strip()
            set_code = m1.group(3).strip().lower()
            cn = m1.group(4).strip().lower() if m1.group(4) else None
            entry = {
                'name': name,
                'quantity': qty,
                'set': set_code,
                'collector_number': cn if cn else None,
                'is_sideboard': in_sideboard
            }
            if in_sideboard:
                sideboard.append(entry)
            else:
                mainboard.append(entry)
            continue
            
        m2 = pattern_bracket_set.match(line)
        if m2:
            qty = int(m2.group(1))
            name = m2.group(2).strip()
            set_code = m2.group(3).strip().lower()
            cn = m2.group(4).strip().lower() if m2.group(4) else None
            entry = {
                'name': name,
                'quantity': qty,
                'set': set_code,
                'collector_number': cn if cn else None,
                'is_sideboard': in_sideboard
            }
            if in_sideboard:
                sideboard.append(entry)
            else:
                mainboard.append(entry)
            continue
            
        m3 = pattern_simple.match(line)
        if m3:
            qty = int(m3.group(1))
            name = m3.group(2).strip()
            entry = {
                'name': name,
                'quantity': qty,
                'set': None,
                'collector_number': None,
                'is_sideboard': in_sideboard
            }
            if in_sideboard:
                sideboard.append(entry)
            else:
                mainboard.append(entry)
            continue
            
    return {'mainboard': mainboard, 'sideboard': sideboard}


def extract_moxfield_deck_id(url_or_id: str) -> str:
    url_or_id = url_or_id.strip()
    match = re.search(r'moxfield\.com/decks/([A-Za-z0-9_\-]+)', url_or_id)
    if match:
        return match.group(1)
    return url_or_id


def parse_moxfield_data(moxfield_json: dict):
    deck_name = moxfield_json.get('name', 'Moxfield Deck')
    fmt = moxfield_json.get('format', 'premodern')
    
    def process_board(board_dict, is_sb=False):
        entries = []
        if not board_dict:
            return entries
        for card_name, item in board_dict.items():
            qty = item.get('quantity', 1)
            card_obj = item.get('card', {})
            set_code = card_obj.get('set', '').lower() or None
            cn = card_obj.get('cn', '') or None
            scryfall_id = card_obj.get('scryfall_id')
            is_foil = item.get('isFoil', False) or (item.get('finish') == 'foil')
            
            img_uri = None
            if 'image_uris' in card_obj and card_obj['image_uris']:
                img_uri = card_obj['image_uris'].get('normal', card_obj['image_uris'].get('large'))
            
            entries.append({
                'name': card_obj.get('name', card_name),
                'quantity': qty,
                'set': set_code,
                'collector_number': cn,
                'scryfall_id': scryfall_id,
                'is_foil': is_foil,
                'is_sideboard': is_sb,
                'image_uri': img_uri
            })
        return entries

    mainboard = process_board(moxfield_json.get('mainboard', {}), is_sb=False)
    sideboard = process_board(moxfield_json.get('sideboard', {}), is_sb=True)
    
    return {
        'name': deck_name,
        'format': fmt,
        'mainboard': mainboard,
        'sideboard': sideboard
    }
