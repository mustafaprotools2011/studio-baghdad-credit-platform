#!/usr/bin/env python3
"""Daily scan for Mustafa Kamal credits - 2026-06-28"""

import urllib.request
import urllib.parse
import re
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7'
    })
    return urllib.request.urlopen(req, timeout=timeout, context=ctx).read().decode('utf-8', errors='replace')

# =====================
# 1. GOOGLE SEARCH
# =====================
print("=" * 60)
print("GOOGLE SEARCH")
print("=" * 60)

queries = [
    '"Mustafa Kamal" "mixing engineer" Iraq',
    '"مهندس صوت" "مصطفى كمال" بغداد',
    '"Mustafa Kamal" "mix" "master" "عراق"',
    '"مصطفى كمال" "مكس" "ماستر"',
    'ستوديو بغداد "مصطفى كمال"',
]

for q in queries:
    url = f'https://www.google.com/search?q={urllib.parse.quote(q)}&hl=ar&num=10'
    print(f'\nQuery: {q}')
    try:
        html = fetch(url)
        
        # Extract links
        links = re.findall(r'href="(https?://[^"]*)"', html)
        relevant = []
        for l in links:
            if any(s in l.lower() for s in ['youtube.com/watch', 'facebook.com', 'instagram.com',
                                              'anghami.com', 'discogs.com', 'wneen.com',
                                              'soundcloud.com', 'tiktok.com']):
                if l not in relevant:
                    relevant.append(l)
        
        print(f'  Relevant links: {len(relevant)}')
        for l in relevant[:10]:
            print(f'    {l[:130]}')
        
        # Also look for text results
        results = re.findall(r'<div[^>]*class="[^"]*BNeawe[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
        for r in results[:3]:
            clean = re.sub(r'<[^>]+>', ' ', r).strip()[:150]
            if clean:
                print(f'  Result: {clean}')
                
    except Exception as e:
        print(f'  Error: {e}')

# =====================
# 2. ANGHAMI SEARCH
# =====================
print("\n" + "=" * 60)
print("ANGHAMI SEARCH")
print("=" * 60)

try:
    url = 'https://www.anghami.com/search?q=' + urllib.parse.quote('Mustafa Kamal')
    html = fetch(url)
    print(f'Page size: {len(html)} bytes')
    
    if 'مصطفى كمال' in html:
        print('Found "مصطفى كمال" on page')
    if 'Mustafa Kamal' in html:
        print('Found "Mustafa Kamal" on page')
    
    # Try to find any tracks or artist references
    tracks = re.findall(r'"trackName":"([^"]+)"', html)
    print(f'Tracks found: {len(tracks)}')
    for t in tracks[:10]:
        print(f'  - {t}')
    
    artists = re.findall(r'"artistName":"([^"]+)"', html)
    print(f'Artists found: {len(artists)}')
    for a in artists[:10]:
        print(f'  - {a}')
        
except Exception as e:
    print(f'Error: {e}')

# Also try Anghami API-style search
try:
    url2 = 'https://api.anghami.com/v4/search?q=' + urllib.parse.quote('مصطفى كمال') + '&type=artist'
    req = urllib.request.Request(url2, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    })
    resp = urllib.request.urlopen(req, timeout=10, context=ctx)
    data = json.loads(resp.read())
    print(f'API Response: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}')
except Exception as e:
    print(f'API error: {e}')

# =====================
# 3. DISCOGS SEARCH
# =====================
print("\n" + "=" * 60)
print("DISCOGS SEARCH")
print("=" * 60)

try:
    url = 'https://www.discogs.com/search/?q=Mustafa+Kamal&type=all'
    html = fetch(url)
    print(f'Page size: {len(html)} bytes')
    
    # Look for result titles
    titles = re.findall(r'<a[^>]*class="[^"]*search_result_title[^"]*"[^>]*>(.*?)</a>', html, re.DOTALL)
    print(f'Titles: {len(titles)}')
    for t in titles[:10]:
        clean = re.sub(r'<[^>]+>', '', t).strip()
        print(f'  - {clean[:100]}')
    
    # Also look for card titles
    cards = re.findall(r'card_title[^>]*>(.*?)</', html, re.DOTALL)
    print(f'Card titles: {len(cards)}')
    for c in cards[:10]:
        clean = re.sub(r'<[^>]+>', '', c).strip()
        print(f'  - {clean[:100]}')
        
    # Check for credits mention
    if 'مصطفى كمال' in html or 'Mustafa Kamal' in html:
        print('Found Mustafa Kamal reference')
        
except Exception as e:
    print(f'Error: {e}')

# Also search Discogs for artist page
try:
    url2 = 'https://www.discogs.com/search/?q=Mostapha+Kamal&type=all'
    html2 = fetch(url2)
    print(f'\nSearching "Mostapha Kamal":')
    titles2 = re.findall(r'<a[^>]*class="[^"]*search_result_title[^"]*"[^>]*>(.*?)</a>', html2, re.DOTALL)
    for t in titles2[:10]:
        clean = re.sub(r'<[^>]+>', '', t).strip()
        print(f'  - {clean[:100]}')
except Exception as e:
    print(f'Error: {e}')

# =====================
# 4. WNEEN.COM CHECK
# =====================
print("\n" + "=" * 60)
print("WNEEN.COM CHECK")
print("=" * 60)

try:
    # Master page
    url = 'https://www.wneen.com/master/13'
    html = fetch(url)
    print(f'Master page size: {len(html)} bytes')
    if 'مصطفى كمال' in html:
        # Count occurrences
        count = html.count('مصطفى كمال')
        print(f'Found "مصطفى كمال" {count} times')
    
    # Mixer page
    url2 = 'https://www.wneen.com/mixer/19'
    html2 = fetch(url2)
    print(f'Mixer page size: {len(html2)} bytes')
    if 'مصطفى كمال' in html2:
        count2 = html2.count('مصطفى كمال')
        print(f'Found "مصطفى كمال" {count2} times')
        
except Exception as e:
    print(f'Error: {e}')

print("\n" + "=" * 60)
print("SCAN COMPLETE")
print("=" * 60)
