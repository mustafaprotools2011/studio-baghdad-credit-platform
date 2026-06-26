import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

try:
    import pytesseract
    from PIL import Image
except:
    print("المكتبات مفقودة")
    sys.exit(1)

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

parser = argparse.ArgumentParser()
parser.add_argument("--channel", "-c")
parser.add_argument("--max", type=int, default=30)
parser.add_argument("--names", default="مصطفى كمال,مهندس صوت,مكس,ماستر,مصطفى,كمال")
args = parser.parse_args()

print("MUSTAFA MIXING OCR Scanner (Tesseract)")

out = Path("ocr_results")
out.mkdir(exist_ok=True)
names = [n.strip() for n in args.names.split(",")]

ch_url = "https://www.youtube.com/@" + args.channel
print("\nقناة:", ch_url)
r = subprocess.run(["yt-dlp.exe", "--flat-playlist", "--print", "%(id)s", "--playlist-end", str(args.max), ch_url], capture_output=True, text=True, timeout=60)
urls = ["https://www.youtube.com/watch?v=" + v.strip() for v in r.stdout.strip().split("\n") if v.strip()]
print("بمسح", len(urls), "فيديو...")

YT_BASE = ["yt-dlp.exe", "--js-runtimes", "node"]

def get_duration(url, cookies="cookies.txt"):
    try:
        cmd = YT_BASE + (["--cookies", cookies] if os.path.exists(cookies) else [])
        cmd += ["--print", "%(duration)s", "--skip-download", url]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return int(float(r.stdout.strip()))
    except:
        return None

def scan_video(url, out_dir, cookies="cookies.txt"):
    vid = url.split("v=")[-1].split("&")[0] if "v=" in url else url.split("/")[-1][:11]
    dur = get_duration(url, cookies)
    if not dur or dur < 15:
        return None
    start = max(0, dur - 10)
    mp4 = os.path.join(out_dir, f"{vid}_outro.mp4")
    cmd = YT_BASE + ["--cookies", cookies, "--download-sections", f"*{start}-{dur}", "--force-keyframes-at-cuts", "-f", "worst[ext=mp4]", "-o", mp4, url]
    subprocess.run(cmd, capture_output=True, text=True, timeout=40)
    if not os.path.exists(mp4):
        return None
    frame = os.path.join(out_dir, f"{vid}_frame.png")
    subprocess.run(["ffmpeg", "-i", mp4, "-vf", "select=eq(n,0)", "-vsync", "vfr", "-q:v", "2", frame, "-y"], capture_output=True, text=True, timeout=10)
    if not os.path.exists(frame):
        return None
    try:
        img = Image.open(frame)
        texts = pytesseract.image_to_string(img, lang="ara+eng").strip().split("\n")
        texts = [t.strip() for t in texts if t.strip()]
    except:
        texts = []
    for f in [mp4, frame]:
        try: os.remove(f)
        except: pass
    return {"vid": vid, "texts": texts}

matches = []
for i, u in enumerate(urls, 1):
    print("[" + str(i) + "/" + str(len(urls)) + "]", end=" ", flush=True)
    res = scan_video(u, str(out))
    if res:
        t = " | ".join(res["texts"])
        print("نص:", t[:100])
        for txt in res["texts"]:
            for n in names:
                if n.lower() in txt.lower():
                    print("تم العثور:", txt)
                    matches.append({"url": u, "text": txt})
    else:
        print("تخطي")
    time.sleep(1)

print("\nتم.", len(matches), "نتيجة")
for m in matches:
    print(" ", m["url"], ":", m["text"])

with open(out / "scan_report.json", "w", encoding="utf-8") as f:
    json.dump({"matches": matches}, f, ensure_ascii=False, indent=2)
print("\nالتقرير:", out / "scan_report.json")
