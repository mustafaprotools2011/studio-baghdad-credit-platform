#!/usr/bin/env python3
"""Scan MCP TV Music videos with EasyOCR for مصطفى كمال"""
import json, subprocess, os, sys

COOKIES = "/opt/data/mustafa-mixing-archive/cookies.txt"
VIDEOS_FILE = "/opt/data/mustafa-mixing-archive/scan_queues/mcp_videos.txt"
OUTPUT_FILE = "/opt/data/mustafa-mixing-archive/scan_queues/mcp_ocr_results.json"
SEARCH_TERMS = ["مصطفى كمال", "مهندس صوت", "مكس", "ماستر"]

def run_cmd(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return p.stdout.strip(), p.stderr.strip(), p.returncode

# Read video list
videos = []
with open(VIDEOS_FILE, encoding="utf-8") as f:
    for idx, line in enumerate(f, 1):
        line = line.strip()
        if line and "|" in line:
            parts = line.split("|", 2)
            vid = parts[0]
            title = parts[1]
            videos.append({"idx": idx, "id": vid, "title": title})
            if idx >= 10:
                break

results = []

for v in videos:
    idx = v["idx"]
    vid = v["id"]
    title = v["title"]
    url = f"https://www.youtube.com/watch?v={vid}"
    
    print(f"\n{'='*60}")
    print(f"[{idx}] Processing {vid} - {title}")
    
    result = {"index": idx, "id": vid, "title": title, "duration": None, "ocr_text": "", "matches": [], "error": None}
    
    # Step 1: Get duration
    print("  Step 1: Getting duration...")
    out, err, rc = run_cmd([
        "yt-dlp", "--cookies", COOKIES,
        "--print", "%(duration)s",
        "--skip-download", url
    ])
    if rc != 0 or not out:
        print(f"  FAILED to get duration: {err}")
        result["error"] = f"duration: {err[:200]}"
        results.append(result)
        continue
    
    duration = int(out)
    result["duration"] = duration
    print(f"  Duration: {duration}s")
    
    # Step 2: Download last 10 seconds
    # For videos shorter than 10s, adjust
    start_sec = max(0, duration - 10)
    download_section = f"*{start_sec}-{duration}"
    print(f"  Step 2: Downloading section {download_section}...")
    
    out, err, rc = run_cmd([
        "yt-dlp", "--cookies", COOKIES,
        "--download-sections", download_section,
        "--force-keyframes-at-cuts",
        "-f", "worst[ext=mp4]",
        "-o", "/tmp/mcp_vid.mp4",
        url
    ])
    if rc != 0:
        print(f"  FAILED download: {err}")
        result["error"] = f"download: {err[:200]}"
        results.append(result)
        continue
    print("  Downloaded OK")
    
    # Step 3: Extract frame
    print("  Step 3: Extracting frame...")
    out, err, rc = run_cmd([
        "ffmpeg", "-i", "/tmp/mcp_vid.mp4",
        "-vf", "select=eq(n,0)",
        "-vsync", "vfr", "-q:v", "2",
        "/tmp/mcp_frame.png", "-y"
    ])
    if rc != 0:
        print(f"  FAILED ffmpeg: {err}")
        result["error"] = f"ffmpeg: {err[:200]}"
        results.append(result)
        continue
    print("  Frame extracted")
    
    # Step 4: EasyOCR
    print("  Step 4: Running EasyOCR...")
    import easyocr
    reader = easyocr.Reader(['ar', 'en'], gpu=False)
    texts = reader.readtext('/tmp/mcp_frame.png')
    ocr_text = " | ".join([t[1] for t in texts])
    result["ocr_text"] = ocr_text
    print(f"  OCR: {ocr_text[:200]}")
    
    # Step 5: Search for terms
    matches = []
    for term in SEARCH_TERMS:
        if term in ocr_text:
            matches.append(term)
            print(f"  >>> MATCH FOUND: {term}")
    
    if not matches:
        print("  No matches found")
    
    result["matches"] = matches
    results.append(result)
    
    # Cleanup
    for f in ["/tmp/mcp_vid.mp4", "/tmp/mcp_frame.png"]:
        try:
            os.remove(f)
        except:
            pass

# Save results
output = {"channel": "MCP TV Music", "total": len(results), "results": results}
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n{'='*60}")
print(f"Done. {len(results)} videos scanned.")
print(f"Results saved to {OUTPUT_FILE}")
