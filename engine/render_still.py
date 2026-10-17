#!/usr/bin/env python3
"""Render a faceless, typographic Instagram reel (1080x1920, 30 fps) from a JSON spec.

Usage:
  python3 render_reel.py spec.json out.mp4 --fonts FONT_DIR [--frames-only DIR]

FONT_DIR must hold: sans.ttf (Inter, static or variable) and mono.ttf (IBM Plex Mono or any mono).

Spec:
{
  "signature": "Muhh",                 # small label in the corner and on the outro
  "scenes": [
    {"type": "hook",   "lines": ["Your activation rate", "is a *design decision*."], "dur": 3.0},
    {"type": "text",   "kicker": "the usual setup", "lines": ["..."], "dur": 3.5},
    {"type": "bars",   "kicker": "illustrative numbers", "title": "...",
                       "items": [{"label": "Signed up", "value": 100}, ...], "suffix": "%", "dur": 4.5},
    {"type": "number", "kicker": "...", "value": 38, "suffix": "%", "caption": ["...", "..."], "dur": 3.5},
    {"type": "compare","left_title": "what teams track", "left": ["..."],
                       "right_title": "what it means", "right": ["..."], "dur": 4.5},
    {"type": "outro",  "lines": ["Metrics are", "*design decisions.*"], "cta": "follow for more", "dur": 3.0}
  ]
}
Wrap a phrase in *asterisks* to paint it in the accent color. Keep lines short: the renderer
wraps long lines, but 3 to 5 short lines per scene read best on a phone.
"""
import json, math, os, shutil, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
PAPER = (244, 241, 234)
INK = (20, 20, 20)
MUTED = (120, 116, 108)
LINE = (214, 209, 198)
ACCENT = (43, 75, 238)
SAFE_L, SAFE_R, SAFE_T, SAFE_B = 96, 1080 - 150, 250, 1920 - 420

FONT_DIR = "."
_font_cache = {}

def font(kind, size, weight=400):
    key = (kind, size, weight)
    if key in _font_cache:
        return _font_cache[key]
    path = os.path.join(FONT_DIR, "sans.ttf" if kind == "sans" else "mono.ttf")
    f = ImageFont.truetype(path, size)
    try:  # variable font: set weight (and optical size when present)
        axes = f.get_variation_axes()
        vals = []
        for ax in axes:
            name = ax.get("name", b"")
            name = name.decode() if isinstance(name, bytes) else str(name)
            lo, hi = ax["minimum"], ax["maximum"]
            if "eight" in name or name.lower().startswith("wght"):
                vals.append(max(lo, min(hi, weight)))
            elif "ptical" in name or name.lower().startswith("opsz"):
                vals.append(max(lo, min(hi, size / 2)))
            else:
                vals.append(ax.get("default", lo))
        if vals:
            f.set_variation_by_axes(vals)
    except Exception:
        pass
    _font_cache[key] = f
    return f

def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))

def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3

def ease_in_out(t):
    t = clamp(t)
    return 3 * t * t - 2 * t * t * t

def blend(c, bg, a):
    return tuple(int(bg[i] + (c[i] - bg[i]) * a) for i in range(3))

def parse_rich(line):
    """'a *b* c' -> [('a ', False), ('b', True), (' c', False)]"""
    out, acc, buf = [], False, ""
    for ch in line:
        if ch == "*":
            if buf:
                out.append((buf, acc))
            buf, acc = "", not acc
        else:
            buf += ch
    if buf:
        out.append((buf, acc))
    return out

def wrap_rich(line, f, max_w):
    words = []
    for seg, acc in parse_rich(line):
        for i, w in enumerate(seg.split(" ")):
            if i > 0:
                words.append((" ", acc))
            if w:
                words.append((w, acc))
    lines, cur, cur_w = [], [], 0
    for w, acc in words:
        ww = f.getlength(w)
        if w == " ":
            if cur:
                cur.append((w, acc))
                cur_w += ww
            continue
        if cur and cur_w + ww > max_w:
            while cur and cur[-1][0] == " ":
                cur_w -= f.getlength(" ")
                cur.pop()
            lines.append(cur)
            cur, cur_w = [], 0
        cur.append((w, acc))
        cur_w += ww
    if cur:
        lines.append(cur)
    return lines

def draw_rich_line(d, x, y, parts, f, alpha, underline_acc=True):
    cx = x
    for w, acc in parts:
        col = blend(ACCENT if acc else INK, PAPER, alpha)
        d.text((cx, y), w, font=f, fill=col)
        cx += f.getlength(w)
    return cx

def text_block(d, lines, t, x, y, size, weight=700, lead=1.12, stagger=0.12, max_w=None):
    """Lines rise and fade in one after another. Returns bottom y."""
    f = font("sans", size, weight)
    max_w = max_w or (SAFE_R - x)
    wrapped = []
    for ln in lines:
        wrapped.extend(wrap_rich(ln, f, max_w))
    lh = int(size * lead)
    for i, parts in enumerate(wrapped):
        p = ease_out((t - i * stagger) / 0.45)
        if p <= 0:
            continue
        draw_rich_line(d, x, y + i * lh + int((1 - p) * 40), parts, f, p)
    return y + len(wrapped) * lh

def block_h(lines, size, weight=700, lead=1.12, max_w=None):
    f = font("sans", size, weight)
    max_w = max_w or (SAFE_R - SAFE_L)
    n = sum(len(wrap_rich(ln, f, max_w)) for ln in lines)
    return n * int(size * lead)

def fit_size(lines, size, weight=800, min_size=68):
    """Shrink until no authored line has to wrap (keeps hooks from orphaning one word)."""
    while size > min_size:
        f = font("sans", size, weight)
        if all(len(wrap_rich(ln, f, SAFE_R - SAFE_L)) == 1 for ln in lines):
            break
        size -= 4
    return size

def centered_y(h):
    mid = (SAFE_T + 60 + SAFE_B) // 2
    return max(SAFE_T + 120, mid - h // 2)

def kicker(d, txt, t, y):
    if not txt:
        return y
    p = ease_out(t / 0.4)
    f = font("mono", 34, 400)
    d.text((SAFE_L, y), txt.lower(), font=f, fill=blend(MUTED, PAPER, p))
    w = int(70 * p)
    d.rectangle([SAFE_L, y + 56, SAFE_L + w, y + 60], fill=ACCENT)
    return y + 110

def chrome(d, sig, gt, total, idx, n):
    d.rectangle([SAFE_L, 180, SAFE_R, 184], fill=LINE)
    d.rectangle([SAFE_L, 180, SAFE_L + int((SAFE_R - SAFE_L) * clamp(gt / total)), 184], fill=INK)
    f = font("mono", 30, 400)
    d.text((SAFE_L, 205), sig.lower() + "_", font=f, fill=MUTED)
    lab = f"{idx + 1:02d}/{n:02d}"
    d.text((SAFE_R - f.getlength(lab), 205), lab, font=f, fill=MUTED)

def cursor(d, x, y, h, gt):
    if int(gt * 2) % 2 == 0:
        d.rectangle([x + 8, y + h - 14, x + 8 + int(h * 0.55), y + h - 2], fill=ACCENT)

def scene_hook(d, s, t, gt):
    size = fit_size(s["lines"], s.get("size", 96))
    h = block_h(s["lines"], size, 800, 1.08) + (block_h([s["sub"]], 46, 500, 1.3) + 50 if s.get("sub") else 0)
    bottom = text_block(d, s["lines"], t, SAFE_L, centered_y(h), size, 800, 1.08, 0.18)
    if s.get("sub"):
        text_block(d, [s["sub"]], t - 0.6, SAFE_L, bottom + 50, 46, 500, 1.3)

def scene_text(d, s, t, gt):
    size = s.get("size", 76)
    h = block_h(s["lines"], size, 700, 1.16) + (110 if s.get("kicker") else 0)
    y = kicker(d, s.get("kicker"), t, centered_y(h))
    text_block(d, s["lines"], t - 0.15, SAFE_L, y, size, 700, 1.16, 0.22)

def scene_bars(d, s, t, gt):
    y = kicker(d, s.get("kicker"), t, 520)
    if s.get("title"):
        y = text_block(d, [s["title"]], t - 0.1, SAFE_L, y, 60, 700, 1.15) + 60
    items = s["items"]
    vmax = max(i["value"] for i in items) or 1
    fl = font("sans", 40, 500)
    fv = font("mono", 40, 500)
    bar_w_max = SAFE_R - SAFE_L
    row = 170
    for k, it in enumerate(items):
        p = ease_in_out((t - 0.5 - k * 0.45) / 0.9)
        a = ease_out((t - 0.4 - k * 0.45) / 0.3)
        if a <= 0:
            continue
        ry = y + k * row
        d.text((SAFE_L, ry), it["label"], font=fl, fill=blend(INK, PAPER, a))
        by = ry + 60
        d.rectangle([SAFE_L, by, SAFE_R, by + 54], fill=blend(LINE, PAPER, a))
        bw = int(bar_w_max * (it["value"] / vmax) * p)
        hl = it.get("highlight", False)
        if bw > 0:
            d.rectangle([SAFE_L, by, SAFE_L + bw, by + 54], fill=ACCENT if hl else INK)
        val = f"{round(it['value'] * p)}{s.get('suffix', '')}"
        vw = fv.getlength(val)
        vx = SAFE_L + bw + 16
        if vx + vw > SAFE_R - 10:
            d.text((SAFE_L + bw - vw - 16, by + 5), val, font=fv, fill=PAPER)
        else:
            d.text((vx, by + 5), val, font=fv, fill=blend(INK, PAPER, a))
    if s.get("note"):
        ny = y + len(items) * row + 30
        text_block(d, [s["note"]], t - 0.6 - len(items) * 0.45, SAFE_L, ny, 50, 600, 1.2)

def scene_number(d, s, t, gt):
    y = kicker(d, s.get("kicker"), t, 560)
    p = ease_out((t - 0.2) / 1.2)
    val = s["value"]
    shown = f"{val * p:.{s.get('decimals', 0)}f}{s.get('suffix', '')}"
    f = font("sans", 300, 800)
    d.text((SAFE_L - 10, y - 40), shown, font=f, fill=blend(ACCENT, PAPER, ease_out(t / 0.3)))
    text_block(d, s.get("caption", []), t - 0.9, SAFE_L, y + 330, 62, 700, 1.15, 0.2)

def scene_compare(d, s, t, gt):
    y = kicker(d, s.get("kicker"), t, 640)
    fh = font("mono", 32, 400)
    col_w = (SAFE_R - SAFE_L - 40) // 2
    xs = [SAFE_L, SAFE_L + col_w + 40]
    for c, (title, rows, col) in enumerate([(s["left_title"], s["left"], INK), (s["right_title"], s["right"], ACCENT)]):
        a = ease_out((t - c * 0.25) / 0.4)
        d.text((xs[c], y), title.lower(), font=fh, fill=blend(MUTED, PAPER, a))
        d.rectangle([xs[c], y + 52, xs[c] + col_w, y + 54], fill=blend(LINE, PAPER, a))
        fr = font("sans", 46, 700 if c else 500)
        ry = y + 90
        for k, r in enumerate(rows):
            p = ease_out((t - 0.4 - k * 0.35 - c * 0.18) / 0.4)
            if p <= 0:
                continue
            for ln in wrap_rich(r, fr, col_w):
                cx = xs[c]
                for w, acc in ln:
                    d.text((cx, ry + int((1 - p) * 24)), w, font=fr, fill=blend(col, PAPER, p))
                    cx += fr.getlength(w)
                ry += 58
            ry += 46

def mono_wrap(txt, f, max_w):
    out, cur = [], ""
    for w in txt.split(" "):
        cand = (cur + " " + w).strip()
        if cur and f.getlength(cand) > max_w:
            out.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        out.append(cur)
    return out

def scene_outro(d, s, t, gt):
    size = fit_size(s["lines"], s.get("size", 100))
    fm = font("mono", 38, 400)
    cta = mono_wrap(s["cta"].lower(), fm, SAFE_R - SAFE_L) if s.get("cta") else []
    h = block_h(s["lines"], size, 800, 1.08) + (70 + 52 * len(cta) if cta else 0)
    bottom = text_block(d, s["lines"], t, SAFE_L, centered_y(h), size, 800, 1.08, 0.2)
    f = font("sans", size, 800)
    last = wrap_rich(s["lines"][-1], f, SAFE_R - SAFE_L)[-1]
    lw = sum(f.getlength(w) for w, _ in last)
    if t > 0.6:
        cursor(d, SAFE_L + int(lw), bottom - int(size * 1.08), int(size * 1.0), gt)
    a = ease_out((t - 0.9) / 0.4)
    for i, ln in enumerate(cta):
        d.text((SAFE_L, bottom + 70 + i * 52), ln, font=fm, fill=blend(MUTED, PAPER, a))

WHITE = (255, 255, 255)
SOFT = (247, 245, 240)
RED = (204, 62, 50)
GREEN = (38, 138, 82)
BW = 680  # base width every screen is drawn at, then scaled up

def tint(c, a):
    return blend(c, WHITE, a)

def btn_w(b, f):
    return int(f.getlength(b["label"])) + 40

def draw_button(d, x, y, b, h=56):
    f = font("sans", 24, 600)
    w = btn_w(b, f)
    kind = b.get("kind", "ghost")
    if kind == "primary":
        d.rounded_rectangle([x, y, x + w, y + h], 12, fill=ACCENT)
        col = WHITE
    elif kind == "danger":
        d.rounded_rectangle([x, y, x + w, y + h], 12, fill=RED)
        col = WHITE
    elif kind == "danger-ghost":
        d.rounded_rectangle([x, y, x + w, y + h], 12, fill=WHITE, outline=RED, width=3)
        col = RED
    else:
        d.rounded_rectangle([x, y, x + w, y + h], 12, fill=WHITE, outline=LINE, width=3)
        col = INK
    d.text((x + 20, y + h / 2), b["label"], font=f, fill=col, anchor="lm")
    return w

def wrap_plain(txt, f, max_w):
    out, cur = [], ""
    for w in txt.split(" "):
        cand = (cur + " " + w).strip()
        if cur and f.getlength(cand) > max_w:
            out.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        out.append(cur)
    return out

def status_colors(txt):
    t = txt.lower()
    if any(k in t for k in ("overdue", "failed", "error", "blocked", "expired", "rejected")):
        return tint(RED, 0.14), RED
    if any(k in t for k in ("paid", "active", "done", "approved", "live", "sent")):
        return tint(GREEN, 0.14), GREEN
    if any(k in t for k in ("pending", "review", "draft", "due")):
        return tint((196, 140, 20), 0.16), (150, 100, 10)
    return SOFT, MUTED

def c_toolbar(d, x, y, w, c):
    f = font("sans", 32, 700)
    d.text((x, y + 32), c.get("left", ""), font=f, fill=INK, anchor="lm")
    fb = font("sans", 24, 600)
    bx = x + w
    for b in reversed(c.get("buttons", [])):
        bx -= btn_w(b, fb)
        draw_button(d, bx, y + 4, b)
        bx -= 14
    return 64

def c_search(d, x, y, w, c):
    d.rounded_rectangle([x, y, x + w, y + 60], 12, fill=WHITE, outline=LINE, width=3)
    d.ellipse([x + 22, y + 18, x + 42, y + 38], outline=MUTED, width=3)
    d.line([x + 40, y + 36, x + 48, y + 44], fill=MUTED, width=3)
    d.text((x + 64, y + 30), c.get("placeholder", "Search"), font=font("sans", 26, 400), fill=MUTED, anchor="lm")
    return 60

def c_chips(d, x, y, w, c):
    f = font("sans", 24, 500)
    cx = x
    active = set(c.get("active", []))
    for i, it in enumerate(c.get("items", [])):
        cw = int(f.getlength(it)) + 40
        if cx + cw > x + w:
            break
        if i in active:
            d.rounded_rectangle([cx, y, cx + cw, y + 48], 24, fill=tint(ACCENT, 0.14), outline=ACCENT, width=3)
        else:
            d.rounded_rectangle([cx, y, cx + cw, y + 48], 24, fill=WHITE, outline=LINE, width=3)
        d.text((cx + 20, y + 24), it, font=f, fill=INK, anchor="lm")
        cx += cw + 12
    return 48

def c_bulkbar(d, x, y, w, c):
    d.rounded_rectangle([x, y, x + w, y + 64], 12, fill=INK)
    d.text((x + 24, y + 32), c.get("text", ""), font=font("sans", 26, 600), fill=WHITE, anchor="lm")
    f = font("sans", 26, 600)
    ax = x + w - 24
    for a in reversed(c.get("actions", [])):
        aw = f.getlength(a)
        ax -= aw
        col = (255, 150, 140) if a.lower().startswith(("delete", "remove", "archive")) else WHITE
        d.text((ax, y + 32), a, font=f, fill=col, anchor="lm")
        ax -= 36
    return 64

def c_table(d, x, y, w, c):
    cols = c.get("cols", [])
    rows = c.get("rows", [])
    sel = c.get("select", False)
    checked = set(c.get("checked", []))
    scol = c.get("status_col", -1)
    cbw = 56 if sel else 0
    cw = (w - cbw) / max(1, len(cols))
    fh = font("sans", 22, 600)
    fr = font("sans", 25, 400)
    d.rounded_rectangle([x, y, x + w, y + 52], 10, fill=SOFT)
    for j, col in enumerate(cols):
        d.text((x + cbw + j * cw + 16, y + 26), col.upper(), font=fh, fill=MUTED, anchor="lm")
    if sel:
        d.rounded_rectangle([x + 16, y + 13, x + 42, y + 39], 6, fill=WHITE, outline=LINE, width=3)
    ry = y + 52
    for i, r in enumerate(rows):
        if i in checked:
            d.rectangle([x, ry, x + w, ry + 60], fill=tint(ACCENT, 0.08))
        if sel:
            bx, by = x + 16, ry + 17
            if i in checked:
                d.rounded_rectangle([bx, by, bx + 26, by + 26], 6, fill=ACCENT)
                d.line([bx + 6, by + 13, bx + 11, by + 19, bx + 20, by + 7], fill=WHITE, width=3)
            else:
                d.rounded_rectangle([bx, by, bx + 26, by + 26], 6, fill=WHITE, outline=LINE, width=3)
        for j, cell in enumerate(r):
            cx = x + cbw + j * cw + 16
            if j == scol:
                bg, fg = status_colors(cell)
                fp = font("sans", 22, 600)
                pw = fp.getlength(cell) + 28
                d.rounded_rectangle([cx, ry + 14, cx + pw, ry + 46], 16, fill=bg)
                d.text((cx + 14, ry + 30), cell, font=fp, fill=fg, anchor="lm")
            else:
                d.text((cx, ry + 30), cell, font=fr, fill=INK, anchor="lm")
        d.line([x, ry + 60, x + w, ry + 60], fill=LINE, width=2)
        ry += 60
    return ry - y

def c_cards(d, x, y, w, c):
    n = c.get("n", 6)
    k = c.get("cols", 3)
    labels = c.get("labels", [])
    gap = 16
    cwid = (w - gap * (k - 1)) / k
    ch = 150
    f = font("sans", 22, 500)
    rows = math.ceil(n / k)
    pattern = [0.45, 0.8, 0.6, 0.95, 0.7]
    for i in range(n):
        cx = x + (i % k) * (cwid + gap)
        cy = y + (i // k) * (ch + gap)
        hl = i in set(c.get("strong", []))
        d.rounded_rectangle([cx, cy, cx + cwid, cy + ch], 14, fill=WHITE, outline=ACCENT if hl else LINE, width=3)
        lab = labels[i] if i < len(labels) else ""
        d.text((cx + 16, cy + 18), lab, font=f, fill=INK if hl else MUTED)
        bw = (cwid - 32 - 4 * 10) / 5
        for b in range(5):
            bh = 70 * pattern[(b + i) % 5]
            bx = cx + 16 + b * (bw + 10)
            d.rectangle([bx, cy + ch - 18 - bh, bx + bw, cy + ch - 18], fill=ACCENT if hl else LINE)
    return rows * ch + (rows - 1) * gap

def c_kpis(d, x, y, w, c):
    items = c.get("items", [])
    k = max(1, len(items))
    gap = 16
    cwid = (w - gap * (k - 1)) / k
    for i, (lab, val) in enumerate(items):
        cx = x + i * (cwid + gap)
        d.rounded_rectangle([cx, y, cx + cwid, y + 140], 14, fill=WHITE, outline=LINE, width=3)
        d.text((cx + 20, y + 22), lab, font=font("sans", 22, 500), fill=MUTED)
        d.text((cx + 20, y + 60), str(val), font=font("sans", 52, 700), fill=INK)
    return 140

def c_dialog(d, x, y, w, c):
    fb = font("sans", 24, 400)
    body = wrap_plain(c.get("body", ""), fb, w - 64)
    h = 40 + 44 + len(body) * 34 + 30 + 56 + 32
    d.rounded_rectangle([x, y, x + w, y + h], 18, fill=WHITE, outline=INK, width=3)
    d.text((x + 32, y + 36), c.get("title", ""), font=font("sans", 32, 700), fill=INK)
    for i, ln in enumerate(body):
        d.text((x + 32, y + 88 + i * 34), ln, font=fb, fill=MUTED)
    fbn = font("sans", 24, 600)
    bx = x + w - 32
    by = y + h - 32 - 56
    for b in reversed(c.get("buttons", [])):
        bx -= btn_w(b, fbn)
        draw_button(d, bx, by, b)
        bx -= 14
    return h

def c_buttons(d, x, y, w, c):
    fbn = font("sans", 24, 600)
    items = c.get("items", [])
    if c.get("align", "right") == "right":
        bx = x + w
        for b in reversed(items):
            bx -= btn_w(b, fbn)
            draw_button(d, bx, y, b)
            bx -= 14
    else:
        bx = x
        for b in items:
            bx += draw_button(d, bx, y, b) + 14
    return 56

def c_empty(d, x, y, w, c):
    cx = x + w / 2
    d.rounded_rectangle([cx - 40, y + 10, cx + 40, y + 90], 16, outline=LINE, width=4)
    d.line([cx - 18, y + 50, cx + 18, y + 50], fill=LINE, width=4)
    d.text((cx, y + 130), c.get("title", ""), font=font("sans", 30, 700), fill=INK, anchor="mm")
    fb = font("sans", 24, 400)
    lines = wrap_plain(c.get("body", ""), fb, w - 120)
    for i, ln in enumerate(lines):
        d.text((cx, y + 172 + i * 32), ln, font=fb, fill=MUTED, anchor="mm")
    h = 172 + len(lines) * 32
    if c.get("button"):
        b = {"label": c["button"], "kind": "primary"}
        bw = btn_w(b, font("sans", 24, 600))
        draw_button(d, cx - bw / 2, y + h + 10, b)
        h += 76
    return h

def c_text(d, x, y, w, c):
    size = 30 if c.get("size") == "m" else 24
    f = font("sans", size, 600 if c.get("bold") else 400)
    lines = wrap_plain(c.get("text", ""), f, w)
    for i, ln in enumerate(lines):
        d.text((x, y + i * (size + 10)), ln, font=f, fill=MUTED if c.get("muted") else INK)
    return len(lines) * (size + 10)

def c_toast(d, x, y, w, c):
    d.rounded_rectangle([x, y, x + w, y + 64], 14, fill=INK)
    d.text((x + 24, y + 32), c.get("text", ""), font=font("sans", 26, 500), fill=WHITE, anchor="lm")
    if c.get("action"):
        f = font("sans", 26, 700)
        d.text((x + w - 24 - f.getlength(c["action"]), y + 32), c["action"], font=f, fill=(160, 178, 255), anchor="lm")
    return 64

def c_field(d, x, y, w, c):
    d.text((x, y), c.get("label", ""), font=font("sans", 22, 600), fill=MUTED)
    dis = c.get("disabled", False)
    d.rounded_rectangle([x, y + 34, x + w, y + 92], 12, fill=SOFT if dis else WHITE, outline=LINE, width=3)
    d.text((x + 20, y + 63), c.get("value", ""), font=font("sans", 26, 400), fill=MUTED if dis else INK, anchor="lm")
    h = 92
    if c.get("hint"):
        d.ellipse([x, y + 106, x + 24, y + 130], outline=ACCENT, width=3)
        d.text((x + 12, y + 118), "i", font=font("sans", 18, 700), fill=ACCENT, anchor="mm")
        d.text((x + 36, y + 118), c["hint"], font=font("sans", 22, 500), fill=INK, anchor="lm")
        h += 46
    return h

def c_lines(d, x, y, w, c):
    n = c.get("n", 3)
    for i in range(n):
        lw = w * (0.92 if i % 3 == 0 else 0.7 if i % 3 == 1 else 0.5)
        d.rounded_rectangle([x, y + i * 30, x + lw, y + i * 30 + 14], 7, fill=LINE)
    return n * 30

COMPONENTS = {"toolbar": c_toolbar, "search": c_search, "chips": c_chips, "bulkbar": c_bulkbar,
              "table": c_table, "cards": c_cards, "kpis": c_kpis, "dialog": c_dialog,
              "buttons": c_buttons, "empty": c_empty, "text": c_text, "toast": c_toast,
              "field": c_field, "lines": c_lines}

def render_screen(screen):
    """Returns (RGB image of the screen at BW wide, {mark: (x1, y1, x2, y2)})."""
    canvas = Image.new("RGB", (BW, 2600), WHITE)
    d = ImageDraw.Draw(canvas)
    pad, top = 28, 56
    y = top + 28
    marks, boxes = {}, []
    for comp in screen.get("items", []):
        h = COMPONENTS[comp["c"]](d, pad, y, BW - 2 * pad, comp)
        box = (pad, y, BW - pad, y + h)
        if comp.get("highlight"):
            boxes.append(box)
        if comp.get("mark"):
            marks[int(comp["mark"])] = box
        y += h + 24
    height = int(y + 4)
    img = canvas.crop((0, 0, BW, height))
    d = ImageDraw.Draw(img)
    d.line([0, top, BW, top], fill=LINE, width=3)
    for i in range(3):
        d.ellipse([24 + i * 26, top / 2 - 8, 40 + i * 26, top / 2 + 8], fill=LINE)
    if screen.get("title"):
        d.text((BW / 2, top / 2), screen["title"].lower(), font=font("mono", 24, 400), fill=MUTED, anchor="mm")
    for (x1, y1, x2, y2) in boxes:
        d.rounded_rectangle([x1 - 10, y1 - 10, x2 + 10, y2 + 10], 16, outline=ACCENT, width=4)
    d.rounded_rectangle([0, 0, BW - 1, height - 1], 22, outline=LINE, width=3)
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, BW - 1, height - 1], 22, fill=255)
    out = Image.new("RGB", img.size, PAPER)
    out.paste(img, (0, 0), mask)
    return out, marks

_screen_cache = {}

def screen_img(scr, width):
    key = (json.dumps(scr, sort_keys=True), width)
    if key not in _screen_cache:
        img, marks = render_screen(scr)
        s = width / BW
        img = img.resize((int(BW * s), int(img.size[1] * s)), Image.LANCZOS)
        marks = {k: tuple(v * s for v in b) for k, b in marks.items()}
        _screen_cache[key] = (img, marks)
    return _screen_cache[key]

def fit_width(scr, width, max_h):
    img, _ = screen_img(scr, width)
    if img.size[1] > max_h:
        width = int(width * max_h / img.size[1])
    return width

def paste_fade(base, img, x, y, a):
    if a <= 0:
        return
    if a >= 1:
        base.paste(img, (int(x), int(y)))
        return
    region = base.crop((int(x), int(y), int(x) + img.size[0], int(y) + img.size[1]))
    base.paste(Image.blend(region, img, a), (int(x), int(y)))

def badge(d, cx, cy, n, p):
    r = 26 * (0.6 + 0.4 * p)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ACCENT, outline=PAPER, width=4)
    d.text((cx, cy), str(n), font=font("sans", int(30 * (0.6 + 0.4 * p)), 700), fill=WHITE, anchor="mm")

def notes_h(notes, f, w):
    return sum(len(wrap_plain(n, f, w)) * 50 + 26 for n in notes)

def scene_fix(d, s, t, gt, img):
    width = SAFE_R - SAFE_L
    width = min(fit_width(s["before"], width, 820), fit_width(s["after"], width, 820))
    bimg, _ = screen_img(s["before"], width)
    aimg, amarks = screen_img(s["after"], width)
    sh = max(bimg.size[1], aimg.size[1])
    fnote = font("sans", 40, 600)
    total = 110 + sh + 56 + notes_h(s.get("notes", []), fnote, SAFE_R - SAFE_L - 70)
    y = kicker(d, s.get("kicker", "fix this screen"), t, centered_y(total))
    x = SAFE_L + (SAFE_R - SAFE_L - width) / 2
    sy = y
    swap = s.get("swap_at", 2.4)
    p_in = ease_out((t - 0.2) / 0.45)
    p_sw = ease_in_out((t - swap) / 0.6)
    lab_f = font("mono", 32, 400)
    if p_sw < 1:
        paste_fade(img, bimg, x, sy + (1 - p_in) * 40, p_in * (1 - p_sw))
        d.text((SAFE_R, y - 110), "before", font=lab_f, fill=blend(MUTED, PAPER, p_in * (1 - p_sw)), anchor="ra")
    if p_sw > 0:
        paste_fade(img, aimg, x, sy, p_sw)
        d.text((SAFE_R, y - 110), "after", font=lab_f, fill=blend(ACCENT, PAPER, p_sw), anchor="ra")
    if p_sw >= 1:
        for k in sorted(amarks):
            p = ease_out((t - swap - 0.7 - (k - 1) * 0.3) / 0.25)
            if p > 0:
                x1, y1, x2, y2 = amarks[k]
                badge(d, x - 40, sy + (y1 + y2) / 2, k, p)
    ny = sy + sh + 56
    for k, note in enumerate(s.get("notes", [])):
        p = ease_out((t - swap - 0.9 - k * 0.45) / 0.4)
        if p <= 0:
            continue
        badge(d, SAFE_L + 22, ny + 26, k + 1, 1)
        lines = wrap_plain(note, fnote, SAFE_R - SAFE_L - 70)
        for i, ln in enumerate(lines):
            d.text((SAFE_L + 70, ny + i * 50 + int((1 - p) * 24)), ln, font=fnote, fill=blend(INK, PAPER, p))
        ny += len(lines) * 50 + 26

def scene_versus(d, s, t, gt, img):
    """Stacked: the bad version on top, the better one below, so both stay readable on a phone."""
    width = SAFE_R - SAFE_L
    width = min(fit_width(s["left"], width, 470), fit_width(s["right"], width, 470))
    timg, _ = screen_img(s["left"], width)
    bimg, _ = screen_img(s["right"], width)
    fcap = font("sans", 52, 700)
    cap_h = block_h([s["caption"]], 52, 700, 1.15) + 40 if s.get("caption") else 0
    total = 110 + 2 * (64 + 0) + timg.size[1] + bimg.size[1] + 40 + cap_h
    y = kicker(d, s.get("kicker", "bad vs better"), t, centered_y(total))
    x = SAFE_L + (SAFE_R - SAFE_L - width) / 2
    lab_f = font("mono", 32, 400)
    rows = [(timg, s.get("left_label", "bad"), RED), (bimg, s.get("right_label", "better"), ACCENT)]
    cy = y
    for i, (im, lab, col) in enumerate(rows):
        p = ease_out((t - 0.2 - i * 0.7) / 0.45)
        if p > 0:
            d.text((SAFE_L, cy), lab, font=lab_f, fill=blend(col, PAPER, p))
            d.rectangle([SAFE_L, cy + 44, SAFE_L + 50, cy + 48], fill=blend(col, PAPER, p))
            paste_fade(img, im, x, cy + 64 + (1 - p) * 30, p)
        cy += 64 + im.size[1] + 40
    if s.get("caption"):
        text_block(d, [s["caption"]], t - 1.6, SAFE_L, cy, 52, 700, 1.15)

IMG_SCENES = {"fix": scene_fix, "versus": scene_versus}

SCENES = {"hook": scene_hook, "text": scene_text, "bars": scene_bars,
          "number": scene_number, "compare": scene_compare, "outro": scene_outro}

def render(spec, out_path, frames_dir=None):
    scenes = spec["scenes"]
    sig = spec.get("signature", "Muhh")
    total = sum(s.get("dur", 3.5) for s in scenes)
    tmp = frames_dir or tempfile.mkdtemp(prefix="reel_")
    os.makedirs(tmp, exist_ok=True)
    fade = 0.28
    n = 0
    start = 0.0
    for idx, s in enumerate(scenes):
        dur = s.get("dur", 3.5)
        fn = SCENES.get(s["type"])
        ifn = IMG_SCENES.get(s["type"])
        for i in range(int(round(dur * FPS))):
            t = i / FPS
            gt = start + t
            img = Image.new("RGB", (W, H), PAPER)
            d = ImageDraw.Draw(img)
            if ifn:
                ifn(d, s, t, gt, img)
            else:
                fn(d, s, t, gt)
            if idx < len(scenes) - 1 and t > dur - fade:
                a = (t - (dur - fade)) / fade
                img = Image.blend(img, Image.new("RGB", (W, H), PAPER), ease_in_out(a))
                d = ImageDraw.Draw(img)
            chrome(d, sig, gt, total, idx, len(scenes))
            img.save(os.path.join(tmp, f"f{n:05d}.png"), compress_level=1)
            n += 1
        start += dur
    for _ in range(int(FPS * 0.6)):
        shutil.copy(os.path.join(tmp, f"f{n - 1:05d}.png"), os.path.join(tmp, f"f{n:05d}.png"))
        n += 1
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(tmp, "f%05d.png"),
           "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
           "-shortest", "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "18",
           "-preset", "medium", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out_path]
    subprocess.run(cmd, check=True)
    if not frames_dir:
        shutil.rmtree(tmp, ignore_errors=True)
    return total

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--fonts" in args:
        i = args.index("--fonts")
        FONT_DIR = args[i + 1]
        del args[i:i + 2]
    frames = None
    if "--frames-only" in args:
        i = args.index("--frames-only")
        frames = args[i + 1]
        del args[i:i + 2]
    spec_path, out = args[0], args[1]
    with open(spec_path) as fh:
        spec = json.load(fh)
    for s in spec["scenes"]:
        blob = json.dumps(s, ensure_ascii=False)
        if "\u2014" in blob:
            sys.exit("spec contains an em dash; rewrite the line")
    secs = render(spec, out, frames)
    print(f"rendered {out} ({secs:.1f}s + hold)")
