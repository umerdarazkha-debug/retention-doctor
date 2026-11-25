"""Scene timeline parsers for retention-doctor (stdlib only).

Every parser returns a list of Scene dicts:
  {start, end, label, text, text_at, audio_note, source}
Times are seconds (float). Best-effort only: see README limits.
"""
import csv
import json
import os
import re
from html.parser import HTMLParser

WARNINGS = []


def warn(msg):
    WARNINGS.append(msg)


def _f(v, default=None):
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return default


def _scene(start, end, label, text="", text_at=None, audio_note="", source=""):
    return {"start": start, "end": end, "label": label or "", "text": (text or "").strip(),
            "text_at": start if text_at is None else text_at,
            "audio_note": audio_note or "", "source": source}


# ---------- scenes.json / scenes.csv ----------
def parse_scenes_rows(rows, source):
    out = []
    for i, r in enumerate(rows, 1):
        r = {str(k).strip().lower(): v for k, v in r.items()}
        s, e = _f(r.get("start_s")), _f(r.get("end_s"))
        if s is None or e is None:
            warn(f"{source}: row {i} has no numeric start_s/end_s, skipped")
            continue
        out.append(_scene(s, e, r.get("label") or f"scene {i}", r.get("on_screen_text", ""),
                          _f(r.get("text_at_s")), r.get("audio_note", ""), source))
    return out


def parse_scenes_json(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    rows = data["scenes"] if isinstance(data, dict) else data
    return parse_scenes_rows(rows, os.path.basename(path))


def parse_scenes_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return parse_scenes_rows(list(csv.DictReader(fh)), os.path.basename(path))


# ---------- SRT ----------
_TS = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)")


def _sec(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")[:3]) / 1000.0


def parse_srt(path):
    with open(path, encoding="utf-8-sig") as fh:
        blocks = re.split(r"\n\s*\n", fh.read().replace("\r\n", "\n").strip())
    out = []
    for b in blocks:
        lines = b.split("\n")
        for idx, ln in enumerate(lines):
            m = _TS.search(ln)
            if m:
                g = m.groups()
                text = " ".join(x.strip() for x in lines[idx + 1:] if x.strip())
                out.append(_scene(_sec(*g[:4]), _sec(*g[4:]), f"cue {len(out) + 1}", text,
                                  source=os.path.basename(path)))
                break
    return out


# ---------- HyperFrames (data-start / data-duration) ----------
class _HF(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.items, self.skip = [], [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        a = dict(attrs)
        entry = None
        if "data-start" in a:
            s = _f(a.get("data-start"))
            d = _f(a.get("data-duration"))
            e = _f(a.get("data-end"))
            if s is not None and (d is not None or e is not None):
                end = s + d if d is not None else e
                label = a.get("data-label") or a.get("id") or (a.get("class") or "").split(" ")[0] or tag
                entry = {"start": s, "end": end, "label": label, "text": [], "tag": tag}
                self.items.append(entry)
            else:
                warn(f"HyperFrames: <{tag}> has data-start but no usable data-duration/data-end, skipped")
        self.stack.append((tag, entry))

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self.skip or not data.strip():
            return
        for _, entry in reversed(self.stack):
            if entry is not None:
                entry["text"].append(data.strip())
                break


def parse_hyperframes(path):
    files = [path]
    if os.path.isdir(path):
        files = []
        for root, dirs, fs in os.walk(path):
            dirs[:] = [d for d in dirs if d not in ("node_modules", ".git")]
            files += [os.path.join(root, f) for f in fs if f.endswith(".html")]
        files.sort()
    out = []
    for fp in files:
        p = _HF()
        with open(fp, encoding="utf-8") as fh:
            p.feed(fh.read())
        for it in p.items:
            out.append(_scene(it["start"], it["end"], it["label"], " ".join(it["text"]),
                              source=os.path.basename(fp)))
    return sorted(out, key=lambda s: (s["start"], s["end"]))


# ---------- Remotion (<Sequence from durationInFrames>) ----------
_SEQ_OPEN = re.compile(r"<Sequence\b(.*?)(/?)>", re.S)
_ATTR_NUM = lambda name: re.compile(r"\b" + name + r"\s*=\s*\{\s*(-?\d+(?:\.\d+)?)\s*\}")
_FROM, _DUR = _ATTR_NUM("from"), _ATTR_NUM("durationInFrames")
_NAME = re.compile(r"\bname\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|\{\s*[\"']([^\"']*)[\"']\s*\})")
_FPS = [re.compile(r"\bfps\s*=\s*\{\s*(\d+(?:\.\d+)?)\s*\}"), re.compile(r"\bfps\s*:\s*(\d+(?:\.\d+)?)")]


def _jsx_text(body):
    texts = re.findall(r">\s*([^<>{}]+?)\s*<", ">" + body + "<")
    texts += re.findall(r"\{\s*[\"'`]([^\"'`]+)[\"'`]\s*\}", body)
    return " ".join(t.strip() for t in texts if t.strip())


def find_fps(text):
    for rx in _FPS:
        m = rx.search(text)
        if m:
            return float(m.group(1))
    return None


def parse_remotion(path, fps=None):
    files = [path]
    if os.path.isdir(path):
        files = []
        for root, dirs, fs in os.walk(path):
            dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", "out", "build")]
            files += [os.path.join(root, f) for f in fs if f.endswith((".tsx", ".jsx", ".ts", ".js"))]
        files.sort()
    texts = {}
    for fp in files:
        with open(fp, encoding="utf-8", errors="replace") as fh:
            texts[fp] = fh.read()
    if fps is None:
        for t in texts.values():
            fps = find_fps(t)
            if fps:
                break
    if not fps:
        raise SystemExit("Remotion: could not find fps in the project. Pass --fps N.")
    out = []
    for fp, t in texts.items():
        for m in _SEQ_OPEN.finditer(t):
            attrs = m.group(1)
            fm, dm = _FROM.search(attrs), _DUR.search(attrs)
            nm = _NAME.search(attrs)
            if not dm:
                warn(f"{os.path.basename(fp)}: <Sequence> with non-numeric durationInFrames skipped")
                continue
            start_f = float(fm.group(1)) if fm else (0.0 if "from" not in attrs else None)
            if start_f is None:
                warn(f"{os.path.basename(fp)}: <Sequence> with non-numeric from skipped")
                continue
            body = ""
            if not m.group(2):
                end_tag = t.find("</Sequence>", m.end())
                body = t[m.end(): end_tag if end_tag != -1 else m.end()]
            label = (nm.group(1) or nm.group(2) or nm.group(3)) if nm else f"sequence {len(out) + 1}"
            out.append(_scene(start_f / fps, (start_f + float(dm.group(1))) / fps, label,
                              _jsx_text(body), source=os.path.basename(fp)))
    if not out:
        warn("Remotion: no <Sequence> with numeric from/durationInFrames found")
    return sorted(out, key=lambda s: (s["start"], s["end"]))


def load_timeline(path, fps=None):
    if os.path.isdir(path):
        has_html = any(f.endswith(".html") for _, _, fs in os.walk(path) for f in fs)
        has_tsx = any(f.endswith((".tsx", ".jsx")) for _, _, fs in os.walk(path) for f in fs)
        if has_tsx and not has_html:
            return parse_remotion(path, fps)
        if has_html and not has_tsx:
            return parse_hyperframes(path)
        raise SystemExit("Folder holds both HTML and TSX/JSX. Pass the exact file.")
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        return parse_scenes_json(path)
    if ext == ".csv":
        return parse_scenes_csv(path)
    if ext in (".srt", ".vtt"):
        return parse_srt(path)
    if ext == ".html":
        return parse_hyperframes(path)
    if ext in (".tsx", ".jsx", ".ts", ".js"):
        return parse_remotion(path, fps)
    raise SystemExit(f"Unknown timeline type: {path}")
