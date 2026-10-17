#!/usr/bin/env python3
"""Render a code-drawn motion video: an HTML page exposing window.render(t) and window.TOTAL.

Usage: python3 render_motion.py page.html out.mp4 [--fps 30] [--frames DIR] [--hold 0.6]
Every frame is drawn deterministically by render(t), captured by headless Chromium, encoded with ffmpeg.
"""
import os, shutil, subprocess, sys, tempfile
from playwright.sync_api import sync_playwright

args = sys.argv[1:]
def opt(name, default):
    if name in args:
        i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
    return default
fps = int(opt("--fps", 30))
frames = opt("--frames", None)
hold = float(opt("--hold", 0.6))
page_path, out = os.path.abspath(args[0]), args[1]

tmp = frames or tempfile.mkdtemp(prefix="motion_")
os.makedirs(tmp, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch(args=["--force-color-profile=srgb", "--font-render-hinting=none"])
    pg = b.new_page(viewport={"width": 1080, "height": 1920}, device_scale_factor=1)
    pg.goto("file://" + page_path)
    pg.evaluate("document.fonts.ready.then(() => true)")
    pg.wait_for_timeout(300)
    total = pg.evaluate("window.TOTAL")
    n = int(round(total * fps))
    for i in range(n):
        pg.evaluate(f"window.render({i / fps})")
        pg.screenshot(path=os.path.join(tmp, f"f{i:05d}.jpg"), type="jpeg", quality=93)
    b.close()
last = os.path.join(tmp, f"f{n - 1:05d}.jpg")
for k in range(int(hold * fps)):
    shutil.copy(last, os.path.join(tmp, f"f{n + k:05d}.jpg"))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", os.path.join(tmp, "f%05d.jpg"),
                "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100", "-shortest",
                "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "17", "-preset", "medium",
                "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out], check=True)
if not frames:
    shutil.rmtree(tmp, ignore_errors=True)
print(f"rendered {out}: {total:.1f}s at {fps} fps")
