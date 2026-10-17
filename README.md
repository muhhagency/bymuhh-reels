# bymuhh-reels

Video files and the motion engine for the @bymuhh_ Instagram and TikTok reels.
Files in `videos/` are public. Buffer downloads them from:

`https://raw.githubusercontent.com/muhhagency/bymuhh-reels/main/videos/<slug>.mp4`

## Style: card-collage motion

- Paper background, black ink, accent blue #2B4BEE, red #CC3E32, green #268A52.
- The "muhh_" signature matches the muhh.design logo in every video and image: bold Inter (800), "muhh" in ink #141414 and only the "_" in accent blue #2B4BEE. Never grey, never all blue, never in the mono font, never thin.
- Every beat is a layer of cards that spring in, keep moving, then whip out. There is a new visual every 1 to 2 seconds.
- UI is recreated in code, and it works: rows filter, numbers sort, checkboxes tick, and a cursor clicks with a press.
- A pixel mascot drawn in code reacts on the hook and the "problem" beat.
- No real screenshots, memes, photos, logos or watermarks. No em dashes anywhere.
- Text stays inside x 96 to 984 and y 250 to 1500. Voice captions sit at y 1360.
- Length is 22 to 30 seconds and 7 to 9 narration lines. Line 1 is the hook (under 3 s) and the last line is the payoff with a follow CTA.

## Make a reel

1. Copy `examples/2026-10-19-table-3-jobs/` to `work/<slug>/`.
2. Edit `spec.json`: the slug, and one entry per line with the narration `text` plus a short `card` headline (the card is used in no-voice mode).
3. Edit `page.html`. Keep the engine parts as they are: the CSS tokens, `pop`, `spring`, `pr`, the mascot, the `render()` timeline, and the captions. Replace layers `L0`..`Ln` and the `ANIM` array with that topic's beats, so there is one layer and one `ANIM` function per line. The number of layers must equal the number of lines, and the loop in `render()` that hides layers must use that count. Point the font urls at `../../engine/fonts/`.
4. Preview with `python3 engine/make_reel.py work/<slug> --preview`, then look at `work/<slug>/preview.png`. Fix any overlap, clipping or empty frames before you encode.
5. Build with `python3 engine/make_reel.py work/<slug>` (AI voice is the default). Use `--mode text` for a no-voice version.
6. Commit only `videos/<slug>.mp4` plus the work folder's `spec.json` and `page.html`, then push. Check the raw URL returns 200 before giving it to Buffer.

Needs Python with playwright, Pillow, numpy, soundfile, and kokoro-onnx (`pip install kokoro-onnx soundfile --break-system-packages`), plus ffmpeg and Chromium. The Kokoro model files download to `~/.cache/kokoro` on the first run.
