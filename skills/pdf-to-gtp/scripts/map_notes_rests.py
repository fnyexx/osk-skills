# map_notes_rests.py
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
                    for sys_idx, sys in enumerate(systems):
                        if sys['y0'] - 10 <= y_mid <= sys['y1'] + 15:
                            containing_sys = sys
                            sys_num = sys_idx + 1
                            break


                    if not containing_sys:
                        continue

                    # In our sheet layout, the TAB section occupies from containing_sys['y0'] to containing_sys['y1']
                    # Any token with y_mid more than 10pt below containing_sys['y1'] is excluded (lyrics / jianpu numbers)
                    if y_mid > containing_sys['y1'] + 10:
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

                    # Check if it is a fret digit
                    if text.isdigit() and span["size"] > 6.0:
                        # Map to string (1 to 6) based on closest line
                        dists = [abs(y_mid - (containing_sys['y0'] + i * containing_sys['spacing'])) for i in range(6)]
                        string_num = dists.index(min(dists)) + 1 # 1-indexed (1=highest, 6=lowest)
                        tokens.append({
                            'type': 'note',
                            'val': int(text),
                            'string': string_num,
                            'x': x_mid,
                            'y': y_mid,
                            'sys_num': sys_num,
                            'measure_idx': measure_idx
                        })

                    # Check if it is a rest symbol
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
    doc = fitz.open("青花瓷 指弹吉他谱_周杰伦.pdf")
    for i in range(1):
        systems = get_systems_and_measures(doc[i])
        tokens = map_tokens(i, doc[i], systems)
        print(f"Page {i+1} mapped {len(tokens)} tokens.")
        # Print first 5 tokens
        for t in tokens[:5]:
            print(t)
