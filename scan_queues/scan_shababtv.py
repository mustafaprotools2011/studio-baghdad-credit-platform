#!/usr/bin/env python3
"""
Scan 10 ShababTV videos using EasyOCR to search for Mustafa Kamal related text.
"""
import json
import os
import subprocess
import sys
import re

COOKIES = "/opt/data/mustafa-mixing-archive/cookies.txt"
RESULTS_FILE = "/opt/data/mustafa-mixing-archive/scan_queues/shababtv_ocr_results.json"
OCR_TMP_DIR = "/tmp/shababtv_scan"
os.makedirs(OCR_TMP_DIR, exist_ok=True)

VIDEOS = [
    ("1", "https://www.youtube.com/watch?v=-SgcEtJMbt4"),
    ("2", "https://www.youtube.com/watch?v=-BpjOqE-rAI"),
    ("3", "https://www.youtube.com/watch?v=UQOo8FvQbXE"),
    ("4", "https://www.youtube.com/watch?v=r4QY0Pj3L2U"),
    ("5", "https://www.youtube.com/watch?v=Gq2hMbXFgIE"),
    ("6", "https://www.youtube.com/watch?v=Ek0-84GzLd8"),
    ("7", "https://www.youtube.com/watch?v=F6kU8gzcrLU"),
    ("8", "https://www.youtube.com/watch?v=pUwaglPcEI8"),
    ("9", "https://www.youtube.com/watch?v=edSWTy1qUDM"),
    ("10", "https://www.youtube.com/watch?v=tq-DfR4HYDE"),
]

SEARCH_TERMS = ["مصطفى كمال", "مهندس صوت", "مكس", "ماستر", "Mustafa Kamal", "مصطفى", "كمال"]

results = []

for idx, url in VIDEOS:
    video_id = url.split("v=")[-1]
    print(f"\n{'='*60}")
    print(f"[{idx}/10] Processing video: {url}")
    print(f"  Video ID: {video_id}")

    vid_mp4 = os.path.join(OCR_TMP_DIR, f"{video_id}.mp4")
    frame_png = os.path.join(OCR_TMP_DIR, f"{video_id}.png")

    entry = {
        "num": idx,
        "url": url,
        "video_id": video_id,
        "duration_sec": None,
        "downloaded": False,
        "ocr_text": None,
        "matches": [],
        "error": None,
    }

    try:
        # Step 1: Get duration
        print(f"  [1] Getting duration...")
        dur_result = subprocess.run(
            ["yt-dlp", "--cookies", COOKIES, "--print", "%(duration)s", "--skip-download", url],
            capture_output=True, text=True, timeout=60
        )
        if dur_result.returncode != 0:
            raise RuntimeError(f"yt-dlp duration failed: {dur_result.stderr.strip()}")
        duration = dur_result.stdout.strip()
        entry["duration_sec"] = duration
        print(f"      Duration: {duration}s")

        dur_float = float(duration)
        if dur_float < 11:
            print(f"      Video too short ({dur_float}s), skipping download")
            entry["error"] = f"Video too short: {dur_float}s"
            results.append(entry)
            continue

        # Step 2: Download last 10 seconds
        print(f"  [2] Downloading last 10 seconds...")
        dl_result = subprocess.run(
            [
                "yt-dlp", "--cookies", COOKIES,
                "--download-sections", f"*{max(0, dur_float-10)}-{dur_float}",
                "--force-keyframes-at-cuts",
                "-f", "worst[ext=mp4]",
                "-o", vid_mp4,
                url
            ],
            capture_output=True, text=True, timeout=120
        )
        if dl_result.returncode != 0:
            raise RuntimeError(f"yt-dlp download failed: {dl_result.stderr.strip()}")
        entry["downloaded"] = True
        print(f"      Downloaded to {vid_mp4}")

        # Step 3: Extract first frame
        print(f"  [3] Extracting frame...")
        ff_result = subprocess.run(
            [
                "ffmpeg", "-i", vid_mp4,
                "-vf", "select=eq(n,0)",
                "-vsync", "vfr",
                "-q:v", "2",
                frame_png,
                "-y"
            ],
            capture_output=True, text=True, timeout=30
        )
        if ff_result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {ff_result.stderr.strip()}")
        print(f"      Frame saved to {frame_png}")

        # Step 4: OCR
        print(f"  [4] Running EasyOCR...")
        ocr_result = subprocess.run(
            [sys.executable, "-c", """
import easyocr, sys
r = easyocr.Reader(['ar','en'], gpu=False)
results = r.readtext(sys.argv[1])
for t in results:
    print('|'.join([t[1]]))
""", frame_png],
            capture_output=True, text=True, timeout=180
        )
        if ocr_result.returncode != 0:
            raise RuntimeError(f"EasyOCR failed: {ocr_result.stderr.strip()}")

        ocr_lines = [l.strip() for l in ocr_result.stdout.split('\n') if l.strip()]
        ocr_text = " | ".join(ocr_lines) if ocr_lines else ""
        entry["ocr_text"] = ocr_text
        print(f"      OCR text: {ocr_text[:200]}")

        # Step 5: Search for keywords
        matches_found = []
        for term in SEARCH_TERMS:
            if term.lower() in ocr_text.lower():
                matches_found.append(term)
        entry["matches"] = matches_found
        if matches_found:
            print(f"  [5] *** MATCHES FOUND: {matches_found}")
        else:
            print(f"  [5] No matches found")

    except Exception as e:
        entry["error"] = str(e)
        print(f"  ERROR: {e}")

    results.append(entry)

    # Cleanup temp files for this video
    for f in [vid_mp4, frame_png]:
        try:
            if os.path.exists(f):
                os.remove(f)
        except:
            pass

# Save results
output = {"videos": results}
with open(RESULTS_FILE, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n{'='*60}")
print(f"Results saved to {RESULTS_FILE}")

# Summary
match_count = sum(1 for r in results if r.get("matches"))
print(f"\nSUMMARY:")
print(f"  Total videos processed: {len(results)}")
print(f"  Videos with matches: {match_count}")
for r in results:
    status = "MATCH!" if r.get("matches") else ("ERROR" if r.get("error") else "OK")
    print(f"  [{r['num']}] {r['video_id']} ({r.get('duration_sec','?')}s) - {status}")
    if r.get("matches"):
        print(f"         Terms: {r['matches']}")
    if r.get("error"):
        print(f"         Error: {r['error']}")
