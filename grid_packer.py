"""
Grid Packer for MTG Deck Visualizer.
Supports 5 distinct physical deck photo layouts inspired by real player submissions:
1. 'classic': Classic 6x10 Table Grid with 38° fanned sideboard below.
2. 'type_columns': Vertical Mana & Type Columns (overlapping cascade, Reddit style).
3. 'sideboard_right': Mainboard on left (8 cols), Sideboard column on right.
4. 'horizontal_cascade': 3-4 wide horizontal tiers across table.
5. 'chaos_table': Wild 'n crazy casual kitchen table spread with organic rotations.

Also supports stacking basic lands only OR stacking all multiple copies with center quantity dice.
"""

import math
import random

def is_basic_land(g):
    name = g.get('name', '').strip().lower()
    type_line = g.get('card_data', {}).get('type_line', '').lower()
    basics = {
        'plains', 'island', 'swamp', 'mountain', 'forest',
        'snow-covered plains', 'snow-covered island', 'snow-covered swamp',
        'snow-covered mountain', 'snow-covered forest'
    }
    return ('basic land' in type_line) or (name in basics)

def should_stack(g, stack_basics=False, stack_all_multiples=False):
    if g.get('quantity', 1) <= 1:
        return False
    if stack_all_multiples:
        return True
    if stack_basics and is_basic_land(g):
        return True
    return False

def pack_mainboard(card_groups, target_rows=6, target_cols=10, stack_basics=False, stack_all_multiples=False, is_chaos=False):
    cols = target_cols
    effective_cards = sum(
        1 if should_stack(g, stack_basics, stack_all_multiples) else g['quantity']
        for g in card_groups
    )
    if stack_all_multiples or stack_basics:
        rows = max(3, math.ceil(effective_cards / cols)) if effective_cards > 0 else target_rows
    else:
        rows = max(target_rows, math.ceil(effective_cards / cols)) if effective_cards > 0 else target_rows
    
    grid = [[None for _ in range(cols)] for _ in range(rows)]
    
    land_groups = []
    spell_groups = []
    
    for g in card_groups:
        type_line = g.get('card_data', {}).get('type_line', '').lower()
        is_land_type = ('land' in type_line) or is_basic_land(g)
        if is_land_type:
            land_groups.append(g)
        else:
            spell_groups.append(g)
            
    spell_groups.sort(key=lambda g: (-g['quantity'], g['name']))
    land_groups.sort(key=lambda g: (-g['quantity'], g['name']))
    
    curr_r = rows - 1
    curr_c = cols - 1
    
    land_instances_placed = []
    for lg in land_groups:
        if should_stack(lg, stack_basics=stack_basics, stack_all_multiples=stack_all_multiples):
            if curr_r >= 0:
                instance = {
                    'instance_id': f"{lg['group_id']}_stack",
                    'name': lg['name'],
                    'group_id': lg['group_id'],
                    'card_data': dict(lg['card_data']),
                    'row': curr_r,
                    'col': curr_c,
                    'is_land': True,
                    'is_stacked': True,
                    'stack_count': lg['quantity']
                }
                grid[curr_r][curr_c] = instance
                land_instances_placed.append(instance)
                curr_c -= 1
                if curr_c < 0:
                    curr_c = cols - 1
                    curr_r -= 1
        else:
            for idx in range(lg['quantity']):
                if curr_r < 0:
                    break
                instance = {
                    'instance_id': f"{lg['group_id']}_{idx}",
                    'name': lg['name'],
                    'group_id': lg['group_id'],
                    'card_data': dict(lg['card_data']),
                    'row': curr_r,
                    'col': curr_c,
                    'is_land': True,
                    'is_stacked': False,
                    'stack_count': 1
                }
                grid[curr_r][curr_c] = instance
                land_instances_placed.append(instance)
                
                curr_c -= 1
                if curr_c < 0:
                    curr_c = cols - 1
                    curr_r -= 1
                    
    def get_shapes(qty):
        if qty == 4:
            return [(2, 2), (1, 4), (4, 1)]
        elif qty == 3:
            return [(1, 3), (3, 1)]
        elif qty == 2:
            return [(1, 2), (2, 1)]
        elif qty == 1:
            return [(1, 1)]
        return [(1, 1)]

    def can_place(r, c, h, w):
        if r + h > rows or c + w > cols:
            return False
        for dr in range(h):
            for dc in range(w):
                if grid[r + dr][c + dc] is not None:
                    return False
        return True

    def place_shape(r, c, h, w, grp, is_stacked_card=False):
        placed_cells = []
        idx = 0
        for dr in range(h):
            for dc in range(w):
                instance = {
                    'instance_id': f"{grp['group_id']}_{'stack' if is_stacked_card else idx}",
                    'name': grp['name'],
                    'group_id': grp['group_id'],
                    'card_data': dict(grp['card_data']),
                    'row': r + dr,
                    'col': c + dc,
                    'is_land': False,
                    'is_stacked': is_stacked_card,
                    'stack_count': grp['quantity'] if is_stacked_card else 1
                }
                grid[r + dr][c + dc] = instance
                placed_cells.append((r + dr, c + dc))
                idx += 1
        return placed_cells

    def unplace_cells(cells):
        for r, c in cells:
            grid[r][c] = None

    def find_first_empty():
        for r in range(rows):
            for c in range(cols):
                if grid[r][c] is None:
                    return r, c
        return None

    solved = False
    processed_spells = []
    for g in spell_groups:
        is_stk = should_stack(g, stack_basics=stack_basics, stack_all_multiples=stack_all_multiples)
        processed_spells.append({
            'group': g,
            'is_stacked': is_stk,
            'eff_qty': 1 if is_stk else g['quantity']
        })

    def backtrack(idx, remaining):
        nonlocal solved
        if not remaining:
            solved = True
            return True
            
        empty = find_first_empty()
        if not empty:
            if all(p['eff_qty'] == 0 for p in remaining):
                solved = True
                return True
            return False
            
        r, c = empty
        for i, item in enumerate(remaining):
            grp = item['group']
            is_stk = item['is_stacked']
            eff_qty = item['eff_qty']
            shapes = get_shapes(eff_qty)
            for h, w in shapes:
                if can_place(r, c, h, w):
                    cells = place_shape(r, c, h, w, grp, is_stacked_card=is_stk)
                    new_remaining = remaining[:i] + remaining[i+1:]
                    if backtrack(idx + 1, new_remaining):
                        return True
                    unplace_cells(cells)
        return False

    success = backtrack(0, list(processed_spells))
    
    if not success:
        for item in processed_spells:
            grp = item['group']
            is_stk = item['is_stacked']
            eff_qty = item['eff_qty']
            placed = 0
            empty = find_first_empty()
            if not empty:
                break
            sr, sc = empty
            frontier = [(sr, sc)]
            visited = set()
            while frontier and placed < eff_qty:
                cr, cc = frontier.pop(0)
                if (cr, cc) in visited or cr < 0 or cr >= rows or cc < 0 or cc >= cols:
                    continue
                visited.add((cr, cc))
                if grid[cr][cc] is None:
                    grid[cr][cc] = {
                        'instance_id': f"{grp['group_id']}_{'stack' if is_stk else placed}",
                        'name': grp['name'],
                        'group_id': grp['group_id'],
                        'card_data': dict(grp['card_data']),
                        'row': cr,
                        'col': cc,
                        'is_land': False,
                        'is_stacked': is_stk,
                        'stack_count': grp['quantity'] if is_stk else 1
                    }
                    placed += 1
                    for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] is None:
                            frontier.append((nr, nc))

    all_instances = []
    rng = random.Random(42)
    
    for r in range(rows):
        for c in range(cols):
            inst = grid[r][c]
            if inst is not None:
                if is_chaos:
                    rot = round((rng.random() - 0.5) * 14.0, 2)
                    dx = round((rng.random() - 0.5) * 14.0, 1)
                    dy = round((rng.random() - 0.5) * 14.0, 1)
                else:
                    rot = round((rng.random() - 0.5) * 1.2, 2)
                    dx = round((rng.random() - 0.5) * 2.5, 1)
                    dy = round((rng.random() - 0.5) * 2.5, 1)
                
                inst['jitter'] = {
                    'rotation': rot,
                    'dx': dx,
                    'dy': dy
                }
                all_instances.append(inst)
                
    return {
        'grid': grid,
        'rows': rows,
        'cols': cols,
        'cards': all_instances,
        'total_cards': len(all_instances)
    }

def pack_sideboard(sb_groups, max_per_row=8, base_angle=-38.0, is_chaos=False):
    card_items = []
    for g in sb_groups:
        for idx in range(g['quantity']):
            card_items.append({
                'name': g['name'],
                'group_id': g['group_id'],
                'card_data': dict(g['card_data']),
                'sub_index': idx
            })
            
    total = len(card_items)
    if total == 0:
        return {'rows': [], 'cards': [], 'total_cards': 0}
        
    num_rows = 2 if total > max_per_row else 1
    if num_rows == 2:
        row0_count = math.ceil(total / 2)
        row1_count = total - row0_count
        row_counts = [row0_count, row1_count]
    else:
        row_counts = [total]
        
    rng = random.Random(1337)
    sb_cards = []
    
    item_idx = 0
    for r_idx, count in enumerate(row_counts):
        for c_idx in range(count):
            if item_idx >= total:
                break
            raw_item = card_items[item_idx]
            
            if is_chaos:
                angle_jitter = round((rng.random() - 0.5) * 10.0, 1)
            else:
                angle_jitter = round((rng.random() - 0.5) * 2.0, 1)
            card_angle = base_angle + angle_jitter
            
            inst = {
                'instance_id': f"sb_{raw_item['group_id']}_{raw_item['sub_index']}",
                'name': raw_item['name'],
                'group_id': raw_item['group_id'],
                'card_data': raw_item['card_data'],
                'sb_row': r_idx,
                'sb_col': c_idx,
                'total_in_row': count,
                'angle': card_angle,
                'is_sideboard': True
            }
            sb_cards.append(inst)
            item_idx += 1
            
    return {
        'cards': sb_cards,
        'num_rows': num_rows,
        'total_cards': len(sb_cards)
    }

def pack_sideboard_flat(sb_groups, max_per_row=8):
    card_items = []
    for g in sb_groups:
        for idx in range(g['quantity']):
            card_items.append({
                'name': g['name'],
                'group_id': g['group_id'],
                'card_data': dict(g['card_data']),
                'sub_index': idx
            })
    total = len(card_items)
    if total == 0:
        return {'rows': [], 'cards': [], 'total_cards': 0}
    num_rows = 2 if total > max_per_row else 1
    per_row = math.ceil(total / num_rows)
    all_instances = []
    for i, it in enumerate(card_items):
        r = i // per_row
        c = i % per_row
        count_in_row = per_row if r < num_rows - 1 else (total - per_row * (num_rows - 1))
        all_instances.append({
            'instance_id': f"sb_{it['group_id']}_{it['sub_index']}",
            'name': it['name'],
            'group_id': it['group_id'],
            'card_data': it['card_data'],
            'sb_row': r,
            'sb_col': c,
            'total_in_row': count_in_row,
            'angle': 0.0,
            'is_sideboard': True
        })
    return {
        'cards': all_instances,
        'num_rows': num_rows,
        'total_cards': len(all_instances)
    }

def pack_type_columns(card_groups, sb_groups, stack_basics=False, stack_all_multiples=False):
    buckets = [[] for _ in range(6)]
    for g in card_groups:
        type_line = g.get('card_data', {}).get('type_line', '').lower()
        cmc = float(g.get('card_data', {}).get('cmc', 0.0))
        if 'basic land' in type_line or is_basic_land(g):
            buckets[5].append(g)
        elif 'land' in type_line:
            buckets[4].append(g)
        elif 'creature' in type_line:
            if cmc <= 2.0:
                buckets[0].append(g)
            else:
                buckets[1].append(g)
        elif 'instant' in type_line:
            buckets[2].append(g)
        else:
            buckets[3].append(g)
            
    for b in buckets:
        b.sort(key=lambda g: (float(g.get('card_data', {}).get('cmc', 0.0)), g.get('name', '')))
        
    active_cols = [b for b in buckets if b]
    if not active_cols:
        active_cols = [card_groups]
        
    balanced_cols = []
    for col in active_cols:
        total_in_col = sum(
            1 if should_stack(g, stack_basics, stack_all_multiples) else g['quantity']
            for g in col
        )
        if total_in_col > 10 and len(col) > 1:
            mid = len(col) // 2
            balanced_cols.append(col[:mid])
            balanced_cols.append(col[mid:])
        else:
            balanced_cols.append(col)
            
    num_cols = len(balanced_cols)
    col_instances = [[] for _ in range(num_cols)]
    rng = random.Random(42)
    
    for c_idx, col in enumerate(balanced_cols):
        for grp in col:
            stacked = should_stack(grp, stack_basics, stack_all_multiples)
            if stacked:
                rot = round((rng.random() - 0.5) * 1.5, 2)
                inst = {
                    'instance_id': f"{grp['group_id']}_stack",
                    'name': grp['name'],
                    'group_id': grp['group_id'],
                    'card_data': dict(grp['card_data']),
                    'row': len(col_instances[c_idx]),
                    'col': c_idx,
                    'is_land': 'land' in grp.get('card_data', {}).get('type_line', '').lower(),
                    'is_stacked': True,
                    'stack_count': grp['quantity'],
                    'jitter': {'rotation': rot, 'dx': 0, 'dy': 0}
                }
                col_instances[c_idx].append(inst)
            else:
                for idx in range(grp['quantity']):
                    rot = round((rng.random() - 0.5) * 1.5, 2)
                    inst = {
                        'instance_id': f"{grp['group_id']}_{idx}",
                        'name': grp['name'],
                        'group_id': grp['group_id'],
                        'card_data': dict(grp['card_data']),
                        'row': len(col_instances[c_idx]),
                        'col': c_idx,
                        'is_land': 'land' in grp.get('card_data', {}).get('type_line', '').lower(),
                        'is_stacked': False,
                        'stack_count': 1,
                        'jitter': {'rotation': rot, 'dx': 0, 'dy': 0}
                    }
                    col_instances[c_idx].append(inst)
                    
    max_rows = max((len(c) for c in col_instances), default=1)
    grid = [[None for _ in range(num_cols)] for _ in range(max_rows)]
    all_cards = []
    for c_idx, cards in enumerate(col_instances):
        for r_idx, inst in enumerate(cards):
            grid[r_idx][c_idx] = inst
            all_cards.append(inst)
            
    packed_mb = {
        'grid': grid,
        'rows': max_rows,
        'cols': num_cols,
        'cards': all_cards,
        'total_cards': len(all_cards),
        'layout': 'type_columns'
    }
    packed_sb = pack_sideboard_flat(sb_groups, max_per_row=8)
    return packed_mb, packed_sb

def pack_sideboard_right(main_groups, sb_groups, stack_basics=False, stack_all_multiples=False):
    mb = pack_mainboard(main_groups, target_rows=6, target_cols=8, stack_basics=stack_basics, stack_all_multiples=stack_all_multiples)
    mb['layout'] = 'sideboard_right'
    
    card_items = []
    for g in sb_groups:
        for idx in range(g['quantity']):
            card_items.append({
                'name': g['name'],
                'group_id': g['group_id'],
                'card_data': dict(g['card_data']),
                'sub_index': idx
            })
    total = len(card_items)
    sb_cards = []
    col_height = math.ceil(total / 2) if total > 8 else total
    for i, it in enumerate(card_items):
        col_offset = 0 if i < col_height else 1
        row_offset = i if col_offset == 0 else (i - col_height)
        sb_cards.append({
            'instance_id': f"sb_{it['group_id']}_{it['sub_index']}",
            'name': it['name'],
            'group_id': it['group_id'],
            'card_data': it['card_data'],
            'sb_row': row_offset,
            'sb_col': col_offset,
            'total_in_row': 2 if total > 8 else 1,
            'angle': 0.0,
            'is_sideboard': True
        })
    packed_sb = {
        'rows': col_height,
        'cols': 2 if total > 8 else 1,
        'cards': sb_cards,
        'total_cards': len(sb_cards),
        'layout': 'sideboard_right'
    }
    return mb, packed_sb

def pack_horizontal_cascade(main_groups, sb_groups, stack_basics=False, stack_all_multiples=False):
    tiers = [[], [], []]
    for g in main_groups:
        type_line = g.get('card_data', {}).get('type_line', '').lower()
        cmc = float(g.get('card_data', {}).get('cmc', 0.0))
        if 'land' in type_line or is_basic_land(g):
            tiers[2].append(g)
        elif 'creature' in type_line or cmc <= 2.0:
            tiers[0].append(g)
        else:
            tiers[1].append(g)
            
    all_cards = []
    grid_rows = 3
    max_in_tier = 0
    tier_cards = [[], [], []]
    rng = random.Random(42)
    
    for r_idx, tier in enumerate(tiers):
        for grp in tier:
            stacked = should_stack(grp, stack_basics, stack_all_multiples)
            if stacked:
                rot = round((rng.random() - 0.5) * 1.5, 2)
                inst = {
                    'instance_id': f"{grp['group_id']}_stack",
                    'name': grp['name'],
                    'group_id': grp['group_id'],
                    'card_data': dict(grp['card_data']),
                    'row': r_idx,
                    'col': len(tier_cards[r_idx]),
                    'is_land': r_idx == 2,
                    'is_stacked': True,
                    'stack_count': grp['quantity'],
                    'jitter': {'rotation': rot, 'dx': 0, 'dy': 0}
                }
                tier_cards[r_idx].append(inst)
            else:
                for idx in range(grp['quantity']):
                    rot = round((rng.random() - 0.5) * 1.5, 2)
                    inst = {
                        'instance_id': f"{grp['group_id']}_{idx}",
                        'name': grp['name'],
                        'group_id': grp['group_id'],
                        'card_data': dict(grp['card_data']),
                        'row': r_idx,
                        'col': len(tier_cards[r_idx]),
                        'is_land': r_idx == 2,
                        'is_stacked': False,
                        'stack_count': 1,
                        'jitter': {'rotation': rot, 'dx': 0, 'dy': 0}
                    }
                    tier_cards[r_idx].append(inst)
        if len(tier_cards[r_idx]) > max_in_tier:
            max_in_tier = len(tier_cards[r_idx])
            
    cols = max(10, max_in_tier)
    grid = [[None for _ in range(cols)] for _ in range(grid_rows)]
    for r in range(3):
        for c, inst in enumerate(tier_cards[r]):
            grid[r][c] = inst
            all_cards.append(inst)
            
    packed_mb = {
        'grid': grid,
        'rows': grid_rows,
        'cols': cols,
        'cards': all_cards,
        'total_cards': len(all_cards),
        'layout': 'horizontal_cascade'
    }
    packed_sb = pack_sideboard(sb_groups, max_per_row=8, base_angle=-38.0)
    return packed_mb, packed_sb

def pack_deck(main_groups, sb_groups, layout='classic', stack_basics=False, stack_all_multiples=False):
    if layout == 'type_columns':
        mb, sb = pack_type_columns(main_groups, sb_groups, stack_basics=stack_basics, stack_all_multiples=stack_all_multiples)
        return mb, sb
    elif layout == 'sideboard_right':
        mb, sb = pack_sideboard_right(main_groups, sb_groups, stack_basics=stack_basics, stack_all_multiples=stack_all_multiples)
        return mb, sb
    elif layout == 'horizontal_cascade':
        mb, sb = pack_horizontal_cascade(main_groups, sb_groups, stack_basics=stack_basics, stack_all_multiples=stack_all_multiples)
        return mb, sb
    elif layout == 'chaos_table':
        mb = pack_mainboard(main_groups, target_rows=6, target_cols=10, stack_basics=stack_basics, stack_all_multiples=stack_all_multiples, is_chaos=True)
        mb['layout'] = 'chaos_table'
        sb = pack_sideboard(sb_groups, max_per_row=8, base_angle=-38.0, is_chaos=True)
        return mb, sb
    else: # 'classic'
        mb = pack_mainboard(main_groups, target_rows=6, target_cols=10, stack_basics=stack_basics, stack_all_multiples=stack_all_multiples, is_chaos=False)
        mb['layout'] = 'classic'
        sb = pack_sideboard(sb_groups, max_per_row=8, base_angle=-38.0, is_chaos=False)
        return mb, sb
