# MUSTAFA MIXING — Studio Baghdad Credit Platform

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/OCR-Tesseract-green" alt="OCR">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey" alt="Platform">
</p>

**Studio Baghdad Credit Platform** — منصة لمسح وتتبع الاعتمادات الموسيقية من قنوات YouTube باستخدام تقنية OCR.  
**Automated music credit discovery and tracking platform using OCR from YouTube channel outros.**

---

## 📋 الميزات / Features

- ✅ **OCR Scanner** — استخراج النصوص من شاشات نهاية الفيديو (outros) باستخدام Tesseract
- ✅ **YouTube Integration** — تحميل تلقائي للفيديوهات عبر yt-dlp
- ✅ **Multi-language** — دعم العربية والإنجليزية
- ✅ **Search Names** — البحث عن أسماء محددة في الاعتمادات (مثل: مصطفى كمال، مهندس صوت)
- ✅ **Reporting** — تقارير JSON منظمة مع جميع النتائج
- ✅ **Logging** — تسجيل كامل بكافة المستويات (INFO, WARNING, ERROR, DEBUG)

## 📦 المتطلبات / Requirements

| الأداة / Tool | المصدر / Source |
|--------------|----------------|
| Python 3.8+ | [python.org](https://python.org) |
| Tesseract-OCR 5.x | [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) (Windows) |
| yt-dlp | `pip install yt-dlp` |
| ffmpeg | [ffmpeg.org](https://ffmpeg.org) |
| pytesseract | `pip install pytesseract` |
| Pillow | `pip install Pillow` |

## 🚀 التثبيت السريع / Quick Start

### 1. تثبيت Tesseract-OCR
**[تحميل Tesseract 5.x](https://github.com/UB-Mannheim/tesseract/wiki)**  
تأكد من تثبيت دعم اللغة العربية (`Arabic script`) أثناء التثبيت.

### 2. تثبيت المكتبات
```bash
pip install -r requirements.txt
pip install yt-dlp
```

### 3. تشغيل المسح
```bash
python ocr_credit_scanner.py --channel CHANNEL_NAME
```

أو على Windows:
```batch
run.bat --channel CHANNEL_NAME
```

## 📖 أمثلة الاستخدام / Usage Examples

```bash
# مسح قناة MCP TV (آخر 30 فيديو)
python ocr_credit_scanner.py --channel MCPTV

# مسح 100 فيديو بأسماء بحث مخصصة
python ocr_credit_scanner.py --channel AlHaneenChannel --max 100 --names "مصطفى كمال,مهندس صوت,مكس,ماستر"

# استخدام ملف كوكيز مخصص
python ocr_credit_scanner.py --channel ShababTV --cookies my_cookies.txt

# تأخير أطول بين الفيديوهات (لتجنب الحظر)
python ocr_credit_scanner.py --channel MCPTV --delay 3.0
```

### جميع الوسائط / All Arguments

| الوسيط / Argument | الاختصار | الوصف | الافتراضي |
|-----------------|---------|------|----------|
| `--channel` | `-c` | اسم القناة (مطلوب) | — |
| `--max` | — | أقصى عدد فيديوهات | `30` |
| `--names` | — | أسماء للبحث (مفصولة بفاصلة) | `مصطفى كمال,مهندس صوت,مكس,ماستر` |
| `--cookies` | — | ملف الكوكيز | `cookies.txt` |
| `--delay` | — | تأخير بين الفيديوهات (ثوان) | `1.0` |

## 📁 هيكل المشروع / Project Structure

```
studio-baghdad-credit-platform/
├── ocr_credit_scanner.py   # أداة المسح البصري
├── run.bat                  # مشغل Windows
├── requirements.txt         # مكتبات Python
├── README.md                # هذا الملف
├── .gitignore
├── ocr_results/             # نتائج المسح (يتم إنشاؤها)
│   └── scan_report.json     # تقرير النتائج
└── ocr_scan.log             # سجل التشغيل
```

## 🔧 Troubleshooting

### `tesseract is not installed`
تأكد من تثبيت Tesseract-OCR ومن وجوده في PATH.

### `yt-dlp not found`
```bash
pip install yt-dlp
```

### `OCR لا يعطي نتائج دقيقة`
- استخدم فيديوهات بدقة عالية
- تأكد من أن الـ outro يحتوي على نصوص واضحة
- جرب ضبط إعدادات Tesseract في الكود

## 🛡️ الأمان / Security

- لا يحتوي الكود على أي معلومات شخصية أو مسارات مشفرة
- يتم البحث عن Tesseract تلقائياً في PATH
- جميع الملفات المؤقتة تُحذف بعد المعالجة
- التحقق من صحة جميع المدخلات

## 📄 الترخيص / License

[MIT License](LICENSE) — استخدم بحرية للتطوير الشخصي والتجاري.

---

<p align="center">
  <strong>MUSTAFA MIXING</strong> — Global Music Credits & Rights Intelligence Agent<br>
  <sub>Built for Studio Baghdad · بغداد</sub>
</p>
