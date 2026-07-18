# analyze_systems.py
import fitz

doc = fitz.open("C:/Users/fnyex/.claude/skills/pdf-to-gtp/scripts/temp.pdf")
page = doc[0]
drawings = page.get_drawings()

candidates = []
for d in drawings:
    r = d['rect']
    w = r.x1 - r.x0
    h = r.y1 - r.y0
    if w <= 2.0 and 25.0 <= h <= 80.0:
        candidates.append(r)

print("Total candidates:", len(candidates))
# Let's see those near X=14.5
left_candidates = [r for r in candidates if 14.0 <= r.x0 <= 16.0]
print(f"Candidates near left edge (x=14.0 to 16.0): {len(left_candidates)}")
for r in left_candidates:
    print(f"  y0={r.y0:.2f}, y1={r.y1:.2f}, h={r.y1-r.y0:.2f}")

# Also examine horizontal lines in the page to find TAB strings
h_lines = []
for d in drawings:
    r = d['rect']
    w = r.x1 - r.x0
    h = r.y1 - r.y0
    if h <= 2.0 and w > 100.0:
        h_lines.append(r)
h_lines.sort(key=lambda r: r.y0)
print(f"\nHorizontal lines (>100 width): {len(h_lines)}")
# Group horizontal lines by similarity in y0 to see systems
systems_h = []
curr_sys = []
for idx, r in enumerate(h_lines):
    if not curr_sys:
        curr_sys.append(r)
    else:
        # If gap is small, say < 15, it's same system
        if r.y0 - curr_sys[-1].y0 < 15.0:
            curr_sys.append(r)
        else:
            systems_h.append(curr_sys)
            curr_sys = [r]
if curr_sys:
    systems_h.append(curr_sys)

for s_idx, sys in enumerate(systems_h):
    print(f"  Sys {s_idx+1}: {len(sys)} lines")
    for r in sys:
        print(f"    y={r.y0:.2f}, w={r.x1-r.x0:.2f}")
    if len(sys) >= 2:
        gaps = [sys[i+1].y0 - sys[i].y0 for i in range(len(sys)-1)]
        print(f"    gaps: {[round(g, 2) for g in gaps]}")
