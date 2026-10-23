#!/usr/bin/env python3
"""Build one reel from a folder containing spec.json (and, for old hand-coded reels, page.html).

v4 (default): no page.html. Every line in spec.json names a ready-made scene from engine/reel.html:
  {"slug": "...", "lead": 0, "meter": {"label": "TIME LOST / WEEK", "unit": "minutes"},
   "lines": [{"text": "...*key*...", "section": "01 of 03 / ...", "cost": [0.5, 120], "pose": "shock",
              "scene": {"type": "stakes", "value": "6h", "label": "lost every week", "behind": "table"}}, ...]}
  Scene types: stakes, chat, cards, table_scroll, filter, sort, bulk, buttons, dialog, toast, dashboard, checklist, bignum, outro.

usage: python3 engine/make_reel.py DIR [--mode voice|text] [--preview]

spec.json: {"slug": "2026-10-19-topic", "voice": "am_michael",
            "lines": [{"text": "narration line", "card": "headline for text mode (html ok)", "dur": 2.0 (text mode only, optional)}]}
page.html: a page in the engine style (see examples/). It must read window.CFG
  ({mode, gap, tail, lines:[{text, dur, card}]}) and expose window.render(t) and window.TOTAL.
Output: videos/<slug>.mp4 (voice mode) or videos/<slug>-novoice.mp4 (text mode).
--preview writes DIR/preview.png (contact sheet of 8 frames) and stops before encoding.
"""
import json, os, subprocess, sys, urllib.request
import numpy as np, soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENG = os.path.join(ROOT, "engine")
args = sys.argv[1:]
d = os.path.abspath(args[0])
mode = args[args.index("--mode") + 1] if "--mode" in args else "voice"
spec = json.load(open(os.path.join(d, "spec.json")))
lines = spec["lines"]
for ln in lines:
    for k in ("text", "card"):
        if "—" in ln.get(k, ""):
            sys.exit("em dash found in spec; rewrite the line")
GAP, TAIL = 0.12, 0.5
LEAD = float(spec.get("lead", 0.15))   # seconds of silence before the first line; the v3 template uses 0

if mode == "voice":
    cache = os.path.expanduser("~/.cache/kokoro"); os.makedirs(cache, exist_ok=True)
    base = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
    for f in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
        p = os.path.join(cache, f)
        if not os.path.exists(p):
            print("downloading", f); urllib.request.urlretrieve(base + f, p)
    from kokoro_onnx import Kokoro
    k = Kokoro(os.path.join(cache, "kokoro-v1.0.onnx"), os.path.join(cache, "voices-v1.0.bin"))
    chunks, sr = [], 24000
    for i, ln in enumerate(lines):
        a, sr = k.create(ln["text"].replace("*", ""), voice=spec.get("voice", "am_michael"), speed=1.12, lang="en-us")
        ln["dur"] = round(len(a) / sr, 3)
        if not chunks: chunks.append(np.zeros(int(LEAD * sr)))
        chunks += [a, np.zeros(int(GAP * sr))]
    wav = os.path.join(d, "narration.wav"); sf.write(wav, np.concatenate(chunks), sr)
else:
    for ln in lines:
        ln["dur"] = ln.get("dur") or max(1.8, min(4.2, len(ln["text"].split()) * 0.36))

cfg = {"mode": mode, "gap": GAP, "tail": TAIL, "lead": LEAD, "lines": lines}
SCENES = {"hook", "stakes", "chat", "cards", "table_scroll", "filter", "sort", "bulk", "buttons", "dialog", "toast", "dashboard", "checklist", "bignum", "outro"}
page = os.path.join(d, "page.html")
if not os.path.exists(page):
    page = os.path.join(ENG, "reel.html")
    for i, ln in enumerate(lines):
        t = (ln.get("scene") or {}).get("type")
        if t not in SCENES:
            sys.exit(f"line {i + 1}: scene type {t!r} is not one of {sorted(SCENES)}")
    cfg["meter"] = spec.get("meter", {"label": "TIME LOST / WEEK", "unit": "minutes"})
src = open(page).read().replace("../../engine/", os.path.relpath(ENG, d).replace(os.sep, "/") + "/")
built = os.path.join(d, f"_built_{mode}.html")
open(built, "w").write(src.replace("<script>", f"<script>window.CFG={json.dumps(cfg)};</script>\n<script>", 1))
print(f"{mode}: {sum(l['dur'] for l in lines):.1f}s narration across {len(lines)} lines")

if "--preview" in args:
    T = sum(l["dur"] + GAP for l in lines) + LEAD
    ts = ",".join(f"{T * (i + 0.6) / 8:.2f}" for i in range(8))
    subprocess.run([sys.executable, os.path.join(ENG, "snap.py"), built, os.path.join(d, "preview.png"), ts], check=True)
    sys.exit(0)

os.makedirs(os.path.join(ROOT, "videos"), exist_ok=True)
slug = spec["slug"] + ("" if mode == "voice" else "-novoice")
out = os.path.join(ROOT, "videos", slug + ".mp4")
silent = os.path.join(d, "_silent.mp4")
subprocess.run([sys.executable, os.path.join(ENG, "render_motion.py"), built, silent if mode == "voice" else out, "--hold", "0.4"], check=True)
if mode == "voice":
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "160k", "-af", "loudnorm=I=-14:TP=-1.5,apad", "-shortest", "-movflags", "+faststart", out], check=True)
    os.remove(silent)
print("wrote", out)
