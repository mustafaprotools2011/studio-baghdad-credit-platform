#!/usr/bin/env python3
"""Check Studio Baghdad channel for latest uploads"""
import urllib.request
import json
import ssl
import re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

channel_id = "UCuH7V5r6858lIrtIs-8Ayww"
print(f"=== Studio Baghdad Channel ({channel_id}) - Latest Videos ===")

url = f"https://www.youtube.com/channel/{channel_id}/videos"
req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})
resp = urllib.request.urlopen(req, timeout=15, context=ctx)
html = resp.read().decode('utf-8', errors='replace')

match = re.search(r'ytInitialData\s*=\s*({.*?});', html, re.DOTALL)
if match:
    data = json.loads(match.group(1))
    tabs = data.get('contents', {}).get('twoColumnBrowseResultsRenderer', {}).get('tabs', [])
    print(f"Found {len(tabs)} tabs")
    
    for tab in tabs:
        trenderer = tab.get('tabRenderer', {})
        title = trenderer.get('title', '')
        print(f"  Tab: {title}")
        
        if title in ('Videos', 'فيديوهات'):
            content = trenderer.get('content', {})
            # Try richGridRenderer
            grid = content.get('richGridRenderer', {})
            if grid:
                items = grid.get('contents', [])
                print(f"    Found {len(items)} items in richGridRenderer")
                for item in items:
                    rich_item = item.get('richItemRenderer', {})
                    if rich_item:
                        vrender = rich_item.get('content', {}).get('videoRenderer', {})
                        if vrender:
                            vid = vrender.get('videoId', '')
                            title_runs = vrender.get('title', {}).get('runs', [])
                            vtitle = ''.join([r.get('text', '') for r in title_runs])
                            published = vrender.get('publishedTimeText', {}).get('simpleText', '')
                            views = vrender.get('viewCountText', {}).get('simpleText', '')
                            print(f"    {vid}: {vtitle} | {published} | {views}")
            
            # Try gridRenderer
            grid2 = content.get('gridRenderer', {})
            if grid2:
                items = grid2.get('items', [])
                print(f"    Found {len(items)} items in gridRenderer")
                for item in items:
                    vrender = item.get('gridVideoRenderer', {})
                    if vrender:
                        vid = vrender.get('videoId', '')
                        title_runs = vrender.get('title', {}).get('runs', [])
                        vtitle = ''.join([r.get('text', '') for r in title_runs])
                        published = vrender.get('publishedTimeText', {}).get('simpleText', '')
                        print(f"    {vid}: {vtitle} | {published}")
    if not tabs:
        print("No tabs found, checking for continuation items...")
        # Try else
        contents = data.get('contents', {}).get('twoColumnBrowseResultsRenderer', {})
        print(f"Contents keys: {contents.keys()}")
        # Try primary contents
        primary = contents.get('primaryContents', {})
        print(f"Primary keys: {primary.keys()}")
else:
    print("No ytInitialData found")
    # Try finding channel RSS feed
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        req2 = urllib.request.Request(rss_url, headers={
            'User-Agent': 'Mozilla/5.0'
        })
        resp2 = urllib.request.urlopen(req2, timeout=15, context=ctx)
        rss = resp2.read().decode('utf-8', errors='replace')
        print(f"\nRSS Feed ({len(rss)} chars):")
        print(rss[:2000])
    except Exception as e2:
        print(f"RSS Error: {e2}")
