# retention-doctor

A Claude Code skill for short-form video creators. It answers two questions:

1. Where in this video did people leave, and what was on screen at that moment?
2. Across my past videos, which hook types, formats and topics hold viewers best?

## Install

```bash
git clone https://github.com/umerdarazkha-debug/retention-doctor ~/.claude/skills/retention-doctor
```

Needs `uv` (the scripts use only the Python standard library, Python 3.12 through `uv run`).

## Part A: one video

Inputs: a retention curve CSV and a scene timeline (Remotion project, HyperFrames html, `scenes.json`/`scenes.csv`, or SRT). Formats and parser limits are in `references/input-shapes.md`.

```bash
uv run --python 3.12 scripts/retention.py --curve curve.csv --timeline my-project/src
```

Sample output:

```
DROP #1: At 1.4-2.0 s you lost 22 points (36.7/s, 10.2x your average)
  Scene 'title card' (1.4-3.0 s), text 'Seven rules ...' appeared at 1.4 s
  Likely causes:
    - Text '...' has 11 words but was on screen only 0.6 s before the drop ended ...
  Fix: Cut the text to 5 words or fewer, or hold it for 3.7 s.
```

A drop is a stretch that loses at least 2x the video's own average points per second (and 3+ points). The first 3 seconds get a separate hook line.

## Part B: many videos

Inputs: `videos.csv` (id, title, length, views, avg watch %, saves, shares) and `tags.csv` (hook type, format, topic, has face, CTA). Claude writes `tags.csv` from your titles and you correct it. The script ranks each tag by median and states n. It refuses to name a winner for a group with fewer than 3 videos, and for a dimension with fewer than two groups of 3+.

```bash
uv run --python 3.12 scripts/portfolio.py --metadata videos.csv --tags tags.csv --metric avg_watch_pct
```

## Where the data comes from

- Retention curve: read the chart in the app by hand, or use a tool that exports it. No standard export of Instagram, TikTok or YouTube is confirmed to hold a per-second curve.
- Metadata: YouTube Studio advanced mode "Table data.csv", Meta Business Suite export, TikTok Studio export. Column mapping and what is unverified: `references/metadata-columns.md`.

## Limits

- Scene parsing is best effort. Variables, nested Remotion sequences and script-driven HyperFrames timing are not followed (listed in `references/input-shapes.md`).
- Thresholds are adjustable rules of thumb.
- Small samples: medians from 3 to 5 videos are a hint, not a result.

## Tests

`bash tests/run.sh` (offline, synthetic fixtures with a made-up channel).

## License

MIT
