"""
Scryfall Client for MTG Deck Visualizer.
Complies with Scryfall API guidelines:
- Identifiable User-Agent
- Rate-limited polite requests
- Bulk /cards/collection usage
- Local SQLite persistent caching
- Support for Retro Border detection (frame: 1993/1997)
- Support for image_status detection (identifies Scryfall placeholders)
- Curated alternate scans for foreign cards missing from Scryfall
"""

import os
import json
import sqlite3
import time
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scryfall_cache.db')

PREMODERN_SETS = {
    '4ed', 'ice', 'chr', 'ren', 'hml', 'all', 'mir', 'vis', '5ed', 'por', 'wth',
    'tmp', 'sth', 'exo', 'usg', 'ath', 'ulg', '6ed', 'uds', 's99', 'p02', 'mmq',
    'brb', 'nem', 's00', 'pcy', 'btd', 'inv', 'pls', '7ed', 'apc', 'ody', 'dkm',
    'tor', 'jud', 'ons', 'lgn', 'scg',
    'wc97', 'wc98', 'wc99', 'wc00', 'wc01', 'wc02', 'wc03',
    'ptc', 'prm', 'fbb', '4bb', 'rqs', 'drk', 'atq', 'arn', 'leg', '3ed', '2ed', 'leb', 'lea'
}

LANG_MAP = {
    'en': 'English',
    'ja': 'Japanese (日本語)',
    'de': 'German (Deutsch)',
    'fr': 'French (Français)',
    'it': 'Italian (Italiano)',
    'es': 'Spanish (Español)',
    'pt': 'Portuguese (Português)',
    'zhs': 'Simplified Chinese (简体中文)',
    'zht': 'Traditional Chinese (繁體中文)',
    'ko': 'Korean (한국어)',
    'ru': 'Russian (Русский)',
    'la': 'Latin',
    'grc': 'Ancient Greek',
    'ar': 'Arabic',
    'sa': 'Sanskrit',
    'ph': 'Phyrexian'
}

# Curated alternate scans for cards where Scryfall only has placeholders
CURATED_ALTERNATE_SCANS = {
    ('diabolic edict', 'tmp', 'ja'): [
        {
            'id': 'alt_tmp_ja_verified',
            'source': 'Japanese Tempest Scan',
            'name': 'Diabolic Edict',
            'label': 'Tempest (TMP) #128 Japanese [悪魔の布告] — Verified Physical Scan',
            'image_url': '/static/scans/diabolic_edict_tmp_ja.jpg?v=4',
            'image_large': '/static/scans/diabolic_edict_tmp_ja.jpg?v=4',
            'set': 'tmp',
            'set_name': 'Tempest',
            'collector_number': '128',
            'lang': 'ja',
            'lang_name': 'Japanese (日本語)',
            'printed_name': '悪魔の布告',
            'frame': '1997',
            'is_retro': True,
            'is_premodern': True,
            'image_status': 'highres_scan',
            'is_placeholder': False
        },
        {
            'id': 'alt_mh1_ja_verified',
            'source': 'Modern Horizons (MH1)',
            'name': 'Diabolic Edict',
            'label': 'MH1 Japanese [悪魔の布告] — High-Res Japanese Scan',
            'image_url': '/static/scans/diabolic_edict_mh1_ja.png?v=4',
            'image_large': '/static/scans/diabolic_edict_mh1_ja.png?v=4',
            'set': 'mh1',
            'set_name': 'Modern Horizons',
            'collector_number': '87',
            'lang': 'ja',
            'lang_name': 'Japanese (日本語)',
            'printed_name': '悪魔の布告',
            'frame': '2015',
            'is_retro': False,
            'is_premodern': False,
            'image_status': 'highres_scan',
            'is_placeholder': False
        },
        {
            'id': 'alt_a25_ja_verified',
            'source': 'Masters 25 (A25)',
            'name': 'Diabolic Edict',
            'label': 'A25 Japanese [悪魔の布告] — Real Japanese Scan',
            'image_url': '/static/scans/diabolic_edict_a25_ja.jpg?v=4',
            'image_large': '/static/scans/diabolic_edict_a25_ja.jpg?v=4',
            'set': 'a25',
            'set_name': 'Masters 25',
            'collector_number': '85',
            'lang': 'ja',
            'lang_name': 'Japanese (日本語)',
            'printed_name': '悪魔の布告',
            'frame': '2015',
            'is_retro': False,
            'is_premodern': False,
            'image_status': 'lowres',
            'is_placeholder': False
        }
    ],
    ('faerie conclave', 'ulg', 'ja'): [
        {
            'id': 'alt_fc_ulg_ja_verified',
            'source': "Japanese Urza's Legacy Scan",
            'name': 'Faerie Conclave',
            'label': "Urza's Legacy (ULG) #139 Japanese [フェアリーの集会場] — Verified Physical Scan",
            'image_url': '/static/scans/faerie_conclave_ulg_ja.jpg?v=1',
            'image_large': '/static/scans/faerie_conclave_ulg_ja.jpg?v=1',
            'set': 'ulg',
            'set_name': "Urza's Legacy",
            'collector_number': '139',
            'lang': 'ja',
            'lang_name': 'Japanese (日本語)',
            'printed_name': 'フェアリーの集会場',
            'frame': '1997',
            'is_retro': True,
            'is_premodern': True,
            'image_status': 'highres_scan',
            'is_placeholder': False
        }
    ]
}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS card_cache (
            cache_key TEXT PRIMARY KEY,
            card_json TEXT,
            updated_at REAL
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS printings_cache (
            card_name TEXT PRIMARY KEY,
            printings_json TEXT,
            updated_at REAL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_cached_card(cache_key: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT card_json FROM card_cache WHERE cache_key = ?', (cache_key.lower(),))
    row = cur.fetchone()
    conn.close()
    if row:
        try:
            return json.loads(row[0])
        except Exception:
            return None
    return None

def set_cached_card(cache_key: str, card_data: dict):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        INSERT OR REPLACE INTO card_cache (cache_key, card_json, updated_at)
        VALUES (?, ?, ?)
    ''', (cache_key.lower(), json.dumps(card_data), time.time()))
    conn.commit()
    conn.close()

def get_cached_printings(card_name: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT printings_json FROM printings_cache WHERE card_name = ?', (card_name.lower(),))
    row = cur.fetchone()
    conn.close()
    if row:
        try:
            return json.loads(row[0])
        except Exception:
            return None
    return None

def set_cached_printings(card_name: str, printings_data: list):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        INSERT OR REPLACE INTO printings_cache (card_name, printings_json, updated_at)
        VALUES (?, ?, ?)
    ''', (card_name.lower(), json.dumps(printings_data), time.time()))
    conn.commit()
    conn.close()

def normalize_card_dict(c: dict, is_foil=False):
    if not c:
        return None
    image_uris = c.get('image_uris', {})
    if not image_uris and 'card_faces' in c and c['card_faces']:
        image_uris = c['card_faces'][0].get('image_uris', {})
    image_normal = image_uris.get('normal', image_uris.get('large', image_uris.get('small', '')))
    image_large = image_uris.get('large', image_uris.get('png', image_normal))
    set_code = c.get('set', '').lower()
    released = c.get('released_at', '')
    is_premodern = (
        set_code in PREMODERN_SETS or 
        (released and '1995-04-01' <= released <= '2003-06-01')
    )
    lang_code = c.get('lang', 'en').lower()
    lang_name = LANG_MAP.get(lang_code, lang_code.upper())
    border_color = c.get('border_color', 'black')
    frame = c.get('frame', '1997')
    
    # Retro border filter: 1993 and 1997 frames
    is_retro = (frame in ('1993', '1997'))
    
    # Scryfall image status: 'placeholder', 'lowres', 'highres_scan'
    image_status = c.get('image_status', 'highres_scan')
    is_placeholder = (image_status == 'placeholder')

    # Check for curated alternate scan replacement if placeholder
    card_name = c.get('name', '').lower()
    alt_scans = CURATED_ALTERNATE_SCANS.get((card_name, set_code, lang_code), [])

    # If placeholder and curated scan exists, default to the real scan!
    if is_placeholder and alt_scans:
        best_alt = alt_scans[0]
        image_normal = best_alt['image_url']
        image_large = best_alt.get('image_large', image_normal)
        image_status = 'highres_scan'
        is_placeholder = False

    return {
        'id': c.get('id'),
        'name': c.get('name'),
        'printed_name': c.get('printed_name', c.get('name')),
        'set': set_code,
        'set_name': c.get('set_name', set_code.upper()),
        'collector_number': c.get('collector_number', ''),
        'lang': lang_code,
        'lang_name': lang_name,
        'released_at': released,
        'image_url': image_normal,
        'image_large': image_large,
        'image_status': image_status,
        'is_placeholder': is_placeholder,
        'mana_cost': c.get('mana_cost', ''),
        'cmc': c.get('cmc', 0.0),
        'type_line': c.get('type_line', ''),
        'oracle_text': c.get('oracle_text', ''),
        'power': c.get('power'),
        'toughness': c.get('toughness'),
        'frame': frame,
        'is_retro': is_retro,
        'border_color': border_color,
        'is_foil': is_foil or ('foil' in c.get('finishes', []) and not 'nonfoil' in c.get('finishes', [])),
        'is_premodern': is_premodern,
        'alternate_scans': alt_scans
    }

def fetch_from_scryfall(url: str, post_data: dict = None):
    headers = {
        'User-Agent': 'MTGPremodernDeckVisualizer/1.0 (https://github.com/granolaFPV/premodern-deck-visualizer)',
        'Accept': 'application/json'
    }
    data_bytes = None
    if post_data is not None:
        data_bytes = json.dumps(post_data).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data_bytes, headers=headers)
    
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                time.sleep(0.5 * (attempt + 1))
                continue
            return None
        except Exception:
            time.sleep(0.2)
            continue
    return None

def resolve_card_premodern_fallback(card_name: str):
    cache_key = f"pm_fallback:{card_name}"
    cached = get_cached_card(cache_key)
    if cached:
        return cached
    query = f'!\"{card_name}\" (date>=1995-04-01 date<=2003-06-01) unique:prints order:released dir:asc'
    url = f"https://api.scryfall.com/cards/search?q={urllib.parse.quote(query)}"
    data = fetch_from_scryfall(url)
    card_obj = None
    if data and data.get('data'):
        for candidate in data['data']:
            if candidate.get('image_uris') or ('card_faces' in candidate and candidate['card_faces'][0].get('image_uris')):
                card_obj = candidate
                break
    if not card_obj:
        query_all = f'!\"{card_name}\" unique:prints order:released dir:asc'
        url_all = f"https://api.scryfall.com/cards/search?q={urllib.parse.quote(query_all)}"
        data_all = fetch_from_scryfall(url_all)
        if data_all and data_all.get('data'):
            card_obj = data_all['data'][0]
    if card_obj:
        normalized = normalize_card_dict(card_obj)
        set_cached_card(cache_key, normalized)
        return normalized
    return None

def resolve_single_card(item: dict):
    name = item['name']
    set_code = (item.get('set') or '').lower()
    cn = item.get('collector_number')
    scryfall_id = item.get('scryfall_id')
    is_foil = item.get('is_foil', False)

    # 1. If scryfall_id is provided, respect it exactly!
    if scryfall_id:
        cache_key = f"id:{scryfall_id}"
        cached = get_cached_card(cache_key)
        if cached:
            c = dict(cached)
            c['is_foil'] = is_foil
            return c
        raw = fetch_from_scryfall(f"https://api.scryfall.com/cards/{scryfall_id}")
        if raw:
            norm = normalize_card_dict(raw, is_foil=is_foil)
            set_cached_card(cache_key, norm)
            return norm

    # 2. If set_code and collector_number are provided, respect them exactly!
    if set_code and cn:
        cache_key = f"set_cn:{set_code}:{cn}"
        cached = get_cached_card(cache_key)
        if cached:
            c = dict(cached)
            c['is_foil'] = is_foil
            return c
        raw = fetch_from_scryfall(f"https://api.scryfall.com/cards/{set_code}/{cn}")
        if raw:
            norm = normalize_card_dict(raw, is_foil=is_foil)
            set_cached_card(cache_key, norm)
            return norm

    # 3. If set_code is provided without collector_number, query exact name and set:
    if set_code:
        cache_key = f"set_name:{set_code}:{name}"
        cached = get_cached_card(cache_key)
        if cached:
            c = dict(cached)
            c['is_foil'] = is_foil
            return c
        raw = fetch_from_scryfall(f"https://api.scryfall.com/cards/named?exact={urllib.parse.quote(name)}&set={set_code}")
        if raw:
            norm = normalize_card_dict(raw, is_foil=is_foil)
            set_cached_card(cache_key, norm)
            return norm

    # 4. If NO set was provided: default to the authentic Premodern era (4ED -> SCG) printing!
    norm = resolve_card_premodern_fallback(name)
    if norm:
        c = dict(norm)
        c['is_foil'] = is_foil
        return c

    # 5. Final fallback to named query
    raw = fetch_from_scryfall(f"https://api.scryfall.com/cards/named?exact={urllib.parse.quote(name)}")
    if raw:
        return normalize_card_dict(raw, is_foil=is_foil)
    return {
        'id': f'unknown-{name}',
        'name': name,
        'printed_name': name,
        'set': '???',
        'set_name': 'Unknown Set',
        'collector_number': '',
        'lang': 'en',
        'lang_name': 'English',
        'released_at': '',
        'image_url': '',
        'image_large': '',
        'image_status': 'placeholder',
        'is_placeholder': True,
        'is_foil': is_foil,
        'is_retro': False,
        'is_premodern': False,
        'alternate_scans': []
    }

def resolve_deck_cards(deck_items: list):
    resolved_map = {}
    items_to_resolve = []
    for it in deck_items:
        key_tuple = (it['name'], it.get('set'), it.get('collector_number'), it.get('scryfall_id'))
        set_code = (it.get('set') or '').lower()
        cn = it.get('collector_number')
        scryfall_id = it.get('scryfall_id')

        # Check cache first
        if scryfall_id:
            c = get_cached_card(f"id:{scryfall_id}")
            if c:
                resolved_map[key_tuple] = c
                continue
        elif set_code and cn:
            c = get_cached_card(f"set_cn:{set_code}:{cn}")
            if c:
                resolved_map[key_tuple] = c
                continue
        elif set_code:
            c = get_cached_card(f"set_name:{set_code}:{it['name']}")
            if c:
                resolved_map[key_tuple] = c
                continue
        else:
            c = get_cached_card(f"pm_fallback:{it['name']}")
            if c:
                resolved_map[key_tuple] = c
                continue

        items_to_resolve.append((key_tuple, it))

    if not items_to_resolve:
        return resolved_map

    collection_items = []
    other_items = []
    for key_tuple, it in items_to_resolve:
        set_code = (it.get('set') or '').lower()
        cn = it.get('collector_number')
        scryfall_id = it.get('scryfall_id')

        if scryfall_id:
            # 1. Exact Scryfall ID
            ident = {'id': scryfall_id}
            collection_items.append((key_tuple, ident, it))
        elif set_code and cn:
            # 2. Exact set and collector_number (DO NOT include 'name', which causes Scryfall to ignore collector_number!)
            ident = {'set': set_code, 'collector_number': str(cn).lower()}
            collection_items.append((key_tuple, ident, it))
        elif set_code:
            # 3. Exact name and set
            ident = {'name': it['name'], 'set': set_code}
            collection_items.append((key_tuple, ident, it))
        else:
            # 4. No set specified: resolve via premodern fallback
            other_items.append((key_tuple, it))

    if collection_items:
        for i in range(0, len(collection_items), 75):
            batch = collection_items[i:i+75]
            identifiers = [b[1] for b in batch]
            res = fetch_from_scryfall('https://api.scryfall.com/cards/collection', {'identifiers': identifiers})
            if res and res.get('data'):
                for card_obj in res['data']:
                    norm = normalize_card_dict(card_obj)
                    set_cached_card(f"id:{norm['id']}", norm)
                    if norm.get('set') and norm.get('collector_number'):
                        set_cached_card(f"set_cn:{norm['set']}:{norm['collector_number']}", norm)
                    if norm.get('set') and norm.get('name'):
                        set_cached_card(f"set_name:{norm['set']}:{norm['name']}", norm)
                    for key_tuple, ident, orig_it in batch:
                        if key_tuple not in resolved_map:
                            # Match precisely by the identifier format that was requested
                            if orig_it.get('scryfall_id') and orig_it['scryfall_id'] == norm['id']:
                                resolved_map[key_tuple] = norm
                            elif orig_it.get('set') and orig_it.get('collector_number'):
                                if (orig_it['set'].lower() == norm['set'].lower() and 
                                    str(orig_it['collector_number']).lower() == str(norm.get('collector_number', '')).lower()):
                                    resolved_map[key_tuple] = norm
                            elif orig_it.get('set'):
                                if (orig_it['set'].lower() == norm['set'].lower() and 
                                    orig_it['name'].lower() == norm['name'].lower()):
                                    resolved_map[key_tuple] = norm
                            elif orig_it['name'].lower() == norm['name'].lower():
                                resolved_map[key_tuple] = norm

            for key_tuple, ident, orig_it in batch:
                if key_tuple not in resolved_map:
                    other_items.append((key_tuple, orig_it))

    if other_items:
        for key_tuple, it in other_items:
            time.sleep(0.06)
            res_card = resolve_single_card(it)
            resolved_map[key_tuple] = res_card

    return resolved_map

def get_all_printings_and_languages(card_name: str):
    cached = get_cached_printings(card_name)
    if cached:
        # Ensure curated alternate scans always override cached Scryfall placeholders
        curated_keys = set()
        curated_items = []
        for (cname, s_code, l_code), alts in CURATED_ALTERNATE_SCANS.items():
            if cname == card_name.lower():
                for alt in alts:
                    key = (alt['set'].lower(), str(alt.get('collector_number', '')).lower(), alt['lang'].lower())
                    curated_keys.add(key)
                    curated_items.append(alt)
        if curated_keys:
            merged = [p for p in cached if (p['set'].lower(), str(p.get('collector_number', '')).lower(), p['lang'].lower()) not in curated_keys]
            merged.extend(curated_items)
            def sort_k(p):
                is_ph = 1 if p.get('is_placeholder') else 0
                is_pm = 0 if p.get('is_premodern') else 1
                is_retro = 0 if p.get('is_retro') else 1
                lang_order = 0 if p['lang'] in ('en', 'ja') else (1 if p['lang'] in ('de', 'fr', 'it', 'es') else 2)
                rel = p.get('released_at') or '9999-99-99'
                return (is_ph, is_pm, is_retro, lang_order, rel)
            merged.sort(key=sort_k)
            return merged
        return cached

    # Optimize query for basic lands to avoid fetching 3,000+ prints across 21 pages
    is_basic_land = card_name.lower() in ('swamp', 'island', 'plains', 'mountain', 'forest')
    if is_basic_land:
        query = f'!\"{card_name}\" (date<=2003-06-01 or is:retro) lang:any include:extras unique:prints'
        max_pages = 4
    else:
        query = f'!\"{card_name}\" lang:any include:extras unique:prints'
        max_pages = 10

    url = f"https://api.scryfall.com/cards/search?q={urllib.parse.quote(query)}"
    all_cards = []
    page_count = 0
    while url and page_count < max_pages:
        page_count += 1
        data = fetch_from_scryfall(url)
        if not data:
            break
        if data.get('data'):
            all_cards.extend(data['data'])
        if data.get('has_more') and data.get('next_page'):
            url = data['next_page']
            time.sleep(0.06)
        else:
            break
    seen_keys = set()
    unique_printings = []
    
    # 1. Curated verified scans take highest precedence
    for (cname, s_code, l_code), alts in CURATED_ALTERNATE_SCANS.items():
        if cname == card_name.lower():
            for alt in alts:
                key = (alt['set'].lower(), str(alt.get('collector_number', '')).lower(), alt['lang'].lower())
                seen_keys.add(key)
                unique_printings.append(alt)

    # 2. Add Scryfall printings (skipping any already covered by curated scans)
    for c in all_cards:
        norm = normalize_card_dict(c)
        if norm and norm.get('image_url'):
            key = (norm['set'].lower(), str(norm.get('collector_number', '')).lower(), norm['lang'].lower())
            if key not in seen_keys:
                seen_keys.add(key)
                unique_printings.append(norm)

    printings = unique_printings

    def sort_key(p):
        # 1. Real scans before placeholders!
        is_ph = 1 if p.get('is_placeholder') else 0
        # 2. Premodern era first
        is_pm = 0 if p.get('is_premodern') else 1
        # 3. Retro border first
        is_retro = 0 if p.get('is_retro') else 1
        # 4. Preferred languages (EN, JA)
        lang_order = 0 if p['lang'] in ('en', 'ja') else (1 if p['lang'] in ('de', 'fr', 'it', 'es') else 2)
        rel = p.get('released_at') or '9999-99-99'
        return (is_ph, is_pm, is_retro, lang_order, rel)

    printings.sort(key=sort_key)
    if printings:
        set_cached_printings(card_name, printings)
    return printings
