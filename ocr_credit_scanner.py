#!/usr/bin/env python3
"""
MUSTAFA MIXING OCR Credit Scanner
----------------------------------
مسح بصري للاعتمادات الموسيقية من قنوات YouTube باستخدام Tesseract OCR.

المتطلبات:
  - Python 3.8+
  - Tesseract-OCR (نظام تشغيل)
  - yt-dlp
  - ffmpeg
  - pip install pytesseract pillow
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

# ─── التحقق من المكتبات المطلوبة ──────────────────────────────────────
try:
    import pytesseract
    from PIL import Image
except ImportError as e:
    logger.error("المكتبات المطلوبة غير مثبتة: %s", e)
    logger.error("قم بتشغيل: pip install pytesseract Pillow")
    sys.exit(1)

# ─── البحث عن Tesseract في النظام ─────────────────────────────────────
def find_tesseract() -> str:
    """ابحث عن Tesseract-OCR في PATH أو المسارات الافتراضية."""
    tesseract_path = shutil.which("tesseract")
    if tesseract_path:
        return tesseract_path

    # مسارات Windows الافتراضية
    win_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for p in win_paths:
        if os.path.exists(p):
            return p

    logger.error(
        "لم يتم العثور على Tesseract-OCR. قم بتثبيته من:\n"
        "  https://github.com/UB-Mannheim/tesseract/wiki"
    )
    sys.exit(1)


tesseract_cmd = find_tesseract()
pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
logger.info("Tesseract: %s", tesseract_cmd)

# ─── التحقق من الأدوات المساعدة ───────────────────────────────────────
def check_tool(name: str) -> str:
    """تحقق من وجود أداة مساعدة في PATH."""
    tool_path = shutil.which(name)
    if not tool_path:
        logger.error("لم يتم العثور على %s في PATH. قم بتثبيته.", name)
        sys.exit(1)
    logger.info("%s: %s", name, tool_path)
    return tool_path


YT_DLP = check_tool("yt-dlp")
FFMPEG = check_tool("ffmpeg")

# ─── تحليل وسائط سطر الأوامر ──────────────────────────────────────────
parser = argparse.ArgumentParser(
    description="MUSTAFA MIXING OCR Scanner - مسح بصري للاعتمادات الموسيقية",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
أمثلة:
  %(prog)s --channel MCPTV
  %(prog)s --channel MCPTV --max 50 --names "مصطفى كمال,مهندس صوت"
  %(prog)s --channel AlHaneenChannel --max 100 --cookies my_cookies.txt
    """,
)
parser.add_argument(
    "--channel", "-c",
    required=True,
    help="اسم قناة YouTube (بدون @)",
)
parser.add_argument(
    "--max", type=int, default=30,
    help="أقصى عدد فيديوهات للمسح (الافتراضي: 30، الحد الأقصى: 500)",
)
parser.add_argument(
    "--names",
    default="مصطفى كمال,مهندس صوت,مكس,ماستر,مصطفى,كمال",
    help="أسماء للبحث عنها مفصولة بفواصل (الافتراضي: مصطفى كمال,مهندس صوت,...)",
)
parser.add_argument(
    "--cookies",
    default="cookies.txt",
    help="مسار ملف الكوكيز (الافتراضي: cookies.txt)",
)
parser.add_argument(
    "--delay", type=float, default=1.0,
    help="تأخير بين الفيديوهات بالثواني (الافتراضي: 1.0)",
)

args = parser.parse_args()

# التحقق من صحة المدخلات
if args.max <= 0:
    parser.error("--max يجب أن يكون أكبر من 0")
if args.max > 500:
    parser.error("--max يجب أن يكون أقل من أو يساوي 500")
if args.delay < 0:
    parser.error("--delay لا يمكن أن يكون سالباً")

# تنظيف اسم القناة من @ إذا وُجد
channel_name = args.channel.lstrip("@")
if not re.match(r"^[\w.-]+$", channel_name):
    parser.error("اسم القناة يحتوي على أحرف غير صالحة")

# ─── الإعدادات ─────────────────────────────────────────────────────────
out_dir = Path("ocr_results")
out_dir.mkdir(exist_ok=True)
search_names = [n.strip() for n in args.names.split(",") if n.strip()]
cookies_file = args.cookies if os.path.exists(args.cookies) else None

logger.info("=" * 60)
logger.info("MUSTAFA MIXING OCR Scanner")
logger.info("=" * 60)
logger.info("القناة: %s", channel_name)
logger.info("أقصى عدد: %d", args.max)
logger.info("أسماء البحث: %s", search_names)
logger.info("ملف الكوكيز: %s", cookies_file or "غير موجود")
logger.info("دليل الإخراج: %s", out_dir.resolve())
logger.info("=" * 60)

# ─── الحصول على قائمة الفيديوهات ───────────────────────────────────────
channel_url = f"https://www.youtube.com/@{channel_name}"
logger.info("جلب قائمة التشغيل من: %s", channel_url)

try:
    playlist_cmd = [
        YT_DLP, "--flat-playlist", "--print", "%(id)s",
        "--playlist-end", str(args.max), channel_url,
    ]
    r = subprocess.run(
        playlist_cmd,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if r.returncode != 0:
        logger.error("yt-dlp فشل في جلب القائمة: %s", r.stderr[:200])
        sys.exit(1)
    video_ids = [v.strip() for v in r.stdout.strip().split("\n") if v.strip()]
    logger.info("تم العثور على %d فيديو", len(video_ids))
except subprocess.TimeoutExpired:
    logger.error("انتهت مهلة yt-dlp (60 ثانية)")
    sys.exit(1)
except FileNotFoundError:
    logger.error("yt-dlp غير موجود. قم بتثبيته: pip install yt-dlp")
    sys.exit(1)

# ─── تنظيف الملفات المؤقتة ─────────────────────────────────────────────
def cleanup_temp_files(files: list) -> None:
    """حذف الملفات المؤقتة بشكل آمن."""
    for f in files:
        try:
            if f and os.path.exists(f):
                os.remove(f)
                logger.debug("تم حذف: %s", f)
        except OSError as e:
            logger.warning("فشل حذف %s: %s", f, e)


def validate_video_id(vid: str) -> bool:
    """تحقق من أن vid هو معرف YouTube صالح (11 حرفاً أبجدياً رقماً)."""
    return bool(re.match(r"^[a-zA-Z0-9_-]{11}$", vid))


# ─── دالة الحصول على المدة ────────────────────────────────────────────
def get_duration(video_id: str) -> int | None:
    """احصل على مدة الفيديو بالثواني."""
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        cookies_args = ["--cookies", args.cookies] if cookies_file else []
        cmd = [YT_DLP, *cookies_args, "--print", "%(duration)s", "--skip-download", url]
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=15, check=False,
        )
        if r.returncode != 0:
            logger.warning("فشل الحصول على المدة لـ %s: %s", video_id, r.stderr[:100])
            return None
        val = r.stdout.strip()
        return int(float(val)) if val else None
    except (ValueError, subprocess.TimeoutExpired, Exception) as e:
        logger.warning("خطأ في المدة لـ %s: %s", video_id, e)
        return None


# ─── دالة مسح الفيديو ─────────────────────────────────────────────────
def scan_video(video_id: str, output_dir: Path) -> dict | None:
    """حمل الـ outro من الفيديو، استخرج الإطار، وشغل OCR."""
    if not validate_video_id(video_id):
        logger.warning("معرف فيديو غير صالح: %s", video_id)
        return None

    dur = get_duration(video_id)
    if dur is None or dur < 15:
        return None

    start = max(0, dur - 10)
    url = f"https://www.youtube.com/watch?v={video_id}"

    mp4_path = os.path.join(str(output_dir), f"{video_id}_outro.mp4")
    frame_path = os.path.join(str(output_dir), f"{video_id}_frame.png")

    temp_files = [mp4_path, frame_path]

    try:
        # تحميل outro
        cookies_args = ["--cookies", args.cookies] if cookies_file else []
        download_cmd = [
            YT_DLP, *cookies_args,
            "--download-sections", f"*{start}-{dur}",
            "--force-keyframes-at-cuts",
            "-f", "worst[ext=mp4]",
            "-o", mp4_path,
            url,
        ]
        r = subprocess.run(
            download_cmd, capture_output=True, text=True, timeout=40, check=False,
        )
        if r.returncode != 0:
            logger.debug("فشل تحميل %s: %s", video_id, r.stderr[:100])
            return None
        if not os.path.exists(mp4_path) or os.path.getsize(mp4_path) == 0:
            return None

        # استخراج أول إطار
        frame_cmd = [
            FFMPEG, "-i", mp4_path,
            "-vf", "select=eq(n,0)",
            "-vsync", "vfr",
            "-q:v", "2",
            frame_path, "-y",
        ]
        subprocess.run(
            frame_cmd, capture_output=True, text=True, timeout=10, check=False,
        )
        if not os.path.exists(frame_path):
            return None

        # OCR
        img = Image.open(frame_path)
        raw_text = pytesseract.image_to_string(img, lang="ara+eng")
        texts = [t.strip() for t in raw_text.strip().split("\n") if t.strip()]

        return {"vid": video_id, "url": url, "texts": texts}

    except Exception as e:
        logger.warning("خطأ أثناء مسح %s: %s", video_id, e)
        return None
    finally:
        cleanup_temp_files(temp_files)


# ─── التنفيذ الرئيسي ──────────────────────────────────────────────────
matches = []
total = len(video_ids)

for idx, vid in enumerate(video_ids, 1):
    logger.info("[%d/%d] %s", idx, total, vid)
    result = scan_video(vid, out_dir)
    if result and result["texts"]:
        sample = " | ".join(result["texts"])
        logger.info("  النص: %s", sample[:120])
        for txt in result["texts"]:
            for name in search_names:
                if name.lower() in txt.lower():
                    logger.info("  ✅ تم العثور على '%s': %s", name, txt)
                    matches.append({"url": result["url"], "text": txt})
    else:
        logger.debug("[%d/%d] %s — تخطي", idx, total, vid)

    if idx < total:
        time.sleep(args.delay)

# ─── التقرير النهائي ──────────────────────────────────────────────────
logger.info("=" * 60)
logger.info("تم المسح. %d نتيجة من %d فيديو", len(matches), total)
for m in matches:
    logger.info("  %s : %s", m["url"], m["text"])

# حفظ التقرير
report_path = out_dir / "scan_report.json"
try:
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "channel": channel_name,
                "videos_scanned": total,
                "matches_found": len(matches),
                "search_names": search_names,
                "matches": matches,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    logger.info("التقرير: %s", report_path.resolve())
except OSError as e:
    logger.error("فشل كتابة التقرير: %s", e)
    sys.exit(1)
