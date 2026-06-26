#!/usr/bin/env python3
"""
MUSTAFA MIXING — OCR Credit Scanner
=====================================
مسح آخر ثواني فيديوهات يوتيوب للبحث عن أسماء في شريط الإنتاج.

الاستخدام:
  # مسح قناة:
  python ocr_credit_scanner.py --channel ShababTV --max 30

  # مسح من ملف URLs:
  python ocr_credit_scanner.py --urls-file urls.txt

  # ملف URLs.txt مثال:
  https://www.youtube.com/watch?v=VIDEO_ID_1
  https://www.youtube.com/watch?v=VIDEO_ID_2
  # سطر يبدأ بـ # هو تعليق

الإعدادات:
  --tail N      عدد الثواني من النهاية (10-15، افتراضي 15)
  --keywords    كلمات مفتاحية مفصولة بفاصلة
  --output      مجلد النتائج (افتراضي ocr_results)
  --cookies     ملف الكوكيز (افتراضي cookies.txt)
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# ---------- اعتماديات اختيارية (تُفحص لاحقاً) ----------

YT_DLP = None           # يُعيَّن بعد find_ytdlp()

# ---------- كلمات البحث المفتاحية ----------
DEFAULT_KEYWORDS = "مصطفى كمال,مصطفى,مهندس,مكس,ماستر"

# ---------- أدوات مساعدة ----------

def find_ytdlp():
    """تحديد مسار yt-dlp"""
    for candidate in [
        "yt-dlp",
        "/opt/data/mustafa-mixing-archive/.venv/bin/yt-dlp",
        os.path.expanduser("~/.local/bin/yt-dlp"),
    ]:
        try:
            r = subprocess.run([candidate, "--version"],
                               capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                return candidate
        except Exception:
            continue
    return None


def check_deps():
    """فحص الاعتماديات الأساسية"""
    global YT_DLP
    YT_DLP = find_ytdlp()
    if not YT_DLP:
        print("❌ yt-dlp غير موجود. اركب:")
        print("   pip install yt-dlp")
        return False

    try:
        import easyocr
    except ImportError:
        print("❌ easyocr غير موجود. اركب:")
        print("   pip install easyocr opencv-python")
        return False

    try:
        import cv2
    except ImportError:
        print("❌ opencv-python غير موجود. اركب:")
        print("   pip install opencv-python")
        return False

    try:
        import numpy as np
    except ImportError:
        print("❌ numpy غير موجود. اركب:")
        print("   pip install numpy")
        return False

    # ffmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=3)
    except Exception:
        print("❌ ffmpeg غير موجود")
        return False

    return True


def extract_video_id(url):
    """استخراج YouTube video ID من أي صيغة URL"""
    # youtube.com/watch?v=ID
    m = re.search(r'[?&]v=([a-zA-Z0-9_-]{11})', url)
    if m:
        return m.group(1)
    # youtu.be/ID
    m = re.search(r'youtu\.be/([a-zA-Z0-9_-]{11})', url)
    if m:
        return m.group(1)
    # shorts/ID
    m = re.search(r'/shorts/([a-zA-Z0-9_-]{11})', url)
    if m:
        return m.group(1)
    # embed/ID
    m = re.search(r'/embed/([a-zA-Z0-9_-]{11})', url)
    if m:
        return m.group(1)
    return None


def get_duration(url, cookies_path):
    """الحصول على مدة الفيديو بالثواني"""
    try:
        cmd = [YT_DLP]
        if cookies_path and os.path.exists(cookies_path):
            cmd += ["--cookies", cookies_path]
        cmd += ["--print", "%(duration)s", "--skip-download", url]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if r.returncode == 0 and r.stdout.strip():
            return int(float(r.stdout.strip()))
    except Exception:
        pass
    return None


def download_tail(url, video_id, duration, tail_sec, out_dir, cookies_path):
    """
    تحميل آخر tail_sec ثانية من الفيديو مباشرة.
    يستخدم --download-sections مع --force-keyframes-at-cuts.
    """
    start = max(0, duration - tail_sec)
    mp4 = os.path.join(out_dir, f"{video_id}_tail.mp4")

    cmd = [YT_DLP]
    if cookies_path and os.path.exists(cookies_path):
        cmd += ["--cookies", cookies_path]
    cmd += [
        "--download-sections", f"*{start}-{duration}",
        "--force-keyframes-at-cuts",
        "-f", "worst[ext=mp4]",
        "-o", mp4,
        url,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0 or not os.path.exists(mp4):
        # محاولة ثانية بدون force-keyframes
        cmd2 = [YT_DLP]
        if cookies_path and os.path.exists(cookies_path):
            cmd2 += ["--cookies", cookies_path]
        cmd2 += [
            "--download-sections", f"*{start}-{duration}",
            "-f", "worst[ext=mp4]",
            "-o", mp4,
            url,
        ]
        r2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=60)
        if r2.returncode != 0 or not os.path.exists(mp4):
            return None

    return mp4


def extract_frames(mp4_path, out_dir, video_id, num_frames=3):
    """
    استخراج إطارات من المقطع المحمّل.
    num_frames: عدد الإطارات (موزعة بالتساوي على طول المقطع).
    """
    # الحصول على مدة المقطع
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
             mp4_path],
            capture_output=True, text=True, timeout=10,
        )
        clip_dur = float(r.stdout.strip())
    except Exception:
        clip_dur = 10.0

    frames = []
    for i in range(num_frames):
        # توزيع الإطارات (آخر إطار = آخر 0.5 ثانية من المقطع)
        if num_frames == 1:
            ts = clip_dur - 0.5
        else:
            ts = clip_dur * (i + 1) / (num_frames + 1)
        ts = max(0, ts)

        frame_path = os.path.join(out_dir, f"{video_id}_frame_{i}.png")
        r = subprocess.run(
            ["ffmpeg", "-i", mp4_path,
             "-ss", str(max(ts - 0.1, 0)),
             "-vframes", "1",
             "-q:v", "2",
             frame_path, "-y"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0 and os.path.exists(frame_path):
            frames.append(frame_path)

    return frames


def upscale_image(image_path, scale=4):
    """
    تكبير الصورة بـ scale مرات قبل OCR.
    يستخدم cv2.resize مع INTER_CUBIC.
    """
    import cv2
    import numpy as np

    img = cv2.imread(image_path)
    if img is None:
        return None

    h, w = img.shape[:2]
    new_h, new_w = h * scale, w * scale
    upscaled = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

    # تحسين التباين (CLAHE) لتحسين قراءة النص
    lab = cv2.cvtColor(upscaled, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge((l, a, b))
    enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    return enhanced


def ocr_frame(image, reader):
    """
    OCR على الصورة بعد تكبيرها 4x.
    - PSM 6 (paragraph mode): easyocr paragraph=True
    - Fallback: لو ما عاد شي، نعيد المحاولة مع paragraph=False
    """
    import cv2
    import numpy as np

    # تكبير 4x + تحسين
    enhanced = upscale_image(image, scale=4)
    if enhanced is None:
        return []

    # المحاولة الأولى: paragraph mode (≈ PSM 6)
    results = reader.readtext(enhanced, paragraph=True)

    # فلترة النصوص الفارغة أو القصيرة جداً
    texts = []
    for r in results:
        # في paragraph mode، r[1] هو النص المجمّع
        txt = r[1].strip()
        if len(txt) >= 1:
            texts.append(txt)

    # Fallback: لو ما حصلنا نصوص، نجرب بدون paragraph (≈ PSM 3)
    if not texts:
        results2 = reader.readtext(enhanced, paragraph=False)
        for r in results2:
            txt = r[1].strip()
            if len(txt) >= 1:
                texts.append(txt)

    return texts


def match_keywords(texts, keywords):
    """البحث عن الكلمات المفتاحية في النصوص المستخرجة"""
    matches = []
    for txt in texts:
        txt_lower = txt.lower()
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in txt_lower:
                matches.append({
                    "keyword": kw,
                    "matched_text": txt,
                })
                break  # كل نص يتطابق مرة فقط
    return matches


def cleanup_temp(files):
    """حذف الملفات المؤقتة"""
    for f in files:
        try:
            if f and os.path.exists(f):
                os.remove(f)
        except Exception:
            pass


# ---------- المنطق الرئيسي ----------

def scan_single_video(url, reader, out_dir, cookies_path, tail_sec, keywords):
    """مسح فيديو واحد: تحميل → فريمات → OCR → بحث → تنظيف"""
    vid = extract_video_id(url)
    if not vid:
        print(f"  ⚠️  لا يمكن استخراج ID الفيديو: {url[:60]}")
        return None

    # الحصول على المدة
    dur = get_duration(url, cookies_path)
    if dur is None:
        print(f"  ⚠️  لا يمكن الحصول على مدة الفيديو: {vid}")
        return None
    if dur < tail_sec + 1:
        print(f"  ⚠️  الفيديو قصير جداً ({dur}s): {vid}")
        return None

    # تحميل آخر tail_sec ثانية
    print(f"  ⏬ تحميل آخر {tail_sec}ث من {dur}ث...", end=" ", flush=True)
    mp4 = download_tail(url, vid, dur, tail_sec, out_dir, cookies_path)
    if not mp4:
        # محاولة مع tail أصغر
        alt_tail = min(tail_sec, max(5, dur // 4))
        if alt_tail < tail_sec:
            print(f"⚠️  المقطع طويل، نحاول {alt_tail}ث...", end=" ", flush=True)
            mp4 = download_tail(url, vid, dur, alt_tail, out_dir, cookies_path)
        if not mp4:
            print("❌ فشل التحميل")
            return None

    print("✅ استخراج الفريمات...", end=" ", flush=True)

    # استخراج 3 فريمات
    frame_paths = extract_frames(mp4, out_dir, vid, num_frames=3)
    if not frame_paths:
        print("❌ لا يمكن استخراج فريمات")
        cleanup_temp([mp4])
        return None

    print(f"({len(frame_paths)} فريم) OCR...", end=" ", flush=True)

    # OCR على كل فريم
    all_texts = []
    for fp in frame_paths:
        try:
            texts = ocr_frame(fp, reader)
            all_texts.extend(texts)
        except Exception as e:
            print(f"⚠️  خطأ OCR: {e}", end=" ", flush=True)

    # تنظيف
    cleanup_temp(frame_paths + [mp4])

    # إزالة التكرارات مع الحفاظ على الترتيب
    seen = set()
    unique_texts = []
    for t in all_texts:
        t_norm = t.strip()
        if t_norm and t_norm not in seen:
            seen.add(t_norm)
            unique_texts.append(t_norm)

    # البحث عن كلمات مفتاحية
    kw_matches = match_keywords(unique_texts, keywords)

    result = {
        "url": url,
        "video_id": vid,
        "duration_sec": dur,
        "tail_sec": tail_sec,
        "extracted_texts": unique_texts,
        "keyword_matches": kw_matches,
        "has_match": len(kw_matches) > 0,
    }

    if kw_matches:
        kw_str = ", ".join(m["keyword"] for m in kw_matches)
        print(f"🎯 {kw_str}")
    else:
        print("❌ لا توجد كلمات مفتاحية")

    return result


# ---------- نقطة الدخول ----------

def main():
    parser = argparse.ArgumentParser(
        description="MUSTAFA MIXING — OCR Credit Scanner\nمسح آخر ثواني فيديوهات يوتيوب للبحث عن أسماء في شريط الإنتاج.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
أمثلة:
  python ocr_credit_scanner.py --channel ShababTV --max 30
  python ocr_credit_scanner.py --urls-file urls.txt --tail 12
  python ocr_credit_scanner.py --urls-file urls.txt --output my_results

ملف URLs.txt مثال:
  https://www.youtube.com/watch?v=VIDEO_ID_1
  https://www.youtube.com/watch?v=VIDEO_ID_2
  # هذا تعليق
        """.strip(),
    )

    # واجهة مسح قناة (قديمة + جديدة)
    parser.add_argument("--channel", "-c",
                        help="اسم القناة (YouTube @username)")
    parser.add_argument("--max", type=int, default=30,
                        help="عدد الفيديوهات من القناة (افتراضي 30)")

    # واجهة ملف URLs
    parser.add_argument("--urls-file", "-f",
                        help="ملف نصي يحتوي على روابط يوتيوب (سطر لكل رابط)")

    # إعدادات مشتركة
    parser.add_argument("--tail", type=int, default=15,
                        help="عدد الثواني من نهاية الفيديو (10-15، افتراضي 15)")
    parser.add_argument("--keywords", default=",".join(DEFAULT_KEYWORDS),
                        help=f"كلمات مفتاحية مفصولة بفاصلة (افتراضي: {DEFAULT_KEYWORDS})")
    parser.add_argument("--output", default="ocr_results",
                        help="مجلد النتائج (افتراضي: ocr_results)")
    parser.add_argument("--cookies", default="cookies.txt",
                        help="ملف الكوكيز (افتراضي: cookies.txt)")
    parser.add_argument("--sleep", type=float, default=1.0,
                        help="ثواني الانتظار بين الفيديوهات (افتراضي 1)")

    args = parser.parse_args()

    # التحقق من أن واحداً من --channel أو --urls-file موجود
    if not args.channel and not args.urls_file:
        parser.print_help()
        print("\n⚠️  يجب تحديد --channel أو --urls-file")
        sys.exit(1)

    # التحقق من الاعتماديات
    print("🔍 فحص الاعتماديات...")
    if not check_deps():
        sys.exit(1)

    import torch

    # --- إعداد ---
    out_dir = Path(args.output)
    out_dir.mkdir(exist_ok=True)

    # كلمات البحث
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    if not keywords:
        keywords = list(DEFAULT_KEYWORDS)

    tail_sec = max(10, min(15, args.tail))
    cookies_path = args.cookies if os.path.exists(args.cookies) else None

    # --- تجميع قائمة URLs ---
    urls = []
    source_desc = ""

    if args.channel:
        source_desc = f"قناة @{args.channel}"
        ch_url = f"https://www.youtube.com/@{args.channel}"
        print(f"📡 جلب فيديوهات {source_desc}...")
        r = subprocess.run(
            [YT_DLP, "--flat-playlist", "--print", "%(id)s",
             "--playlist-end", str(args.max), ch_url],
            capture_output=True, text=True, timeout=60,
        )
        if r.returncode != 0:
            print(f"❌ فشل في جلب القناة: {r.stderr.strip()}")
            sys.exit(1)
        ids = [v.strip() for v in r.stdout.strip().split("\n") if v.strip()]
        urls = [f"https://www.youtube.com/watch?v={v}" for v in ids]
        print(f"📋 {len(urls)} فيديو")

    elif args.urls_file:
        urls_file = Path(args.urls_file)
        if not urls_file.exists():
            print(f"❌ الملف {args.urls_file} غير موجود")
            sys.exit(1)
        source_desc = f"ملف {args.urls_file}"
        with open(urls_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # تصفية الروابط
                if "youtube.com/watch" in line or "youtu.be/" in line or "youtube.com/shorts" in line:
                    urls.append(line)
        print(f"📋 {len(urls)} رابط من {source_desc}")

    if not urls:
        print("❌ لا توجد URLs للمسح")
        sys.exit(1)

    # --- OCR Engine ---
    gpu = torch.cuda.is_available()
    print(f"🤖 EasyOCR: GPU={'✅ متوفر' if gpu else '❌ غير متوفر'}")
    print(f"🎯 البحث عن: {', '.join(keywords)}")
    print(f"⏱️ آخر {tail_sec} ثانية من كل فيديو")
    print("=" * 50)

    import easyocr
    reader = easyocr.Reader(["ar", "en"], gpu=gpu)

    # --- المسح ---
    all_results = []
    total_matches = 0

    for i, url in enumerate(urls, 1):
        vid_short = extract_video_id(url) or url[:20]
        print(f"\n[{i}/{len(urls)}] {vid_short}")
        print(f"   {url[:70]}")

        try:
            result = scan_single_video(
                url, reader, str(out_dir), cookies_path,
                tail_sec, keywords,
            )
        except KeyboardInterrupt:
            print("\n\n⚠️  تم إيقاف المسح يدوياً")
            break
        except Exception as e:
            print(f"  ❌ خطأ غير متوقع: {e}")
            result = None

        if result:
            all_results.append(result)
            if result["has_match"]:
                total_matches += 1

        if i < len(urls):
            time.sleep(args.sleep)

    # --- حفظ النتائج ---
    summary = {
        "scan_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source": source_desc,
        "tail_sec": tail_sec,
        "keywords": keywords,
        "total_videos": len(urls),
        "scanned": len(all_results),
        "matched": total_matches,
        "results": all_results,
    }

    report_path = out_dir / "scan_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # --- التقرير ---
    print("\n" + "=" * 50)
    print(f"📊 تقرير المسح")
    print("=" * 50)
    print(f"📂 المصدر:      {source_desc}")
    print(f"🔎 الكلمات:     {', '.join(keywords)}")
    print(f"📝 إجمالي:      {len(urls)}")
    print(f"✅ تم المسح:    {len(all_results)}")
    print(f"🎯 بالتطابق:    {total_matches}")

    if total_matches > 0:
        print("\n📋 النتائج:")
        for r in all_results:
            if r["has_match"]:
                for m in r["keyword_matches"]:
                    print(f"  🎯 {m['keyword']}")
                    print(f"     {r['url']}")
                    print(f"     النص: {m['matched_text'][:80]}")
                    print()

    print(f"\n📄 التقرير الكامل: {report_path.resolve()}")

    # طباعة ملخص بسيط أيضاً
    matches_only = [
        {
            "url": r["url"],
            "video_id": r["video_id"],
            "duration": r["duration_sec"],
            "matches": r["keyword_matches"],
        }
        for r in all_results if r["has_match"]
    ]
    simple_report = out_dir / "scan_matches.json"
    with open(simple_report, "w", encoding="utf-8") as f:
        json.dump(matches_only, f, ensure_ascii=False, indent=2)
    print(f"📄 المطابقات فقط: {simple_report.resolve()}")


if __name__ == "__main__":
    main()
