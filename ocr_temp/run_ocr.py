#!/usr/bin/env python3
"""Smart OCR on all frames for AlRemas video - searching for مصطفى كمال and related terms."""

import json
import os
import glob
import sys
import time

# Install easyocr if needed
try:
    import easyocr
except ImportError:
    os.system("uv pip install easyocr --quiet")
    import easyocr

PYTHON = "/opt/data/mustafa-mixing-archive/.venv/bin/python3"
WORKDIR = "/opt/data/mustafa-mixing-archive/ocr_temp"
OUTPUT = os.path.join(WORKDIR, "alremas_ocr_final.json")

# Target search terms (Arabic and English)
TARGET_TERMS = [
    "مصطفى كمال",
    "مصطفى",
    "كمال",
    "Mustafa Kamal",
    "Mustafa",
    "Kamal",
    "مكس",
    "ماستر",
    "مهندس صوت",
    "مهندس",
    "master",
    "mix",
    "mixing",
]

def collect_all_frames():
    """Collect all frame PNGs from ocr_temp directory."""
    patterns = [
        "hd_key_*.png",
        "first_fr_*.png",
        "frame_*.png",
        "every5s_*.png",
    ]
    all_frames = []
    for pat in patterns:
        matches = sorted(glob.glob(os.path.join(WORKDIR, pat)))
        all_frames.extend(matches)
    print(f"Total frames collected: {len(all_frames)}")
    return all_frames

def search_text(text, frame_name):
    """Search for target terms in OCR text."""
    results = []
    text_lower = text.lower()
    for term in TARGET_TERMS:
        if term.lower() in text_lower:
            # Find context around match
            idx = text_lower.find(term.lower())
            start = max(0, idx - 40)
            end = min(len(text), idx + len(term) + 40)
            context = text[start:end]
            results.append({
                "term": term,
                "context": context,
                "frame": frame_name
            })
    return results

def main():
    print("=" * 60)
    print("AlRemas OCR Scan - searching for مصطفى كمال and related")
    print("=" * 60)

    # Check if output already exists
    if os.path.exists(OUTPUT):
        print(f"Output file {OUTPUT} already exists. Loading existing results...")
        with open(OUTPUT, "r", encoding="utf-8") as f:
            existing = json.load(f)
        print(f"Existing results contain {len(existing.get('matches', []))} matches across {len(existing.get('frames_processed', []))} frames")
        # Ask whether to redo
        print("Will re-run to capture any new frames.")

    frames = collect_all_frames()
    if not frames:
        print("ERROR: No frame images found!")
        sys.exit(1)

    # Initialize EasyOCR reader (Arabic + English)
    print("\nInitializing EasyOCR reader (ar + en)...")
    t0 = time.time()
    reader = easyocr.Reader(['ar', 'en'], gpu=False)
    print(f"Reader loaded in {time.time()-t0:.1f}s")

    all_results = {
        "video": "AlRemas hm-OZGH6aoY",
        "video_file": "full_hd.mp4",
        "video_duration_sec": 334,
        "search_terms": TARGET_TERMS,
        "frames_processed": [],
        "matches": [],
        "frames_with_matches": [],
        "total_frames": len(frames)
    }

    processed = 0
    match_count = 0
    frame_match_ids = set()

    for fpath in frames:
        fname = os.path.basename(fpath)
        processed += 1

        # Progress
        if processed % 10 == 0 or processed == 1 or processed == len(frames):
            print(f"[{processed}/{len(frames)}] OCR on {fname}...")

        try:
            t1 = time.time()
            raw_result = reader.readtext(fpath, detail=0, paragraph=True)
            elapsed = time.time() - t1
            # Handle both list-of-strings and list-of-dicts return formats
            if raw_result and isinstance(raw_result[0], dict):
                full_text = " ".join(r.get("text", "") for r in raw_result) if raw_result else ""
            elif raw_result:
                full_text = " ".join(str(r) for r in raw_result) if raw_result else ""
            else:
                full_text = ""
            all_results["frames_processed"].append({
                "frame": fname,
                "text": full_text[:500],  # truncate for storage
                "ocr_time_sec": round(elapsed, 2)
            })

            if full_text.strip():
                matches = search_text(full_text, fname)
                if matches:
                    match_count += len(matches)
                    frame_match_ids.add(fname)
                    all_results["matches"].extend(matches)
                    print(f"  >>> MATCH in {fname}: {[m['term'] for m in matches]}")
                    print(f"  >>> Context: {matches[0]['context'][:100]}")

        except Exception as e:
            print(f"  ERROR on {fname}: {e}")
            all_results["frames_processed"].append({
                "frame": fname,
                "error": str(e)
            })

    all_results["frames_with_matches"] = sorted(list(frame_match_ids))
    all_results["total_matches"] = match_count
    all_results["frames_with_match_count"] = len(frame_match_ids)

    # Save results
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print(f"OCR COMPLETE")
    print(f"Frames processed: {len(all_results['frames_processed'])}")
    print(f"Total matches found: {match_count}")
    print(f"Frames with matches: {len(frame_match_ids)}")
    if frame_match_ids:
        print(f"Matching frames: {sorted(list(frame_match_ids))}")
    print(f"Results saved to: {OUTPUT}")
    print("=" * 60)

if __name__ == "__main__":
    main()
