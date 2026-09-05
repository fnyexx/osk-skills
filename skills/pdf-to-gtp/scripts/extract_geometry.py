# extract_geometry.py
import sys
import fitz

def get_systems_and_measures(page):
    drawings = page.get_drawings()
    v_barlines = []
    h_lines = []

    for d in drawings:
        r = d['rect']
        w = r.x1 - r.x0
        h = r.y1 - r.y0

        # Barline candidates: tall, thin vertical lines (h typically 28.0 to 42.0)
        if w <= 3.5 and 27.0 <= h <= 45.0:
            v_barlines.append(r)

        # Horizontal staff lines
        if h <= 2.5 and w >= 5.0:
            h_lines.append(r)

    # Cluster barlines by Y coordinates
    clusters = []
    for r in sorted(v_barlines, key=lambda item: item.y0):
        matched = False
        for c in clusters:
            ref = c[0]
            if abs(r.y0 - ref.y0) <= 5.0 and abs(r.y1 - ref.y1) <= 5.0:
                c.append(r)
                matched = True
                break
        if not matched:
            clusters.append([r])

    systems = []
    for c in clusters:
        # Deduplicate X coordinates (accounting for double barlines / repeats)
        xs = sorted(list(set(round(r.x0, 2) for r in c)))
        unique_xs = []
        for x in xs:
            if not unique_xs or x - unique_xs[-1] > 3.5:
                unique_xs.append(x)

        # A valid system must span at least 100 pt across the page and have >= 2 barlines
        if len(unique_xs) < 2 or (unique_xs[-1] - unique_xs[0]) < 100.0:
            continue

        c_y0 = min(r.y0 for r in c)
        c_y1 = max(r.y1 for r in c)
        h = c_y1 - c_y0
        spacing = (h - 0.46) / 5.0 if 28.0 <= h <= 36.0 else (h / 5.0)
        y0 = c_y0
        y1 = y0 + 5.0 * spacing

        systems.append({
            'y0': y0,
            'y1': y1,
            'barlines_x': unique_xs,
            'spacing': spacing
        })

    # Sort systems vertically top-to-bottom
    systems.sort(key=lambda s: s['y0'])
    return systems

if __name__ == "__main__":
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        print("Usage: python extract_geometry.py <pdf_path>")
        sys.exit(1)

    doc = fitz.open(pdf_path)
    for i in range(len(doc)):
        systems = get_systems_and_measures(doc[i])
        print(f"Page {i+1} has {len(systems)} systems:")
        for idx, sys in enumerate(systems):
            print(f"  Sys {idx+1}: Y={sys['y0']:.1f} to {sys['y1']:.1f}, spacing={sys['spacing']:.3f}, measures count={len(sys['barlines_x'])-1}")
