# copy_correct_file.py
import os
import glob
import shutil

# Correct filename: 兰亭序 指弹吉他谱_周杰伦.gp5
# Let's find all *.gp5 in the current directory and sort by modification time, newest first.
gp5_files = glob.glob("*.gp5")
gp5_files.sort(key=os.path.getmtime, reverse=True)

print("All local gp5 files sorted by modification time (newest first):")
for f in gp5_files:
    print(f"  {f} (mod time: {os.path.getmtime(f)})")

# Find the one that corresponds to "兰亭序".
# The filename saved by convert_pdf_to_gp5.py is based on pdf_path.
# "兰亭序 指弹吉他谱_周杰伦.pdf" -> bytes object/utf-8 or gbk filename.
# Let's check which files are NOT the historical ones.
# Historical ones are:
# - 故乡吉他谱_许巍_Bb调简单版指弹谱-谱全了.gp5
# - 偏爱 指弹吉他谱_张芸京.gp5
# - 偏偏喜欢你 指弹吉他谱_陈百强.gp5
# - 江南 指弹吉他谱_林俊杰.gp5
# - 说好的幸福呢 指弹吉他谱_周杰伦.gp5
# - 天空之城_久石让.gp5

historical = [
    "故乡吉他谱_许巍_Bb调简单版指弹谱-谱全了.gp5",
    "偏爱 指弹吉他谱_张芸京.gp5",
    "偏偏喜欢你 指弹吉他谱_陈百强.gp5",
    "江南 指弹吉他谱_林俊杰.gp5",
    "说好的幸福呢 指弹吉他谱_周杰伦.gp5",
    "天空之城_久石让.gp5"
]

target_file = None
for f in gp5_files:
    if f not in historical:
        target_file = f
        break

if target_file:
    print(f"\nDetected newly generated gp5 file: {target_file}")
    dest_path = "D:/吉他谱/谱/兰亭序 指弹吉他谱_周杰伦.gp5"
    shutil.copy2(target_file, dest_path)
    print(f"Successfully copied to: {dest_path}")

    # Now verify the copied file
    import guitarpro
    try:
        s = guitarpro.parse(dest_path, encoding='gbk')
        print("\n=== Verified Correct GP5 Audit ===")
        print(f"Title: {s.title}")
        print(f"Subtitle: {s.subtitle}")
        print(f"Artist: '{s.artist}'")
        print(f"Instructions: '{s.instructions}'")
        print(f"Tempo: {s.tempo}")
        print(f"Measure Count: {len(s.measureHeaders)}")
        print(f"Track Count: {len(s.tracks)}")

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
        print(f"Total Ties: {total_tie}")
        print(f"Total Hammer-ons/Pull-offs: {total_hammer}")
        print(f"Total Slides: {total_slide}")
        print(f"Total Brush/Strum/Arpeggio Effects: {total_stroke}")
        print(f"Total Rest Beats: {total_rests}")

        markers = []
        for idx, header in enumerate(s.measureHeaders):
            if header.marker:
                markers.append((idx + 1, header.marker.title))
        print(f"Markers (Sections): {markers}")

        repeats = []
        endings = []
        for idx, header in enumerate(s.measureHeaders):
            if header.isRepeatOpen:
                repeats.append((idx + 1, "Open"))
            if header.repeatClose > 0:
                repeats.append((idx + 1, f"Close (count={header.repeatClose})"))
            if header.repeatAlternative > 0:
                endings.append((idx + 1, f"Alt={header.repeatAlternative}"))
        print(f"Repeats: {repeats}")
        print(f"Alt Endings: {endings}")
    except Exception as e:
        print(f"Error parsing newly copied file: {e}")
else:
    print("\nNo newly generated file found!")
