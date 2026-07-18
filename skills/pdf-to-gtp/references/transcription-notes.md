# Transcription Notes

## PDF Inspection

- `pdftotext -layout` is useful for finding titles, tempo markings, page count hints, and rough fret-number sequences. It is not reliable enough for final note placement.
- Render pages at 250-350 DPI or scale 3x. Crop each system so TAB digits, stems, and technique markings are readable.
- Keep a text extraction file and rendered page images next to the working GP5 file. They make later corrections faster.
- Check PDF metadata with PyMuPDF. Browser-created PDFs often reveal source pages through title, creator, rendered footer text, or visible site branding.
- Do NOT search the web, do NOT fetch online source files, and do NOT reference other local/external files. You MUST transcribe the input PDF strictly from its own coordinate visual extraction based on the built-in skill rules.

## Coordinate Transcription

- For vector PDFs, use `page.get_text("words")` or `page.get_text("dict")` with PyMuPDF.
- Red or otherwise colored measure numbers often have a distinct PDF color value; use that color to segment bars when available. This is safer than size-only matching because small fret digits, grace notes, and fingering can share the same font size as bar numbers.
- Determine each TAB system's six string-line y positions from drawn horizontal TAB objects, not from text alone. Group horizontal line y-values and choose six consecutive y-values with consistent gaps.
- Do not hard-code one TAB-line spacing. Browser/vector PDFs seen in this workflow used both about 6.7 pt gaps and about 4.5 pt gaps. Detect candidate groups by consistent gaps, then verify against nearby TAB digit y positions.
- Some layouts put measure numbers above the standard staff and TAB digits much lower in the same printed system. If the first six horizontal lines after the measure number yield zero tokens, extend the y search window and choose the six-line group whose y positions align with fret/dead-note digits.
- In two-staff systems, avoid picking the upper standard staff as TAB. A useful check is to count candidate TAB digit hits after applying the baseline offset; the correct six-line group should produce many hits, while the notation staff produces near zero.
- With PyMuPDF, do not map TAB digits using the text bbox top (`y0`) directly. In many guitar PDFs the digit bbox top sits about 3-4 pt above the actual erased TAB line; raw `y0` can shift notes up by one string (for example a 6th-string bass note becomes 5th string). Map with a baseline-adjusted value such as `y0 + 3.2` for 7.4 pt Arial tab digits, or calibrate the offset from visible digit rows and the six drawn TAB lines.
- After coordinate mapping, inspect the first bass note and several known low-string notes against the PDF image before generating the full file. This catches one-string vertical offsets early.
- Use x position within each measure for beat order. Preserve multi-digit frets (`10`, `12`, `<12>`) as one note.
- Use standard notation stems and beams to infer rhythm when the TAB text layer does not include durations.
- For rhythm, never just divide a 4/4 measure by the number of extracted note groups. Use the visual rhythm beams/stems when possible; otherwise quantize each note group's x position inside the measure to a 16th/32nd grid and derive durations from adjacent x positions.
- When the PDF draws rhythm beams below TAB, infer duration from beam count and group shape before x spacing. For example, a 3-note group with the first note on a single beam and the next two on a double beam is `8,16,16`; x spacing can easily reverse this into `16,16,8`. A 6-note cadence with two beamed pairs and two standalone stems is commonly `8,8,4,8,8,4`, while a standalone stem followed by a pair is `4,8,8`.
- For under-TAB rhythm, search from just below the top TAB line through roughly 30-40 pt below the sixth TAB line, then classify beams only when their center is below the sixth line. This prevents the six TAB string lines or ledger-like fragments from being counted as rhythm beams. For line-drawn beams, count paired top/bottom beam edges as one beam level; do not count each edge as a separate level.
- For existing GP5 correction jobs, do not trust old durations just because every measure sums to 4/4. Keep note groups only after PDF token counts match, then rebuild every `Beat.duration` from the PDF under-TAB rhythm drawings.
- To simplify rhythm inference and support scanned/bitmap PDFs, skip stem/beam drawing detection entirely. Group beats by X coordinates of note/rest tokens, calculate initial target durations from relative X-spacing, and run a DFS optimizer to find GP-representable values that sum to 16. To prevent spacing from creating false syncopated dotted rhythms, add a flat penalty (e.g., 1.5) in the DFS cost function for dotted values (1.5, 3.0, 6.0, 12.0) unless the beat is an explicitly protected rest or dot.
- Map chord name text blocks (size ~5.6, starting with A-G) above the systems to the closest beat in the system by X coordinate. Construct a `guitarpro.models.Chord` object with `firstFret = 1` and assign it to `beat.effect.chord`.
- Solve under-TAB rhythm as a constrained measure problem: stem/beam/dot evidence creates candidate durations, stemless pickup groups immediately before a stem-backed group may borrow from that group, the whole measure must match the time signature exactly, and x-position spacing is only a penalty/tiebreaker after visual candidates are built.
- Use GP-representable borrowed durations. For small stemless `H`/`P`/`sl.` pickup groups, split as a 32nd or 16th and reduce the following note to a representable value such as dotted 16th, eighth, dotted eighth, quarter, or dotted quarter. If exact visual spacing implies unsupported ticks, choose the closest representable solution and name the normalized measure.
- For x-position quantization, do not use the full barline span as the note span when there is left padding for measure numbers or chord boxes. Use the first and last note-group x positions as the active span, then quantize to a 16th grid for ordinary measures or a 32nd grid for dense measures.
- Quantized duration units should normalize to GP-representable values. Good unit choices in sixteenth-note units are `1, 2, 3, 4, 6, 8, 12, 16`; `3, 6, 12` map to dotted values. After normalization, adjust neighboring units so the bar total is exact.
- When extracting measure boundaries from PDF drawing objects, distinguish full-height TAB barlines from rhythm stems below the TAB. A vertical rhythm stem can have similar height, but its y-range does not span from the top TAB line to the bottom TAB line. Filtering by the six-line TAB height prevents false measure splits and missing notes. Use a looser x grouping tolerance for duplicate barline objects (for example 3-4 pt), because some PDFs draw the same barline as both line and rectangle objects.
- When measure numbers share the same size as fret digits, first cluster candidate numbers by x position. Repeated columns such as left/middle/right system starts are usually real bar numbers; isolated numeric spans inside the measure are usually frets or technique labels. Keep only rows where measure numbers increase left-to-right and by a small step.
- For three-measure-per-row layouts, fallback bar boundaries can be inferred from the measure-number columns plus the rightmost detected TAB barline or page margin. Verify boundaries by checking that notes in each measure fall inside the expected span.
- After writing GP5, compute each 4/4 measure's duration sum. It must equal 16 sixteenth-note units, with no empty measures, empty beats, or generated rests unless visible in the PDF.
- Do not fill missing bar duration by appending visible rest beats unless the PDF contains rests. For coordinate-generated drafts, rebalance the measure duration across real notes/chords so Guitar Pro does not show extra rests that are absent from the source.
- Do not flatten all numeric words into a single note stream. That destroys strings, voices, chords, and bar timing.


- **Auto-Detecting Repeats and Endings:** Do not hard-code repeat indexes. Instead, automatically scan PDF drawings for vertically aligned small filled shapes (width/height 1.0 to 4.0 pt) serving as repeat dots.
  - A repeat open is identified if a pair of dots sits immediately to the right of a barline ($X_{\text{dots}} > X_{\text{bar}}$). Set `isRepeatOpen = True` on the measure header starting after this barline.
  - A repeat close is identified if a pair of dots sits immediately to the left of a barline ($X_{\text{dots}} < X_{\text{bar}}$). Set `repeatClose = 2` on the measure header ending at this barline.
  - Match alternative endings by scanning text spans for `1.` and `2.` (size 4.8 to 5.5). Ending 1 covers all measures from the closest barline start to the next repeat close. Ending 2 starts at the next measure and covers up to 2-3 measures until the next logical boundary (system end, repeat open, double barline, etc.). Set `hasDoubleBar = True` at endings boundaries and section changes. 
- **Text-based H/P mapping:** For AlphaTab or similar PDFs where slur/legato curves are irregular or don't span the exact X coordinates, extract the literal 'H' and 'P' text spans. Map them by sorting all notes on the same string within that measure by X-coordinate, and choosing the adjacent pair of notes that strictly surround the X-coordinate of the text mark (e.g., `x_a < x_mark + 10.0` and `x_b > x_mark - 10.0`). Do not simply look for the absolute closest X without enforcing the left-to-right temporal order.
- **Handling Font Sizes for Digits:** AlphaTab PDFs may render fret digits using different font sizes (e.g. 7.5pt for regular notes, 6.5pt or 5.9pt for ghost notes or specific voices). Do not strictly filter digits by `size > 7.0`; use a looser threshold (e.g. `> 5.5`) to prevent missing notes, while retaining filtering for measure numbers.

## Troubleshooting Zero Notes

- If `rows > 0` and extracted tokens/notes are zero, print candidate fret/dead-note characters with page, x, `bbox.y0`, nearest row lines, and y-distance. This quickly shows whether the chosen lines are the standard staff instead of TAB.
- If `rows == 0`, print candidate measure-number spans with text, x, y, and size. Loosen measure-number size filters only after adding x-column/order filters so fret numbers do not become measure rows.
- If generated GP5 parses but has zero notes, discard that output and fix extraction. A structurally valid empty GP5 is not a usable conversion.
- If many `X` glyphs appear far above or below the selected TAB lines, check whether they are percussion/dead-note notation on a companion staff. Map only glyphs whose adjusted y coordinate lands close to one of the six TAB lines unless deliberately preserving a separate percussion voice.

## Vector PDF Rhythm And Techniques

- Inspect `page.get_drawings()` for rhythm beams and stems. Many browser-generated TAB PDFs store rhythm brackets as small line (`l`) objects below the TAB; these are useful for timing but must not be treated as measure bars.
- Preserve printed PDF system breaks when the user compares measure numbers visually. Write GP line breaks at the same measure endings where practical, and audit the PDF measure-number-to-GP-measure map before delivery.
- Treat visually optional TAB notes as playable-but-omittable notes: if a fret digit is gray/faded, has reduced text `alpha`, or is enclosed in a small circle/oval, keep the note and set `NoteEffect.ghostNote = True` in GP5. Do not delete optional notes or convert them to rests.
- In alphaTab/browser-rendered PDFs, faded optional fret digits may report `color == 0` but `alpha < 255`; inspect span alpha in addition to color. Circled notes are often drawn as two small curve (`c`) arcs with a narrow black oval rect around the digit; match oval-contained TAB digit centers to mark ghost notes.
- Extract explicit technique text first: `H`, `P`, and `sl.` are often independent PDF text spans. Map each marker to the nearest same-string adjacent note pair around the marker x-position. Do not map a marker across an intervening note on the same string, even if the midpoint score looks closer.
- Keep technique text row assignment tight vertically. A wide window below the current TAB row can accidentally capture `H` or `sl.` from the next system and leave it unpaired or attach it to the wrong notes. After extraction, print unpaired technique marks with measure, kind, x, and y; zero unpaired explicit marks is the target unless the PDF visibly contains orphan technique text.
- Validate technique direction: `H` should connect to a higher fret on the same string, and `P` should connect to a lower fret. In Guitar Pro 5, both are encoded as `NoteEffect.hammer=True`; the visual pull-off/hammer meaning comes from fret direction. Slides should use a slide effect on the left note of the same-string pair.
- Do not solve false H/P/sl by deleting all connectors. Classify visible marks: diagonal straight connectors between adjacent same-string notes are slides; curved connectors between adjacent same-string different frets are H/P by fret direction (mapped as GP legato/hammer effect); curved connectors between identical same-string frets are ties or let-ring continuations. 
- Enforce strict slur coordinate matching to filter out watermark or chord diagram circle noise: ensure the slur curve's Y0/Y1 endpoints are within 2.5 pt of the target string line, and the curve's X0/X1 boundaries align closely with the X coordinates of the connected notes (abs(note_a.x - curve.x0) < 8.0 and abs(note_b.x - curve.x1) < 8.0). If they share the same fret value, map it as a Tie (next note type set to NoteType.tie). If they differ, map it as a Legato curve (first note effect set to hammer = True). Report ambiguous connectors instead of guessing across non-adjacent notes.
- For vector PDFs, dead notes (slap / X marks) are often drawn using two crossed short line segment drawings rather than text characters. Detect them by identifying a pair of stroke ('s') line items ('l') whose width and height are between 2.0 and 6.0 pt, and whose midpoints are less than 1.0 pt apart. To filter out false positives from strumming arrowheads (which are chevron shapes meeting at endpoints), exclude any X candidates that lie within 3.0 pt of any long vertical strumming axis line (height > 12 pt).
- Avoid global `letRing` for fingerstyle conversion. Let-ring should come from explicit notation or a user playback request; otherwise GP can display continuation marks that look like false ties, slurs, H/P, or slides.
- Detect strum marks separately from rhythm stems. Common forms include vertical or diagonal wavy arrows through a chord, up/down arrowheads, brush slashes spanning several strings, rasgueado-like stroke glyphs, and explicit text such as `strum`, `brush`, `扫弦`, or direction hints. Attach the mark to the nearest chord or multi-string beat at the same x position, not to the nearest single TAB digit.
- In alphaTab/browser-rendered PDFs, technique arrowheads/slur triangles near `H`, `P`, or `sl.` can look like strum candidates. Require a visible shaft or wavy/diagonal stroke spanning multiple TAB strings before encoding a strum. Attach vertical arrow shafts to the following chord/note group when the shaft sits just before the group x position.
- In `pyguitarpro` GP5, beat-stroke visual direction can be counterintuitive because the GP5 reader/writer swaps `BeatStrokeDirection` internally. Parse-back enum counts are useful for presence only, not final visual direction. Validate with a rendered/opened GP file or a small known-direction test; if Guitar Pro displays the opposite arrow, set the opposite enum for GP5 output and record the visual direction in the audit.
- Detect arpeggio marks separately from slurs. Common forms include vertical wavy lines beside stacked chord notes, broken-chord arrows, rolled-chord brackets, and explicit text such as `arp.`, `arpeggio`, `琶音`, or `分解`. Attach the mark to the full chord beat and preserve up/down direction where visible.
- Do not silently drop strum/arpeggio marks if the writer cannot encode the exact GP effect. Store a beat text marker such as `strum down`, `strum up`, `brush`, `arpeggio up`, or `arpeggio down`, and include the affected measures in the final audit.
- For every strum or arpeggio mark, crop/compare the local PDF region and infer visual direction from the arrowhead endpoint, not from a global default. Attach it to the actual chord/note group at that x-position; some marks belong to later beats inside the measure, not beat 0. Do not add a strum/arpeggio mark where the PDF only shows a tie, slur, slide, or technique arrowhead.
- In GP5 output, distinguish intended visual direction from the parsed `BeatStrokeDirection` enum. `pyguitarpro` may write/read swapped directions, so store the intended visual direction in the audit and use a rendered/opened GP file or known-direction test when the user reports reversed arrows.
- Treat short curved (`c`) drawing objects near or just above TAB numbers as slur/legato candidates only when no explicit `H`, `P`, or `sl.` text is nearby. Curves are visually noisy in many generated PDFs and can easily over-tag hammer-ons.
- Small-font TAB digits are not automatically grace notes. If the user asks to preserve them as normal notes, include them as real beat groups and split the local duration with the following main note rather than stretching the phrase.
- Filter large watermark glyphs, section labels, chord-box text, and measure numbers before extracting TAB digits. For common browser PDFs, TAB digits are often a distinct size such as 7.4 pt Arial; measure numbers may be around 5.1 pt.
- Private-use glyphs can represent dead-note boxes or other notation. Only convert them to `NoteType.dead` when their size and y-position match the TAB line system; otherwise they may be chord-box or watermark artifacts.
- Repeat endings need both visual alternatives and repeat-close data. When the PDF shows `1.` and `2.`, set `repeatAlternative` on the ending measures and set `repeatClose` on the last measure of the first ending. Set `isRepeatOpen` at the visible repeat start. Ensure all measures covered by Ending 1 share the same `repeatAlternative` bitmask (e.g. value = 1 for the 1st ending, 2 for the 2nd ending, or 3 for the 1st and 2nd repeat together). Set `repeatClose` to the exact repeat count (e.g. 3 if a 3x text label is present). Always set `measure.header.hasDoubleBar = True` at the boundaries of endings or section transitions to render double barlines.
- Avoid creating fake notes or empty rests. Combine note fret coordinates with stems-only vertical line drawings to establish the full beat X positions. If a stems-only beat without notes is detected (which indicates a tied/held note in notation), merge its duration forward into the preceding non-empty beat (extend the duration of the preceding note) and remove the empty beat from the GP structure entirely. This prevents cluttering the score with fake rests.
- Chord names are safer than guessed chord diagrams. Only create a GP chord diagram when the visible fingering is legible or the shape is known with high confidence; otherwise store the chord name as beat text and say chord-box refinement may be needed.

## Metadata Cleanup

- When the user asks to keep only the Chinese title, set `Song.title` to the title, put requested generated-by text in `Song.subtitle`, and clear Chinese-bearing fields such as `artist`, `album`, `words`, `music`, `copyright`, `instructions`, and `notice`.
- Parse the output with the same encoding used for writing and print non-empty string fields. Treat unexpected non-ASCII metadata outside the allowed title/subtitle fields as a cleanup failure.

## MIDI Reference Alignment

- Use a supplied `.mid` as a rhythm reference, not as the authoritative transcription. Keep PDF strings, frets, chord voicings, techniques, sections, and repeats unless the user explicitly asks to replace them from MIDI.
- Parse MIDI note-on start ticks and group simultaneous starts into onsets. With standard 960 ticks/quarter MIDI, a 4/4 bar is 3840 ticks and a 32nd-note grid is 120 ticks.
- Apply MIDI durations only when a printed PDF measure can be aligned to the same number of note groups. If MIDI has extra grace/performance onsets, arpeggiated strums, or missing printed notes, keep the PDF rhythm inference for that measure or align manually.
- Be careful with pickup-like empty space at the start of a measure. A visual blank before a first TAB digit may mean the first visible note is delayed, but in GP5 a visible rest changes the printed score. Do not add rests unless shown in the PDF or requested.
- Always round-trip validate after writing GP5. `pyguitarpro` may not preserve hidden `BeatStatus.empty` beats, arbitrary tuplets, or extra tied continuation beats reliably in GP5; if parse-back fails or measure totals change, fall back to representable durations and document the compromise.

## Guitar Pro Mapping

- Standard guitar tuning MIDI values:
  - E standard: string 1-6 = `64, 59, 55, 50, 45, 40`
  - Eb standard: string 1-6 = `63, 58, 54, 49, 44, 39`
  - Drop D: string 1-6 = `64, 59, 55, 50, 45, 38`
- In `pyguitarpro`, string numbers are Guitar Pro string numbers: `1` is the highest string, `6` is the lowest string.
- Use `NoteType.dead` for `x`.
- Use `NoteEffect.hammer = True` for hammer-ons and pull-offs; GP stores both as legato connection.
- Use `NoteEffect.ghostNote = True` for gray/faded/circled optional notes that the player may omit.
- Use `NoteEffect.letRing = True` only for explicit let-ring notation or user-requested playback sustain. Do not enable it globally for fingerstyle; it can create visual continuation marks that look like false H/P/sl/ties.
- Use `NoteEffect.slides = [SlideType.legatoSlideTo]` or `shiftSlideTo` for visible `sl.` markings.
- Use Guitar Pro beat brush/strum/arpeggio effects when the local `pyguitarpro` model exposes them on `BeatEffect`; otherwise preserve the mark as `Beat.text` and report that GP effect encoding was not available.
- Use `NaturalHarmonic()` for `<12>`, `<7>`, and similar natural harmonics.
- Use `MeasureHeader.isRepeatOpen`, `repeatClose`, and `repeatAlternative` for repeat structures.

## Delivery Standard

- Include the full output path.
- State whether the file is a draft or precision-checked.
- If a source `.gpx` was found during fallback but GP5 conversion is still pending, provide the `.gpx` path and do not present a generated approximation as corrected.
- If only part of the score was carefully checked, name the checked measure range.
- When the user asks to preserve chord diagrams but they are not visible or not represented by the script, add chord names/text markers and tell the user which measures need manual chord-box refinement in Guitar Pro.
