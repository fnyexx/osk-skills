# -*- coding: utf-8 -*-
# rhythm_inference.py
import fitz

def get_gp_duration_value(units):
    """Map 16th-note units to GP Duration (value, isDotted)"""
    if units == 16.0: return (1, False)
    elif units == 12.0: return (2, True)
    elif units == 8.0: return (2, False)
    elif units == 6.0: return (4, True)
    elif units == 4.0: return (4, False)
    elif units == 3.0: return (8, True)
    elif units == 2.0: return (8, False)
    elif units == 1.5: return (16, True)
    elif units == 1.0: return (16, False)
    elif units == 0.5: return (32, False)
    else: return (4, False)

def find_best_durations(beats, allowed_values=[0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 16.0], target_sum=16.0):
    """
    DFS optimizer to balance measure durations to target_sum (default 16 units for 4/4).
    Enforces strong penalties against arbitrary dotted/32nd values unless protected.
    """
    n = len(beats)
    if n == 0:
        return []

    memo = {}

    def dfs(index, current_sum):
        if index == n:
            return (0.0, []) if abs(current_sum - target_sum) < 1e-4 else (float('inf'), [])

        state = (index, round(current_sum, 3))
        if state in memo:
            return memo[state]

        best_cost = float('inf')
        best_path = []

        b = beats[index]
        target = b.get('target', 2.0)
        is_protected = b.get('is_protected', False)

        sorted_values = sorted(allowed_values, key=lambda v: abs(v - target))

        for v in sorted_values:
            if current_sum + v > target_sum + 1e-4:
                continue

            if is_protected:
                cost = 0.0 if abs(v - target) < 1e-4 else (10000.0 + (v - target)**2)
            else:
                cost = (v - target)**2
                # Penalize non-standard dotted / 32nd values unless backed by target
                if v in [0.5, 1.5, 3.0, 6.0, 12.0] and abs(v - target) > 0.1:
                    cost += 5.0

            sub_cost, sub_path = dfs(index + 1, current_sum + v)
            if sub_cost != float('inf'):
                total_cost = cost + sub_cost
                if total_cost < best_cost:
                    best_cost = total_cost
                    best_path = [v] + sub_path

        memo[state] = (best_cost, best_path)
        return best_cost, best_path

    cost, path = dfs(0, 0)
    return path

def infer_measure_rhythm(beats, m_data=None, target_sum=16.0):
    """
    Derive natural durations for beats in a 4/4 measure using Beat-Cell architecture
    and beam connectivity evidence.
    """
    n_beats = len(beats)
    if n_beats == 0:
        return []

    staff_beams = m_data.get('staff_beams', []) if m_data else []
    below_beams = m_data.get('below_beams', []) if m_data else []
    staff_dots = m_data.get('staff_dots', []) if m_data else []

    # Calculate beam connectivity between adjacent beats
    beams_between = []
    for i in range(n_beats - 1):
        x1 = beats[i]['x_avg']
        x2 = beats[i+1]['x_avg']
        s_count = sum(1 for b in staff_beams if b.x0 <= x1 + 4.0 and b.x1 >= x2 - 4.0)
        b_count = sum(1 for b in below_beams if b.x0 <= x1 + 4.0 and b.x1 >= x2 - 4.0)
        beams_between.append(max(s_count, b_count))

    # Check dots
    for b in beats:
        bx = b['x_avg']
        b['has_dot'] = any(abs((d.x0 + d.x1)/2 - bx) <= 7.0 for d in staff_dots)

    # Standard Fingerstyle Beat Cell Mapping for 4/4 and 2/4
    if n_beats == 1:
        return [target_sum]
    elif target_sum == 16.0:
        if n_beats == 16:
            return [1.0] * 16
        elif n_beats == 8:
            return [2.0] * 8
        elif n_beats == 4:
            return [4.0] * 4
        elif n_beats == 2:
            return [8.0] * 2
    elif target_sum == 8.0:
        if n_beats == 8:
            return [1.0] * 8
        elif n_beats == 4:
            return [2.0] * 4
        elif n_beats == 2:
            return [4.0] * 2

    has_any_beam = any(b > 0 for b in beams_between)

    # Assign initial target from beam levels and relative spacing
    targets = [2.0] * n_beats
    for i in range(n_beats):
        left_b = beams_between[i-1] if i > 0 else 0
        right_b = beams_between[i] if i < n_beats - 1 else 0
        has_dot = beats[i].get('has_dot', False)

        if has_any_beam:
            if left_b >= 2 or right_b >= 2:
                targets[i] = 1.0  # 16th note
            elif left_b == 1 or right_b == 1:
                targets[i] = 3.0 if has_dot else 2.0  # 8th / dotted 8th
            else:
                if has_dot:
                    targets[i] = 6.0  # dotted quarter
                elif n_beats <= 4:
                    targets[i] = 4.0  # quarter note
                else:
                    targets[i] = 2.0
        else:
            # Spacing-based initial estimation if no beams detected
            if 'spacing_target' in beats[i]:
                targets[i] = beats[i]['spacing_target']
            elif has_dot:
                targets[i] = 3.0 if n_beats > 6 else 6.0
            else:
                targets[i] = target_sum / n_beats

        beats[i]['target'] = targets[i]
        beats[i]['is_protected'] = (targets[i] in [1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 16.0] and (left_b > 0 or right_b > 0 or has_dot))

    # Balance measure with DFS
    final_durations = find_best_durations(beats, allowed_values=[0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 16.0], target_sum=target_sum)
    if not final_durations or len(final_durations) != n_beats:
        final_durations = [targets[i] for i in range(n_beats)]
        scale = target_sum / max(sum(final_durations), 1e-4)
        final_durations = [d * scale for d in final_durations]

    return final_durations

def extract_page_rests(page):
    """
    Extracts standard music rest symbols from page text spans.
    """
    rests = []
    if page is None:
        return rests
    blocks = page.get_text("dict")["blocks"]
    for b in blocks:
        for l in b.get("lines", []):
            for s in l.get("spans", []):
                for c in s["text"]:
                    cp = ord(c)
                    if cp == 0xE4E4:
                        rests.append({'x': (s['bbox'][0]+s['bbox'][2])/2, 'y': (s['bbox'][1]+s['bbox'][3])/2, 'dur': 8.0})
                    elif cp == 0xE4E5:
                        rests.append({'x': (s['bbox'][0]+s['bbox'][2])/2, 'y': (s['bbox'][1]+s['bbox'][3])/2, 'dur': 4.0})
                    elif cp == 0xE4E6:
                        rests.append({'x': (s['bbox'][0]+s['bbox'][2])/2, 'y': (s['bbox'][1]+s['bbox'][3])/2, 'dur': 2.0})
                    elif cp == 0xE4E7:
                        rests.append({'x': (s['bbox'][0]+s['bbox'][2])/2, 'y': (s['bbox'][1]+s['bbox'][3])/2, 'dur': 1.0})
    return rests


def extract_beam_rhythm_for_measure(sys_item, bx0, bx1, m_tokens, all_tokens, sys_num, m_idx, drawings, rests_on_page, curves, target_sum, is_last_measure=False):
    """
    Extracts physical stems, beams, flags, dots, rests and curves to determine exact beat durations.
    Uses DFS micro-tuning solver to balance measure durations to target_sum.
    Returns list of beats balanced to target_sum, or None if no valid stems/rests.
    """
    if not drawings:
        return None

    y_top = sys_item['y1']
    y_bot = sys_item['y1'] + 25.0

    # 1. 真实符干提取：排除波浪线笔画，底端深入符干区，必须有音符或连音线匹配
    candidate_stems = []
    for d in drawings:
        r = d['rect']
        w, h = r.width, r.height
        if w <= 1.5 and h >= 3.5:
            if y_top + 2.0 <= r.y1 <= y_bot + 5.0 and r.y0 >= sys_item['y0'] - 2.0:
                if bx0 - 1.0 <= r.x0 <= bx1 + 1.0:
                    matched = [t for t in m_tokens if abs(t['x'] - r.x0) <= 3.5]
                    is_tie_stem = False
                    if not matched and curves:
                        is_tie_stem = any(abs(c['rect'].x1 - r.x0) < 4.0 and sys_item['y0'] - 5 <= c['rect'].y0 <= sys_item['y1'] + 5 for c in curves)
                    if matched or is_tie_stem:
                        candidate_stems.append({
                            'x': r.x0,
                            'y0': r.y0,
                            'y1': r.y1,
                            'h': h,
                            'matched': matched,
                            'is_tie': is_tie_stem
                        })

    candidate_stems.sort(key=lambda s: s['x'])
    m_stems = []
    for s in candidate_stems:
        if not m_stems or abs(s['x'] - m_stems[-1]['x']) > 2.0:
            m_stems.append(s)
        else:
            for m_tok in s['matched']:
                if m_tok not in m_stems[-1]['matched']:
                    m_stems[-1]['matched'].append(m_tok)

    # 2. 符杠 (Beams)
    beams = []
    for d in drawings:
        r = d['rect']
        if y_top <= r.y0 <= y_bot and r.width >= 1.5 and r.height <= 2.5:
            beams.append((r.x0, r.x1, r.y0, r.y1))

    # 3. 附点 (Dots)
    dots = []
    for d in drawings:
        r = d['rect']
        if y_top <= r.y0 <= y_bot and 0.8 <= r.width <= 2.5 and 0.8 <= r.height <= 2.5:
            dots.append(((r.x0 + r.x1)/2.0, (r.y0 + r.y1)/2.0))

    # 4. 符尾 (Flags: 单音符八分符尾)
    flags = []
    for d in drawings:
        if d['type'] == 's':
            r = d['rect']
            if y_top <= r.y0 <= y_bot and 2.0 <= r.width <= 5.0 and 4.0 <= r.height <= 12.0:
                if any(it[0] == 'c' for it in d.get('items', [])):
                    flags.append(r)

    # 5. 休止符
    m_rests = [
        r for r in (rests_on_page or [])
        if sys_item['y0'] - 10 <= r['y'] <= sys_item['y1'] + 10 and bx0 <= r['x'] <= bx1
    ]

    if not m_stems and not m_rests:
        return None

    measure_beats = []
    for r in m_rests:
        measure_beats.append({
            'x_avg': r['x'],
            'x_start': r['x'],
            'duration': r['dur'],
            'target': r['dur'],
            'is_protected': True,
            'is_rest': True,
            'tokens': []
        })

    meas_w = bx1 - bx0
    # 仅在 4/4 拍且开头没有拍号时，根据前空距离与时值缺口智能补齐首拍休止 (例如 M58)
    if target_sum == 16.0 and m_stems and not m_rests:
        first_sx = m_stems[0]['x']
        if (first_sx - bx0) > meas_w * 0.22 and len(m_stems) <= 6:
            rest_x = (bx0 + first_sx) / 2.0
            measure_beats.append({
                'x_avg': rest_x,
                'x_start': bx0,
                'duration': 4.0,
                'target': 4.0,
                'is_protected': False,
                'is_rest': True,
                'tokens': []
            })

    for s_idx_in_m, s in enumerate(m_stems):
        sx = s['x']
        overlapping_beams = [b for b in beams if b[0] - 1.5 <= sx <= b[1] + 1.5]
        beam_y = [round(b[2], 1) for b in overlapping_beams if abs(b[2] - y_top) > 2.0]
        distinct_y = len(set(beam_y))

        is_dotted = any(abs(dx - sx) < 10.0 and abs(dy - s['y1']) < 6.0 for dx, dy in dots)
        has_flag = any(abs(fl.x0 - sx) <= 2.0 and abs(fl.y1 - s['y1']) <= 3.0 for fl in flags)
        # 严格限制附点：只有单符干或单符杠(distinct_y <= 1)才可能有附点！十六分音符(>=2)不带附点
        is_dotted = (distinct_y <= 1) and any(0.5 <= (dx - sx) <= 10.0 and abs(dy - s['y1']) < 6.0 for dx, dy in dots)

        if distinct_y >= 3:
            base_dur = 0.5
            is_protected = True
        elif distinct_y == 2:
            base_dur = 1.0
            is_protected = True
        elif distinct_y == 1:
            base_dur = 2.0
            is_protected = True
        elif has_flag:
            base_dur = 2.0
            is_protected = True
        else:
            is_protected = False
            if s['h'] >= 10.0 and (s_idx_in_m == 0 or s_idx_in_m == len(m_stems) - 1):
                base_dur = 8.0
            else:
                base_dur = 4.0

        dur = base_dur * 1.5 if is_dotted else base_dur
        if is_dotted:
            is_protected = True

        matched_tokens = s['matched']
        if not matched_tokens and s['is_tie'] and curves:
            arriving_curves = [
                c for c in curves
                if abs(c['rect'].x1 - sx) < 4.0 and sys_item['y0'] - 5 <= c['rect'].y0 <= sys_item['y1'] + 5
            ]
            if arriving_curves:
                c = arriving_curves[0]
                src_tokens = [t for t in m_tokens if abs(t['x'] - c['rect'].x0) < 5.0 and abs(t['y'] - c['rect'].y0) < 5.0]
                if not src_tokens:
                    src_tokens = [t for t in all_tokens if t.get('sys_num') == sys_num and abs(t['x'] - c['rect'].x0) < 5.0]
                for st in src_tokens:
                    matched_tokens.append({
                        'type': 'note',
                        'string': st['string'],
                        'val': st['val'],
                        'is_tied': True,
                        'x': sx,
                        'y': st['y'],
                        'sys_num': sys_num,
                        'measure_idx': m_idx
                    })

        measure_beats.append({
            'x_avg': sx,
            'x_start': sx,
            'duration': dur,
            'target': dur,
            'is_protected': is_protected,
            'is_rest': False,
            'tokens': matched_tokens
        })

    measure_beats.sort(key=lambda b: b['x_avg'])

    if is_last_measure and len(measure_beats) >= 2:
        cur_sum = sum(b['target'] for b in measure_beats[:-1])
        if cur_sum < target_sum:
            measure_beats[-1]['target'] = target_sum - cur_sum
            measure_beats[-1]['duration'] = target_sum - cur_sum
            measure_beats[-1]['is_protected'] = True

    cur_sum = sum(b['duration'] for b in measure_beats)
    if abs(cur_sum - target_sum) < 1e-4:
        return measure_beats

    balanced_durs = find_best_durations(measure_beats, target_sum=target_sum)
    if balanced_durs and len(balanced_durs) == len(measure_beats):
        for b, d in zip(measure_beats, balanced_durs):
            b['duration'] = d
        return measure_beats

    return None


def group_elements(tokens, systems, target_sum=16.0, measure_targets=None, page=None, page_drawings=None, rests_on_page=None, curves=None, is_last_page=False):
    """
    Groups tokens by system and measure, clusters simultaneous notes into beats,
    and infers beat durations to sum to target_sum (default 16 units for 4/4).
    Uses physical beam lines & stems when available; falls back to spacing solver.
    """
    measures = []

    drawings = page_drawings if page_drawings is not None else (page.get_drawings() if page else None)
    if rests_on_page is None and page:
        rests_on_page = extract_page_rests(page)
    if curves is None and drawings:
        curves = [d for d in drawings if any(it[0] == 'c' for it in d.get('items', []))]

    num_systems = len(systems)
    for sys_idx, sys in enumerate(systems):
        bar_xs = sys['barlines_x']
        num_meas = len(bar_xs) - 1

        for m_idx in range(num_meas):
            bx0 = bar_xs[m_idx]
            bx1 = bar_xs[m_idx + 1]
            meas_w = max(bx1 - bx0, 10.0)
            m_target = measure_targets.get((sys_idx, m_idx), target_sum) if measure_targets else target_sum
            is_last_m = is_last_page and (sys_idx == num_systems - 1) and (m_idx == num_meas - 1)

            # Filter tokens belonging to this system and measure
            m_tokens = [
                t for t in tokens
                if t.get('sys_num') == sys_idx + 1 and t.get('measure_idx') == m_idx
            ]

            # Try beam-aware physical extraction first
            if drawings:
                beam_beats = extract_beam_rhythm_for_measure(
                    sys_item=sys,
                    bx0=bx0,
                    bx1=bx1,
                    m_tokens=m_tokens,
                    all_tokens=tokens,
                    sys_num=sys_idx + 1,
                    m_idx=m_idx,
                    drawings=drawings,
                    rests_on_page=rests_on_page,
                    curves=curves,
                    target_sum=m_target,
                    is_last_measure=is_last_m
                )
                if beam_beats:
                    measures.append({
                        'sys_idx': sys_idx,
                        'measure_idx': m_idx,
                        'beats': beam_beats
                    })
                    continue

            if not m_tokens:
                # Empty measure: add single full-measure rest beat
                measures.append({
                    'sys_idx': sys_idx,
                    'measure_idx': m_idx,
                    'beats': [{
                        'duration': m_target,
                        'is_rest': True,
                        'tokens': [],
                        'x_avg': (bx0 + bx1) / 2.0,
                        'x_start': bx0
                    }]
                })
                continue

            # Fallback: Sort tokens by x coordinate and cluster
            m_tokens.sort(key=lambda t: t['x'])

            beat_clusters = []
            for t in m_tokens:
                if not beat_clusters:
                    beat_clusters.append([t])
                else:
                    last_cluster = beat_clusters[-1]
                    cluster_x = sum(item['x'] for item in last_cluster) / len(last_cluster)
                    if abs(t['x'] - cluster_x) <= 3.0:
                        last_cluster.append(t)
                    else:
                        beat_clusters.append([t])

            beats = []
            n_beats = len(beat_clusters)
            for b_idx, cluster in enumerate(beat_clusters):
                x_avg = sum(item['x'] for item in cluster) / len(cluster)
                is_rest = all(item.get('type') == 'rest' for item in cluster)

                if b_idx < n_beats - 1:
                    next_cluster = beat_clusters[b_idx + 1]
                    next_x = sum(item['x'] for item in next_cluster) / len(next_cluster)
                    interval = max(next_x - x_avg, 2.0)
                else:
                    interval = max(bx1 - x_avg, 5.0)

                beats.append({
                    'tokens': cluster,
                    'x_avg': x_avg,
                    'x_start': min(item['x'] for item in cluster),
                    'is_rest': is_rest,
                    'interval': interval
                })

            total_interval = sum(b['interval'] for b in beats)
            for b in beats:
                b['spacing_target'] = (b['interval'] / max(total_interval, 1.0)) * m_target

            durations = infer_measure_rhythm(beats, m_data=None, target_sum=m_target)
            for b, d in zip(beats, durations):
                b['duration'] = d

            measures.append({
                'sys_idx': sys_idx,
                'measure_idx': m_idx,
                'beats': beats
            })

    return measures

