# MUSTAFA MIXING — Windows OCR Pipeline
# Run this on your PC one time, takes 2 mins per video with GPU

## Step 1: Install Python + Dependencies
# 1. Download Python 3.12 from python.org (check "Add to PATH")
# 2. Open CMD or PowerShell and run:

pip install yt-dlp easyocr pillow opencv-python torch torchvision --index-url https://download.pytorch.org/whl/cu121

## Step 2: Get YouTube Cookies
# In Chrome: Install "Get cookies.txt LOCALLY" extension
# Go to youtube.com, log in, click the extension icon → Download
# Save as cookies.txt

## Step 3: Create Desktop Folder
# mkdir C:\Users\%USERNAME%\Desktop\MUSTAFA_MIXING
# cd C:\Users\%USERNAME%\Desktop\MUSTAFA_MIXING
# Put cookies.txt and the script in this folder

## Step 4: Run Scan
# For ShababTV:
python ocr_credit_scanner.py --channel ShababTV --max-videos 50 --output results_shababtv

# For MCP TV Music:
python ocr_credit_scanner.py --channel MCPTVMusic --max-videos 34 --output results_mcp

# For a single video:
python ocr_credit_scanner.py --url "https://youtube.com/watch?v=VIDEO_ID"

## That's it! Results saved as JSON in the output folder
