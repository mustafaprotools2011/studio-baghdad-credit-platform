#!/usr/bin/env python3
"""
تشغيل سريع للمشروع
python run.py
"""
import os, sys, subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)

# تشغيل الخادم
print("=" * 50)
print("🚀 MUSTAFA MIXING Dashboard")
print("=" * 50)
print(f"📂 المسار: {BASE}")
print()

# تثبيت المكتبات إذا لزم
try:
    import flask
except ImportError:
    print("📦 تثبيت المكتبات...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

# تشغيل
os.environ["MUSTAFA_MIXING_BASE"] = BASE
subprocess.run([sys.executable, "app.py"])
