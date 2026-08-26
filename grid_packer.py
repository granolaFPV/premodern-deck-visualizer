"""
Grid Packer for MTG Deck Visualizer.
Packs maindeck cards into a 6x10 grid such that all copies of each card
are grouped together (adjacent on at least one edge, in 2x2 squares, 1x4 lines,
1x3 lines, 1x2 lines, 1x1, or contiguous land blocks).
Also arranges the sideboard into angled rows (as seen in tournament deck check photos).
"""

import math
import random

def pack_mainboard(card_groups, target_rows=6, target_cols=10):
    """
    card_groups: list of dicts:
    [
        {
            'name': str,
            'quantity': int,
            'card_data': dict,
            'group_id': str
        },
        ...
    ]
    Returns:
    {
        'grid': 2D list of size [rows][cols], where each cell contains a card instance or None
        'rows': int,
        'cols': int,
        'cards': list of all card instances with grid coordinates
    }
    """
    total_cards = sum(g['quantity'] for g in card_groups)
    cols = target_cols
    rows = max(target_rows, math.ceil(total_cards / cols)) if total_cards > 0 else target_rows
    
    grid = [[None for _ in range(cols)] for _ in range(rows)]
    
    # Separate large land groups (e.g. basic lands qty >= 5) and normal cards
    land_groups = []
    spell_groups = []
    
    for g in card_groups:
        type_line = g.get('card_data', {}).get('type_line', '').lower()
        is_basic_or_large = ('basic land' in type_line) or (g['quantity'] >= 5) or ('land' in type_line and g['quantity'] >= 4)
        if is_basic_or_large:
            land_groups.append(g)
        else:
            spell_groups.append(g)
            
    # Sort spells: 4-ofs first, then 3-ofs, 2-ofs, 1-ofs
    spell_groups.sort(key=lambda g: (-g['quantity'], g['name']))
    land_groups.sort(key=lambda g: (-g['quantity'], g['name']))
    
    # 1. Place lands at the bottom rows (rows-1 down to 0, filling from bottom right/left)
    # Fill from bottom row upwards
    curr_r = rows - 1
    curr_c = cols - 1
    
    land_instances_placed = []
    for lg in land_groups:
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
                'is_land': True
            }
            grid[curr_r][curr_c] = instance
            land_instances_placed.append(instance)
            
            # Step backward
            curr_c -= 1
            if curr_c < 0:
                curr_c = cols - 1
                curr_r -= 1
                
    # 2. Pack spell groups into the remaining free cells
    # We want to place:
    # 4 -> prefer 2x2, then 1x4, then 4x1
    # 3 -> prefer 1x3, then 3x1
    # 2 -> prefer 1x2, then 2x1
    # 1 -> 1x1
    
    def get_shapes(qty):
        if qty == 4:
            return [(2, 2), (1, 4), (4, 1)]
        elif qty == 3:
            return [(1, 3), (3, 1)]
        elif qty == 2:
            return [(1, 2), (2, 1)]
        elif qty == 1:
            return [(1, 1)]
        return []

    def can_place(r, c, h, w):
        if r + h > rows or c + w > cols:
            return False
        for dr in range(h):
            for dc in range(w):
                if grid[r + dr][c + dc] is not None:
                    return False
        return True

    def place_shape(r, c, h, w, grp):
        placed_cells = []
        idx = 0
        for dr in range(h):
            for dc in range(w):
                instance = {
                    'instance_id': f"{grp['group_id']}_{idx}",
                    'name': grp['name'],
                    'group_id': grp['group_id'],
                    'card_data': dict(grp['card_data']),
                    'row': r + dr,
                    'col': c + dc,
                    'is_land': False
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

    # Backtracking solver
    solved = False
    
    def backtrack(idx, remaining):
        nonlocal solved
        if not remaining:
            solved = True
            return True
            
        empty = find_first_empty()
        if not empty:
            # Check if all remaining have 0 qty
            if all(g['quantity'] == 0 for g in remaining):
                solved = True
                return True
            return False
            
        r, c = empty
        for i, grp in enumerate(remaining):
            shapes = get_shapes(grp['quantity'])
            for h, w in shapes:
                if can_place(r, c, h, w):
                    cells = place_shape(r, c, h, w, grp)
                    if backtrack(idx + 1, remaining[:i] + remaining[i+1:]):
                        return True
                    unplace_cells(cells)
        return False

    backtrack(0, spell_groups)
    
    # Fallback: if backtracking didn't find an exact rectangular match for unusual combinations,
    # use greedy contiguous flood fill for any remaining items
    if not solved:
        for grp in spell_groups:
            # Check if already placed
            already_placed = any(
                grid[r][c] and grid[r][c].get('group_id') == grp['group_id']
                for r in range(rows) for c in range(cols)
            )
            if already_placed:
                continue
                
            # Place contiguously
            qty = grp['quantity']
            placed = 0
            # Find first empty cell
            empty = find_first_empty()
            if not empty:
                break
            sr, sc = empty
            
            # BFS or adjacent expansion
            frontier = [(sr, sc)]
            visited = set()
            
            while frontier and placed < qty:
                cr, cc = frontier.pop(0)
                if (cr, cc) in visited or cr < 0 or cr >= rows or cc < 0 or cc >= cols:
                    continue
                visited.add((cr, cc))
                if grid[cr][cc] is None:
                    instance = {
                        'instance_id': f"{grp['group_id']}_{placed}",
                        'name': grp['name'],
                        'group_id': grp['group_id'],
                        'card_data': dict(grp['card_data']),
                        'row': cr,
                        'col': cc,
                        'is_land': False
                    }
                    grid[cr][cc] = instance
                    placed += 1
                    # Add adjacent neighbors
                    for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] is None:
                            frontier.append((nr, nc))

    # Collect all instances with deterministic jitter
    all_instances = []
    rng = random.Random(42) # Deterministic default seed
    
    for r in range(rows):
        for c in range(cols):
            inst = grid[r][c]
            if inst is not None:
                # Add natural subtle physical table jitter (like in the photo)
                # Angle: -0.6° to +0.6°
                rot = round((rng.random() - 0.5) * 1.2, 2)
                # Translation: -1.5px to +1.5px
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


def pack_sideboard(sb_groups, max_per_row=8, base_angle=-38.0):
    """
    Arranges sideboard cards into angled fanned rows (as in the uploaded photo).
    sb_groups: list of dicts with 'name', 'quantity', 'card_data', 'group_id'
    Returns list of sideboard card instances with row, col, angle, and layout coordinates.
    """
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
        
    # If 15 cards: Row 0 has 8 cards, Row 1 has 7 cards (exactly matching the user photo!)
    # Otherwise split evenly
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
            
            # Subtle variation in angle around base_angle
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
