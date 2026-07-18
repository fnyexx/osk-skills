# rhythm_inference.py
import fitz

def find_best_durations(beats, allowed_values):
    n = len(beats)
    if n == 0:
        return []

    memo = {}

    def dfs(index, current_sum):
        if index == n:
            if current_sum == 16:
                return 0.0, []
            else:
                return float('inf'), []

        state = (index, current_sum)
        if state in memo:
            return memo[state]

        best_cost = float('inf')
        best_path = []

        b = beats[index]
        target = b['target']
        is_protected = b['is_protected']

        sorted_values = sorted(allowed_values, key=lambda v: abs(v - target))

        for v in sorted_values:
            if current_sum + v > 16:
                continue

            if is_protected:
                cost = 0.0 if v == target else 100000.0 + (v - target)**2
            else:
                # Base cost is square deviation from target
                cost = (v - target)**2
                # If v is a dotted value (1.5, 3, 6, 12) and not protected, add a penalty
                if v in [1.5, 3.0, 6.0, 12.0]:
                    cost += 1.5 # Flat penalty to discourage dotted values

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

def group_elements(tokens, systems):
    page_measures = []

    # Process system by system
    for sys_idx, sys in enumerate(systems):
        sys_num = sys_idx + 1
        num_measures = len(sys['barlines_x']) - 1

        for m_idx in range(num_measures):
            # Boundaries of this measure
            x_start = sys['barlines_x'][m_idx]
            x_end = sys['barlines_x'][m_idx+1]

            # Filter tokens in this measure
            measure_tokens = [t for t in tokens if t['sys_num'] == sys_num and t['measure_idx'] == m_idx]

            # If measure is empty, represent as a single whole rest (duration 16)
            if not measure_tokens:
                beat = {
                    'x_avg': (x_start + x_end) / 2,
                    'duration': 16.0,
                    'is_rest': True,
                    'tokens': [{
                        'type': 'rest',
                        'val': 'whole',
                        'sys_num': sys_num,
                        'measure_idx': m_idx,
                        'x': (x_start + x_end) / 2,
                        'y': (sys['y0'] + sys['y1']) / 2
                    }]
                }
                page_measures.append({
                    'sys_num': sys_num,
                    'measure_idx': m_idx,
                    'beats': [beat]
                })
                continue

            # Group tokens by X coordinate (abs(x1 - x2) < 3.0)
            sorted_tokens = sorted(measure_tokens, key=lambda t: t['x'])
            beats = []
            for t in sorted_tokens:
                if not beats or abs(t['x'] - beats[-1]['x_avg']) >= 6.0:
                    beats.append({
                        'tokens': [t],
                        'x_avg': t['x'],
                        'sys_num': sys_num,
                        'measure_idx': m_idx,
                        'is_rest': False,
                        'is_protected': False,
                        'detected_duration': 4.0
                    })
                else:
                    beats[-1]['tokens'].append(t)
                    # Recompute average
                    beats[-1]['x_avg'] = sum(x['x'] for x in beats[-1]['tokens']) / len(beats[-1]['tokens'])

            # Detect properties for each beat
            for b in beats:
                # Check if it contains a rest token
                rest_tokens = [t for t in b['tokens'] if t['type'] == 'rest']
                if rest_tokens:
                    b['is_rest'] = True
                    b['is_protected'] = True
                    rest_val = rest_tokens[0]['val']
                    b['detected_duration'] = 4.0 if rest_val == 'quarter' else 2.0
                else:
                    b['is_rest'] = False

            n_beats = len(beats)
            spacings = []
            for i in range(n_beats):
                if i < n_beats - 1:
                    sp = beats[i+1]['x_avg'] - beats[i]['x_avg']
                else:
                    sp = x_end - beats[i]['x_avg']
                spacings.append(max(sp, 2.0))

            total_sp = sum(spacings)
            for i in range(n_beats):
                b = beats[i]
                b['spacing_duration'] = (spacings[i] / total_sp) * 16.0
                b['target'] = b['detected_duration'] if b['is_protected'] else b['spacing_duration']

            # Quantize and balance to exactly 16 units using allowed GP values
            allowed_gp_durations = [1, 2, 3, 4, 6, 8, 12, 16]
            final_durations = find_best_durations(beats, allowed_gp_durations)
            if not final_durations:
                # Fallback if balancing fails
                final_durations = []
                acc = 0
                for idx, b in enumerate(beats):
                    v = min(allowed_gp_durations, key=lambda x: abs(x - b['target']))
                    if idx == n_beats - 1:
                        final_durations.append(16 - acc)
                    else:
                        final_durations.append(v)
                        acc += v

            for i in range(n_beats):
                beats[i]['duration'] = final_durations[i]

            page_measures.append({
                'sys_num': sys_num,
                'measure_idx': m_idx,
                'beats': beats
            })

    return page_measures
