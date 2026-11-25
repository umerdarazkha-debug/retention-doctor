# Input shapes

## Retention curve (CSV)

```
second,percent_watching
0,100
1.4,92
```

- Must start at second 0. At least 3 rows.
- Also accepted column names: time, time_s, seconds, t / percent, retention, audience retention, audience retention (%).
- Where to get it: type values by eye from the audience retention chart in the app (read the % at each notch), or read them off a screenshot. Some tools export a curve; none of the three apps' standard CSV exports is known to include a per-second curve. UNVERIFIED: check the current export in your app.
- YouTube charts retention against percent of video, not seconds. Multiply by the video length to get seconds.

## Scene timeline (pick one)

1. `scenes.json` or `scenes.csv`: columns `start_s, end_s, label, on_screen_text`. Optional `text_at_s` (when the text appears, default = start) and `audio_note`. JSON may be a list or `{"scenes": [...]}`.
2. Remotion: a `.tsx` file or a project folder. Reads `<Sequence from={N} durationInFrames={M} name="...">` with numeric values, plus `fps={30}` or `fps: 30` from a `<Composition>`. Pass `--fps` if it is not found. Text comes from plain JSX text and `{"string literals"}` inside the Sequence.
3. HyperFrames: an `.html` file or folder. Reads every element with `data-start` and (`data-duration` or `data-end`), in seconds. Label = `data-label`, else `id`, else first class. Text goes to the innermost timed element.
4. SRT (or VTT-like with comma/dot times): each cue becomes a scene labelled `cue N` with its words.

## Parser limits (best effort, regex and HTML parsing, no code execution)

- Remotion: `from` or `durationInFrames` given as a variable or expression is skipped and reported as a NOTE. Nested Sequences are read as if `from` were absolute (Remotion adds the parent offset; the script does not). `TransitionSeries`, `Series`, `<Audio from>` and text coming from props or other files are not followed. Sequences inside a component used several times are counted once.
- HyperFrames: only static attributes. Times set by script are not seen. Text added by JavaScript is not seen.
- SRT: cue text is what is spoken, which may differ from what is on screen.

## Portfolio files

`videos.csv` columns: `video_id, title, length_s, views, avg_watch_pct, saves, shares`. See `metadata-columns.md` for accepted export names.

`tags.csv` columns: `video_id, hook_type, format, topic, has_face, cta`. Claude fills these in during the workflow (see SKILL.md). Keep each value to one short lowercase word or hyphenated phrase so groups match.
