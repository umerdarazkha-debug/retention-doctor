#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/.."
F=tests/fixtures
R="uv run --python 3.12 scripts/retention.py"
P="uv run --python 3.12 scripts/portfolio.py"
fail=0
expect() { if grep -qF -- "$3" <<<"$2"; then echo "ok   $1"; else echo "FAIL $1: missing '$3'"; fail=1; fi; }
refute() { if grep -qF -- "$3" <<<"$2"; then echo "FAIL $1: should not contain '$3'"; fail=1; else echo "ok   $1"; fi; }

# scene level, scenes.json
out=$($R --curve $F/curve.csv --timeline $F/scenes.json)
expect hook-flag "$out" "HOOK (first 3 s): 100% -> 66%, lost 34 points"
expect hook-verdict "$out" "HOOK DROP"
expect drop1 "$out" "DROP #1: At 1.4-2.0 s you lost 22 points (36.7/s, 10.2x your average)"
expect drop1-scene "$out" "Scene 'title card' (1.4-3.0 s), text 'Seven rules nobody told you about editing reels fast and clean' appeared at 1.4 s"
expect drop1-cause "$out" "has 11 words but was on screen only 0.6 s"
expect drop2 "$out" "DROP #2: At 11.0-12.0 s you lost 16 points"
expect drop2-scene "$out" "Scene 'cta' (11.0-14.0 s), text 'Follow for part 2' appeared at 11.0 s"
expect drop2-cta "$out" "call to action is on screen at 11.0 s (55% into the video)"
expect only-two "$out" "DROP #2"
refute no-drop3 "$out" "DROP #3"
refute no-flat-drop "$out" "At 3.0 s"

# csv with audio note, same drops
out=$($R --curve $F/curve.csv --timeline $F/scenes.csv)
expect csv-music "$out" "Audio note at this time: 'music stops'"

# SRT: cue text maps
out=$($R --curve $F/curve.csv --timeline $F/captions.srt)
expect srt-drop1 "$out" "Scene 'cue 2'"
expect srt-text "$out" "Seven rules nobody told you"

# HyperFrames
out=$($R --curve $F/curve.csv --timeline $F/hyperframes/index.html)
expect hf-drop1 "$out" "Scene 'title-card' (1.4-3.0 s)"
expect hf-drop2 "$out" "Scene 'cta' (11.0-14.0 s)"

# Remotion project folder (fps found in Root.tsx), plus the unparseable Sequence is reported
out=$($R --curve $F/curve.csv --timeline $F/remotion)
expect rm-drop1 "$out" "Scene 'title card' (1.4-3.0 s)"
expect rm-drop2 "$out" "Scene 'cta' (11.0-14.0 s)"
expect rm-warn "$out" "non-numeric from skipped"

# negative: a steady curve has no steep drops and no hook drop
out=$($R --curve $F/smooth.csv --timeline $F/scenes.json)
expect smooth-none "$out" "No steep drops"
refute smooth-hook "$out" "HOOK DROP"
expect smooth-hook-ok "$out" "in line with the rest of this video"

# negative: bad curve rejected
echo "second,percent_watching" > "$(mktemp -d)/x" ; bad=$(mktemp -d)/bad.csv; printf "a,b\n1,2\n" > "$bad"
$R --curve "$bad" --timeline $F/scenes.json >/dev/null 2>&1 && { echo "FAIL bad-curve accepted"; fail=1; } || echo "ok   bad-curve rejected"

# portfolio
out=$($P --metadata $F/videos.csv --tags $F/tags.csv)
expect p-hook-bold "$out" "bold-claim         n=5   median      50.0  range 47.0-55.0  [ok]"
expect p-story-refused "$out" "story              n=2   median      62.5  range 60.0-65.0  [INSUFFICIENT DATA (n=2), no call]"
expect p-leader "$out" "LEADER: 'bold-claim' (median 50.0, n=5) over 'question' (median 41.0, n=4)"
refute p-story-not-leader "$out" "LEADER: 'story'"
expect p-face "$out" "LEADER: 'yes' (median 52.0, n=7) over 'no' (median 44.5, n=4)"
expect p-topic-nowinner "$out" "NO WINNER: need at least 2 groups with 3+ videos to compare (have 1)."
expect p-cta-follow-refused "$out" "follow             n=2 "
out=$($P --metadata $F/videos.csv --tags $F/tags.csv --metric saves_per_1k --json)
n=$(jq -r '.report.hook_type.rows[] | select(.value=="bold-claim") | .n' <<<"$out")
[ "$n" = "5" ] && echo "ok   p-json-n" || { echo "FAIL p-json-n=$n"; fail=1; }
out=$($P --metadata $F/videos.csv --tags $F/tags.csv --min-n 6)
expect p-minn "$out" "NO WINNER"
refute p-minn-noleader "$out" "LEADER: 'bold-claim'"

[ $fail -eq 0 ] && echo "ALL PASS" || { echo "FAILED"; exit 1; }
