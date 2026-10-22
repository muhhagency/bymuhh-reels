# bymuhh-reels

Video files and the motion engine for the @bymuhh_ Instagram and TikTok reels.
Files in `videos/` are public. Buffer downloads them from:

`https://raw.githubusercontent.com/muhhagency/bymuhh-reels/main/videos/<slug>.mp4`

## Style: card-collage motion (v3 template)

Every reel is built from `engine/reel.html` (v4 scene template) and a spec.json; see "Make a reel" below.

Look
- Colors are the muhh_ brand tokens only (from the muhh_socials Figma file): paper #f7f7f5, white #ffffff, ink #0e0e0c, ink-60 #676765, ink-40 #70706e, rule #d2d2d0, accent #0b4af1 (tints of the accent are fine). No red, green, amber or any other color, including for warnings, stakes numbers and status pills: stakes and highlights use the accent, bad or overdue states use ink, neutral states use ink-60 with a rule outline. Fonts: Inter and IBM Plex Mono only.
- The "muhh_" signature matches the muhh.design logo in every video and image: bold Inter (800), "muhh" in ink #0e0e0c and only the "_" in accent blue #0b4af1. Never grey, never all blue, never in the mono font, never thin.
- The mascot is Under_ (engine/mascot.js), and it is the only character ever used: the blue underscore from the muhh_ logo, alive (3.9 : 1 bar, square corners, cursor-shaped ink eyes on top, no limbs, no pixel style). Never draw any other mascot, and never anything that resembles another brand's character.
- No real screenshots, memes, photos, logos or watermarks. No em dashes anywhere.

Structure (what makes people stay)
1. Frame 0 is the whole hook. The first line is shown in full at 0:00 with a stakes prop (a big accent-blue number card) already on screen, and the voice starts at 0.0 s ("lead": 0). No empty frames, no pop-in before the claim.
2. The narration is the headline. Each phrase appears word by word in big type (86 px) near the top; key words are wrapped in *asterisks* in spec.json and show in blue. No small captions.
3. A stakes meter top right (mono, accent blue, marked "illustrative" unless sourced), for example TIME LOST / WEEK, CLICKS WASTED, TICKETS / MONTH. It climbs on every problem beat ("cost": [where in the line, amount]) and the costs add up to the number promised in the hook.
4. A section label under the logo: "// 01 of 03 / find". Numbered parts make people stay to the end.
5. Under_ narrates from the bottom of the screen the whole time (POSE per line), and jumps into shock whenever the meter goes up. In the outro it does its underline move under the last key word.
6. Every point shows the problem first (it costs, the meter climbs), then the fix working in recreated UI: rows filter, numbers sort, checkboxes tick, a cursor clicks with a press. One big prop per beat; a new visual every 1 to 2 seconds.
7. Frame stakes as time, money, clicks or support tickets, so PMs and founders care too. Numbers are illustrative unless sourced, and the meter says so.
8. End with a save line ("Save this for your next table review") and the follow line. No "comment X to get Y".
- Length 30 to 40 seconds, 8 to 10 lines. Text stays inside x 96 to 984 and y 170 to 1500.

## Make a reel (v4: write a spec, nothing else)

A reel is only `work/<slug>/spec.json`. The animation comes from ready-made scenes in `engine/reel.html`, which you never edit for a single video. Examples: `examples/v4-table-3-jobs/spec.json` and `work/2026-10-23-delete-button/spec.json`.

spec.json:
- `slug`, `"lead": 0`, `meter`: `{"label": "TIME LOST / WEEK", "unit": "minutes"}` (or `"unit": "count", "suffix": ""` for clicks, tickets and so on; costs are then plain numbers).
- `lines`: 8 to 10 items, each `{"text", "section", "pose", "cost"?, "scene"}`. `text` is the narration with 1 or 2 key words in *asterisks*. `cost` is `[where in the line 0..1, amount]` on problem beats; the costs add up to the hook's number. `pose` is Under_'s pose (idle, shock, shrug, point, cheer, wave).

Scenes (`"scene": {"type": ..., options}`):
- `stakes` {value, label, behind: table | buttons | dashboard | none}: the hook prop, already on screen at frame 0. Use it on line 1 only.
- `chat` {role, channel, msg, stamp}: someone waves the problem away, then a stamp card ("It's not.").
- `cards` {items: [up to 5 short words], strike: [indexes]}: big word cards tossed in; struck ones get crossed out.
- `table_scroll` {count, label}: a long table flies past behind a closed "Filters" button; a counter climbs.
- `filter` {chips, keep}: filter chips on screen; the cursor clicks the first and rows filter down.
- `sort` {left, right}: numbers start left-aligned and unsorted, then align right and sort.
- `bulk` {actions}: actions hidden in a "..." menu, then rows get selected and the bulk bar appears.
- `buttons` {mode: bad | good, buttons, danger, primary, title, oops}: a form's action row. bad: equal buttons, the cursor slips onto the dangerous one and an "oops" card appears. good: the dangerous one moves far left as a text button and the gap is marked.
- `dialog` {mode: bad | good, title, body, cancel, confirm, oops}: bad: "Are you sure?" clicked straight through, then the consequence. good: names the object and the consequence.
- `toast` {text, action}: the row disappears, a toast with Undo slides in, the cursor clicks Undo and the row returns.
- `dashboard` {questions: [3]}: 12 equal charts; 9 fade and 3 grow, each labelled with the question it answers.
- `checklist` {title, items}: items appear and tick one by one (good for "Steal this").
- `bignum` {value, label, items?}: one big accent-blue number card, optionally under struck-out word cards (the total).
- `outro` {words: [2 to 4 short phrases], save}: the takeaway in big type, Under_ underlines the last phrase, then the save line. Always the last line.

Pick scenes that show the problem first and then the fix. If a topic needs a scene that does not exist, use the closest one; never edit reel.html during a daily run.

Build:
1. `python3 engine/make_reel.py work/<slug> --preview` and look at `work/<slug>/preview.png`; also snapshot t=0 with `python3 engine/snap.py work/<slug>/_built_voice.html out.png 0`. The whole hook and the stakes card must be readable at frame 0.
2. `python3 engine/make_reel.py work/<slug>` (AI voice; add `--mode text` for no-voice). Output: `videos/<slug>.mp4`.
3. Commit only `videos/<slug>.mp4` and `work/<slug>/spec.json`, push, and check the raw URL returns 200.
Old hand-coded reels (a `page.html` in the folder) still build the same way.

Needs Python with playwright, Pillow, numpy, soundfile, and kokoro-onnx (`pip install kokoro-onnx soundfile --break-system-packages`), plus ffmpeg and Chromium. The Kokoro model files download to `~/.cache/kokoro` on the first run.
