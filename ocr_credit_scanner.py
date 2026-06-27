#!/usr/bin/env python3
"""MUSTAFA MIXING — OCR Credit Scanner v2.1 (Security & Logging Fix)

مسح آخر ثواني فيديوهات يوتيوب للبحث عن أسماء في شريط الإنتاج.

الاستخدام:
  python ocr_credit_scanner.py --channel ShababTV --max 30
  python ocr_credit_scanner.py --urls-file urls.txt

المتطلبات:
  pip install easyocr opencv-python numpy
  pip install yt-dlp
  نظام التشغيل: ffmpeg
"""

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ─── إعداد التسجيل (Logging) ─────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("ocr_scan.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("ocr_scanner")

# ---------- كلمات البحث المفتاحية ----------
DEFAULT_KEYWORDS = "مصطفى كمال,مصطفى,مهندس,مكس,ماستر"

# ---------- أدوات مساعدة ----------

def find_tool(name: str) -> str | None:
    """البحث عن أداة في PATH أو المسارات المحددة"""
    tool_path = shutil.which(name)
    if tool_path:
        return tool_path
    # مسارات إضافية معروفة
    extra = {
        "yt-dlp": [
            "/opt/data/mustafa-mixing-archive/.venv/bin/yt-dlp",
            os.path.expanduser("~/.local/bin/yt-dlp"),
        ],
    }
    for candidate in extra.get(name, []):
        try:
            r = subprocess.run([candidate, "--version"],
                               capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                return candidate
        except Exception:
            continue
    return None


def check_deps():
    """فحص الاعتماديات الأساسية مع رسائل خطأ مفصلة"""
    global YT_DLP
    YT_DLP = find_tool("yt-dlp")
    if not YT_DLP:
        logger.error("yt-dlp غير موجود. قم بتثبيته: pip install yt-dlp")
        return False

    try:
        import easyocr
        logger.info("easyocr: ✅")
    except ImportError as e:
        logger.error("easyocr غير موجود: %s", e)
        logger.error("قم بتثبيته: pip install easyocr opencv-python")
        return False

    try:
        import cv2
        logger.info("opencv: ✅")
    except ImportError as e:
        logger.error("opencv-python غير موجود: %s", e)
        logger.error("قم بتثبيته: pip install opencv-python")
        return False

    try:
        import numpy as np
        logger.info("numpy: ✅")
    except ImportError as e:
        logger.error("numpy غير موجود: %s", e)
        logger.error("قم بتثبيته: pip install numpy")
        return False

    # ffmpeg
    try:
        subprocess.run(["ffmpeg", "-version"],
                       capture_output=True, text=True, timeout=3, check=False)
        logger.info("ffmpeg: ✅")
    except FileNotFoundError:
        logger.error("ffmpeg غير موجود في PATH")
        return False
    except Exception as e:
        logger.error("خطأ في فحص ffmpeg: %s", e)
        return False

    return True


def extract_video_id(url):
    """استخراج YouTube video ID من أي صيغة URL، مع التحقق من الصحة"""
    if not url or not isinstance(url, str):
        return None
    patterns = [
        r'[?&]v=([a-zA-Z0-9_-]{11})',      # youtube.com/watch?v=ID
        r'youtu\.be/([a-zA-Z0-9_-]{11})',   # youtu.be/ID
        r'/shorts/([a-zA-Z0-9_-]{11})',     # shorts/ID
        r'/embed/([a-zA-Z0-9_-]{11})',      # embed/ID
    ]
    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            vid = m.group(1)
            # التحقق من أن الـ ID صالح (11 حرفاً)
            if re.match(r'^[a-zA-Z0-9_-]{11}$', vid):
                return vid
    logger.warning("لا يمكن استخراج ID صالح من: %s", url[:80])
    return None


def get_duration(url, cookies_path):
    """الحصول على مدة الفيديو بالثواني"""
    try:
        cmd = [YT_DLP]
        if cookies_path and os.path.exists(cookies_path):
            cmd += ["--cookies", cookies_path]
        cmd += ["--print", "%(duration)s", "--skip-download", url]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15, check=False)
        if r.returncode == 0 and r.stdout.strip():
            return int(float(r.stdout.strip()))
        logger.warning("فشل الحصول على المدة (رمز %d): %s", r.returncode, url[:60])
    except FileNotFoundError:
        logger.error("yt-dlp غير موجود في المسار المحدد")
    except subprocess.TimeoutExpired:
        logger.warning("انتهت مهلة الحصول على المدة: %s", url[:60])
    except Exception as e:
        logger.warning("خطأ في get_duration: %s", e)
    return None


def download_tail(url, video_id, duration, tail_sec, out_dir, cookies_path):
    """
    تحميل آخر tail_sec ثانية من الفيديو مباشرة.
    يستخدم --download-sections مع --force-keyframes-at-cuts.
    """
    start = max(0, duration - tail_sec)
    mp4 = os.path.join(out_dir, f"{video_id}_tail.mp4")

    def _try_download(cmd_template):
        """محاولة تحميل واحدة"""
        nonlocal mp4
        try:
            cmd = [YT_DLP]
            if cookies_path and os.path.exists(cookies_path):
                cmd += ["--cookies", cookies_path]
            cmd += cmd_template
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
            if r.returncode == 0 and os.path.exists(mp4) and os.path.getsize(mp4) > 0:
                return mp4
            logger.debug("فشل التحميل (رمز %d): %s", r.returncode, r.stderr[:100])
        except FileNotFoundError:
            logger.error("yt-dlp غير موجود")
        except subprocess.TimeoutExpired:
            logger.warning("انتهت مهلة التحميل")
        except Exception as e:
            logger.warning("خطأ في التحميل: %s", e)
        return None

    # المحاولة الأولى: مع force-keyframes
    result = _try_download([
        "--download-sections", f"*{start}-{duration}",
        "--force-keyframes-at-cuts",
        "-f", "worst[ext=mp4]",
        "-o", mp4,
        url,
    ])
    if result:
        return result

    # المحاولة الثانية: بدون force-keyframes
    result = _try_download([
        "--download-sections", f"*{start}-{duration}",
        "-f", "worst[ext=mp4]",
        "-o", mp4,
        url,
    ])
    return result


def extract_frames(mp4_path, out_dir, video_id, num_frames=3):
    """
    استخراج إطارات من المقطع المحمّل.
    num_frames: عدد الإطارات (موزعة بالتساوي على طول المقطع).
    """
    if not os.path.exists(mp4_path) or os.path.getsize(mp4_path) == 0:
        logger.warning("ملف المقطع غير موجود أو فارغ: %s", mp4_path)
        return []

    # الحصول على مدة المقطع
    clip_dur = 10.0
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
             mp4_path],
            capture_output=True, text=True, timeout=10, check=True,
        )
        if r.stdout.strip():
            clip_dur = float(r.stdout.strip())
    except FileNotFoundError:
        logger.error("ffprobe غير موجود في PATH")
        return []
    except (subprocess.TimeoutExpired, ValueError, Exception) as e:
        logger.warning("خطأ في ffprobe: %s", e)
        clip_dur = 10.0

    frames = []
    for i in range(num_frames):
        try:
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
                capture_output=True, text=True, timeout=10, check=False,
            )
            if r.returncode == 0 and os.path.exists(frame_path) and os.path.getsize(frame_path) > 0:
                frames.append(frame_path)
            else:
                logger.debug("فشل استخراج الإطار %d (رمز %d)", i, r.returncode)
        except (subprocess.TimeoutExpired, Exception) as e:
            logger.warning("خطأ في استخراج الإطار %d: %s", i, e)

    if not frames:
        logger.warning("لم يتم استخراج أي إطار من %s", mp4_path)
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
    """حذف الملفات المؤقتة بشكل آمن"""
    for f in files:
        try:
            if f and os.path.exists(f):
                os.remove(f)
                logger.debug("تم حذف: %s", f)
        except OSError as e:
            logger.warning("فشل حذف %s: %s", f, e)


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

    # ─── التحقق من صحة المدخلات ─────────────────────────────────────────
    if not args.channel and not args.urls_file:
        parser.print_help()
        logger.error("يجب تحديد --channel أو --urls-file")
        sys.exit(1)

    if args.max <= 0:
        parser.error("--max يجب أن يكون أكبر من 0")
    if args.max > 500:
        parser.error("--max يجب أن لا يتجاوز 500")

    if args.tail < 5 or args.tail > 30:
        logger.warning("--tail بقيمة %d خارج النطاق الموصى به (5-30). سيتم استخدام 15.", args.tail)
        args.tail = max(5, min(30, args.tail))

    if args.sleep < 0:
        parser.error("--sleep لا يمكن أن يكون سالباً")

    # التحقق من الاعتماديات
    logger.info("🔍 فحص الاعتماديات...")
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
