# analyze_pdf.py
import fitz

doc = fitz.open("C:/Users/fnyex/.claude/skills/pdf-to-gtp/scripts/temp.pdf")
print("Total pages:", len(doc))

for i in range(len(doc)):
    page = doc[i]
    drawings = page.get_drawings()
    print(f"\n--- Page {i+1} drawings summary ---")
    print("Total drawings:", len(drawings))

    # Let's count vertical-like lines (width <= 2.0)
    v_lines = []
    h_lines = []
    for d in drawings:
        r = d['rect']
        w = r.x1 - r.x0
        h = r.y1 - r.y0
        if w <= 3.0:
            v_lines.append(r)
        if h <= 3.0:
            h_lines.append(r)

    print(f"Vertical-like lines: {len(v_lines)}")
    print(f"Horizontal-like lines: {len(h_lines)}")

    # Print some details of vertical lines
    # Sort them by x0, then y0
    v_lines.sort(key=lambda r: (r.x0, r.y0))
    print("Some vertical lines (sorted by x0):")
    for r in v_lines[:20]:
        print(f"  rect: x0={r.x0:.2f}, y0={r.y0:.2f}, x1={r.x1:.2f}, y1={r.y1:.2f}, w={r.x1-r.x0:.2f}, h={r.y1-r.y0:.2f}")

    # Let's check text blocks of size ~5 to ~10
    print("Some text spans:")
    blocks = page.get_text("dict")["blocks"]
    text_count = 0
    for block in blocks:
        if "lines" in block:
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if text:
                        text_count += 1
                        if text_count <= 20:
                            print(f"  text='{text}', bbox=[{span['bbox'][0]:.1f}, {span['bbox'][1]:.1f}, {span['bbox'][2]:.1f}, {span['bbox'][3]:.1f}], size={span['size']:.1f}")
    print(f"Total non-empty text spans: {text_count}")
