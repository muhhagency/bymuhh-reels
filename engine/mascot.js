// Under_: the official muhh_ mascot. The blue underscore from the muhh_ logo, alive.
// Proportions match the logo underscore (Inter 800): 3.9 : 1, square corners, accent blue #2B4BEE.
// Cursor-shaped ink eyes stand on top of the bar. No limbs: it acts with hops, squash, tilt and small marks.
// usage: el.innerHTML = under({pose, t, scale, len})
//   pose: idle | cheer | shrug | point | shock | wave | underline
//   t: seconds (drives blink and motion); scale: size multiplier (1 = 172 px wide bar)
//   len: bar length in px at scale 1, for "underline" (it stretches under a word)
// The svg is (bar width + 120) x 190 at scale 1; the bar starts at x = 30 and its bottom sits at y = 150.
(function () {
  const BLUE = "#2B4BEE", INK = "#141414", PAPER = "#F4F1EA";
  const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
  window.under = function ({ pose = "idle", t = 0, scale = 1, len = 170 } = {}) {
    const W = pose === "underline" ? len : 172, H = 44;
    let hop = Math.max(0, Math.sin(t * 3)) * 6, tilt = 0, sx = 1, sy = 1, eyeH = 36, eyeGap = 38, look = 0;
    if (pose === "cheer") { const k = Math.abs(Math.sin(t * 7)); hop = k * 34; sx = 1 - k * 0.08; sy = 1 + k * 0.15; }
    if (pose === "shock") { hop = 18; sx = 0.9; sy = 1.2; eyeH = 48; }
    if (pose === "shrug") { tilt = -7; hop = 0; }
    if (pose === "point") { tilt = 6; look = 8; }
    if (pose === "wave") { tilt = Math.sin(t * 8) * 7; }
    if (pose === "underline") { hop = 0; look = -4; }
    const blink = (t % 2.6) > 2.42 && pose !== "cheer";
    const bw = W * sx, bh = H * sy, base = 150, x = 30 + (W - bw) / 2, y = base - bh - hop, cx = x + bw / 2;
    const ex = pose === "underline" ? [x + 24, x + 24 + eyeGap] : [cx - eyeGap / 2 - 6, cx + eyeGap / 2 + 6];
    // eyes are cursor bars standing on the body, pupils as small paper notches
    let eyes = "";
    if (pose === "cheer") eyes = ex.map(e => `<path d="M${e - 9} ${y - 8} Q${e} ${y - 24} ${e + 9} ${y - 8}" fill="none" stroke="${INK}" stroke-width="8" stroke-linecap="round"/>`).join("");
    else if (blink) eyes = ex.map(e => `<rect x="${e - 9}" y="${y - 9}" width="18" height="6" rx="3" fill="${INK}"/>`).join("");
    else eyes = ex.map(e => `<rect x="${e - 9 + look * 0.3}" y="${y - eyeH - 3}" width="18" height="${eyeH}" rx="9" fill="${INK}"/><circle cx="${e + look * 0.6}" cy="${y - eyeH + 9}" r="4.2" fill="${PAPER}"/>`).join("");
    if (pose === "shrug") eyes += ex.map((e, i) => `<path d="M${e - 10} ${y - eyeH - 12 + (i ? -5 : 0)} L${e + 10} ${y - eyeH - 12 + (i ? 0 : -5)}" stroke="${INK}" stroke-width="6" stroke-linecap="round"/>`).join("");
    if (pose === "shock") eyes += `<text x="${x + bw + 12}" y="${y - 20}" font-family="MuhhSans, Inter, sans-serif" font-weight="800" font-size="44" fill="${BLUE}">!</text>`;
    if (pose === "point") eyes += `<path d="M${x + bw + 14} ${y + bh / 2} l30 0 m-12 -10 l12 10 l-12 10" fill="none" stroke="${INK}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>`;
    if (pose === "wave") eyes += `<path d="M${x + bw + 12} ${y - 10} q10 -14 0 -28 M${x + bw + 26} ${y - 2} q14 -22 0 -44" fill="none" stroke="${BLUE}" stroke-width="5" stroke-linecap="round"/>`;
    const shadowW = bw * (1 - clamp(hop / 60, 0, 0.5));
    const shadow = pose === "underline" ? "" : `<ellipse cx="${cx}" cy="${base + 10}" rx="${shadowW / 2}" ry="5" fill="rgba(20,20,20,0.12)"/>`;
    const body = `<rect x="${x}" y="${y}" width="${bw}" height="${bh}" rx="2" fill="${BLUE}"/>`;
    const vw = W + 120, vh = 190;
    return `<svg width="${vw * scale}" height="${vh * scale}" viewBox="0 0 ${vw} ${vh}" overflow="visible">${shadow}<g transform="rotate(${tilt} ${cx} ${base})">${body}${eyes}</g></svg>`;
  };
})();
