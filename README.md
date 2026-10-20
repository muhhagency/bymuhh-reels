# bymuhh-reels

Video files and the motion engine for the @bymuhh_ Instagram and TikTok reels.
Files in `videos/` are public. Buffer downloads them from:

`https://raw.githubusercontent.com/muhhagency/bymuhh-reels/main/videos/<slug>.mp4`

## Style: card-collage motion (v3 template)

The template is `examples/2026-10-21-table-3-jobs-v3/` (page.html + spec.json). Every reel is built from it.

Look
- Paper background, black ink, accent blue #2B4BEE, red #CC3E32, green #268A52. Fonts: Inter and IBM Plex Mono only.
- The "muhh_" signature matches the muhh.design logo in every video and image: bold Inter (800), "muhh" in ink #141414 and only the "_" in accent blue #2B4BEE. Never grey, never all blue, never in the mono font, never thin.
- The mascot is Under_ (engine/mascot.js), and it is the only character ever used: the blue underscore from the muhh_ logo, alive (3.9 : 1 bar, square corners, cursor-shaped ink eyes on top, no limbs, no pixel style). Never draw any other mascot, and never anything that resembles another brand's character.
- No real screenshots, memes, photos, logos or watermarks. No em dashes anywhere.

Structure (what makes people stay)
1. Frame 0 is the whole hook. The first line is shown in full at 0:00 with a stakes prop (a big red number card) already on screen, and the voice starts at 0.0 s ("lead": 0). No empty frames, no pop-in before the claim.
2. The narration is the headline. Each phrase appears word by word in big type (86 px) near the top; key words are wrapped in *asterisks* in spec.json and show in blue. No small captions.
3. A stakes meter top right (mono, red, marked "illustrative" unless sourced), for example TIME LOST / WEEK, CLICKS WASTED, TICKETS / MONTH. It climbs on every problem beat ("cost": [where in the line, amount]) and the costs add up to the number promised in the hook.
4. A section label under the logo: "// 01 of 03 / find". Numbered parts make people stay to the end.
5. Under_ narrates from the bottom of the screen the whole time (POSE per line), and jumps into shock whenever the meter goes up. In the outro it does its underline move under the last key word.
6. Every point shows the problem first (it costs, the meter climbs), then the fix working in recreated UI: rows filter, numbers sort, checkboxes tick, a cursor clicks with a press. One big prop per beat; a new visual every 1 to 2 seconds.
7. Frame stakes as time, money, clicks or support tickets, so PMs and founders care too. Numbers are illustrative unless sourced, and the meter says so.
8. End with a save line ("Save this for your next table review") and the follow line. No "comment X to get Y".
- Length 30 to 40 seconds, 8 to 10 lines. Text stays inside x 96 to 984 and y 170 to 1500.

## Make a reel

1. Copy `examples/2026-10-21-table-3-jobs-v3/` to `work/<slug>/` (spec.json and page.html only).
2. Edit `spec.json`: the slug, "lead": 0, and one entry per line: narration `text` (key words in *asterisks*), `section` label, and `cost` on problem beats.
3. Edit `page.html`. Keep the engine parts as they are (tokens, chrome, meter, kinetic headline, narrator, pop/spring helpers, render). Replace the layers `L0`..`Ln`, the `ANIM` functions and `POSE` with this topic's beats: one layer, one ANIM function and one pose per line. Font and mascot urls point at `../../engine/`.
4. Preview with `python3 engine/make_reel.py work/<slug> --preview`, then look at `work/<slug>/preview.png`. Also check frame 0 by itself: the whole hook and the stakes prop must be readable. Fix overlap, clipping or empty frames before you encode.
5. Build with `python3 engine/make_reel.py work/<slug>` (AI voice). Use `--mode text` for a no-voice version: same headline, silent track for a trending sound.
6. Commit only `videos/<slug>.mp4` plus the work folder's `spec.json` and `page.html`, then push. Check the raw URL returns 200 before giving it to Buffer. Test renders go to `videos/test-*` (not committed).

Needs Python with playwright, Pillow, numpy, soundfile, and kokoro-onnx (`pip install kokoro-onnx soundfile --break-system-packages`), plus ffmpeg and Chromium. The Kokoro model files download to `~/.cache/kokoro` on the first run.
