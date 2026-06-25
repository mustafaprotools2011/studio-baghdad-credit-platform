# MUSTAFA MIXING - Channels & Artists to Scan
# Copy this whole folder to your PC and run:
# python ocr_credit_scanner.py --channel ShababTV --max-videos 100
# python ocr_credit_scanner.py --channel MCPTVMusic --max-videos 34
# python ocr_credit_scanner.py --channel AlHaneen

# KNOWN ARTISTS (from user: حسام الرسام, نور الزين, زيد الحبيب, قائد حلمي, فضل شاكر)
# Each artist name is followed by their YouTube search/channel

# To scan by artist name search (finds all videos with that name):
# yt-dlp --flat-playlist --print "%(id)s|%(title)s" "ytsearch100:نور الزين"

# Already scanned:
# - MCP TV Music: 34 videos (2010-2014) - includes زيد الحبيب, قائد حلمي
# - ShababTV: 50 videos (2021-2026) - includes حسين غزال, عبد الله البدر
# - AlHaneen: 3 videos (Dabkeh)
# - Music AlRemas: 1 video scanned (نور الزين - no credits found)

# Pending artist searches:
# حسام الرسام - 80 videos searched (0 matches in descriptions)
# نور الزين - needs full OCR
# فضل شاكر - needs search
