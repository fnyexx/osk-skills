import re
import sys
import fitz
from extract_geometry import get_systems_and_measures

def map_tokens(page_idx, page, systems):
    tokens = []
    blocks = page.get_text("dict")["blocks"]

    for block in blocks:
        if "lines" in block:
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if not text:
                        continue

                    x0, y0, x1, y1 = span["bbox"]
                    x_mid = (x0 + x1) / 2
                    y_mid = (y0 + y1) / 2

                    # Find containing system
                    containing_sys = None
                    sys_num = -1
                    for sys_idx, sys_item in enumerate(systems):
                        if sys_item['y0'] - 10 <= y_mid <= sys_item['y1'] + 15:
                            containing_sys = sys_item
                            sys_num = sys_idx + 1
                            break

                    if not containing_sys:
                        continue

                    # Exclude text far below the TAB staff (lyrics / jianpu)
                    if y_mid > containing_sys['y1'] + 12:
                        continue

                    # Find containing measure index inside the system
                    bar_xs = containing_sys['barlines_x']
                    measure_idx = -1
                    for k in range(len(bar_xs) - 1):
                        if bar_xs[k] - 2 <= x_mid <= bar_xs[k+1] + 2:
                            measure_idx = k
                            break

                    if measure_idx == -1:
                        continue

                    # Distance to each of the 6 strings (1 = highest string, 6 = lowest string)
                    dists = [abs(y_mid - (containing_sys['y0'] + i * containing_sys['spacing'])) for i in range(6)]
                    min_dist = min(dists)
                    if min_dist > 2.0:
                        # Too far vertically from any string line (e.g. measure numbers, chord text)
                        continue
                    string_num = dists.index(min_dist) + 1

                    # 1. Match fret number (regular, harmonic <12>, ghost note (3))
                    m_fret = re.match(r'^[<(]?(\d+)[>)]?$', text)
                    if m_fret and span["size"] >= 4.5:
                        fret_val = int(m_fret.group(1))
                        tokens.append({
                            'type': 'note',
                            'val': fret_val,
                            'string': string_num,
                            'x': x_mid,
                            'y': y_mid,
                            'sys_num': sys_num,
                            'measure_idx': measure_idx,
                            'is_harmonic': ('<' in text and '>' in text),
                            'is_ghost': ('(' in text and ')' in text)
                        })

                    # 2. Match dead note text X / x
                    elif text.upper() == 'X' and span["size"] >= 4.5:
                        tokens.append({
                            'type': 'note',
                            'val': 'X',
                            'string': string_num,
                            'x': x_mid,
                            'y': y_mid,
                            'sys_num': sys_num,
                            'measure_idx': measure_idx,
                            'is_dead': True
                        })

                    # 3. Check for rest symbols
                    elif any(ord(c) in [0xE4E5, 0xE4E6] for c in text):
                        rest_type = 'quarter' if any(ord(c) == 0xE4E5 for c in text) else 'eighth'
                        tokens.append({
                            'type': 'rest',
                            'val': rest_type,
                            'x': x_mid,
                            'y': y_mid,
                            'sys_num': sys_num,
                            'measure_idx': measure_idx
                        })

    return tokens

if __name__ == "__main__":
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        print("Usage: python map_notes_rests.py <pdf_path>")
        sys.exit(1)

    doc = fitz.open(pdf_path)
    for i in range(len(doc)):
        systems = get_systems_and_measures(doc[i])
        tokens = map_tokens(i, doc[i], systems)
        print(f"Page {i+1} mapped {len(tokens)} tokens.")
        for t in tokens[:5]:
            print(" ", t)
