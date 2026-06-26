@echo off
chcp 65001 >nul
echo ============================================
echo MUSTAFA MIXING — OCR Scanner v2
echo ============================================
echo.
echo 1) مسح قناة
echo 2) مسح من ملف URLs
echo 3) exit
echo.
set /p MODE="اختر (1-3): "

if "%MODE%"=="3" exit /b

if "%MODE%"=="1" (
    echo.
    echo اختر قناة للمسح:
    echo 1) ShababTV
    echo 2) MCP TV Music
    echo 3) AlHaneen
    echo 4) AlRemas (Music AlRemas)
    echo 5) قناة مخصصة (اكتب الاسم)
    echo.
    set /p ch="رقم القناة (1-5): "

    if "!ch!"=="1" set CHANNEL=ShababTV
    if "!ch!"=="2" set CHANNEL=MCPTVMusic
    if "!ch!"=="3" set CHANNEL=AlHaneen
    if "!ch!"=="4" set CHANNEL=musicAlRemas
    if "!ch!"=="5" (
        set /p CHANNEL="اكتب اسم القناة: "
    )

    set /p MAX="عدد الفيديوهات (Enter = 30): "
    if "!MAX!"=="" set MAX=30

    echo.
    echo بدأ المسح للقناة @%CHANNEL% - %MAX% فيديو
    echo.
    set TAIL=15
    set /p TAIL="آخر كم ثانية (10-15, Enter=15): "
    if "!TAIL!"=="" set TAIL=15

    "C:\Users\musta\AppData\Local\hermes\hermes-agent\venv\Scripts\python" ocr_credit_scanner.py --channel %CHANNEL% --max %MAX% --tail %TAIL%
    goto :DONE
)

if "%MODE%"=="2" (
    if not exist urls.txt (
        echo.
        echo ⚠️  ملف urls.txt غير موجود!
        echo إنشئ الملف وضع فيه روابط يوتيوب (سطر لكل رابط)
        echo.
        pause
        exit /b
    )
    set /p TAIL="آخر كم ثانية (10-15, Enter=15): "
    if "!TAIL!"=="" set TAIL=15

    "C:\Users\musta\AppData\Local\hermes\hermes-agent\venv\Scripts\python" ocr_credit_scanner.py --urls-file urls.txt --tail %TAIL%
    goto :DONE
)

:DONE
echo.
echo تم المسح! النتائج في مجلد ocr_results/
pause
