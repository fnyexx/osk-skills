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

7. **Final Exhaustive Rhythm & Duration Audit (最后全面检查节奏时值，100% 与 PDF 严格对齐)**:
   - **逐小节逐拍核对**：遍历每一小节中的所有 Beat，核对生成的 GP5 音符时值（4分/8分/16分/32分/附点/三连音等）与 PDF 原谱对应位置的符干（Stems）、符杠层级（Beams）、附点（Dots）及休止符（Rests）是否 100% 完全一致。
   - **严禁时值偏差**：小节内所有 Beat 时值之和必须精确匹配拍号目标总值（如 4/4 拍为 16.0u / 1.000），绝不允许因平分或微调导致时值偏移。
   - **延音与切分再确证**：重点复核跨拍延音（Tied Stems）与附点音符，确保切分节奏与 PDF 视觉节奏绝对对齐。若发现任何差异，必须立即修正，不可放行。

## Rules

### Encoding
- **MUST** write Chinese metadata/beat text with `encoding="gbk"`, fallback `gb18030`.
- On Windows, **MUST** copy non-ASCII input paths to ASCII work path for PDF/GP libs; output to original directory.
- **MUST** output `.gp5` beside source PDF with same basename unless told otherwise.

### Notes and Duration
- **MUST** ensure clef, string tuning, fret positions, and all note values are 100% correct. Any vertical offset (e.g. mapping notes to the wrong string) is a critical failure.
- **MUST** detect all dead-notes (slap/拍弦/打板 `X` marks). Check both vector drawing crossed short lines AND font glyphs:
  - Vector drawings: 2 crossed stroke lines (w/h 2.0 to 6.0 pt) crossing at midpoints (< 1.0 pt).
  - Private font glyphs: characters such as `\u22a0` (boxed X) in Type3 or symbol fonts (font size ~7.5 pt) aligned on string lines. Map all valid instances to `NoteType.dead`.
- **MUST** extract dotted notes for accurate syncopation. Detect small solid fill square/circle drawings (width/height between 1.0 to 2.2 pt) located within 8.0 pt of any Beat's X coordinate as dots. A Beat with 0 beams + dot = dotted quarter (6 units); 1 beam + dot = dotted eighth (3 units).
- **MUST NOT** add visible rests unless the PDF shows rests. Rebalance underfilled bars across real notes.
- **Beat-Cell Rhythm Architecture & Physical Beam Extraction (拍胞架构与矢量符杠层级分析)**:
  - Derive note durations primarily from visual **beam connectivity (符杠连接层级)** and physical vertical stems:
    - **Stems**: Vertical stroke/fill lines ($W \le 1.5\text{ pt}$, $3.0 \le H \le 40.0\text{ pt}$) beneath the TAB staff or standard staff. Every beat onset aligns with a stem.
    - **Beams & Flags**: Horizontal lines ($W \ge 1.5\text{ pt}$, $0.8 \le H \le 2.5\text{ pt}$), including short flags/partial beams ($1.5 \le W \le 3.5\text{ pt}$).
    - Count distinct horizontal beam Y-levels overlapping each stem at $X$:
      - $\ge 3$ overlapping beams $\to$ **32nd note (`0.5u`)**
      - 2 overlapping beams $\to$ **16th note (`1.0u`)**
      - 1 overlapping beam $\to$ **8th note (`2.0u`)**
      - 0 overlapping beams $\to$ **Quarter note (`4.0u`)** (or final chord Half note `8.0u` in final bar)
    - **Augmentation Dots**: Small square/circular dots ($0.8 \le W, H \le 2.5\text{ pt}$, $|W - H| < 0.8\text{ pt}$) within $10\text{ pt}$ X and $6\text{ pt}$ Y of a stem. Multiplies duration by $1.5$ (e.g. dotted 8th = `3.0u`, dotted quarter = `6.0u`).
  - **SMuFL Rest Glyphs (音乐字体休止符识别)**:
    - Detect standard SMuFL rest characters in text blocks (`0xE4E0` to `0xE4FF`):
      - `U+E4E4`: Half rest (二分休止符, `8.0u`)
      - `U+E4E5`: Quarter rest (四分休止符, `4.0u`)
      - `U+E4E6`: 8th rest (八分休止符, `2.0u`)
      - `U+E4E7`: 16th rest (十六分休止符, `1.0u`)
    - **MUST NOT** drop these characters as unrecognized font symbols; construct corresponding rest beats.
  - **Tied Empty Stems (跨拍延音切分与空符干追溯)**:
    - If a rhythm stem has no fret numbers directly on the TAB staff, inspect for an arriving curved tie (`item[0] == 'c'`) terminating at that stem's X position ($|X_{\text{curve\_end}} - X_{\text{stem}}| < 4.0\text{ pt}$).
    - Backtrack along the curve to the source note onset and insert a tied note (`note.type = models.NoteType.tie`) on the beat.
    - **NEVER** discard empty stems with arriving ties; they preserve syncopation, sustain ringing, and prevent measure duration collapse.
  - **Dynamic Time Signatures**:
    - Detect Unicode time signature glyphs (e.g., `\ue082` for 2, `\ue084` for 4).
    - Dynamically update `MeasureHeader.timeSignature` and set per-measure `target_sum` (e.g., 2/4 = `8.0u`, 4/4 = `16.0u`).
  - **MUST NOT** let raw X-spacing create unnatural 32nd notes or awkward dotted syncopations unless explicitly confirmed by triple beams or visual dotted notation.
  - **Fallback Only**: Only when vector stems/beams are completely missing (e.g. pure text-based or degraded scanned PDFs) should the algorithm fall back to spacing/DFS optimization.
- **MUST** map chord name texts (usually printed above the systems, font size ~5.6) to the closest beats by X coordinate. Construct a `guitarpro.models.Chord` object with `firstFret = 1` and assign it to the beat's chord effect.
- **MUST** protect dotted note values (3 or 6) during rhythm micro-tuning to balance a measure to 1.000. **NEVER** alter raw_units that were explicitly mapped to dotted values; micro-tuning adjustments must only modify even-valued non-dotted beats.
- **MUST** preserve gray/faded/circled TAB notes as ghost notes, not rests or deletions.
- **MUST** preserve: tuning, capo, tempo changes, meter changes, bar numbers, repeats, endings, alternatives, D.S./D.C./Coda, chord names/diagrams, fingerings, double bars, final bars.
- When initializing `guitarpro.Song()`, **MUST** clear default measure headers (`song.measureHeaders.clear()`) and tracks (`song.tracks.clear()`) before appending newly generated elements.

### Repeats, Double-Dot Barlines, and Endings
- **MUST** automatically detect and pair repeat opens and closes from PDF vector drawings by identifying pairs of vertically aligned small filled circles or squares (width/height 1.0 to 4.0 pt) located near a vertical barline (distance < 15.0 pt):
  - **Repeat Open (前反复双小节点 `|:`)**: If the dots are on the right side of the barline ($X_{\text{dots}} > X_{\text{bar}}$), or at the start of a repeated theme/verse, set `isRepeatOpen = True` on the measure header starting after that barline.
  - **Repeat Close (后反复双小节点 `:|`)**: If the dots are on the left side of the barline ($X_{\text{dots}} < X_{\text{bar}}$), or at the end of Ending 1 (房子 1), set `repeatClose = 2` (or repeat count) on the measure header ending at that barline.
- **Alternative Endings (`1.` and `2.` brackets / 反复跳跃记号)**:
  - **CRITICAL GP5 RULE**: In Guitar Pro 5, `repeatAlternative` bitmask (`1` for `[1.`, `2` for `[2.`) **MUST ONLY BE SET ON THE FIRST MEASURE** of the alternative ending (e.g. `m_start.repeatAlternative = 1`), **NEVER** on every measure across the ending block. Setting `repeatAlternative` on multiple consecutive measures creates broken, redundant `1.` / `2.` flags on every bar instead of a single continuous ending bracket.
  - Ending 1 automatically spans from its starting measure to the `repeatClose` measure (`:|`).
  - Ending 2 automatically spans from its starting measure to the next section boundary / double barline.
- **Double Barlines (`||` 双小节线)**:
  - **MUST** set `hasDoubleBar = True` at the boundaries of major musical sections (e.g., end of Intro before Verse repeat open, end of Ending 2 before Coda, and final measure of the score).
  - Do NOT confuse `hasDoubleBar` (plain double lines `||`) with repeat barlines (`|:` and `:|` with double dots).

### Techniques and Strumming
- **MUST** correctly identify and map all techniques: H (Hammer-on), P (Pull-off), and sl. (Slide) must match the source exactly. If there are no H/P text markings on the PDF slur curves, or if specified by the user, you **MUST** map all curves as **Ties (延音线)** instead of Hammer-ons/Pull-offs.
- **MUST NOT** delete or simplify H/P/slide connectors even if they are complex, dense, or ambiguous. If a connector is visually ambiguous, you **MUST** report it in the delivery notes for user review instead of skipping it or converting it to normal notes.
- **MUST** verify that slur curves connecting to a parenthesized next note (e.g., `(3)`) are mapped as **Ties (延音线)**, and the preceding note **MUST NOT** have a legato/hammer-on/pull-off/slide effect attached.
- GP5: H and P both use `NoteEffect.hammer=True`. Distinguish by fret direction in audits.
- **MUST NOT** apply `NoteEffect.letRing` globally — only for explicit let-ring marks or user-requested sustain.
- **Strum and Arpeggio Arrow Direction (CRITICAL DIRECTION SWAP RULE)**:
  - In `pyguitarpro` GP5 serialization, `GP5File.writeBeatStroke` internally calls `stroke.swapDirection()`.
  - **Visual UP ARROW (↑)** (sweeping from low/bass strings towards high/treble strings): You **MUST** pass `BeatStrokeDirection.down` in Python code.
  - **Visual DOWN ARROW (↓)** (sweeping from high/treble strings towards low/bass strings): You **MUST** pass `BeatStrokeDirection.up` in Python code.
  - Strum duration speed: `BeatStroke(direction, 64)` (sixty-fourth duration value); Arpeggio duration speed: `BeatStroke(direction, 16)` (sixteenth duration value).
  - **MANDATORY Visual Strum Direction Verification**: During visual validation, verify that each strum arrow on the rendered GP score matches the exact printed arrow direction (↑ or ↓) in the PDF.
- **MUST** automatically detect strum and arpeggio marks from PDF vector drawings by pairing stroke arrowheads (chevrons) with vertical lines.
  - Arrowheads are drawn as stroke ('s') drawings containing 2 small lines (width/height <= 5.0 pt) sharing one endpoint. If the shared endpoint is at the minimum Y, the visual arrow points **UP**; if at the maximum Y, it points **DOWN**.
  - Strum shafts are vertical straight lines (width <= 1.0 pt, height 10.0 to 30.0 pt) inside system ranges (excluding barlines).
  - Arpeggio wavy lines are series of small diagonal strokes (width <= 3.0 pt, height 1.5 to 8.0 pt) that are close in X and vertically contiguous (combined height >= 10.0 pt).
  - A strum/arpeggio is valid **ONLY** when a chevron arrowhead is matched near its top/bottom (X distance < 3.0 pt, Y distance < 5.0 pt). Attach validated stroke to the closest beat by X-coordinate.
- **MUST NOT** create any "fake notes" or unnecessary rest beats. If a stems-only beat without fret numbers is detected and is part of a tie/slur connection, you **MUST** merge its duration forward into the preceding non-empty beat (i.e. extend the duration of the preceding note) and remove the empty beat from the GP structure entirely. This prevents cluttering the score with duplicate notes or fake rests.

### Metadata
- **MUST** keep song title in `Song.title`, set `Song.subtitle` to `oske AI`, clear all other fields (artist, copyright, instructions, notice).
- **MUST** parse back and print non-empty string fields to prove Chinese survived and unwanted fields are empty.

## Validation (MANDATORY — not optional)

Parse the written `.gp5` back with `guitarpro.parse()` using the same encoding. Zero extracted notes = failed conversion.

Run and report every audit:
- **Structure:** measure count, track count, tempo, time signatures, line-break/measure-number mapping, and double barlines (hasDoubleBar) / repeats alignment at transitions.
  - **MANDATORY Repeats Check**: Compare all repeat headers (isRepeatOpen, repeatClose, repeatAlternative) and double barlines (hasDoubleBar) against the original PDF layout. Ensure they are matched, paired, and set correctly on the corresponding measures.
- **Rhythm & Durations (节奏与时值对齐终审):** 必须全量核对每一小节的每个 Beat 时值与 PDF 原始符杠层数（0/1/2/3层分别对应4/8/16/32分音符）、符干及附点。小节内所有 Beat 时值之和必须精确等于该小节拍号的目标总值，严禁出现时值偏差、多出或缺少休止符。列出所有节奏来源统计，若有任何小节使用 fallback/x-position，必须特别标注并人工核准。
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
python ./scripts/verify_gp5.py "./song.gp5"
python -c "import guitarpro; s=guitarpro.parse(r'./song.gp5', encoding='gbk'); print(s.title, s.subtitle, s.tempo, len(s.measureHeaders), len(s.tracks))"
```

## Delivery

- State full output path and whether draft or precision-checked.
- **MUST** explicitly state that a 100% full-scale visual comparison and rhythm duration PDF-alignment audit have been performed for every single measure.
- Summarize: metadata, rhythm sources, note count audit, technique audit, strum/arpeggio audit, unresolved measures, repeat/endings validation results, and exact rhythm duration alignment status.
- If source rhythm/notation was not fully encoded, name the measures and why.
