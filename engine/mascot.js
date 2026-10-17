// "Under": the muhh_ mascot. The blue underscore from the muhh_ signature, alive.
// A rounded blue bar with two eyes, rubber-hose ink limbs and a caret-style blink.
// usage: el.innerHTML = under({pose, t, scale, len})
//   pose: idle | cheer | shrug | point | shock | underline | wave
//   t: seconds (drives blink, bob and limb motion), scale: size multiplier, len: body length for "underline" (px at scale 1)
(function () {
  const BLUE = "#2B4BEE", INK = "#141414";
  function limb(x1, y1, x2, y2, bend) {
    const mx = (x1 + x2) / 2 + bend, my = (y1 + y2) / 2 - Math.abs(bend) * 0.4;
    return `<path d="M${x1} ${y1} Q${mx} ${my} ${x2} ${y2}" fill="none" stroke="${INK}" stroke-width="6" stroke-linecap="round"/>` +
      `<circle cx="${x2}" cy="${y2}" r="5.5" fill="${INK}"/>`;
  }
  window.under = function ({ pose = "idle", t = 0, scale = 1, len = 150 } = {}) {
    let W = 150, H = 50, bob = Math.sin(t * 4) * 3, sq = 1, eyes = "open";
    if (pose === "underline") W = len;
    if (pose === "cheer") { bob = -Math.abs(Math.sin(t * 7)) * 22; sq = 1 + Math.sin(t * 14) * 0.06; eyes = "happy"; }
    if (pose === "shock") { bob = -10; sq = 0.9; eyes = "wide"; }
    if (pose === "underline") { bob = 0; }
    // caret blink: eyes close briefly every ~2.6s
    const blink = (t % 2.6) > 2.45;
    if (blink && eyes === "open") eyes = "blink";
    const cx = 110, top = 70 + bob, bw = W * (2 - sq), bh = H * sq, bx = cx - bw / 2 + (pose === "underline" ? (W - 150) / 2 : 0);
    const by = top + (H - bh);
    const L = bx, R = bx + bw, mid = by + bh * 0.55;
    // limbs
    let arms = "", legs = "";
    const sw = Math.sin(t * 6);
    if (pose === "idle") arms = limb(L + 6, mid, L - 26, mid + 24 + sw * 3, -6) + limb(R - 6, mid, R + 26, mid + 24 - sw * 3, 6);
    if (pose === "cheer") arms = limb(L + 8, mid - 6, L - 22, by - 34 + sw * 6, -10) + limb(R - 8, mid - 6, R + 22, by - 34 - sw * 6, 10);
    if (pose === "shrug") arms = limb(L + 6, mid, L - 34, mid - 18, 14) + limb(R - 6, mid, R + 34, mid - 18, -14);
    if (pose === "point") arms = limb(L + 6, mid, L - 24, mid + 26, -6) + limb(R - 6, mid - 4, R + 52, mid - 30 + sw * 2, -4);
    if (pose === "shock") arms = limb(L + 6, mid - 4, L - 30, by - 22, -12) + limb(R - 6, mid - 4, R + 30, by - 22, 12);
    if (pose === "wave") { const a = Math.sin(t * 9) * 14; arms = limb(L + 6, mid, L - 26, mid + 24, -6) + limb(R - 6, mid - 4, R + 26 + a * 0.4, by - 34 + Math.abs(a) * 0.3, 10); }
    if (pose === "underline") arms = "";
    if (pose !== "underline") {
      const step = pose === "cheer" ? 0 : Math.sin(t * 6) * 3;
      legs = limb(bx + bw * 0.3, by + bh - 4, bx + bw * 0.27 - step, 70 + H + 30, 0) + limb(bx + bw * 0.7, by + bh - 4, bx + bw * 0.73 + step, 70 + H + 30, 0);
      if (pose === "cheer" || pose === "shock") legs = limb(bx + bw * 0.3, by + bh - 4, bx + bw * 0.24, by + bh + 26, -4) + limb(bx + bw * 0.7, by + bh - 4, bx + bw * 0.76, by + bh + 26, 4);
    }
    // eyes
    const ex1 = bx + bw * 0.36, ex2 = bx + bw * 0.64, ey = by + bh * 0.46;
    let face = "";
    const look = pose === "point" ? 4 : pose === "underline" ? -3 : 0;
    if (eyes === "open" || eyes === "wide") {
      const r = eyes === "wide" ? 12 : 10, pr = eyes === "wide" ? 4.5 : 5.5;
      face = [ex1, ex2].map(x => `<circle cx="${x}" cy="${ey}" r="${r}" fill="#fff"/><circle cx="${x + look}" cy="${ey + (pose === "underline" ? -3 : 1)}" r="${pr}" fill="${INK}"/>`).join("");
    } else if (eyes === "blink") {
      face = [ex1, ex2].map(x => `<rect x="${x - 9}" y="${ey - 2}" width="18" height="4.5" rx="2" fill="#fff"/>`).join("");
    } else if (eyes === "happy") {
      face = [ex1, ex2].map(x => `<path d="M${x - 9} ${ey + 3} Q${x} ${ey - 9} ${x + 9} ${ey + 3}" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round"/>`).join("");
    }
    if (pose === "shrug") face += `<path d="M${ex1 - 10} ${ey - 13} L${ex1 + 8} ${ey - 19}" stroke="#fff" stroke-width="4" stroke-linecap="round"/><path d="M${ex2 - 8} ${ey - 19} L${ex2 + 10} ${ey - 13}" stroke="#fff" stroke-width="4" stroke-linecap="round"/>`;
    const shadow = `<ellipse cx="${bx + bw / 2}" cy="${70 + H + 34}" rx="${bw * 0.42 * (1 - Math.max(0, -bob) / 80)}" ry="6" fill="rgba(20,20,20,0.12)"/>`;
    const body = `<rect x="${bx}" y="${by}" width="${bw}" height="${bh}" rx="16" fill="${BLUE}"/><rect x="${bx + 10}" y="${by + 7}" width="${Math.max(0, bw * 0.28)}" height="6" rx="3" fill="rgba(255,255,255,0.35)"/>`;
    const vw = pose === "underline" ? W + 70 : 220, vh = 200;
    return `<svg width="${vw * scale}" height="${vh * scale}" viewBox="0 0 ${vw} ${vh}" overflow="visible">${shadow}${legs}${arms}${body}${face}</svg>`;
  };
})();
