# verify_gp5.py
import sys
import os
import guitarpro

# Decode correct GBK output filename
filename = "兰亭序 指弹吉他谱_周杰伦.gp5"
source_dir = "D:/吉他谱/谱"
dest_path = os.path.join(source_dir, filename)

# If it was saved in current dir as garbled, let's find it.
files = os.listdir(".")
garbled_name = None
for f in files:
    if f.endswith(".gp5") and "兰" not in f and len(f) > 10:
        garbled_name = f
        break

if garbled_name:
    print(f"Found local gp5 with potential encoding issue in filename: {garbled_name}")
    import shutil
    shutil.copy2(garbled_name, dest_path)
    print(f"Copied to correct path: {dest_path}")
elif os.path.exists(filename):
    import shutil
    shutil.copy2(filename, dest_path)
    print(f"Copied to correct path: {dest_path}")

try:
    s = guitarpro.parse(dest_path, encoding='gbk')
    print("=== GP5 Audit ===")
    print(f"Title: {s.title}")
    print(f"Subtitle: {s.subtitle}")
    print(f"Artist: '{s.artist}'")
    print(f"Instructions: '{s.instructions}'")
    print(f"Tempo: {s.tempo}")
    print(f"Measure Count: {len(s.measureHeaders)}")
    print(f"Track Count: {len(s.tracks)}")

    # Audit notes, techniques, strums
    total_notes = 0
    total_rests = 0
    total_hammer = 0
    total_slide = 0
    total_tie = 0
    total_stroke = 0

    for measure in s.tracks[0].measures:
        for beat in measure.voices[0].beats:
            if beat.status == guitarpro.BeatStatus.rest:
                total_rests += 1
            else:
                total_notes += len(beat.notes)
                if beat.effect.stroke:
                    total_stroke += 1
                for note in beat.notes:
                    if note.type == guitarpro.NoteType.tie:
                        total_tie += 1
                    if note.effect.hammer:
                        total_hammer += 1
                    if note.effect.slides:
                        total_slide += 1

    print(f"Total Notes: {total_notes}")
    # Ties are stored as NoteType.tie in pyguitarpro
    print(f"Total Ties: {total_tie}")
    print(f"Total Hammer-ons/Pull-offs (Legato): {total_hammer}")
    print(f"Total Slides: {total_slide}")
    print(f"Total Brush/Strum/Arpeggio Effects: {total_stroke}")
    print(f"Total Rest Beats: {total_rests}")

    # Check measure numbers that have marker
    markers = []
    for idx, header in enumerate(s.measureHeaders):
        if header.marker:
            markers.append((idx + 1, header.marker.title))
    print(f"Markers detected: {markers}")

    # Check repeats and endings
    repeats = []
    endings = []
    for idx, header in enumerate(s.measureHeaders):
        if header.isRepeatOpen:
            repeats.append((idx + 1, "Open"))
        if header.repeatClose > 0:
            repeats.append((idx + 1, f"Close (count={header.repeatClose})"))
        if header.repeatAlternative > 0:
            endings.append((idx + 1, f"Alt={header.repeatAlternative}"))
    print(f"Repeats detected: {repeats}")
    print(f"Alt Endings detected: {endings}")

except Exception as e:
    print(f"Error parsing GP5: {e}")
