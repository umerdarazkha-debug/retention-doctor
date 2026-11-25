---
name: retention-doctor
description: Find why viewers leave a short video and which kinds of videos hold people best. Part A takes a retention curve (second, percent watching) plus the scene timeline (Remotion project, HyperFrames html, scenes.json/csv or SRT), finds the steepest drops and the first-3-second hook drop, maps each to the scene and words on screen, and names likely causes with one fix each. Part B ranks hook type, format, topic, face and CTA tags by median performance across past videos and refuses to call a winner with fewer than 3 videos. Use when the user says "why did people drop off", "analyse my retention", "where do viewers leave", "fix my hook", "which hooks work best", "what kind of video performs".
---

# Retention doctor

Two jobs. Part A explains one video. Part B compares many. Run only the part the user asked for.

## Part A: one video

1. Ask for two things.
   - The retention curve as CSV (`second,percent_watching`). If they only have the chart, ask them to read the percent at each notch from the app, or send a screenshot and read the values yourself. Write the CSV. Format: `references/input-shapes.md`.
   - The scene timeline. Best source first: a Remotion project, a HyperFrames html file, an SRT. Otherwise write a `scenes.json` with the user (start_s, end_s, label, on_screen_text).
2. Run from the skill folder:

```bash
uv run --python 3.12 scripts/retention.py --curve curve.csv --timeline PATH [--fps 30]
```

   `PATH` can be a `.json`, `.csv`, `.srt`, `.html`, a `.tsx` file or a project folder. Add `--json` for machine output. Tune with `--factor` (default 2), `--min-loss` (3), `--hook-seconds` (3), `--wps` (3).
3. Read the NOTE lines. They say what the parser skipped (variables, nested sequences). If a note says the timeline length does not match the curve, fix fps or the timeline before you trust the report.
4. Present the report in this order: hook line, then drops from biggest to smallest. For each drop give the time, the points lost, the scene, the words on screen, the likely causes and the one fix. Use plain words: "you lost 22 points", not "a 22% decrease" (points are of the starting audience).
5. If the report says "No steep drops", say so. Do not invent a problem. Suggest looking at the overall shape instead (a steady slope means the whole video is slow, not one scene).
6. Offer to apply the fix to the Remotion or HyperFrames source. Do not edit it without a yes.

Causes the script cannot see are in `references/causes.md`. Mention at most one of them, and only if the drop has no rule match.

## Part B: many videos

1. Get a metadata CSV of past videos: `video_id, title, length_s, views, avg_watch_pct, saves, shares`. Real export names are mapped in `references/metadata-columns.md`. At least 10 videos gives useful groups. Fewer works but most groups will be refused.
2. Write `tags.csv` yourself. For each video read the title (and the video or thumbnail if the user gives it) and assign:
   - `hook_type`: question, bold-claim, story, demo, list, pov or other
   - `format`: tutorial, listicle, story, talking-head, screen-record, meme or other
   - `topic`: one or two words, reused across videos so groups form
   - `has_face`: yes or no
   - `cta`: save, follow, comment, link, none
   Show the user the table and let them fix any row before you continue. Tags you guessed wrong give a wrong ranking.
3. Run:

```bash
uv run --python 3.12 scripts/portfolio.py --metadata videos.csv --tags tags.csv [--metric avg_watch_pct|views|saves_per_1k|shares_per_1k]
```

4. Report each tag group with n and median. Quote the script's verdict line. A group with n under 3 is shown but never called a winner. If a dimension says NO WINNER, say there is not enough data and name how many more videos would settle it.
5. Do not turn a lead into a rule. Tags overlap (a face video is often also a story). Say "leads in this sample".

## Limits

- Rules of thumb in the script (2x average slope, 3 s hook, 3 words per second reading) are defaults, not platform facts.
- Medians of small samples move a lot. The refusal threshold is `--min-n` (default 3).
- Retention curves from the apps are smoothed. Short drops under about a second can be noise.
