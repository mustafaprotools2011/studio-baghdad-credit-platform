#!/usr/bin/env python3
"""Check latest uploads from Shabab Alqithara channel for Mustafa Kamal credits"""
import urllib.request
import xml.etree.ElementTree as ET
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

channel_id = "UC0e4Rnb9u7b2YBWQN7e7B6A"
url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})
resp = urllib.request.urlopen(req, timeout=15, context=ctx)
data = resp.read().decode('utf-8', errors='replace')

root = ET.fromstring(data)
ns = {'atom': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
entries = root.findall('atom:entry', ns)

print(f"Total entries in Shabab Alqithara feed: {len(entries)}")
print()

# Check the most recent uploads - look at their descriptions for Mustafa Kamal
for entry in entries[:15]:
    title = entry.find('atom:title', ns)
    published = entry.find('atom:published', ns)
    vid_elem = entry.find('yt:videoId', ns)
    vid = vid_elem.text if vid_elem is not None else '?'
    title_text = title.text if title is not None else '?'
    pub = published.text if published is not None else '?'
    
    # Also get the description to check for credits
    # Note: RSS doesn't include full description easily
    print(f"{vid} | {pub[:10]} | {title_text[:80]}")
