#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
verify_gp5.py: Universal audit and validation tool for Guitar Pro (.gp5) files.
Checks structure, measure duration sums, note techniques, strum directions, and repeats.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit and validate Guitar Pro 5 (.gp5) files")
    parser.add_argument("gp5", help="Path to .gp5 file to audit")
    parser.add_argument("--encoding", default="gbk", help="Encoding to parse with (default: gbk)")
    return parser.parse_args()


def audit_gp5(file_path: str, encoding: str = "gbk") -> int:
    try:
        import guitarpro
    except ImportError:
        print("Error: guitarpro library not found. Install via `pip install pyguitarpro`.", file=sys.stderr)
        return 1

    p = Path(file_path)
    if not p.is_file():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        return 1

    song = None
    encodings_to_try = [encoding, "gbk", "gb18030", "utf-8", "cp1252"]
    for enc in encodings_to_try:
        try:
            song = guitarpro.parse(str(p), encoding=enc)
            used_enc = enc
            break
        except Exception:
            continue

    if song is None:
        print(f"Error: Failed to parse '{file_path}' with tested encodings ({encodings_to_try}).", file=sys.stderr)
        return 1

    print("=" * 60)
    print(f"GP5 AUDIT REPORT: {p.name}")
    print(f"File Path: {p.resolve()}")
    print(f"Encoding:  {used_enc}")
    print("=" * 60)

    # 1. Metadata
    print("\n[1. METADATA]")
    print(f"  Title:        '{song.title}'")
    print(f"  Subtitle:     '{song.subtitle}' (expected: 'oske AI')")
    print(f"  Artist:       '{song.artist}'")
    print(f"  Album:        '{song.album}'")
    print(f"  Tempo:        {song.tempo} BPM")
    print(f"  Tracks:       {len(song.tracks)}")
    print(f"  Measures:     {len(song.measureHeaders)}")

    # 2. Track & Tuning
    print("\n[2. TRACK & TUNING]")
    for t_idx, track in enumerate(song.tracks):
        tuning_str = " ".join(str(s.value) for s in track.strings)
        print(f"  Track {t_idx+1}: '{track.name}', Capo: {track.offset}, Strings: {len(track.strings)} [{tuning_str}]")

    # 3. Measures, Repeats, Endings, Markers
    print("\n[3. STRUCTURE, REPEATS & SECTIONS]")
    markers = []
    repeats = []
    endings = []
    double_bars = []

    for idx, h in enumerate(song.measureHeaders):
        m_num = idx + 1
        if h.marker:
            markers.append(f"M{m_num}: '{h.marker.title}'")
        if h.isRepeatOpen:
            repeats.append(f"M{m_num} [|: Open]")
        if h.repeatClose > 0:
            repeats.append(f"M{m_num} [:| Close x{h.repeatClose}]")
        if h.repeatAlternative > 0:
            endings.append(f"M{m_num} [Alt={h.repeatAlternative}]")
        if h.hasDoubleBar:
            double_bars.append(f"M{m_num}")

    print(f"  Markers:      {', '.join(markers) if markers else 'None'}")
    print(f"  Repeats:      {', '.join(repeats) if repeats else 'None'}")
    print(f"  Alt Endings:  {', '.join(endings) if endings else 'None'}")
    print(f"  Double Bars:  {', '.join(double_bars) if double_bars else 'None'}")

    # 4. Notes & Techniques Audit
    print("\n[4. NOTES & TECHNIQUES AUDIT]")
    total_notes = 0
    total_rests = 0
    total_dead = 0
    total_ghost = 0
    total_harmonic = 0
    total_hammer = 0
    total_slide = 0
    total_tie = 0
    total_strums = 0
    total_arpeggios = 0
    timing_issues = []

    for m_idx, track_measure in enumerate(song.tracks[0].measures):
        m_num = m_idx + 1
        voice = track_measure.voices[0]
        header = track_measure.header

        # Expected duration units (in 16th-note units)
        expected_units = (header.timeSignature.numerator * 16.0) / (header.timeSignature.denominator.value / 4.0)
        actual_units = 0.0
        for beat in voice.beats:
            dur = beat.duration
            base_units = 16.0 / (dur.value / 4.0) if dur.value > 0 else 0.0
            if dur.isDotted:
                base_units *= 1.5
            if dur.tuplet and dur.tuplet.enters > 0 and dur.tuplet.times > 0:
                base_units = base_units * dur.tuplet.times / dur.tuplet.enters
            actual_units += base_units

            if beat.status == guitarpro.BeatStatus.rest:
                total_rests += 1
            else:
                total_notes += len(beat.notes)
                if beat.effect.stroke and beat.effect.stroke.direction != guitarpro.BeatStrokeDirection.none and beat.effect.stroke.value > 0:
                    if beat.effect.stroke.value == 64:
                        total_strums += 1
                    else:
                        total_arpeggios += 1

                for n in beat.notes:
                    if n.type == guitarpro.NoteType.dead:
                        total_dead += 1
                    elif n.type == guitarpro.NoteType.tie:
                        total_tie += 1

                    if n.effect.ghostNote:
                        total_ghost += 1
                    if n.effect.harmonic:
                        total_harmonic += 1
                    if n.effect.hammer:
                        total_hammer += 1
                    if n.effect.slides:
                        total_slide += 1

        if abs(actual_units - expected_units) > 0.05:
            timing_issues.append((m_num, actual_units, expected_units))

    print(f"  Total Notes:              {total_notes}")
    print(f"  - Dead Notes (拍弦/打板):   {total_dead}")
    print(f"  - Ghost Notes (括号音):    {total_ghost}")
    print(f"  - Harmonics (泛音):        {total_harmonic}")
    print(f"  Total Ties (延音线):       {total_tie}")
    print(f"  Total Hammer/Pull (圆滑):  {total_hammer}")
    print(f"  Total Slides (滑音):       {total_slide}")
    print(f"  Total Strums (扫弦箭头):   {total_strums}")
    print(f"  Total Arpeggios (琶音):    {total_arpeggios}")
    print(f"  Total Rest Beats (休止):   {total_rests}")

    # 5. Timing / Rhythm verification
    print("\n[5. TIMING INTEGRITY]")
    if timing_issues:
        print(f"  WARNING: Found {len(timing_issues)} measures with duration mismatch:")
        for m_num, act, exp in timing_issues[:10]:
            print(f"    Measure {m_num}: total {act:.2f} units, expected {exp:.2f} units")
        if len(timing_issues) > 10:
            print(f"    ... and {len(timing_issues) - 10} more.")
    else:
        print(f"  PASS: All {len(song.measureHeaders)} measures have balanced durations.")

    print("\n" + "=" * 60)
    print("AUDIT COMPLETE")
    print("=" * 60)
    return 0 if not timing_issues else 2


def main() -> None:
    args = parse_args()
    ret = audit_gp5(args.gp5, args.encoding)
    sys.exit(ret)


if __name__ == "__main__":
    main()
