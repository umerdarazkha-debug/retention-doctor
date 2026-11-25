#!/usr/bin/env python3
"""retention-doctor, portfolio level: rank tags by median performance, refuse thin evidence.

Usage:
  uv run --python 3.12 scripts/portfolio.py --metadata videos.csv --tags tags.csv
      [--metric avg_watch_pct|views|saves_per_1k|shares_per_1k] [--min-n 3] [--json]
"""
import argparse
import csv
import json
import statistics
import sys

ALIASES = {
    "video_id": ["video_id", "id", "content", "post id", "video id"],
    "title": ["title", "video title", "description"],
    "length_s": ["length_s", "length", "duration", "duration (sec)", "duration (s)"],
    "views": ["views", "video views", "total views"],
    "avg_watch_pct": ["avg_watch_pct", "average percentage viewed (%)", "average percentage viewed",
                      "avg watch %", "avg_watch_percent", "watched full video (%)"],
    "saves": ["saves", "saved", "total saves"],
    "shares": ["shares", "total shares"],
}
TAG_DIMS = ["hook_type", "format", "topic", "has_face", "cta"]
METRICS = {"avg_watch_pct": "average watch %", "views": "views",
           "saves_per_1k": "saves per 1,000 views", "shares_per_1k": "shares per 1,000 views"}


def num(v):
    if v is None:
        return None
    s = str(v).strip().replace(",", "").rstrip("%")
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def load_metadata(path):
    rows = read_csv(path)
    if not rows:
        raise SystemExit("Metadata file is empty.")
    cols = {c.strip().lower(): c for c in rows[0].keys()}
    m = {k: next((cols[x] for x in v if x in cols), None) for k, v in ALIASES.items()}
    if not m["video_id"]:
        raise SystemExit(f"Metadata needs a video id column. Found: {list(rows[0].keys())}")
    out = {}
    for r in rows:
        vid = r[m["video_id"]].strip()
        if not vid or vid.lower() == "total":
            continue
        d = {k: (num(r[c]) if k not in ("video_id", "title") and c else (r[c] if c else None))
             for k, c in m.items()}
        v = d.get("views")
        d["saves_per_1k"] = d["saves"] / v * 1000 if v and d.get("saves") is not None else None
        d["shares_per_1k"] = d["shares"] / v * 1000 if v and d.get("shares") is not None else None
        out[vid] = d
    return out


def rank(meta, tags, metric, min_n):
    dims = [d for d in TAG_DIMS if d in tags[0]] or [c for c in tags[0] if c != "video_id"]
    report = {}
    for dim in dims:
        groups = {}
        for r in tags:
            vid, val = r["video_id"].strip(), (r.get(dim) or "").strip()
            if not val or vid not in meta or meta[vid].get(metric) is None:
                continue
            groups.setdefault(val, []).append(meta[vid][metric])
        rows = [{"value": k, "n": len(v), "median": statistics.median(v), "min": min(v), "max": max(v)}
                for k, v in groups.items()]
        rows.sort(key=lambda r: (-r["median"], r["value"]))
        eligible = [r for r in rows if r["n"] >= min_n]
        for r in rows:
            r["status"] = "ok" if r["n"] >= min_n else f"INSUFFICIENT DATA (n={r['n']}), no call"
        if len(eligible) < 2:
            verdict = (f"NO WINNER: need at least 2 groups with {min_n}+ videos to compare "
                       f"(have {len(eligible)}).")
        elif eligible[0]["median"] == eligible[1]["median"]:
            verdict = f"NO WINNER: '{eligible[0]['value']}' and '{eligible[1]['value']}' tie on median."
        else:
            verdict = (f"LEADER: '{eligible[0]['value']}' (median {eligible[0]['median']:.1f}, n={eligible[0]['n']}) "
                       f"over '{eligible[1]['value']}' (median {eligible[1]['median']:.1f}, n={eligible[1]['n']}). "
                       "A lead, not proof: other tags and topics are mixed in.")
        report[dim] = {"rows": rows, "verdict": verdict}
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--metadata", required=True)
    ap.add_argument("--tags", required=True)
    ap.add_argument("--metric", default="avg_watch_pct", choices=list(METRICS))
    ap.add_argument("--min-n", type=int, default=3)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    meta = load_metadata(a.metadata)
    tags = read_csv(a.tags)
    if not tags or "video_id" not in tags[0]:
        raise SystemExit("tags.csv needs a video_id column.")
    unknown = [r["video_id"] for r in tags if r["video_id"].strip() not in meta]
    untagged = [v for v in meta if v not in {r["video_id"].strip() for r in tags}]
    rep = rank(meta, tags, a.metric, a.min_n)
    if a.json:
        print(json.dumps({"metric": a.metric, "report": rep, "tag_ids_not_in_metadata": unknown,
                          "untagged_videos": untagged}, indent=2))
        return
    print(f"PORTFOLIO REPORT  metric: {METRICS[a.metric]}  videos with metadata: {len(meta)}  tagged: {len(tags)}")
    print(f"Rule: no winner is called for a group with fewer than {a.min_n} videos.\n")
    for dim, d in rep.items():
        print(f"{dim}")
        for r in d["rows"]:
            print(f"  {r['value']:<18} n={r['n']:<3} median {r['median']:>9.1f}  range {r['min']:.1f}-{r['max']:.1f}  [{r['status']}]")
        print(f"  -> {d['verdict']}\n")
    if unknown:
        print("WARNING: tags.csv has ids missing from metadata: " + ", ".join(unknown))
    if untagged:
        print("WARNING: videos with no tags yet: " + ", ".join(untagged))


if __name__ == "__main__":
    main()
