# extract_geometry.py
import fitz

def get_systems_and_measures(page):
    drawings = page.get_drawings()
    candidates = []
    for d in drawings:
        r = d['rect']
        w = r.x1 - r.x0
        h = r.y1 - r.y0
        # Candidates for barlines or system boundaries (height between 25.0 and 80.0, width <= 2.0)
        if w <= 2.0 and 25.0 <= h <= 80.0:
            candidates.append(r)

    # Left barlines defining systems are candidates starting at x near 14.5 and height >= 30.0
    left_barlines = [r for r in candidates if 14.0 <= r.x0 <= 16.0 and (r.y1 - r.y0) >= 30.0]

    # Remove duplicates
    unique_left_barlines = []
    for r in left_barlines:
        duplicate = False
        for ur in unique_left_barlines:
            if abs(r.y0 - ur.y0) < 5.0 and abs(r.x0 - ur.x0) < 5.0:
                duplicate = True
                break
        if not duplicate:
            unique_left_barlines.append(r)
    unique_left_barlines.sort(key=lambda r: r.y0)

    # Gather potential horizontal lines to detect TAB system lines
    h_lines = []
    for d in drawings:
        r = d['rect']
        w = r.x1 - r.x0
        h = r.y1 - r.y0
        if h <= 2.0 and w > 100.0:
            h_lines.append(r)

    systems = []
    for left_r in unique_left_barlines:
        y_start = left_r.y0
        y_end = left_r.y1
        h_cand = y_end - y_start

        # Find all barlines belonging to this system (starts near y_start, height >= 27)
        sys_barlines = [r for r in candidates if abs(r.y0 - y_start) < 5.0 and (r.y1 - r.y0) >= 27.0]
        # Sort by X coordinate
        sys_barlines.sort(key=lambda r: r.x0)

        # Unique X coordinates
        xs = []
        for r in sys_barlines:
            if not xs or abs(r.x0 - xs[-1]) > 3:
                xs.append(r.x0)

        if len(xs) < 2:
            continue

        # Adaptive detection of the six TAB lines
        sys_h_lines = [r for r in h_lines if y_start - 5.0 <= r.y0 <= y_end + 5.0]
        unique_y = []
        for r in sorted(sys_h_lines, key=lambda r: r.y0):
            if not unique_y or r.y0 - unique_y[-1] >= 1.0:
                unique_y.append(r.y0)

        found_tab = False
        best_y0, best_y1, best_spacing = 0.0, 0.0, 6.51

        if len(unique_y) >= 6:
            for idx in range(len(unique_y) - 5):
                sub = unique_y[idx : idx + 6]
                gaps = [sub[j+1] - sub[j] for j in range(5)]
                if all(4.0 <= g <= 8.5 for g in gaps) and (max(gaps) - min(gaps) < 0.6):
                    best_y0 = sub[0]
                    best_y1 = sub[5]
                    best_spacing = sum(gaps) / 5.0
                    found_tab = True
                    break

        if not found_tab:
            if 30.0 <= h_cand <= 36.0:
                best_y0 = y_start
                best_y1 = y_end
                best_spacing = h_cand / 5.0
            else:
                best_y0 = y_start
                best_spacing = 6.51
                best_y1 = y_start + 5 * best_spacing

        systems.append({
            'y0': best_y0,
            'y1': best_y1,
            'barlines_x': xs,
            'spacing': best_spacing
        })

    # Sort systems vertically
    systems.sort(key=lambda s: s['y0'])
    return systems

if __name__ == "__main__":
    doc = fitz.open("temp.pdf")
    for i in range(len(doc)):
        systems = get_systems_and_measures(doc[i])
        print(f"Page {i+1} has {len(systems)} systems:")
        for idx, sys in enumerate(systems):
            print(f"  Sys {idx+1}: Y={sys['y0']:.1f} to {sys['y1']:.1f}, spacing={sys['spacing']:.3f}, measures count={len(sys['barlines_x'])-1}")
