#!/usr/bin/env python3
"""
MUSTAFA MIXING — OCR Credit Scanner v2.0 (Windows/Linux)
Scans YouTube videos for "Mustafa Kamal" / "مصطفى كمال" credits inside video frames.

Usage:
  python ocr_credit_scanner.py --channel ShababTV
  python ocr_credit_scanner.py --url https://youtube.com/watch?v=xxx
  python ocr_credit_scanner.py --urls-file urls.txt
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

__version__ = "2.0"

def check_deps():
    missing = []
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True)
    except FileNotFoundError:
        missing.append("yt-dlp (pip install yt-dlp)")
    try:
        import easyocr
        import cv2
    except ImportError:
        missing.append("easyocr + opencv (pip install easyocr opencv-python)")
    if missing:
        print("❌ Missing:", ", ".join(missing))
        print("   pip install yt-dlp easyocr opencv-python pillow torch torchvision --index-url https://download.pytorch.org/whl/cu121")
        return False
    return True

def build_yt_cmd(video_url, cookies="cookies.txt"):
    cmd = ["yt-dlp"]
    if os.path.exists(cookies):
        cmd += ["--cookies", cookies]
    cmd += [video_url]
    return cmd

def get_video_duration(video_url, cookies="cookies.txt"):
    try:
        cmd = ["yt-dlp"]
        if os.path.exists(cookies):
            cmd += ["--cookies", cookies]
        cmd += ["--print", "%(duration)s", "--skip-download", video_url]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return int(float(r.stdout.strip()))
    except:
        return None

def download_outro(video_url, out_dir, cookies="cookies.txt"):
    """Download last 8 seconds of video for credit OCR."""
    vid = video_url.split("v=")[-1].split("&")[0] if "v=" in video_url else video_url.split("/")[-1][:11]
    duration = get_video_duration(video_url, cookies)
    if not duration or duration < 15:
        return None, vid
    start = max(0, duration - 10)
    out_path = os.path.join(out_dir, f"{vid}_outro.mp4")
    cmd = ["yt-dlp"]
    if os.path.exists(cookies):
        cmd += ["--cookies", cookies]
    cmd += ["--download-sections", f"*{start}-{duration}",
            "--force-keyframes-at-cuts", "-f", "worst[ext=mp4]", "-o", out_path, video_url]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
    if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
        return out_path, vid
    return None, vid

def extract_frame(video_path, output_dir, vid):
    frame_path = os.path.join(output_dir, f"{vid}_frame.png")
    subprocess.run(["ffmpeg", "-i", video_path, "-vf", "select=eq(n\\,0)", "-vsync", "vfr",
                    "-q:v", "2", frame_path, "-y"], capture_output=True, text=True, timeout=10)
    if os.path.exists(frame_path):
        return frame_path
    return None

def scan_video(video_url, reader, output_dir, cookies="cookies.txt"):
    """Full pipeline: download outro -> extract frame -> OCR -> cleanup."""
    print(f"  📥 تحميل outro...", end=" ", flush=True)
    video_path, vid = download_outro(video_url, output_dir, cookies)
    if not video_path:
        print("❌ فشل")
        return None
    
    print(f"📸 استخراج فريم...", end=" ", flush=True)
    frame_path = extract_frame(video_path, output_dir, vid)
    if not frame_path:
        print("❌ لايوجد فريم")
        return None
    
    print(f"🔍 OCR...", end=" ", flush=True)
    results = reader.readtext(frame_path)
    texts = [r[1] for r in results]
    
    for f in [video_path, frame_path]:
        try:
            os.remove(f)
        except:
            pass
    
    print(f"تم ({len(texts)} نص)")
    return {"video_id": vid, "text_found": texts, "raw_results": [(r[1], float(r[2])) for r in results]}

def search_channel_url(channel_name):
    url = f"https://www.youtube.com/@{channel_name}"
    try:
        r = subprocess.run(["yt-dlp", "--flat-playlist", "--print", "%(id)s",
                            "--playlist-end", "1", url], capture_output=True, text=True, timeout=15)
        if r.returncode == 0 and r.stdout.strip():
            return url
    except:
        pass
    url = f"https://www.youtube.com/c/{channel_name}"
    try:
        r = subprocess.run(["yt-dlp", "--flat-playlist", "--print", "%(id)s",
                            "--playlist-end", "1", url], capture_output=True, text=True, timeout=15)
        if r.returncode == 0 and r.stdout.strip():
            return url
    except:
        pass
    return None

def get_channel_videos(channel_url, max_videos=50):
    r = subprocess.run(
        ["yt-dlp", "--flat-playlist", "--print", "%(id)s", "--playlist-end", str(max_videos), channel_url],
        capture_output=True, text=True, timeout=60)
    ids = [v.strip() for v in r.stdout.strip().split("\n") if v.strip()]
    return [f"https://www.youtube.com/watch?v={vid}" for vid in ids]

def main():
    parser = argparse.ArgumentParser(description="MUSTAFA MIXING OCR Scanner")
    parser.add_argument("--url", "-u", help="Single video URL")
    parser.add_argument("--channel", "-c", help="Channel name or @handle")
    parser.add_argument("--urls-file", "-f", help="File with URLs (one per line)")
    parser.add_argument("--output", "-o", default="ocr_results", help="Output folder")
    parser.add_argument("--max-videos", type=int, default=50)
    parser.add_argument("--cookies", default="cookies.txt", help="Cookies file path")
    parser.add_argument("--names", default="Mustafa Kamal,مصطفى كمال,مهندس صوت,مكس,ماستر,مصطفى,كمال",
                        help="Comma-separated names to search for")
    args = parser.parse_args()
    
    if not check_deps():
        sys.exit(1)
    
    import torch
    import easyocr
    
    gpu = torch.cuda.is_available()
    known_names = [n.strip() for n in args.names.split(",")]
    
    print(f"\n🚀 MUSTAFA MIXING OCR Scanner v{__version__}")
    print(f"   GPU: {'✅ متوفر (سريع!)' if gpu else '❌ CPU فقط (بطيء)'}")
    
    reader = easyocr.Reader(["ar", "en"], gpu=gpu)
    print(f"   OCR: جاهز")
    
    out_dir = Path(args.output)
    out_dir.mkdir(exist_ok=True)
    
    urls = []
    if args.url:
        urls.append(args.url)
    if args.urls_file:
        with open(args.urls_file, encoding="utf-8") as f:
            urls.extend([l.strip() for l in f if l.strip()])
    if args.channel:
        print(f"\n📺 البحث عن القناة: @{args.channel}")
        ch_url = search_channel_url(args.channel)
        if not ch_url:
            print(f"   ❌ ما لقيت القناة @{args.channel}")
            sys.exit(1)
        print(f"   ✅ وجدت: {ch_url}")
        urls.extend(get_channel_videos(ch_url, args.max_videos))
    
    if not urls:
        print("❌ ما في فيديوهات. استخدم --url او --channel او --urls-file")
        sys.exit(1)
    
    print(f"\n🎯 بمسح {len(urls)} فيديو عن: {', '.join(known_names)}")
    print("="*60)
    
    all_matches = []
    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] {url[:60]}...")
        result = scan_video(url, reader, str(out_dir), args.cookies)
        if result:
            text_all = " | ".join(result["text_found"])
            print(f"   النص: {text_all[:200]}")
            
            matched = False
            for t in result["text_found"]:
                for name in known_names:
                    if name.lower() in t.lower():
                        print(f"   ✅✅✅ تم العثور! '{t}' -> '{name}'")
                        all_matches.append({
                            "video_id": result["video_id"],
                            "url": url,
                            "text": t,
                            "matched_name": name
                        })
                        matched = True
                        break
                if matched:
                    break
        time.sleep(1)
    
    print("\n" + "="*60)
    print(f"📊 تم المسح: {len(urls)} فيديو, {len(all_matches)} نتيجة")
    if all_matches:
        print("\n✅ النتائج:")
        for m in all_matches:
            print(f"   🎬 {m['url']}")
            print(f"      {m['text']} -> {m['matched_name']}")
    else:
        print("\n❌ ما لقينا اسم مصطفى كمال في هذي الفيديوهات")
    
    report = {"version": __version__, "videos_scanned": len(urls), "matches": all_matches,
              "names_searched": known_names, "gpu": gpu}
    with open(out_dir / "scan_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n📁 التقرير: {(out_dir / 'scan_report.json').resolve()}")
    
    if all_matches:
        print("\n💡 أرسل لي ملف scan_report.json عشان أضيف النتائج للقاعدة!")

if __name__ == "__main__":
    main()
