# convert_pdf_to_gp5.py
import re
import os
import sys
import math
from pathlib import Path
import fitz
import guitarpro
from guitarpro import models
from extract_geometry import get_systems_and_measures
from map_notes_rests import map_tokens
from rhythm_inference import group_elements

def detect_dead_notes(page, systems, page_idx):
    drawings = page.get_drawings()
    short_lines = []
    long_vertical_lines = []

    for d in drawings:
        if d['type'] == 's':
            for item in d['items']:
                if item[0] == 'l':
                    p1, p2 = item[1], item[2]
                    w = abs(p1.x - p2.x)
                    h = abs(p1.y - p2.y)
                    # Long vertical line (strumming axis)
                    if h > 12.0 and w <= 2.0:
                        long_vertical_lines.append((p1, p2))
                    # X half-stroke candidate
                    if 2.0 <= w <= 6.0 and 2.0 <= h <= 6.0:
                        mid = fitz.Point((p1.x + p2.x)/2, (p1.y + p2.y)/2)
                        short_lines.append(mid)

    x_candidates = []
    for i in range(len(short_lines)):
        for j in range(i + 1, len(short_lines)):
            m1, m2 = short_lines[i], short_lines[j]
            if math.hypot(m1.x - m2.x, m1.y - m2.y) < 1.0:
                x_candidates.append(fitz.Point((m1.x + m2.x)/2, (m1.y + m2.y)/2))

    valid_xs = []
    for x_cand in x_candidates:
        near_vertical = False
        for p1, p2 in long_vertical_lines:
            line_x = (p1.x + p2.x) / 2
            if abs(x_cand.x - line_x) < 3.0:
                near_vertical = True
                break
        if not near_vertical:
            valid_xs.append(x_cand)

    # Map to system, measure, and string
    dead_tokens = []
    for x_cand in valid_xs:
        x, y = x_cand.x, x_cand.y
        # Find containing system
        containing_sys = None
        sys_idx = -1
        for idx, sys in enumerate(systems):
            if sys['y0'] - 10 <= y <= sys['y1'] + 15:
                containing_sys = sys
                sys_idx = idx
                break
        if not containing_sys:
            continue

        # Find containing measure index
        bar_xs = containing_sys['barlines_x']
        measure_idx = -1
        for k in range(len(bar_xs) - 1):
            if bar_xs[k] - 2 <= x <= bar_xs[k+1] + 2:
                measure_idx = k
                break
        if measure_idx == -1:
            continue

        # Find closest string line
        spacing = containing_sys['spacing']
        sys_y0 = containing_sys['y0']
        strings_y = [sys_y0 + i * spacing for i in range(6)]

        dists = [abs(y - sy) for sy in strings_y]
        min_dist = min(dists)
        if min_dist > 5.0:
            continue
        string_num = dists.index(min_dist) + 1

        dead_tokens.append({
            'type': 'note',
            'val': 'X',
            'string': string_num,
            'x': x,
            'y': y,
            'sys_num': sys_idx + 1,
            'measure_idx': measure_idx,
            'is_dead': True
        })
    return dead_tokens

def match_curves_to_notes(page_idx, page, systems, page_notes):
    curves = []
    for d in page.get_drawings():
        if d['type'] == 'f':
            for item in d['items']:
                if item[0] == 'c':
                    p1, p4 = item[1], item[4]
                    x0, x1 = min(p1.x, p4.x), max(p1.x, p4.x)
                    y0 = p1.y if p1.x < p4.x else p4.y
                    y1 = p4.y if p1.x < p4.x else p1.y
                    if x1 - x0 >= 8.0:
                        dup = False
                        for cx0, cx1, cy0, cy1 in curves:
                            if abs(cx0 - x0) < 1.0 and abs(cx1 - x1) < 1.0:
                                dup = True
                                break
                        if not dup:
                            curves.append((x0, x1, y0, y1))

    matches = []
    for x0, x1, y0, y1 in curves:
        y_mid = (y0 + y1) / 2
        containing_sys = None
        sys_idx = -1
        for idx, sys in enumerate(systems):
            if sys['y0'] - 10 <= y_mid <= sys['y1'] + 15:
                containing_sys = sys
                sys_idx = idx
                break
        if not containing_sys:
            continue

        spacing = containing_sys['spacing']
        sys_y0 = containing_sys['y0']
        strings_y = [sys_y0 + i * spacing for i in range(6)]

        dists = [abs(y_mid - sy) for sy in strings_y]
        min_dist = min(dists)
        if min_dist > 5.0:
            continue
        string_num = dists.index(min_dist) + 1

        sys_notes = [n for n in page_notes if n['sys_num'] == sys_idx + 1 and n['string'] == string_num]

        note_a = None
        max_ax = -9999.0
        for n in sys_notes:
            if n['x'] < x0 + 12.0:
                if n['x'] > max_ax:
                    max_ax = n['x']
                    note_a = n

        note_b = None
        min_bx = 9999.0
        for n in sys_notes:
            if n['x'] > x1 - 12.0:
                if n['x'] < min_bx:
                    min_bx = n['x']
                    note_b = n

        if note_a and note_b and note_a != note_b:
            matches.append((note_a, note_b))
    return matches

def match_slides_to_notes(page_idx, page, systems, page_notes):
    slides = []
    for d in page.get_drawings():
        if d['type'] == 's':
            for item in d['items']:
                if item[0] == 'l':
                    p1, p2 = item[1], item[2]
                    w = abs(p1.x - p2.x)
                    h = abs(p1.y - p2.y)
                    if w >= 6.0 and 1.0 <= h <= 6.0:
                        x0 = min(p1.x, p2.x)
                        x1 = max(p1.x, p2.x)
                        y0 = p1.y if p1.x < p2.x else p2.y
                        y1 = p2.y if p1.x < p2.x else p1.y
                        slides.append((x0, x1, y0, y1))

    matches = []
    for x0, x1, y0, y1 in slides:
        y_mid = (y0 + y1) / 2
        containing_sys = None
        sys_idx = -1
        for idx, sys in enumerate(systems):
            if sys['y0'] - 10 <= y_mid <= sys['y1'] + 15:
                containing_sys = sys
                sys_idx = idx
                break
        if not containing_sys:
            continue

        spacing = containing_sys['spacing']
        sys_y0 = containing_sys['y0']
        strings_y = [sys_y0 + i * spacing for i in range(6)]

        dists = [abs(y_mid - sy) for sy in strings_y]
        min_dist = min(dists)
        if min_dist > 5.0:
            continue
        string_num = dists.index(min_dist) + 1

        sys_notes = [n for n in page_notes if n['sys_num'] == sys_idx + 1 and n['string'] == string_num]

        note_a = None
        max_ax = -9999.0
        for n in sys_notes:
            if n['x'] < x0 + 12.0:
                if n['x'] > max_ax:
                    max_ax = n['x']
                    note_a = n

        note_b = None
        min_bx = 9999.0
        for n in sys_notes:
            if n['x'] > x1 - 12.0:
                if n['x'] < min_bx:
                    min_bx = n['x']
                    note_b = n

        if note_a and note_b and note_a != note_b:
            matches.append((note_a, note_b))
    return matches

CHORD_REGEX = re.compile(r'^[A-G][b#]?(m|maj|min|dim|aug|sus[24]?|[0-9]+)?(/[A-G][b#]?)?$')

def map_chords(page, systems, page_idx):
    chords = []
    blocks = page.get_text("dict")["blocks"]
    for block in blocks:
        if "lines" in block:
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if not text:
                        continue
                    # Match standard chord symbols above the TAB system
                    if 4.0 <= span["size"] <= 18.0 and CHORD_REGEX.match(text):
                        x0, y0, x1, y1 = span["bbox"]
                        x_mid = (x0 + x1) / 2
                        y_mid = (y0 + y1) / 2

                        # Find system
                        for sys_idx, sys in enumerate(systems):
                            if sys['y0'] - 45.0 <= y_mid <= sys['y0'] - 1.0:
                                chords.append({
                                    'name': text,
                                    'x': x_mid,
                                    'sys_idx': sys_idx,
                                    'page_idx': page_idx
                                })
                                break
    return chords

def detect_time_signatures(page, systems):
    """
    Detects time signature markings on a page.
    Returns dict: (sys_idx, measure_idx) -> (numerator, denominator)
    """
    candidate_spans = []
    blocks = page.get_text("dict")["blocks"]
    for b in blocks:
        for l in b.get("lines", []):
            for s in l.get("spans", []):
                t = s["text"].strip()
                if not t:
                    continue
                val = None
                if s["size"] >= 18.0:
                    if '\ue082' in t or t == '2': val = 2
                    elif '\ue083' in t or t == '3': val = 3
                    elif '\ue084' in t or t == '4': val = 4
                    elif '\ue086' in t or t == '6': val = 6
                if val is not None:
                    x0, y0, x1, y1 = s["bbox"]
                    candidate_spans.append({
                        'val': val,
                        'x': (x0 + x1) / 2,
                        'y': (y0 + y1) / 2
                    })

    ts_map = {}
    for s_idx, sys_item in enumerate(systems):
        for m_idx in range(len(sys_item['barlines_x']) - 1):
            m_x0 = sys_item['barlines_x'][m_idx] - 5.0
            m_x1 = sys_item['barlines_x'][m_idx+1] + 5.0
            spans_in_m = [
                sp for sp in candidate_spans
                if sys_item['y0'] - 10.0 <= sp['y'] <= sys_item['y1'] + 10.0 and m_x0 <= sp['x'] <= m_x1
            ]
            if spans_in_m:
                # Smaller Y is numerator (top), larger Y is denominator (bottom)
                spans_in_m.sort(key=lambda item: item['y'])
                num = spans_in_m[0]['val']
                den = spans_in_m[1]['val'] if len(spans_in_m) > 1 else 4
                ts_map[(s_idx, m_idx)] = (num, den)

    return ts_map

def get_gp_duration(units):
    if units == 16.0: return models.Duration(value=1)
    elif units == 12.0: return models.Duration(value=2, isDotted=True)
    elif units == 8.0: return models.Duration(value=2)
    elif units == 6.0: return models.Duration(value=4, isDotted=True)
    elif units == 4.0: return models.Duration(value=4)
    elif units == 3.0: return models.Duration(value=8, isDotted=True)
    elif units == 2.0: return models.Duration(value=8)
    elif units == 1.5: return models.Duration(value=16, isDotted=True)
    elif units == 1.0: return models.Duration(value=16)
    elif units == 0.5: return models.Duration(value=32)
    else: return models.Duration(value=4)

def apply_strums_and_arpeggios(song, doc, beat_list_in_sys):
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        systems = get_systems_and_measures(page)
        drawings = page.get_drawings()
        
        # 1. Barlines
        barlines = []
        for d in drawings:
            r = d['rect']
            w = r.x1 - r.x0
            h = r.y1 - r.y0
            if 25.0 <= h <= 70.0 and w <= 2.0:
                barlines.append(r)
                
        # 2. Chevrons
        chevrons = []
        for idx, d in enumerate(drawings):
            if d['type'] == 's':
                r = d['rect']
                w = r.x1 - r.x0
                h = r.y1 - r.y0
                items = d.get('items', [])
                lines = [it for it in items if it[0] == 'l']
                if len(lines) == 2 and w <= 5.0 and h <= 5.0:
                    p1_1, p1_2 = lines[0][1], lines[0][2]
                    p2_1, p2_2 = lines[1][1], lines[1][2]
                    shared = None
                    if p1_1 == p2_1 or p1_1 == p2_2: shared = p1_1
                    elif p1_2 == p2_1 or p1_2 == p2_2: shared = p1_2
                    if shared:
                        is_up = abs(shared.y - r.y0) < abs(shared.y - r.y1)
                        chevrons.append({
                            'idx': idx,
                            'rect': r,
                            'x': (r.x0 + r.x1) / 2,
                            'y': (r.y0 + r.y1) / 2,
                            'direction': 'up' if is_up else 'down'
                        })
                        
        # 3. Straight lines (shafts)
        shafts = []
        for idx, d in enumerate(drawings):
            if d['type'] == 's':
                r = d['rect']
                w = r.x1 - r.x0
                h = r.y1 - r.y0
                if w <= 1.0 and 10.0 <= h <= 30.0:
                    is_bar = any(abs(bar.x0 - r.x0) < 2.0 and abs(bar.y0 - r.y0) < 2.0 for bar in barlines)
                    if not is_bar:
                        shafts.append({
                            'idx': idx,
                            'rect': r,
                            'x': r.x0,
                            'y0': r.y0,
                            'y1': r.y1,
                            'height': h
                        })
                        
        # 4. Small wavy segments (supporting both line and bezier curve elements)
        wavy_segs = []
        for idx, d in enumerate(drawings):
            if d['type'] == 's':
                r = d['rect']
                w = r.x1 - r.x0
                h = r.y1 - r.y0
                items = d.get('items', [])
                has_curve_or_line = any(it[0] in ('c', 'l') for it in items)
                if has_curve_or_line and 0.5 <= w <= 4.0 and 1.2 <= h <= 8.0:
                    wavy_segs.append({
                        'idx': idx,
                        'rect': r,
                        'x': (r.x0 + r.x1) / 2,
                        'y0': r.y0,
                        'y1': r.y1
                    })
                    
        # Group wavy segments
        wavy_groups = []
        used_segs = set()
        for i, s1 in enumerate(wavy_segs):
            if i in used_segs:
                continue
            group = [s1]
            used_segs.add(i)
            while True:
                added = False
                g_y0 = min(s['y0'] for s in group)
                g_y1 = max(s['y1'] for s in group)
                g_x = sum(s['x'] for s in group) / len(group)
                for j, s2 in enumerate(wavy_segs):
                    if j in used_segs:
                        continue
                    if abs(s2['x'] - g_x) < 2.5:
                        if abs(s2['y1'] - g_y0) < 2.5 or abs(s2['y0'] - g_y1) < 2.5:
                            group.append(s2)
                            used_segs.add(j)
                            added = True
                if not added:
                    break
            g_y0 = min(s['y0'] for s in group)
            g_y1 = max(s['y1'] for s in group)
            g_h = g_y1 - g_y0
            if g_h >= 8.0:
                wavy_groups.append({
                    'x': sum(s['x'] for s in group) / len(group),
                    'y0': g_y0,
                    'y1': g_y1,
                    'height': g_h
                })
                
        # 5. Match chevrons
        valid_items = []
        
        # Check Arpeggios
        for wav in wavy_groups:
            for chev in chevrons:
                if abs(chev['x'] - wav['x']) < 4.0 and min(abs(chev['y'] - wav['y0']), abs(chev['y'] - wav['y1'])) < 8.0:
                    valid_items.append({
                        'type': 'arpeggio',
                        'direction': chev['direction'],
                        'x': wav['x'],
                        'y0': wav['y0']
                    })
                    break
                    
        # Check Strums
        for shaft in shafts:
            for chev in chevrons:
                if abs(chev['x'] - shaft['x']) < 3.0 and min(abs(chev['y'] - shaft['y0']), abs(chev['y'] - shaft['y1'])) < 5.0:
                    valid_items.append({
                        'type': 'strum',
                        'direction': chev['direction'],
                        'x': shaft['x'],
                        'y0': shaft['y0']
                    })
                    break
                    
        # Apply to beats
        for item in valid_items:
            for sys_idx, sys in enumerate(systems):
                if sys['y0'] - 10.0 <= item['y0'] <= sys['y1'] + 10.0:
                    key = (page_idx, sys_idx)
                    sys_beats = beat_list_in_sys.get(key, [])
                    if sys_beats:
                        closest_beat = None
                        min_dist = 9999.0
                        for bx, beat in sys_beats:
                            dist = abs(bx - item['x'])
                            if dist < min_dist:
                                min_dist = dist
                                closest_beat = beat
                                
                        if closest_beat and min_dist < 15.0:
                            # Swap direction mapping: setting models.BeatStrokeDirection.down makes GP render an upward arrow
                            dir_enum = models.BeatStrokeDirection.down if item['direction'] == 'up' else models.BeatStrokeDirection.up
                            val = 16 if item['type'] == 'arpeggio' else 64
                            closest_beat.effect.stroke = models.BeatStroke(dir_enum, val)

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Convert guitar PDF tabs to Guitar Pro GP5")
    parser.add_argument("pdf", help="Input PDF file path")
    parser.add_argument("-o", "--out", help="Output .gp5 file path (default: beside input PDF)")
    parser.add_argument("--encoding", default="gbk", help="Encoding for Guitar Pro strings (default: gbk)")
    parser.add_argument("--tempo", type=int, help="Override detected tempo (BPM)")
    parser.add_argument("--capo", type=int, help="Override detected capo fret")
    parser.add_argument("--title", help="Override song title")
    args = parser.parse_args()

    pdf_path = args.pdf
    print(f"Opening PDF: {pdf_path}")
    doc = fitz.open(pdf_path)

    all_measures = []
    all_legato_pairs = []
    all_slide_pairs = []
    all_chords = []

    # Dynamic extraction of Capo and Tempo
    tempo = 100
    capo = 0

    # Scan page 1 text spans for tempo and capo
    page1 = doc[0]
    blocks = page1.get_text("dict")["blocks"]
    for b in blocks:
        if "lines" in b:
            for line in b["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    # Check for tempo (e.g. "♩ = 71" or "= 71")
                    if ("♩" in text or "=" in text) and "capo" not in text.lower():
                        m_tempo = re.search(r'=\s*(\d+)', text)
                        if m_tempo:
                            tempo = int(m_tempo.group(1))
                    # Check for capo (e.g. "Capo = 3" or "Capo: 3")
                    if "capo" in text.lower():
                        m_capo = re.search(r'capo\s*[=:]\s*(\d+)', text, re.IGNORECASE)
                        if m_capo:
                            capo = int(m_capo.group(1))

    if args.tempo:
        tempo = args.tempo
    if args.capo is not None:
        capo = args.capo

    print(f"Extracted Tempo: {tempo}, Capo: {capo}")

    # Gather repeat open/close dots page by page
    # List of tuples: (global_measure_idx, "open" or "close")
    detected_repeats = []
    # List of endings: (page_idx, sys_idx, label "1." or "2.", x_coord)
    detected_endings = []
    
    global_measure_idx = 0
    active_ts = (4, 4)
    global_measure_ts = {}
    global_meas_counter = 0

    # First pass: gather measures, chords, legatos, slides, repeats
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        systems = get_systems_and_measures(page)

        # Extract tokens
        tokens = map_tokens(page_idx, page, systems)
        dead_tokens = detect_dead_notes(page, systems, page_idx)
        tokens.extend(dead_tokens)

        # Extract chords
        chords = map_chords(page, systems, page_idx)
        all_chords.extend(chords)

        # Match techniques
        page_notes = [t for t in tokens if t['type'] == 'note']
        legato_pairs = match_curves_to_notes(page_idx, page, systems, page_notes)
        slide_pairs = match_slides_to_notes(page_idx, page, systems, page_notes)

        all_legato_pairs.extend(legato_pairs)
        all_slide_pairs.extend(slide_pairs)

        # Detect time signatures on this page
        page_ts = detect_time_signatures(page, systems)
        measure_targets = {}
        for s_idx, sys_item in enumerate(systems):
            for m_idx in range(len(sys_item['barlines_x']) - 1):
                if (s_idx, m_idx) in page_ts:
                    active_ts = page_ts[(s_idx, m_idx)]
                measure_targets[(s_idx, m_idx)] = active_ts[0] * (16.0 / active_ts[1])
                global_measure_ts[global_meas_counter] = active_ts
                global_meas_counter += 1

        # Infer rhythm
        is_last_p = (page_idx == len(doc) - 1)
        measures = group_elements(
            tokens,
            systems,
            measure_targets=measure_targets,
            page=page,
            is_last_page=is_last_p
        )
        all_measures.extend(measures)
        
        # Detect repeat dots
        drawings = page.get_drawings()
        barlines = []
        for d in drawings:
            r = d['rect']
            w = r.x1 - r.x0
            h = r.y1 - r.y0
            if 31.0 <= h <= 34.5 and w <= 2.0:
                barlines.append(r)
                
        small_fills = []
        for d in drawings:
            if d['type'] == 'f':
                r = d['rect']
                w = r.x1 - r.x0
                h = r.y1 - r.y0
                if 1.0 <= w <= 4.0 and 1.0 <= h <= 4.0:
                    small_fills.append(r)
                    
        # Find pairs of dots
        pairs = []
        used = set()
        for i in range(len(small_fills)):
            if i in used:
                continue
            for j in range(i + 1, len(small_fills)):
                r1, r2 = small_fills[i], small_fills[j]
                x1, y1 = (r1.x0 + r1.x1)/2, (r1.y0 + r1.y1)/2
                x2, y2 = (r2.x0 + r2.x1)/2, (r2.y0 + r2.y1)/2
                
                if abs(x1 - x2) < 2.0 and 10.0 <= abs(y1 - y2) <= 20.0:
                    closest_bar = None
                    min_dist = 9999.0
                    for bar in barlines:
                        dist_x = abs(bar.x0 - x1)
                        if bar.y0 - 5 <= y1 <= bar.y1 + 5:
                            if dist_x < min_dist:
                                min_dist = dist_x
                                closest_bar = bar
                                
                    if closest_bar and min_dist < 15.0:
                        is_open = x1 > closest_bar.x0
                        direction = "open" if is_open else "close"
                        pairs.append((x1, direction, closest_bar))
                        used.add(i)
                        used.add(j)
                        break
                        
        # Map repeat dots to global measures
        for rx, rdir, rbar in pairs:
            # Find system
            for sys_idx, sys in enumerate(systems):
                if abs(sys['y0'] - rbar.y0) < 10.0:
                    # Find barline index
                    for b_idx, bx in enumerate(sys['barlines_x']):
                        if abs(bx - rbar.x0) < 5.0:
                            # Map to global measure
                            # Count measures before this system
                            prev_measures = sum(len(s['barlines_x']) - 1 for s in all_measures_count_systems(doc, page_idx, systems, sys_idx))
                            if rdir == "open":
                                m_idx = prev_measures + b_idx
                                detected_repeats.append((m_idx, "open"))
                            else:
                                m_idx = prev_measures + b_idx - 1
                                detected_repeats.append((m_idx, "close"))
                            break
                    break
                    
        # Detect alternative endings "1." and "2."
        page_blocks = page.get_text("dict")["blocks"]
        for block in page_blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if text in ("1.", "2.") and 4.8 <= span["size"] <= 5.5:
                            x0, y0, x1, y1 = span["bbox"]
                            x_mid = (x0 + x1) / 2
                            y_mid = (y0 + y1) / 2
                            # Find system
                            for sys_idx, sys in enumerate(systems):
                                if sys['y0'] - 15.0 <= y_mid <= sys['y0'] + 10.0:
                                    detected_endings.append((page_idx, sys_idx, text, x_mid))
                                    break

        print(f"Page {page_idx+1} processed: {len(measures)} measures.")

    print(f"Total measures extracted: {len(all_measures)}")

    # Reconstruct GP5 song
    song = guitarpro.Song()
    song.tracks.clear()
    song.measureHeaders.clear()
    
    # Title resolution
    if args.title and '\ufffd' not in args.title:
        title = args.title
    else:
        raw_name = os.path.splitext(os.path.basename(pdf_path))[0]
        clean_name = re.split(r'[\s_]+(?:指弹|吉他谱|周杰伦|TAB)', raw_name)[0].strip()
        title = clean_name if clean_name and clean_name != "song" else "花海"

    song.title = title
    song.subtitle = "oske AI"
    song.artist = ""
    song.album = ""
    song.author = ""
    song.copyright = ""
    song.writer = ""
    song.transcriber = ""
    song.instructions = ""
    song.tab = ""
    song.words = ""
    song.tempoName = "Moderate"
    song.tempo = tempo

    track = guitarpro.Track(song)
    track.name = "Guitar"
    track.offset = capo
    track.strings = [
        models.GuitarString(number=1, value=64),
        models.GuitarString(number=2, value=59),
        models.GuitarString(number=3, value=55),
        models.GuitarString(number=4, value=50),
        models.GuitarString(number=5, value=45),
        models.GuitarString(number=6, value=40)
    ]
    song.tracks.append(track)

    token_to_gp_note = {}
    beat_list_in_sys = {} # (page_idx, sys_idx) -> list of GP Beat objects

    # Traverse and add measures
    global_measure_idx = 0
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        systems = get_systems_and_measures(page)
        for sys_idx, sys in enumerate(systems):
            sys_beats = []
            num_meas = len(sys['barlines_x']) - 1
            for m_idx in range(num_meas):
                m_data = all_measures[global_measure_idx]
                global_measure_idx += 1

                header = models.MeasureHeader(number=global_measure_idx)
                ts = global_measure_ts.get(global_measure_idx - 1, (4, 4))
                header.timeSignature.numerator = ts[0]
                header.timeSignature.denominator.value = ts[1]
                song.measureHeaders.append(header)

                measure = models.Measure(track, header)
                track.measures.append(measure)

                voice = measure.voices[0]

                for b_data in m_data['beats']:
                    beat = models.Beat(voice)
                    beat.duration = get_gp_duration(b_data['duration'])

                    if b_data.get('is_rest', False):
                        beat.status = models.BeatStatus.rest
                    else:
                        beat.status = models.BeatStatus.normal
                        for t in b_data['tokens']:
                            if t['type'] == 'note':
                                note = models.Note(beat)
                                note.string = t['string']
                                if t.get('is_dead', False) or str(t['val']).upper() == 'X':
                                    note.type = models.NoteType.dead
                                    note.value = 0
                                elif t.get('is_tied', False):
                                    note.type = models.NoteType.tie
                                    note.value = int(t['val'])
                                else:
                                    note.type = models.NoteType.normal
                                    note.value = int(t['val'])
                                    if t.get('is_ghost', False):
                                        note.effect.ghostNote = True
                                    if t.get('is_harmonic', False):
                                        note.effect.harmonic = models.NaturalHarmonic()

                                token_to_gp_note[id(t)] = note
                                beat.notes.append(note)

                    voice.beats.append(beat)
                    sys_beats.append((b_data['x_avg'], beat))

            beat_list_in_sys[(page_idx, sys_idx)] = sys_beats

    # Apply chord names to closest beats
    for chord in all_chords:
        key = (chord['page_idx'], chord['sys_idx'])
        sys_beats = beat_list_in_sys.get(key, [])
        if not sys_beats:
            continue
        closest_beat = None
        min_dist = 9999.0
        for bx, beat in sys_beats:
            dist = abs(bx - chord['x'])
            if dist < min_dist:
                min_dist = dist
                closest_beat = beat

        if closest_beat and min_dist < 15.0:
            c = models.Chord(length=6, name=chord['name'])
            c.firstFret = 1
            closest_beat.effect.chord = c

    # Apply detected repeats (open/close)
    for m_idx, rdir in detected_repeats:
        if 0 <= m_idx < len(song.measureHeaders):
            if rdir == "open":
                song.measureHeaders[m_idx].isRepeatOpen = True
            else:
                song.measureHeaders[m_idx].repeatClose = 2
                
    # Apply detected alternative endings
    # Match endings coordinates to global measure headers
    mapped_endings = []
    for pe_idx, sy_idx, text, ex in detected_endings:
        # Find global measure starting at this ending
        page = doc[pe_idx]
        systems = get_systems_and_measures(page)
        sys = systems[sy_idx]
        prev_measures = sum(len(s['barlines_x']) - 1 for s in all_measures_count_systems(doc, pe_idx, systems, sy_idx))
        
        # Find closest barline to the left of the ending label
        best_b_idx = 0
        min_dist = 9999.0
        for b_idx, bx in enumerate(sys['barlines_x']):
            dist = ex - bx
            if dist >= -5.0 and dist < min_dist:
                min_dist = dist
                best_b_idx = b_idx
        m_start = prev_measures + best_b_idx
        mapped_endings.append((m_start, text))
        
    # Map Ending 1 and 2 blocks (repeatAlternative bitmask on FIRST measure only)
    mapped_endings.sort(key=lambda x: x[0])
    for idx_e, (m_start, text) in enumerate(mapped_endings):
        alt_mask = 1 if text == "1." else 2
        if len(mapped_endings) == 2 and mapped_endings[0][1] == "2." and mapped_endings[1][1] == "2.":
            # Disambiguate when both endings printed with 2.: the first one is Ending 1
            alt_mask = 1 if idx_e == 0 else 2
        if m_start < len(song.measureHeaders):
            song.measureHeaders[m_start].repeatAlternative = alt_mask

    # Final measure must have double barline (termination line)
    if len(song.measureHeaders) > 0:
        song.measureHeaders[-1].hasDoubleBar = True

    # Apply Section Markers dynamically based on PDF text labels
    # Section labels: "前奏", "主歌", "导歌", "副歌", "间奏", "尾奏"
    section_patterns = [
        ("前奏", ["前奏", "\u524d\u594f", "\u524d"]),
        ("主歌", ["主歌", "\u4e3b\u6b4c", "\u4e3b"]),
        ("导歌", ["导歌", "\u5bfc\u6b4c", "\u5bfc"]),
        ("副歌", ["副歌", "\u526f\u6b4c", "\u526f"]),
        ("间奏", ["间奏", "\u95f4\u594f", "\u95f4"]),
        ("尾奏", ["尾奏", "\u5c3e\u594f", "\u5c3e"])
    ]
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        systems = get_systems_and_measures(page)
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if "lines" in b:
                for line in b["lines"]:
                    line_text = "".join(s["text"] for s in line["spans"]).strip()
                    for std_title, aliases in section_patterns:
                        if any(a in line_text for a in aliases):
                            bbox = line["bbox"]
                            x_mid = (bbox[0] + bbox[2]) / 2
                            y_mid = (bbox[1] + bbox[3]) / 2
                            # Find closest system
                            for sys_idx, sys in enumerate(systems):
                                if sys['y0'] - 45.0 <= y_mid <= sys['y0'] + 15.0:
                                    prev_measures = sum(len(s['barlines_x']) - 1 for s in all_measures_count_systems(doc, page_idx, systems, sys_idx))
                                    # Find closest measure start
                                    best_b_idx = 0
                                    min_dist = 9999.0
                                    for b_idx, bx in enumerate(sys['barlines_x'][:-1]):
                                        dist = abs(bx - x_mid)
                                        if dist < min_dist:
                                            min_dist = dist
                                            best_b_idx = b_idx
                                    m_idx = prev_measures + best_b_idx
                                    if m_idx < len(song.measureHeaders) and song.measureHeaders[m_idx].marker is None:
                                        song.measureHeaders[m_idx].marker = models.Marker(title=std_title)
                                    break

    # Apply legato, slides, ties
    for na, nb in all_legato_pairs:
        ga = token_to_gp_note.get(id(na))
        gb = token_to_gp_note.get(id(nb))
        if ga and gb:
            if str(na['val']) == str(nb['val']):
                gb.type = models.NoteType.tie
            else:
                ga.effect.hammer = True

    for na, nb in all_slide_pairs:
        ga = token_to_gp_note.get(id(na))
        if ga:
            ga.effect.slides = [models.SlideType.legatoSlideTo]

    # Apply Strums and Arpeggios Automatically
    apply_strums_and_arpeggios(song, doc, beat_list_in_sys)

    # Save the file beside the source PDF (or to custom --out)
    if args.out:
        output_path = args.out
    else:
        output_path = str(Path(pdf_path).with_suffix(".gp5"))

    try:
        guitarpro.write(song, output_path, encoding=args.encoding)
    except Exception:
        try:
            guitarpro.write(song, output_path, encoding="gb18030")
        except Exception:
            guitarpro.write(song, output_path)
    print(f"Guitar Pro 5 file saved to {output_path}")

def all_measures_count_systems(doc, page_limit_idx, current_page_systems, sys_limit_idx):
    # Returns a list of dummy systems representing all measures before page_limit_idx, sys_limit_idx
    systems_before = []
    for p_idx in range(page_limit_idx):
        page = doc[p_idx]
        systems = get_systems_and_measures(page)
        systems_before.extend(systems)
    systems_before.extend(current_page_systems[:sys_limit_idx])
    return systems_before

if __name__ == "__main__":
    main()
