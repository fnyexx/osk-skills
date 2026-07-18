#!/usr/bin/env python
"""Render PDF pages to PNG files for guitar tab transcription."""

from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", help="Input PDF path")
    parser.add_argument("--out", default="pdf_pages", help="Output directory")
    parser.add_argument("--scale", type=float, default=3.0, help="Render scale; 3.0 is usually readable")
    parser.add_argument("--prefix", default="page", help="Output filename prefix")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pdf = Path(args.pdf)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise SystemExit("Missing dependency: install with `python -m pip install pymupdf`.") from exc

    doc = fitz.open(str(pdf))
    written: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="pdf_to_gtp_") as tmp:
        tmp_dir = Path(tmp)
        for index, page in enumerate(doc, start=1):
            pix = page.get_pixmap(matrix=fitz.Matrix(args.scale, args.scale), alpha=False)
            tmp_png = tmp_dir / f"{args.prefix}{index}.png"
            pix.save(str(tmp_png))
            final_png = out_dir / f"{args.prefix}{index}.png"
            shutil.copy2(tmp_png, final_png)
            written.append(final_png)

    for path in written:
        print(path)


if __name__ == "__main__":
    main()
