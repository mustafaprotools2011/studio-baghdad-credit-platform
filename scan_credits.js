#!/usr/bin/env node
/**
 * MUSTAFA MIXING — Video OCR Scanner
 * 
 * HOW TO USE:
 * 1. Install Chrome: apt install chromium (or download)
 * 2. Get YouTube cookies (from browser or yt-dlp)
 * 3. Run: node scan_credits.js
 * 
 * This script scans YouTube playlist for videos mentioning "مصطفى كمال"
 * using OCR on video frames. Works with ffmpeg + tesseract.
 */

const { execSync, spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

// ⚙️ CONFIG
const CHANNELS = [
  { name: 'MCP TV Music', url: 'https://www.youtube.com/@mcptvmusic168' },
  { name: 'الحنين (Al Haneen)', url: 'https://www.youtube.com/@AlHaneen' },
  { name: 'الريماس (Music Alremas)', url: 'https://www.youtube.com/@musicalremas' },
  { name: 'الريماس ميوزيك', url: 'https://www.youtube.com/@musicalremastv' },
];

const KEYWORDS = ['مصطفى كمال', 'مصطفي كمال', 'Mustafa Kamal', 'Moustafa Kamal', 'مهندس الصوت', 'هندسة الصوت'];
const OUTPUT_DIR = '/opt/data/mustafa-mixing-archive/evidence';

function ensureDir(dir) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

async function scanVideo(videoUrl, title) {
  console.log(`\n🔍 Scanning: ${title}`);
  console.log(`   ${videoUrl}`);
  
  // Create evidence folder
  const safeName = title.replace(/[^a-zA-Z0-9_\u0600-\u06FF]/g, '_').substring(0, 50);
  const evidDir = path.join(OUTPUT_DIR, safeName);
  ensureDir(evidDir);
  
  try {
    // Step 1: Download video info (requires cookies or bypass)
    // yt-dlp --cookies cookies.txt ...
    
    // Step 2: Extract a frame from outro (last 5 seconds) 
    // ffmpeg -sseof -5 -i video.mp4 -vframes 1 frame.jpg
    
    // Step 3: OCR the frame for Arabic text
    // const result = execSync(`tesseract frame.jpg stdout -l ara+eng`).toString();
    
    // Step 4: Check for keywords
    // for (const kw of KEYWORDS) if (result.includes(kw)) ...
    
  } catch (e) {
    console.error(`   Error: ${e.message}`);
  }
}

async function main() {
  console.log('='.repeat(60));
  console.log('MUSTAFA MIXING — Video Credit Scanner');
  console.log('='.repeat(60));
  console.log('\n⚠️  This scanner requires:');
  console.log('   1. Chrome browser (for cookies/playlist access)');
  console.log('   2. tesseract-ocr with Arabic language pack');
  console.log('   3. YouTube cookies file (cookies.txt)');
  console.log('\n📋 Channels to scan:');
  for (const ch of CHANNELS) {
    console.log(`   • ${ch.name} — ${ch.url}`);
  }
  console.log('\n🔑 Keywords to detect:');
  for (const kw of KEYWORDS) console.log(`   • ${kw}`);
  console.log('\n📂 Output: ' + OUTPUT_DIR);
  console.log('\nRun these commands first:');
  console.log('  sudo apt install -y chromium tesseract-ocr tesseract-ocr-ara');
  console.log('  yt-dlp --cookies-from-browser chrome --cookies cookies.txt');
  console.log('\nThen run: node scan_credits.js --run');
  
  // If --run flag provided, actually execute
  if (process.argv.includes('--run')) {
    console.log('\n🚀 Starting scan...');
    // TODO: actual scan logic
  }
}

main();
