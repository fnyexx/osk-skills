---
name: pdf-to-gtp
description: Use when converting PDF guitar tabs, scanned tablature, numbered tabs, or mixed staff+TAB PDFs into Guitar Pro files (.gp5/.gtp/.gpx). Also use when GP5 output has wrong notes, missing techniques, garbled Chinese metadata, rhythm misalignment, or parse-back failures.
---

# PDF To GTP

## Overview

Convert guitar PDFs into editable `.gp5` files via `pyguitarpro`. Every rule below exists because a conversion failed without it.

## Process (in order — DO NOT skip steps)

1. **Inspect the PDF FIRST.** Render pages with `scripts/render_pdf_pages.py`. Extract text with `pdftotext -layout`. Check: page count, measure count, tuning, capo, tempo, meter, repeats, endings, section markers, chord names, line breaks. **DO NOT** search the web or reference other local/external tab files; parse strictly from the original source PDF coordinates and structures. Read `references/transcription-notes.md` before writing any converter code.

2. **Build the GP5 skeleton** with correct measure count, tuning, tempo, and time signatures.

3. **Encode notes from image coordinates**, not from text extraction. Map TAB digits by x/y position to measure spans and nearest string line. Never flatten numeric text into a sequential note stream.

4. **Derive durations** from visual rhythm sources in strict priority order:
   1. Below-TAB beams/stems
   2. Standard staff rhythm
   3. Other explicit timing references
   4. MIDI alignment (safe fallback)
   5. x-position spacing (last resort)
   **NEVER** evenly divide a measure by note count.

5. **Classify every connector** (do NOT bulk-delete them):
   - Diagonal same-string = slide
   - Curved same-string different-fret = H/P (fret up→H, fret down→P)
   - Curved same-string same-fret = tie or let-ring
   - Ambiguous/non-adjacent = report, do not guess

6. **Validate** (see Validation section below).

## Rules

### Encoding
- **MUST** write Chinese metadata/beat text with `encoding="gbk"`, fallback `gb18030`.
- On Windows, **MUST** copy non-ASCII input paths to ASCII work path for PDF/GP libs; output to original directory.
- **MUST** output `.gp5` beside source PDF with same basename unless told otherwise.

### Notes and Duration
- **MUST** ensure clef, string tuning, fret positions, and all note values are 100% correct. Any vertical offset (e.g. mapping notes to the wrong string) is a critical failure.
- **MUST** detect all dead-notes (slap/拍弦/打板 `X` marks). In many vector PDFs, the `X` is drawn using two crossed short line segment drawings (width/height between 2.0 to 6.0 pt) rather than ordinary text characters. You **MUST** inspect the drawings to extract these `X` notes; relying only on text characters will miss them. To avoid false positives from strumming arrowheads, ensure the two short lines cross at their midpoints (the distance between their midpoints must be < 1.0 pt) rather than meeting at their endpoints (which form a chevron ^ or v). Always exclude X candidates that lie within 3.0 pt of any long vertical strumming axis line (height > 12 pt).
- **MUST** extract dotted notes for accurate syncopation. Detect small solid fill square/circle drawings (width/height between 1.0 to 2.2 pt) located within 8.0 pt of any Beat's X coordinate as dots. A Beat with 0 beams + dot = dotted quarter (6 units); 1 beam + dot = dotted eighth (3 units).
- **MUST NOT** add visible rests unless the PDF shows rests. Rebalance underfilled bars across real notes.
- When below-TAB stems/beams are missing, or to simplify detection and support scanned/bitmap PDFs: **MUST** group beats by X coordinates of note/rest tokens, estimate initial target durations from relative X-spacing, and balance the measure using a DFS optimizer. To prevent spacing from creating awkward syncopation, add a flat penalty (e.g. 1.5) in the DFS cost function for selecting dotted values (1.5, 3, 6, 12) unless the beat is an explicitly protected dotted note or rest.
- **MUST** map chord name texts (usually printed above the systems, font size ~5.6) to the closest beats by X coordinate. Construct a `guitarpro.models.Chord` object with `firstFret = 1` and assign it to the beat's chord effect.
- **MUST** protect dotted note values (3 or 6) during rhythm micro-tuning to balance a measure to 1.000. **NEVER** alter raw_units that were explicitly mapped to dotted values; micro-tuning adjustments must only modify even-valued non-dotted beats.
- **MUST** preserve gray/faded/circled TAB notes as ghost notes, not rests or deletions.
- **MUST** preserve: tuning, capo, tempo changes, meter changes, bar numbers, repeats, endings, alternatives, D.S./D.C./Coda, chord names/diagrams, fingerings, double bars, final bars.

### Repeats and Endings (Double-Dot Referencing)
- **MUST** automatically detect repeat opens and closes from PDF vector drawings by identifying pairs of vertically aligned small filled circles or squares (width/height 1.0 to 4.0 pt) located near a vertical barline (distance < 15.0 pt).
  - If the dots are on the right side of the barline ($X_{\text{dots}} > X_{\text{bar}}$), it is a **Repeat Open** (`isRepeatOpen = True` on the measure starting after the barline).
  - If the dots are on the left side of the barline ($X_{\text{dots}} < X_{\text{bar}}$), it is a **Repeat Close** (`repeatClose = 2` on the measure ending at the barline).
- **MUST** automatically map Alternative Endings (`1.` and `2.` brackets) by scanning for text spans containing `1.` or `2.` (size 4.8 to 5.5). 
  - Associate the label with the closest measure start.
  - Ending 1 covers all measures from its start to the nearest Repeat Close.
  - Ending 2 covers all measures from its start to the next logical boundary (e.g., next repeat open, next double barline, next section, or system boundary).
  - Always set `hasDoubleBar = True` at boundaries of endings and section transitions.

### Techniques and Strumming
- **MUST** correctly identify and map all techniques: H (Hammer-on), P (Pull-off), and sl. (Slide) must match the source exactly. If there are no H/P text markings on the PDF slur curves, or if specified by the user, you **MUST** map all curves as **Ties (延音线)** instead of Hammer-ons/Pull-offs.
- **MUST NOT** delete or simplify H/P/slide connectors even if they are complex, dense, or ambiguous. If a connector is visually ambiguous, you **MUST** report it in the delivery notes for user review instead of skipping it or converting it to normal notes.
- **MUST** verify that slur curves connecting to a parenthesized next note (e.g., `(3)`) are mapped as **Ties (延音线)**, and the preceding note **MUST NOT** have a legato/hammer-on/pull-off/slide effect attached.
- GP5: H and P both use `NoteEffect.hammer=True`. Distinguish by fret direction in audits.
- **MUST NOT** apply `NoteEffect.letRing` globally — only for explicit let-ring marks or user-requested sustain.
- **MUST** automatically detect strum and arpeggio marks from PDF vector drawings by pairing stroke arrowheads (chevrons) with vertical lines.
  - Arrowheads are drawn as stroke ('s') drawings containing 2 small lines (width/height <= 5.0 pt) sharing one endpoint. If the shared endpoint is at the minimum Y, the arrow points **UP** (`BeatStrokeDirection.up`); if at the maximum Y, it points **DOWN** (`BeatStrokeDirection.down`).
  - Strum shafts are vertical straight lines (width <= 1.0 pt, height 10.0 to 30.0 pt) inside system ranges (excluding barlines).
  - Arpeggio wavy lines are series of small diagonal strokes (width <= 3.0 pt, height 1.5 to 8.0 pt) that are close in X and vertically contiguous (combined height >= 10.0 pt).
  - A strum/arpeggio is valid **ONLY** when a chevron arrowhead is matched near its top/bottom (X distance < 3.0 pt, Y distance < 5.0 pt).
  - Map validated items to the closest beat by X-coordinate. Strum = `BeatStroke(direction, 64)` (sixty-fourth duration value); Arpeggio = `BeatStroke(direction, 16)` (sixteenth duration value). Do not add strokes to beats without a matched drawing.
- **MUST NOT** create any "fake notes" or unnecessary rest beats. If a stems-only beat without fret numbers is detected and is part of a tie/slur connection, you **MUST** merge its duration forward into the preceding non-empty beat (i.e. extend the duration of the preceding note) and remove the empty beat from the GP structure entirely. This prevents cluttering the score with duplicate notes or fake rests.

### Metadata
- **MUST** keep song title in `Song.title`, set `Song.subtitle` to `oske AI`, clear all other fields (artist, copyright, instructions, notice).
- **MUST** parse back and print non-empty string fields to prove Chinese survived and unwanted fields are empty.

## Validation (MANDATORY — not optional)

Parse the written `.gp5` back with `guitarpro.parse()` using the same encoding. Zero extracted notes = failed conversion.

Run and report every audit:
- **Structure:** measure count, track count, tempo, time signatures, line-break/measure-number mapping, and double barlines (hasDoubleBar) / repeats alignment at transitions.
  - **MANDATORY Repeats Check**: Compare all repeat headers (isRepeatOpen, repeatClose, repeatAlternative) and double barlines (hasDoubleBar) against the original PDF layout. Ensure they are matched, paired, and set correctly on the corresponding measures.
- **Rhythm:** count measures by duration source; name any using fallback/x-position.
- **Notes:** compare PDF TAB token count to GP note count per measure; investigate mismatches.
- **Techniques:** count explicit H/P/slide marks, connector classifications, encoded hammer/legato/slide/tie, ambiguous measures.
- **Strum/Arpeggio:** count visible marks, encoded marks, up/down directions, ambiguous measures.
- **Visual:** Compare rendered PDF crops against output for **EVERY SINGLE MEASURE**. You **MUST** perform a 100% full-scale visual comparison (clef, notes, fret, chords, strum directions, rhythm beams/stems, double barlines, and connectors). **Spot-checking or sampling is strictly forbidden.**

## Common Mistakes & Red Flags

| Mistake / Excuse / Red Flag | Correct Action & Reality |
|-----------------------------|--------------------------|
| **Skipping PDF rendering** / *"Text extraction is clean, I'll ignore rendering"* | Text layers lack coordinate context. Notes will be mapped to the wrong string/fret. **MUST** render pages first. |
| **Skipping parse-back validation** / *"The GP file wrote without errors"* | `pyguitarpro` writes silently; written files may still contain rests/duration errors or broken repeats. **MUST** parse-back to validate. |
| **Averaging durations / Ignoring beam lines** / *"I'll just average the durations"* | Evenly dividing measures causes broken rhythm. **MUST** verify note durations match visual beam counts. |
| **Incorrect repeat opens/closes / missing endings** | Placements based on guesses or rough guidelines fail playback. **MUST** detect repeat open/close dots via vector coordinates and align Ending 1/2 blocks. |
| **Spot-checking / Sampling visual validation** | Missing errors elsewhere leads to broken transcriptions. **MUST** perform a 100% full-scale visual comparison of **every single measure**. |

## Useful Commands

```powershell
python ./scripts/render_pdf_pages.py "./song.pdf" --out "./images"
python ./scripts/convert_pdf_to_gp5.py "./song.pdf"
python -c "import guitarpro; s=guitarpro.parse(r'./song.gp5', encoding='gbk'); print(s.title, s.subtitle, s.tempo, len(s.measureHeaders), len(s.tracks))"
```

## Delivery

- State full output path and whether draft or precision-checked.
- **MUST** explicitly state that a 100% full-scale visual comparison has been performed for every single measure.
- Summarize: metadata, rhythm sources, note count audit, technique audit, strum/arpeggio audit, unresolved measures, and repeat/endings validation results.
- If source rhythm/notation was not fully encoded, name the measures and why.
