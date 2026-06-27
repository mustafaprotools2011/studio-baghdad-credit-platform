#!/usr/bin/env python3
"""
MUSTAFA MIXING OCR Credit Scanner - OPTIMIZED & CORRECTED VERSION
==================================================================
مسح بصري محسّن للاعتمادات الموسيقية من قنوات YouTube باستخدام Tesseract OCR.

التحسينات:
✅ معالجة متوازية (Parallel Processing)
✅ استخراج منطقة الاعتمادات (ROI Extraction)
✅ نظام التخزين المؤقت (Caching)
✅ Delay ذكي (Smart Delay)
✅ بحث بـ Regex محسّن
✅ تحسين صور OCR
✅ معالجة على دفعات (Batch Processing)
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
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple

# مكتبات الصور
try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter
except ImportError as e:
    print(f"❌ خطأ: المكتبات المطلوبة غير مثبتة: {e}")
    print("📦 قم بتشغيل: pip install pytesseract Pillow")
    sys.exit(1)

# ─── إعداد التسجيل (Logging) ───────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("ocr_scan.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("ocr_scanner")

# ─── الثوابت ───────────────────────────────────────────────────────
CACHE_FILE = Path("ocr_results/processed_videos.json")
BATCH_SIZE = 100
MAX_WORKERS = 4
MIN_DELAY = 1.0
TIMEOUT_SECONDS = 60

# ─── البحث عن Tesseract ────────────────────────────────────────────
def find_tesseract() -> str:
    """ابحث عن Tesseract-OCR في النظام"""
    tesseract_path = shutil.which("tesseract")
    if tesseract_path:
        return tesseract_path

    win_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for p in win_paths:
        if os.path.exists(p):
            return p

    logger.error(
        "❌ لم يتم العثور على Tesseract-OCR. قم بتثبيته من:\n"
        "   https://github.com/UB-Mannheim/tesseract/wiki"
    )
    sys.exit(1)

tesseract_cmd = find_tesseract()
pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
logger.info(f"✅ Tesseract: {tesseract_cmd}")

# ─── التحقق من الأدوات المساعدة ────────────────────────────────────
def check_tool(name: str) -> str:
    """تحقق من وجود أداة مساعدة في PATH"""
    tool_path = shutil.which(name)
    if not tool_path:
        logger.error(f"❌ لم يتم العثور على {name} في PATH")
        sys.exit(1)
    logger.info(f"✅ {name}: {tool_path}")
    return tool_path

YT_DLP = check_tool("yt-dlp")
FFMPEG = check_tool("ffmpeg")

# ═══════════════════════════════════════════════════════════════════════
# ✨ التحسين #1: نظام التخزين المؤقت (Caching System)
# ═══════════════════════════════════════════════════════════════════════

class CacheManager:
    """إدارة التخزين المؤقت للفيديوهات المعالجة"""

    def __init__(self, cache_file: Path = CACHE_FILE):
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache = self._load_cache()

    def _load_cache(self) -> dict:
        """تحميل بيانات التخزين المؤقت"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ خطأ في تحميل الـ cache: {e}")
                return {}
        return {}

    def _save_cache(self):
        """حفظ بيانات التخزين المؤقت"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ الـ cache: {e}")

    def get_processed_videos(self, channel: str) -> set:
        """الحصول على الفيديوهات المعالجة"""
        return set(self.cache.get(channel, {}).get('video_ids', []))

    def add_processed_videos(self, channel: str, video_ids: List[str]):
        """إضافة فيديوهات معالجة"""
        if channel not in self.cache:
            self.cache[channel] = {'video_ids': [], 'last_updated': None}

        existing = set(self.cache[channel]['video_ids'])
        existing.update(video_ids)
        self.cache[channel]['video_ids'] = list(existing)
        self.cache[channel]['last_updated'] = datetime.now().isoformat()
        self._save_cache()

    def is_fresh(self, channel: str, max_days: int = 7) -> bool:
        """التحقق من أن الـ cache حديث"""
        if channel not in self.cache:
            return False

        last_updated = self.cache[channel].get('last_updated')
        if not last_updated:
            return False

        try:
            last_date = datetime.fromisoformat(last_updated)
            return datetime.now() - last_date < timedelta(days=max_days)
        except:
            return False


# ═══════════════════════════════════════════════════════════════════════
# ✨ التحسين #2 & #3: معالجة صور OCR + استخراج ROI
# ═══════════════════════════════════════════════════════════════════════

class ImageProcessor:
    """معالجة الصور لزيادة دقة OCR"""

    @staticmethod
    def extract_credits_roi(img: Image.Image, roi_height_ratio: float = 0.3) -> Image.Image:
        """استخراج منطقة الاعتمادات من أسفل الصورة"""
        try:
            height = img.height
            width = img.width

            # استخراج آخر 30% من الصورة
            start_y = int(height * (1 - roi_height_ratio))
            roi = img.crop((0, start_y, width, height))

            logger.debug(f"📏 استخراج ROI: {width}x{height} → {roi.width}x{roi.height}")
            return roi
        except Exception as e:
            logger.warning(f"⚠️ خطأ في استخراج ROI: {e}")
            return img

    @staticmethod
    def preprocess_for_ocr(img: Image.Image) -> Image.Image:
        """تحسين الصورة قبل OCR"""
        try:
            # تحويل إلى grayscale
            if img.mode != 'L':
                img = img.convert('L')

            # زيادة التباين
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.5)

            # تحسين الحدة
            img = img.filter(ImageFilter.SHARPEN)

            # تحسين الإضاءة
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(1.1)

            logger.debug("🖼 تم تحسين الصورة")
            return img
        except Exception as e:
            logger.warning(f"⚠️ خطأ في تحسين الصورة: {e}")
            return img

    @staticmethod
    def process_frame(frame_path: Path) -> Optional[Image.Image]:
        """معالجة كاملة للصورة"""
        try:
            img = Image.open(frame_path)
            roi = ImageProcessor.extract_credits_roi(img)
            processed = ImageProcessor.preprocess_for_ocr(roi)
            return processed
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة الصورة {frame_path}: {e}")
            return None


# ═══════════════════════════════════════════════════════════════════════
# ✨ التحسين #4: Delay ذكي
# ═══════════════════════════════════════════════════════════════════════

class SmartDelay:
    """إدارة التأخير الذكي"""

    @staticmethod
    def wait_remaining(start_time: float, min_delay: float = MIN_DELAY):
        """انتظر الوقت المتبقي فقط"""
        try:
            elapsed = time.time() - start_time
            wait_time = max(0, min_delay - elapsed)

            if wait_time > 0:
                logger.debug(f"⏱️ انتظار {wait_time:.2f}ث")
                time.sleep(wait_time)
            else:
                logger.debug(f"⚡️ تم المعالجة في {elapsed:.2f}ث")
        except Exception as e:
            logger.warning(f"⚠️ خطأ في التأخير: {e}")


# ═══════════════════════════════════════════════════════════════════════
# ✨ التحسين #5: بحث بـ Regex محسّن
# ═══════════════════════════════════════════════════════════════════════

class SearchOptimizer:
    """تحسين البحث عن الأسماء"""

    def __init__(self, names: List[str]):
        """تجميع الأسماء في regex واحد"""
        self.names = [n.strip() for n in names if n.strip()]
        self.pattern = self._compile_pattern(self.names)

    @staticmethod
    def _compile_pattern(names: List[str]) -> re.Pattern:
        """دمج الأسماء في regex"""
        if not names:
            return re.compile(r'(?!)', re.UNICODE)

        patterns = [re.escape(n) for n in names]
        combined = '|'.join(f'({p})' for p in patterns)

        try:
            pattern = re.compile(combined, re.IGNORECASE | re.UNICODE)
            logger.debug(f"🔍 تم تجميع {len(names)} اسم")
            return pattern
        except re.error as e:
            logger.error(f"❌ خطأ في الـ regex: {e}")
            return re.compile(r'(?!)', re.UNICODE)

    def find_all(self, text: str) -> List[str]:
        """البحث عن جميع التطابقات"""
        try:
            if not text:
                return []

            matches = self.pattern.findall(text)
            cleaned = []

            for match in matches:
                if isinstance(match, tuple):
                    match = next((m for m in match if m), None)
                if match:
                    cleaned.append(match)

            return cleaned
        except Exception as e:
            logger.warning(f"⚠️ خطأ في البحث: {e}")
            return []

    def find_with_context(self, text: str, context_chars: int = 50) -> List[Dict]:
        """البحث مع السياق"""
        try:
            if not text:
                return []

            results = []
            for match in self.pattern.finditer(text):
                start = max(0, match.start() - context_chars)
                end = min(len(text), match.end() + context_chars)
                context = text[start:end].strip()

                results.append({
                    'name': match.group() if isinstance(match.group(), str) else str(match.group()),
                    'position': match.start(),
                    'context': context
                })

            return results
        except Exception as e:
            logger.warning(f"⚠️ خطأ في البحث مع السياق: {e}")
            return []


# ═══════════════════════════════════════════════════════════════════════
# ✨ التحسين #6: استخلاص النصوص من Tesseract محسّن
# ═══════════════════════════════════════════════════════════════════════

class OCRExtractor:
    """استخلاص النصوص من الصور"""

    OCR_CONFIG = r'--oem 3 --psm 6 -l ara+eng'

    @staticmethod
    def extract_text(img: Image.Image) -> str:
        """استخراج النص من صورة"""
        try:
            if img is None:
                return ""

            text = pytesseract.image_to_string(img, config=OCRExtractor.OCR_CONFIG)
            logger.debug(f"📝 تم استخراج {len(text)} حرف")
            return text
        except Exception as e:
            logger.error(f"❌ خطأ في OCR: {e}")
            return ""


# ═══════════════════════════════════════════════════════════════════════
# دوال تحميل وتصنع الفيديو
# ═══════════════════════════════════════════════════════════════════════

def validate_video_id(video_id: str) -> bool:
    """التحقق من صحة معرف الفيديو"""
    return bool(re.match(r'^[a-zA-Z0-9_-]{11}$', video_id))

def download_video(video_id: str, output_dir: Path, cookies_file: Optional[str] = None) -> Optional[str]:
    """تحميل الفيديو"""
    try:
        if not validate_video_id(video_id):
            logger.warning(f"⚠️ معرف فيديو غير صحيح: {video_id}")
            return None

        output_template = str(output_dir / f"{video_id}.%(ext)s")

        cmd = [
            YT_DLP,
            f"https://www.youtube.com/watch?v={video_id}",
            "-f", "worst",
            "-o", output_template,
            "--quiet",
            "--no-warnings",
        ]

        if cookies_file and os.path.exists(cookies_file):
            cmd.extend(["--cookies", cookies_file])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=False
        )

        if result.returncode != 0:
            logger.warning(f"⚠️ فشل تحميل {video_id}")
            return None

        # البحث عن الملف المحمل
        for file in output_dir.glob(f"{video_id}.*"):
            if file.suffix.lower() in ['.mp4', '.webm', '.mkv']:
                logger.debug(f"✅ تم تحميل {file.name}")
                return str(file)

        logger.warning(f"⚠️ لم يتم العثور على ملف الفيديو {video_id}")
        return None

    except subprocess.TimeoutExpired:
        logger.warning(f"⚠️ انتهت المهلة الزمنية: {video_id}")
        return None
    except Exception as e:
        logger.error(f"❌ خطأ في تحميل {video_id}: {e}")
        return None

def extract_frame(video_path: str, output_dir: Path, video_id: str) -> Optional[Path]:
    """استخراج آخر إطار من الفيديو"""
    try:
        output_frame = output_dir / f"{video_id}_frame.png"

        cmd = [
            FFMPEG,
            "-i", video_path,
            "-vf", "fps=1,scale=1280:-1",
            "-frames:v", "1",
            str(output_frame),
            "-loglevel", "quiet",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=TIMEOUT_SECONDS,
            check=False
        )

        if result.returncode == 0 and output_frame.exists():
            logger.debug(f"✅ تم استخراج الإطار")
            return output_frame

        logger.warning(f"⚠️ فشل استخراج الإطار من {video_id}")
        return None

    except subprocess.TimeoutExpired:
        logger.warning(f"⚠️ انتهت المهلة الزمنية في الاستخراج: {video_id}")
        return None
    except Exception as e:
        logger.error(f"❌ خطأ في استخراج الإطار: {e}")
        return None

def cleanup_temp_files(files: List[Optional[str]]):
    """تنظيف الملفات المؤقتة"""
    for f in files:
        try:
            if f and os.path.exists(f):
                os.remove(f)
                logger.debug(f"🗑 حذف {f}")
        except Exception as e:
            logger.warning(f"⚠️ خطأ في حذف {f}: {e}")


# ═══════════════════════════════════════════════════════════════════════
# ✨ التحسين #7: معالجة متوازية
# ═══════════════════════════════════════════════════════════════════════

def scan_video(video_id: str, output_dir: Path, search_pattern: SearchOptimizer,
               cookies_file: Optional[str] = None, min_delay: float = MIN_DELAY) -> Optional[Dict]:
    """معالجة فيديو واحد"""
    start_time = time.time()
    temp_files = []

    try:
        # تحميل الفيديو
        video_path = download_video(video_id, output_dir, cookies_file)
        if not video_path:
            return None
        temp_files.append(video_path)

        # استخراج الإطار
        frame_path = extract_frame(video_path, output_dir, video_id)
        if not frame_path:
            return None
        temp_files.append(str(frame_path))

        # معالجة الصورة
        processed_img = ImageProcessor.process_frame(frame_path)
        if not processed_img:
            return None

        # استخراج النص
        raw_text = OCRExtractor.extract_text(processed_img)
        if not raw_text or len(raw_text.strip()) == 0:
            logger.debug(f"⏭️ لم يتم استخراج نص من {video_id}")
            return None

        # البحث عن الأسماء
        matches = search_pattern.find_with_context(raw_text)

        elapsed = time.time() - start_time

        # تطبيق التأخير الذكي
        SmartDelay.wait_remaining(start_time, min_delay)

        return {
            'video_id': video_id,
            'url': f"https://www.youtube.com/watch?v={video_id}",
            'matches_found': len(matches),
            'matches': matches,
            'processing_time': f"{elapsed:.2f}s"
        }

    except Exception as e:
        logger.error(f"❌ خطأ في معالجة {video_id}: {e}")
        return None

    finally:
        cleanup_temp_files(temp_files)


def process_videos_parallel(video_ids: List[str], output_dir: Path,
                           search_pattern: SearchOptimizer,
                           cookies_file: Optional[str] = None,
                           max_workers: int = MAX_WORKERS,
                           min_delay: float = MIN_DELAY) -> List[Dict]:
    """معالجة عدة فيديوهات بشكل متوازي"""
    results = []
    total = len(video_ids)
    processed = 0

    logger.info(f"🚀 بدء معالجة {total} فيديو بـ {max_workers} معالج")

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    scan_video, vid, output_dir, search_pattern, cookies_file, min_delay
                ): vid
                for vid in video_ids
            }

            for future in as_completed(futures):
                processed += 1
                vid = futures[future]

                try:
                    result = future.result(timeout=TIMEOUT_SECONDS * 3)
                    if result:
                        results.append(result)
                        logger.info(
                            f"✅ [{processed}/{total}] {vid} - "
                            f"{result['matches_found']} تطابق"
                        )
                    else:
                        logger.info(f"⏭️ [{processed}/{total}] {vid}")

                except Exception as e:
                    logger.error(f"❌ [{processed}/{total}] {vid} - {e}")

    except Exception as e:
        logger.error(f"❌ خطأ في المعالجة المتوازية: {e}")

    return results


def process_in_batches(video_ids: List[str], output_dir: Path,
                      search_pattern: SearchOptimizer,
                      cookies_file: Optional[str] = None,
                      batch_size: int = BATCH_SIZE,
                      max_workers: int = MAX_WORKERS,
                      min_delay: float = MIN_DELAY) -> List[Dict]:
    """معالجة على دفعات"""
    all_results = []
    total_batches = (len(video_ids) + batch_size - 1) // batch_size

    for i, start_idx in enumerate(range(0, len(video_ids), batch_size)):
        batch = video_ids[start_idx:start_idx + batch_size]
        batch_num = i + 1

        logger.info(f"📦 الدفعة {batch_num}/{total_batches} ({len(batch)} فيديو)")

        batch_results = process_videos_parallel(
            batch, output_dir, search_pattern, cookies_file, max_workers, min_delay
        )
        all_results.extend(batch_results)

    return all_results


# ═══════════════════════════════════════════════════════════════════════
# الحصول على قائمة الفيديوهات
# ═══════════════════════════════════════════════════════════════════════

def get_channel_videos(channel_name: str, max_videos: int = 30,
                      cookies_file: Optional[str] = None) -> List[str]:
    """الحصول على قائمة الفيديوهات من القناة"""
    try:
        logger.info(f"📺 جاري الحصول على الفيديوهات من {channel_name}")

        cmd = [
            YT_DLP,
            f"https://www.youtube.com/@{channel_name}/videos",
            "--flat-playlist",
            "-I", f"1:{max_videos}",
            "-o", "%(id)s",
            "--quiet",
            "--no-warnings",
        ]

        if cookies_file and os.path.exists(cookies_file):
            cmd.extend(["--cookies", cookies_file])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            check=False
        )

        if result.returncode != 0:
            logger.error(f"❌ فشل الحصول على الفيديوهات: {result.stderr}")
            return []

        video_ids = [v.strip() for v in result.stdout.strip().split("\n") if v.strip()]
        logger.info(f"✅ تم الحصول على {len(video_ids)} فيديو")
        return video_ids

    except Exception as e:
        logger.error(f"❌ خطأ: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════
# البرنامج الرئيسي
# ═══════════════════════════════════════════════════════════════════════

def main():
    """البرنامج الرئيسي"""

    parser = argparse.ArgumentParser(
        description="MUSTAFA MIXING OCR Scanner - مسح محسّن",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
أمثلة:
  %(prog)s --channel MCPTV
  %(prog)s --channel MCPTV --max 50
  %(prog)s --channel AlHaneenChannel --workers 4
        """,
    )

    parser.add_argument("--channel", "-c", required=True, help="اسم القناة")
    parser.add_argument("--max", type=int, default=30, help="أقصى عدد فيديوهات")
    parser.add_argument("--names", default="مصطفى كمال,مهندس صوت,مكس,ماستر",
                       help="أسماء للبحث")
    parser.add_argument("--cookies", default="cookies.txt", help="ملف الكوكيز")
    parser.add_argument("--delay", type=float, default=MIN_DELAY, help="التأخير بالثواني")
    parser.add_argument("--workers", type=int, default=MAX_WORKERS, help="عدد المعالجات")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="حجم الدفعة")
    parser.add_argument("--no-cache", action="store_true", help="تجاهل الـ cache")

    args = parser.parse_args()

    # التحقق من صحة المعاملات
    if args.max <= 0 or args.max > 500:
        parser.error("❌ --max يجب أن يكون بين 1 و 500")
    if args.delay < 0:
        parser.error("❌ --delay يجب أن يكون موجباً")
    if args.workers < 1:
        parser.error("❌ --workers يجب أن يكون على الأقل 1")

    # إعداد المجلدات
    output_dir = Path("ocr_results")
    output_dir.mkdir(parents=True, exist_ok=True)

    channel_name = args.channel.lstrip("@")

    logger.info("=" * 70)
    logger.info("🎬 MUSTAFA MIXING - OCR Credit Scanner (OPTIMIZED & CORRECTED)")
    logger.info("=" * 70)
    logger.info(f"📺 القناة: {channel_name}")
    logger.info(f"🔍 البحث عن: {args.names}")
    logger.info(f"⚙️ المعالجات: {args.workers} | التأخير: {args.delay}ث")
    logger.info("=" * 70)

    # إعداد البحث
    search_names = [n.strip() for n in args.names.split(",") if n.strip()]
    if not search_names:
        logger.error("❌ لا توجد أسماء للبحث عنها")
        sys.exit(1)

    search_pattern = SearchOptimizer(search_names)

    # إدارة الـ Cache
    cache_manager = CacheManager()

    # الحصول على الفيديوهات
    video_ids = get_channel_videos(channel_name, args.max, args.cookies)
    if not video_ids:
        logger.error("❌ فشل في الحصول على الفيديوهات")
        sys.exit(1)

    # فلترة الفيديوهات المعالجة
    if not args.no_cache and cache_manager.is_fresh(channel_name):
        processed = cache_manager.get_processed_videos(channel_name)
        new_videos = [v for v in video_ids if v not in processed]

        if new_videos:
            logger.info(f"✅ {len(new_videos)} فيديو جديد ({len(processed)} معالج سابقاً)")
            video_ids = new_videos
        else:
            logger.info(f"✅ جميع الفيديوهات معالجة ({len(processed)} فيديو)")
            sys.exit(0)

    # معالجة الفيديوهات
    start_time = time.time()

    all_results = process_in_batches(
        video_ids, output_dir, search_pattern,
        args.cookies, args.batch_size, args.workers, args.delay
    )

    elapsed = time.time() - start_time

    # حفظ في الـ Cache
    if video_ids:
        cache_manager.add_processed_videos(channel_name, video_ids)

    # إنشاء التقرير
    report = {
        "scan_date": datetime.now().isoformat(),
        "channel": channel_name,
        "videos_scanned": len(all_results),
        "total_matches": sum(r['matches_found'] for r in all_results),
        "search_names": search_names,
        "processing_time_seconds": f"{elapsed:.2f}",
        "results": all_results,
    }

    # حفظ التقرير
    report_path = output_dir / "scan_report.json"
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 التقرير: {report_path}")
    except Exception as e:
        logger.error(f"❌ خطأ في حفظ التقرير: {e}")

    # ملخص النتائج
    total_matches = sum(r['matches_found'] for r in all_results)
    logger.info("=" * 70)
    logger.info("📊 النتائج")
    logger.info("=" * 70)
    logger.info(f"✅ الفيديوهات المعالجة: {len(all_results)}")
    logger.info(f"🎯 إجمالي التطابقات: {total_matches}")
    logger.info(f"⏱️ الوقت المستغرق: {elapsed:.2f}ث")
    if elapsed > 0:
        logger.info(f"⚡️ السرعة: {len(all_results) / elapsed:.2f} فيديو/ثانية")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
