#!/usr/bin/env python3
"""
MUSTAFA MIXING — OCR Credit Scanner v1.0
Extracts text from YouTube video frames to discover "Mustafa Kamal" / "مصطفى كمال" credits.

Usage:
  1. First get a cookies.txt file from your browser (see instructions below)
  2. Place video URLs in urls.txt (one per line) OR pass as argument
  3. Run: python3 ocr_credit_scanner.py

Cookies export instructions:
  - Chrome: Install "Get cookies.txt LOCALLY" extension
  - Firefox: Install "cookies.txt" extension
  - Export cookies for youtube.com, save as cookies.txt
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Check if yt-dlp is available
def check_dependencies():
    """Check all required tools are available."""
    missing = []
    
    # Check yt-dlp
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True)
    except FileNotFoundError:
        missing.append("yt-dlp (install: pip install yt-dlp)")
    
    # Check EasyOCR
    try:
        import easyocr
    except ImportError:
        missing.append("easyocr (install: pip install easyocr)")
    
    if missing:
        print("❌ Missing dependencies:")
        for m in missing:
            print(f"   - {m}")
        print("\nInstall with: pip install yt-dlp easyocr pillow")
        return False
    
    # Check cookies.txt
    if not os.path.exists("cookies.txt"):
        print("⚠️  No cookies.txt found. Videos may be blocked.")
        print("   Export cookies from your browser and save as cookies.txt")
        print("   Instructions: youtube.com → export cookies → save as cookies.txt")
    
    return True


def extract_frames_from_youtube(video_url, output_dir, num_frames=5, cookies_file="cookies.txt"):
    """
    Download key frames from a YouTube video using yt-dlp + ffmpeg.
    
    Strategy: Extract frames from the last 30 seconds (where credits usually appear).
    """
    import easyocr
    
    video_id = video_url.split("v=")[-1].split("&")[0] if "v=" in video_url else video_url.split("/")[-1]
    
    # First get video info
    cmd = ["yt-dlp", "--print", "%(duration)s", video_url]
    if os.path.exists(cookies_file):
        cmd = ["yt-dlp", "--cookies", cookies_file, "--print", "%(duration)s", video_url]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        duration = float(result.stdout.strip())
    except:
        print(f"⚠️  Could not get duration for {video_id}, assuming 240s")
        duration = 240
    
    print(f"   Duration: {duration:.0f}s")
    
    # Extract frames from last 30s (or last 15% for short videos)
    extract_duration = min(30, duration * 0.15)
    start_time = max(0, duration - extract_duration)
    
    output_pattern = os.path.join(output_dir, f"{video_id}_frame_%03d.png")
    
    # Download frame sequence from the credits section
    cmd = [
        "yt-dlp", 
        "--cookies", cookies_file,
        "--download-sections", f"*{start_time}-{duration}",
        "--force-keyframes-at-cuts",
        "--downloader", "ffmpeg",
        "-o", output_pattern,
        "--write-thumbnail",
        "--skip-download",
        video_url
    ] if os.path.exists(cookies_file) else [
        "yt-dlp",
        "--download-sections", f"*{start_time}-{duration}",
        "--force-keyframes-at-cuts",
        "--downloader", "ffmpeg",
        "-o", output_pattern,
        "--write-thumbnail",
        "--skip-download",
        video_url
    ]
    
    print(f"   Extracting frames ({start_time:.0f}s → {duration:.0f}s)...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    
    frames = sorted(glob(os.path.join(output_dir, f"{video_id}_frame_*.png")))
    thumbs = sorted(glob(os.path.join(output_dir, f"{video_id}*.webp")) + glob(os.path.join(output_dir, f"{video_id}*.jpg")))
    
    all_images = frames + thumbs
    print(f"   Got {len(all_images)} images to analyze")
    return all_images


def extract_frames_ffmpeg(video_url, output_dir, num_frames=8):
    """
    Alternative: Use ffmpeg directly on a downloaded video segment.
    First download a small segment containing the outro/credits.
    """
    video_id = video_url.split("v=")[-1].split("&")[0] if "v=" in video_url else video_url.split("/")[-1]
    
    # Try to get the video info first
    cmd = ["yt-dlp", "--cookies", "cookies.txt", "--print", "%(duration)s", video_url]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        duration = float(result.stdout.strip())
    except:
        print(f"   ⚠️  Could not get duration, trying without cookies...")
        try:
            # Try to use yt-dlp's internal extractor with iOS client
            cmd = ["yt-dlp", 
                   "--extractor-args", "youtube:player_client=ios",
                   "--print", "%(duration)s", video_url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            duration = float(result.stdout.strip())
        except:
            print(f"   ⚠️  Could not get duration at all")
            return []
    
    print(f"   Duration: {duration:.0f}s")
    
    # Download only last 20 seconds of video at low quality (fast download)
    extract_start = max(0, duration - 20)
    temp_video = os.path.join(output_dir, f"{video_id}_temp.mp4")
    
    cmd = [
        "yt-dlp",
        "--cookies", "cookies.txt",
        "-f", "worst[ext=mp4]",
        "--download-sections", f"*{extract_start}-{duration}",
        "--force-keyframes-at-cuts",
        "-o", temp_video,
        video_url
    ]
    
    print(f"   Downloading last 20s (low quality)...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if os.path.exists(temp_video) and os.path.getsize(temp_video) > 1000:
            print(f"   Downloaded: {os.path.getsize(temp_video)//1024}KB")
            
            # Extract frames with ffmpeg
            frame_pattern = os.path.join(output_dir, f"{video_id}_fr_%03d.png")
            cmd2 = [
                "ffmpeg", "-i", temp_video,
                "-vf", f"fps=1/{20//num_frames}",
                "-frames:v", str(num_frames),
                "-q:v", "2",
                frame_pattern,
                "-y"
            ]
            subprocess.run(cmd2, capture_output=True, text=True, timeout=30)
            
            # Clean up temp video
            os.remove(temp_video)
            
            frames = sorted(glob(os.path.join(output_dir, f"{video_id}_fr_*.png")))
            print(f"   Extracted {len(frames)} frames")
            return frames
    except Exception as e:
        print(f"   ⚠️  Error: {e}")
        # Clean up
        if os.path.exists(temp_video):
            os.remove(temp_video)
    
    return []


def ocr_analysis(reader, image_paths, known_names):
    """
    Run OCR on all extracted images, looking for known names.
    Returns detected matches.
    """
    matches = []
    all_text = ""
    
    for img_path in image_paths:
        if not os.path.exists(img_path) or os.path.getsize(img_path) < 100:
            continue
        
        try:
            # Run EasyOCR
            results = reader.readtext(img_path)
            
            text_found = " | ".join([r[1] for r in results])
            all_text += text_found + "\n"
            
            # Check for name matches
            for (bbox, text, confidence) in results:
                text_clean = text.strip()
                
                for name in known_names:
                    if name.lower() in text_clean.lower():
                        matches.append({
                            "image": os.path.basename(img_path),
                            "text": text_clean,
                            "confidence": float(confidence),
                            "matched_name": name
                        })
                        print(f"      ✅ MATCH! '{text_clean}' (conf: {confidence:.2f})")
            
            # Print all text for manual review
            print(f"      Text: {text_found[:200]}")
            
        except Exception as e:
            print(f"      ⚠️  OCR error on {os.path.basename(img_path)}: {e}")
    
    return matches, all_text


def search_channel_videos(channel_url, max_videos=50):
    """Get list of video URLs from a YouTube channel."""
    cmd = [
        "yt-dlp",
        "--cookies", "cookies.txt",
        "--flat-playlist",
        "--print", "%(id)s",
        "--playlist-end", str(max_videos),
        channel_url
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        video_ids = [v.strip() for v in result.stdout.strip().split("\n") if v.strip()]
        print(f"   Found {len(video_ids)} videos from channel")
        return [f"https://www.youtube.com/watch?v={vid}" for vid in video_ids]
    except Exception as e:
        print(f"   ⚠️  Error fetching channel: {e}")
        return []


def glob(pattern):
    import glob as g
    return g.glob(pattern)


def main():
    parser = argparse.ArgumentParser(description="MUSTAFA MIXING OCR Credit Scanner")
    parser.add_argument("--url", "-u", help="Single video URL to scan")
    parser.add_argument("--channel", "-c", help="Channel URL to scan (e.g., @AlRemas)")
    parser.add_argument("--urls-file", "-f", help="File with video URLs (one per line)")
    parser.add_argument("--output", "-o", default="ocr_results", help="Output directory")
    parser.add_argument("--names", "-n", default="Mustafa Kamal,مصطفى كمال", 
                        help="Comma-separated names to search for")
    parser.add_argument("--max-videos", type=int, default=20, 
                        help="Max videos to scan from a channel")
    
    args = parser.parse_args()
    
    known_names = [n.strip() for n in args.names.split(",")]
    
    # Setup
    check_dependencies()
    
    import easyocr
    print("🚀 Initializing EasyOCR (Arabic + English)...")
    reader = easyocr.Reader(["ar", "en"], gpu=False)
    print("✅ OCR Ready!")
    
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    
    # Collect video URLs
    urls = []
    if args.url:
        urls.append(args.url)
    if args.urls_file:
        with open(args.urls_file) as f:
            urls.extend([line.strip() for line in f if line.strip()])
    if args.channel:
        channel_url = args.channel
        if not channel_url.startswith("http"):
            channel_url = f"https://www.youtube.com/@{channel_url}"
        print(f"\n📺 Scanning channel: {channel_url}")
        channel_videos = search_channel_videos(channel_url, args.max_videos)
        urls.extend(channel_videos)
    
    if not urls:
        print("❌ No URLs provided. Use --url, --channel, or --urls-file")
        print("\nExample:")
        print("  python3 ocr_credit_scanner.py --channel AlRemas")
        print("  python3 ocr_credit_scanner.py --url https://youtube.com/watch?v=xxx")
        print("  python3 ocr_credit_scanner.py --urls-file urls.txt")
        sys.exit(1)
    
    print(f"\n🎯 Scanning {len(urls)} videos for: {', '.join(known_names)}")
    print("="*60)
    
    all_matches = []
    
    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] Processing: {url[:60]}...")
        
        # Extract frames
        frames = extract_frames_ffmpeg(url, str(output_dir))
        
        if not frames:
            print("   ⚠️  Could not extract frames, trying thumbnails...")
            # Try just the thumbnail
            thumb = os.path.join(str(output_dir), f"thumb_{url.split('v=')[-1][:11]}.jpg")
            cmd = ["yt-dlp", "--cookies", "cookies.txt", "--write-thumbnail", 
                   "-o", thumb.replace(".jpg", ""), "--skip-download", "--convert-thumbnails", "jpg", url]
            subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            frames = sorted(glob(str(output_dir) + f"/thumb_{url.split('v=')[-1][:11]}*.jpg"))
            if frames:
                print(f"   Got {len(frames)} thumbnails")
            else:
                print("   ❌ No frames available for this video")
                continue
        
        # OCR analysis
        matches, all_text = ocr_analysis(reader, frames, known_names)
        
        if matches:
            all_matches.append({
                "url": url,
                "video_id": url.split("v=")[-1].split("&")[0] if "v=" in url else url.split("/")[-1],
                "matches": matches,
                "all_text": all_text[:500]
            })
        
        # Small delay to avoid rate limiting
        time.sleep(1)
    
    # Results
    print("\n" + "="*60)
    print(f"📊 SCAN COMPLETE: {len(urls)} videos, {len(all_matches)} matches found")
    print("="*60)
    
    if all_matches:
        for m in all_matches:
            print(f"\n🎬 {m['url']}")
            for match in m['matches']:
                print(f"   ✅ {match['text']} (confidence: {match['confidence']:.2f})")
    else:
        print("❌ No matching credits found.")
    
    # Save results
    results_file = output_dir / "scan_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump({
            "scanned_urls": len(urls),
            "matches_found": len(all_matches),
            "known_names": known_names,
            "results": all_matches
        }, f, ensure_ascii=False, indent=2)
    print(f"\n📁 Results saved to: {results_file}")


if __name__ == "__main__":
    main()
