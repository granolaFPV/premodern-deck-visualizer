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
            lower_line.startswith('~~sideboard') or
            lower_line.startswith('~~side board') or
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

        if (lower_line.startswith('~~mainboard') or
            lower_line.startswith('~~commanders') or
            lower_line.startswith('~~deck') or
            lower_line == 'deck' or 
            lower_line == 'main' or 
            lower_line == 'mainboard'):
            in_sideboard = False
            continue

        if (lower_line.startswith('//') or 
            lower_line.startswith('~~') or
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


def fetch_deck_from_url(url: str) -> dict:
    """
    Auto-detects and fetches deck data from major deck hosting sites:
    - Moxfield (moxfield.com)
    - TopDeck.gg (topdeck.gg)
    - Archidekt (archidekt.com)
    - MTGGoldfish (mtggoldfish.com)
    - MTGTop8 (mtgtop8.com)
    - Cube Cobra (cubecobra.com)
    - Pastebin (pastebin.com)
    - GitHub Gist (gist.github.com)
    - Direct plain text URLs (.txt / .deck)

    Returns:
    {
        'name': str,
        'format': str,
        'mainboard': list of card dicts,
        'sideboard': list of card dicts
    }
    """
    url = url.strip()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) MTGVisualizer/1.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml,application/json;q=0.9,*/*;q=0.8'
    }

    # 1. Moxfield
    if 'moxfield.com' in url:
        deck_id = extract_moxfield_deck_id(url)
        api_url = f'https://api2.moxfield.com/v2/decks/all/{deck_id}'
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            mox_data = json.loads(resp.read().decode('utf-8'))
            return parse_moxfield_data(mox_data)

    # 2. TopDeck.gg
    elif 'topdeck.gg' in url:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode('utf-8', errors='ignore')

        m_title = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
        deck_name = 'TopDeck.gg Deck'
        if m_title:
            raw_title = m_title.group(1).replace('&apos;', "'").replace('&amp;', '&').strip()
            deck_name = raw_title.split(' - ')[0] if ' - ' in raw_title else raw_title

        m_content = re.search(r'const\s+decklistContent\s*=\s*`([^`]+)`', html)
        if not m_content:
            raise ValueError('Could not find decklistContent in TopDeck.gg page.')

        deck_text = m_content.group(1).strip()
        parsed = parse_decklist_text(deck_text)
        return {
            'name': deck_name,
            'format': 'premodern' if 'premodern' in html.lower() else 'constructed',
            'mainboard': parsed['mainboard'],
            'sideboard': parsed['sideboard']
        }

    # 3. Archidekt
    elif 'archidekt.com' in url:
        m = re.search(r'archidekt\.com/decks/(\d+)', url)
        if not m:
            raise ValueError(f'Could not extract Archidekt deck ID from URL: {url}')
        deck_id = m.group(1)
        api_url = f'https://archidekt.com/api/decks/{deck_id}/'
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            arch_data = json.loads(resp.read().decode('utf-8'))

        deck_name = arch_data.get('name') or f'Archidekt Deck #{deck_id}'
        deck_format = arch_data.get('format', 'premodern')

        mainboard = []
        sideboard = []
        for item in arch_data.get('cards', []):
            qty = item.get('quantity', 1)
            card_obj = item.get('card', {})
            oracle_obj = card_obj.get('oracleCard', {})
            name = oracle_obj.get('name') or card_obj.get('displayName') or 'Unknown Card'
            set_code = card_obj.get('edition', {}).get('editioncode', '').lower() or None
            cn = str(card_obj.get('collectorNumber', '')).lower() or None
            scryfall_id = card_obj.get('uid')

            categories = [c.lower() for c in item.get('categories', [])]
            is_sb = 'sideboard' in categories
            is_foil = item.get('modifier') == 'Foil' or item.get('foil', False)

            entry = {
                'name': name,
                'quantity': qty,
                'set': set_code,
                'collector_number': cn,
                'scryfall_id': scryfall_id,
                'is_foil': is_foil,
                'is_sideboard': is_sb
            }
            if is_sb:
                sideboard.append(entry)
            else:
                mainboard.append(entry)

        return {
            'name': deck_name,
            'format': deck_format,
            'mainboard': mainboard,
            'sideboard': sideboard
        }

    # 4. MTGGoldfish
    elif 'mtggoldfish.com' in url:
        m = re.search(r'deck/(?:visual/|download/)?(\d+)', url)
        if not m:
            raise ValueError(f'Could not extract MTGGoldfish deck ID from URL: {url}')
        deck_id = m.group(1)
        dl_url = f'https://www.mtggoldfish.com/deck/download/{deck_id}'
        req = urllib.request.Request(dl_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            deck_text = resp.read().decode('utf-8', errors='ignore')
        parsed = parse_decklist_text(deck_text)
        return {
            'name': f'MTGGoldfish Deck #{deck_id}',
            'format': 'premodern' if 'premodern' in url.lower() else 'constructed',
            'mainboard': parsed['mainboard'],
            'sideboard': parsed['sideboard']
        }

    # 5. MTGTop8
    elif 'mtgtop8.com' in url:
        m = re.search(r'[?&]d=(\d+)', url)
        if not m:
            raise ValueError(f'Could not extract MTGTop8 deck ID (d=...) from URL: {url}')
        deck_id = m.group(1)
        mtgo_url = f'https://www.mtgtop8.com/mtgo?d={deck_id}'
        req = urllib.request.Request(mtgo_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            deck_text = resp.read().decode('utf-8', errors='ignore')
        parsed = parse_decklist_text(deck_text)
        return {
            'name': f'MTGTop8 Deck #{deck_id}',
            'format': 'premodern' if 'premodern' in url.lower() else 'constructed',
            'mainboard': parsed['mainboard'],
            'sideboard': parsed['sideboard']
        }

    # 6. Cube Cobra
    elif 'cubecobra.com' in url:
        m = re.search(r'cubecobra\.com/cube/(?:overview/|list/|deck/|api/cubelist/)?([A-Za-z0-9_\-]+)', url)
        if not m:
            raise ValueError(f'Could not extract Cube Cobra cube ID from URL: {url}')
        cube_id = m.group(1)
        api_url = f'https://cubecobra.com/cube/api/cubelist/{cube_id}'
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            deck_text = resp.read().decode('utf-8', errors='ignore')
        parsed = parse_decklist_text(deck_text)
        return {
            'name': f'Cube Cobra: {cube_id}',
            'format': 'cube',
            'mainboard': parsed['mainboard'],
            'sideboard': parsed['sideboard']
        }

    # 7. Pastebin
    elif 'pastebin.com' in url:
        m = re.search(r'pastebin\.com/(?:raw/)?([A-Za-z0-9]+)', url)
        if not m:
            raise ValueError(f'Could not extract Pastebin ID from URL: {url}')
        raw_url = f'https://pastebin.com/raw/{m.group(1)}'
        req = urllib.request.Request(raw_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            deck_text = resp.read().decode('utf-8', errors='ignore')
        parsed = parse_decklist_text(deck_text)
        return {
            'name': f'Pastebin Deck #{m.group(1)}',
            'format': 'premodern',
            'mainboard': parsed['mainboard'],
            'sideboard': parsed['sideboard']
        }

    # 8. GitHub Gist
    elif 'gist.github.com' in url or 'gist.githubusercontent.com' in url:
        raw_url = url
        if 'raw' not in url:
            m = re.search(r'gist\.github\.com/([^/]+)/([A-Za-z0-9]+)', url)
            if m:
                raw_url = f'https://gist.githubusercontent.com/{m.group(1)}/{m.group(2)}/raw'
        req = urllib.request.Request(raw_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            deck_text = resp.read().decode('utf-8', errors='ignore')
        parsed = parse_decklist_text(deck_text)
        return {
            'name': 'GitHub Gist Deck',
            'format': 'premodern',
            'mainboard': parsed['mainboard'],
            'sideboard': parsed['sideboard']
        }

    # 9. Generic URL fallback (plain text files)
    else:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            content_type = resp.headers.get('Content-Type', '')
            text_data = resp.read().decode('utf-8', errors='ignore')
            parsed = parse_decklist_text(text_data)
            if parsed['mainboard'] or parsed['sideboard']:
                return {
                    'name': 'Imported Deck',
                    'format': 'premodern',
                    'mainboard': parsed['mainboard'],
                    'sideboard': parsed['sideboard']
                }
            else:
                raise ValueError(f'Unsupported deck site or unparseable URL: {url}')

