#!/usr/bin/env python3
"""Parse Nasrat Al Bader Studios RSS feed and check for Mustafa Kamal credits"""
import urllib.request
import xml.etree.ElementTree as ET
import ssl
from datetime import datetime, timezone

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://www.youtube.com/feeds/videos.xml?channel_id=UCG9NsIXjajFP_TNkidggUjw"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
resp = urllib.request.urlopen(req, timeout=15, context=ctx)
data = resp.read().decode('utf-8', errors='replace')

root = ET.fromstring(data.encode('utf-8'))

ns = {
    'atom': 'http://www.w3.org/2005/Atom',
    'yt': 'http://www.youtube.com/xml/schemas/2015',
    'media': 'http://search.yahoo.com/mrss/'
}

now = datetime.now(timezone.utc)
print(f'=== ستوديوهات نصرت البدر Channel ===')
print(f'Current time: {now.isoformat()}')
print()

mustafa_patterns = ['مصطفى كمال', 'مصطفى كامل', 'mustafa kamal', 'mostapha kamal', 'مصطفى کمال']

entries = root.findall('atom:entry', ns)
print(f'Total entries: {len(entries)}')

for entry in entries:
    vid_elem = entry.find('yt:videoId', ns)
    title_elem = entry.find('atom:title', ns)
    pub_elem = entry.find('atom:published', ns)
    up_elem = entry.find('atom:updated', ns)
    media_desc = entry.find('.//media:description', ns)
    
    vid = vid_elem.text if vid_elem is not None else '?'
    title = title_elem.text if title_elem is not None else '?'
    published = pub_elem.text[:10] if pub_elem is not None else '?'
    description = media_desc.text if media_desc is not None else ''
    
    updated_str = up_elem.text if up_elem is not None else '?'
    if updated_str and updated_str != '?':
        updated = datetime.fromisoformat(updated_str.replace('Z', '+00:00'))
        delta = now - updated
        hours_ago = delta.total_seconds() / 3600
    else:
        hours_ago = -1
    
    has_mustafa = False
    mustafa_note = ''
    if description:
        for p in mustafa_patterns:
            if p in description.lower():
                has_mustafa = True
                # Find the context
                idx = description.lower().find(p)
                mustafa_note = description[max(0,idx-30):idx+80].replace('\n', ' | ')
                break
    
    marker = ' *** MUSTAFA ***' if has_mustafa else ''
    print(f'{hours_ago:6.1f}h ago | {published} | {vid} | {title[:60]} | {marker}')
    if has_mustafa:
        print(f'  Context: {mustafa_note}')
