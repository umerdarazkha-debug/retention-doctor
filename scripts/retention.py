#!/usr/bin/env python3
"""retention-doctor, scene level: find the steepest retention drops and map them to scenes.

Usage:
  uv run --python 3.12 scripts/retention.py --curve curve.csv --timeline PATH [--fps 30]
      [--factor 2.0] [--min-loss 3] [--hook-seconds 3] [--wps 3.0] [--json]
"""
import argparse
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline as tl  # noqa: E402

TIME_COLS = ["second", "seconds", "time", "time_s", "t", "video position (s)", "elapsed"]
PCT_COLS = ["percent_watching", "percent", "retention", "audience retention", "audience retention (%)",
            "watching", "pct", "viewers (%)", "percent_viewers"]
CTA_RX = re.compile(r"\b(follow|subscribe|save this|save it|like|share|link in bio|comment|cta|part 2)\b", re.I)
STATIC_RX = re.compile(r"\b(static|still|freeze|blank|black)\b", re.I)
AUDIO_RX = re.compile(r"(drop|stop|silence|silent|cut|ends|fade)", re.I)


def load_curve(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise SystemExit("Curve file is empty.")
    cols = {c.strip().lower(): c for c in rows[0].keys()}
    tc = next((cols[c] for c in TIME_COLS if c in cols), None)
    pc = next((cols[c] for c in PCT_COLS if c in cols), None)
    if not tc or not pc:
        raise SystemExit(f"Curve needs a time column ({TIME_COLS[:2]}...) and a percent column "
                         f"({PCT_COLS[:2]}...). Found: {list(rows[0].keys())}")
    pts = []
    for r in rows:
        try:
            pts.append((float(str(r[tc]).strip()), float(str(r[pc]).strip().rstrip("%"))))
        except ValueError:
            raise SystemExit(f"Bad number in curve row: {r}")
    pts.sort()
    if len(pts) < 3:
        raise SystemExit("Curve needs at least 3 points.")
    if pts[0][0] != 0:
        raise SystemExit("Curve must start at second 0 (usually 100%).")
    return pts


def value_at(pts, t):
    if t <= pts[0][0]:
        return pts[0][1]
    for (t0, p0), (t1, p1) in zip(pts, pts[1:]):
        if t0 <= t <= t1:
            return p0 if t1 == t0 else p0 + (p1 - p0) * (t - t0) / (t1 - t0)
    return pts[-1][1]


def find_drops(pts, factor, min_loss):
    dur = pts[-1][0]
    avg = (pts[0][1] - pts[-1][1]) / dur if dur else 0.0
    flagged = []
    for (t0, p0), (t1, p1) in zip(pts, pts[1:]):
        dt = t1 - t0
        if dt <= 0:
            continue
        slope = (p0 - p1) / dt
        flagged.append((t0, t1, p0 - p1, slope, avg > 0 and slope >= factor * avg and (p0 - p1) >= min_loss))
    drops, cur = [], None
    for t0, t1, loss, slope, hit in flagged:
        if hit:
            if cur and abs(cur["end"] - t0) < 1e-9:
                cur["end"], cur["loss"] = t1, cur["loss"] + loss
            else:
                cur = {"start": t0, "end": t1, "loss": loss}
                drops.append(cur)
        else:
            cur = None
    for d in drops:
        d["slope"] = d["loss"] / (d["end"] - d["start"])
        d["ratio"] = d["slope"] / avg if avg else 0
    drops.sort(key=lambda d: (-d["loss"], d["start"]))
    return drops, avg


def active_at(scenes, t):
    return [s for s in scenes if s["start"] - 1e-9 <= t < s["end"] - 1e-9]


def words(text):
    return len(re.findall(r"\w+", text))


def analyse_drop(d, scenes, dur, wps):
    d["scenes"], d["causes"] = [], []
    act = active_at(scenes, d["start"])
    if not act:
        d["scene_label"], d["text"], d["text_at"] = None, "", None
        d["causes"].append(("no_scene", "No scene found at this time. Check the timeline covers the full video.",
                            "Fix the timeline file, then re-run."))
        return d
    primary = min(act, key=lambda s: s["end"] - s["start"])
    texts = [s for s in act if s["text"]]
    # text that appeared at or just before the drop (within 1 s) also counts
    recent = [s for s in scenes if s["text"] and d["start"] - 1.0 <= s["text_at"] <= d["end"]]
    for s in recent:
        if s not in texts:
            texts.append(s)
    d["scene_label"] = primary["label"]
    d["scene_span"] = (primary["start"], primary["end"])
    d["text"] = " / ".join(s["text"] for s in texts)
    d["text_at"] = min((s["text_at"] for s in texts), default=None)
    d["audio_note"] = " ".join(s["audio_note"] for s in act if s["audio_note"])
    causes = d["causes"]
    if d["start"] < 3.0:
        causes.append(("slow_hook", "Drop falls inside the first 3 seconds, so the hook is not earning the stay.",
                       "Open on the payoff or the problem in the first second. Cut any intro, logo or throat-clearing."))
    for s in texts:
        n = words(s["text"])
        visible = d["end"] - s["text_at"]
        need = n / wps
        if n >= 4 and visible < need:
            causes.append(("text_too_long",
                           f"Text '{s['text']}' has {n} words but was on screen only {max(visible, 0):.1f} s "
                           f"before the drop ended (reading needs about {need:.1f} s at {wps:g} words/s).",
                           f"Cut the text to 5 words or fewer, or hold it for {need:.1f} s."))
            break
    near_cut = [s for s in scenes if d["start"] - 0.3 <= s["start"] <= d["end"] and s["start"] > 0]
    if near_cut:
        blank = [s for s in near_cut if not s["text"] or STATIC_RX.search(s["label"])]
        if blank:
            causes.append(("static_frame", f"A cut to '{blank[0]['label']}' at {blank[0]['start']:.1f} s "
                           "brings a frame with no text or a static look.",
                           "Add motion, a zoom or a new element in the first half second after that cut."))
        else:
            causes.append(("cut", f"A cut to '{near_cut[0]['label']}' at {near_cut[0]['start']:.1f} s "
                           "lines up with the drop.",
                           "Keep the cut but start the new scene with a clear promise or a visual change viewers want to see."))
    if d["audio_note"] and AUDIO_RX.search(d["audio_note"]):
        causes.append(("music_drop", f"Audio note at this time: '{d['audio_note']}'.",
                       "Keep the music bed or a sound effect running through the cut."))
    for s in act:
        if CTA_RX.search(s["label"] + " " + s["text"]) and d["start"] < 0.7 * dur:
            causes.append(("cta_early", f"A call to action is on screen at {d['start']:.1f} s "
                           f"({d['start'] / dur * 100:.0f}% into the video).",
                           "Move the call to action to the last 2 seconds, after the payoff."))
            break
    prio = ["text_too_long", "static_frame", "music_drop", "cta_early", "cut", "slow_hook"]
    causes.sort(key=lambda c: prio.index(c[0]) if c[0] in prio else 99)
    if not causes:
        causes.append(("unknown", "No checklist rule matched. Watch these seconds with sound off and on.",
                       "Re-watch this moment and compare it with references/causes.md."))
    return d


def hook_report(pts, seconds, avg, factor, min_loss):
    dur = pts[-1][0]
    if dur <= seconds + 1:
        return None
    p0, p3, pe = pts[0][1], value_at(pts, seconds), pts[-1][1]
    loss = p0 - p3
    rest = (p3 - pe) / (dur - seconds)
    slope = loss / seconds
    ratio = slope / rest if rest > 0 else float("inf")
    return {"seconds": seconds, "from": p0, "to": p3, "loss": loss, "slope": slope,
            "rest_slope": rest, "ratio": ratio, "flag": loss >= min_loss and ratio >= factor}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--curve", required=True)
    ap.add_argument("--timeline", required=True,
                    help="scenes.json/.csv, .srt, HyperFrames .html (or folder), Remotion .tsx (or folder)")
    ap.add_argument("--fps", type=float)
    ap.add_argument("--factor", type=float, default=2.0, help="drop slope must be this many times the video average")
    ap.add_argument("--min-loss", type=float, default=3.0, help="minimum points lost to count as a drop")
    ap.add_argument("--hook-seconds", type=float, default=3.0)
    ap.add_argument("--wps", type=float, default=3.0, help="reading speed, words per second (adjustable rule of thumb)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    pts = load_curve(a.curve)
    scenes = tl.load_timeline(a.timeline, a.fps)
    if not scenes:
        raise SystemExit("Timeline gave no scenes. " + " ".join(tl.WARNINGS))
    dur = pts[-1][0]
    drops, avg = find_drops(pts, a.factor, a.min_loss)
    for d in drops:
        analyse_drop(d, scenes, dur, a.wps)
    hook = hook_report(pts, a.hook_seconds, avg, a.factor, a.min_loss)
    t_end = max(s["end"] for s in scenes)
    notes = list(tl.WARNINGS)
    if abs(t_end - dur) > 1.0:
        notes.append(f"Timeline ends at {t_end:.1f} s but the curve ends at {dur:.1f} s. Check fps or the timeline.")

    if a.json:
        print(json.dumps({"duration_s": dur, "avg_slope": avg, "hook": hook, "drops": [
            {k: v for k, v in d.items() if k != "scenes"} for d in drops], "notes": notes},
            indent=2, default=list))
        return

    print(f"RETENTION REPORT  ({dur:.1f} s video, {pts[0][1]:.0f}% -> {pts[-1][1]:.0f}%, "
          f"average loss {avg:.2f} points/s)")
    print(f"Units: 'points' = percentage points of the starting audience.\n")
    if hook:
        print(f"HOOK (first {hook['seconds']:g} s): {hook['from']:.0f}% -> {hook['to']:.0f}%, lost {hook['loss']:.0f} points "
              f"({hook['slope']:.1f}/s vs {hook['rest_slope']:.1f}/s for the rest of the video)")
        print("  VERDICT: " + ("HOOK DROP. Viewers leave much faster here than later." if hook["flag"]
                               else "hook loss is in line with the rest of this video.") + "\n")
    if not drops:
        print(f"No steep drops: no stretch lost {a.factor:g}x the average slope with at least {a.min_loss:g} points.")
    for i, d in enumerate(drops, 1):
        span = f"{d['start']:.1f}-{d['end']:.1f} s" if d["end"] - d["start"] > 0.25 else f"{d['start']:.1f} s"
        print(f"DROP #{i}: At {span} you lost {d['loss']:.0f} points "
              f"({d['slope']:.1f}/s, {d['ratio']:.1f}x your average)")
        if d.get("scene_label") is None:
            print("  Scene: none found")
        else:
            line = f"  Scene '{d['scene_label']}' ({d['scene_span'][0]:.1f}-{d['scene_span'][1]:.1f} s)"
            if d["text"]:
                line += f", text '{d['text']}' appeared at {d['text_at']:.1f} s"
            else:
                line += ", no on-screen text"
            print(line)
        print("  Likely causes:")
        for _, why, _fix in d["causes"]:
            print(f"    - {why}")
        print(f"  Fix: {d['causes'][0][2]}\n")
    for n in notes:
        print(f"NOTE: {n}")
    print("Checklist of every cause: references/causes.md. Rules of thumb here are defaults, not platform facts.")


if __name__ == "__main__":
    main()
