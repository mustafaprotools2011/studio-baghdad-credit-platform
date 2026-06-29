#!/usr/bin/env python3
"""Parse Studio Baghdad RSS feed and check for Mustafa Kamal credits"""
import urllib.request
import xml.etree.ElementTree as ET
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Fetch RSS feed
url = "https://www.youtube.com/feeds/videos.xml?channel_id=UCuH7V5r6858lIrtIs-8Ayww"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
resp = urllib.request.urlopen(req, timeout=15, context=ctx)
data = resp.read().decode('utf-8', errors='replace')

root = ET.fromstring(data.encode('utf-8'))

ns = {
    'atom': 'http://www.w3.org/2005/Atom',
    'yt': 'http://www.youtube.com/xml/schemas/2015',
    'media': 'http://search.yahoo.com/mrss/'
}

entries = root.findall('atom:entry', ns)
print(f'Total entries: {len(entries)}')
print()

mustafa_patterns = ['مصطفى كمال', 'مصطفى كامل', 'mustafa kamal', 'mostapha kamal', 'مصطفى کمال']

for entry in entries:
    vid_elem = entry.find('yt:videoId', ns)
    title_elem = entry.find('atom:title', ns)
    pub_elem = entry.find('atom:published', ns)
    link_elem = entry.find('atom:link', ns)
    media_desc = entry.find('.//media:description', ns)
    
    vid = vid_elem.text if vid_elem is not None else '?'
    title = title_elem.text if title_elem is not None else '?'
    published = pub_elem.text if pub_elem is not None else '?'
    url = link_elem.get('href') if link_elem is not None else ''
    description = media_desc.text if media_desc is not None else ''
    
    # Check if description mentions Mustafa Kamal
    has_mustafa = False
    if description:
        for p in mustafa_patterns:
            if p in description.lower():
                has_mustafa = True
                break
    
    marker = ' *** MUSTAFA ***' if has_mustafa else ''
    print(f'{vid} | {published[:10]} | {title[:70]} | {url}{marker}')
    if has_mustafa:
        print(f'  Description: {description[:300]}')
