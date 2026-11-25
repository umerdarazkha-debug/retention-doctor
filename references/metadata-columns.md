# Metadata column mapping (portfolio part)

The script lower-cases headers and maps these names to its own. Checked 2026-11-26.

| Script column | YouTube Studio advanced mode, Table data.csv | Instagram (Meta Business Suite export / Graph API) | TikTok Studio export |
|---|---|---|---|
| video_id | `Content` (the video id) | `Post ID` | `Video link` (use a short id you make) |
| title | `Video title` | `Description` | `Video title` |
| length_s | `Duration` (seconds) | `Duration (sec)` | not in the account export; type it |
| views | `Views` | `Views` (API metric `views`) | `Total views` |
| avg_watch_pct | `Average percentage viewed (%)` | not exported per post; type it from the app | not in the export; type it from the app |
| saves | not provided | `Saves` (API metric `saved`) | not provided; type it |
| shares | not provided | `Shares` (API metric `shares`) | `Total shares` |

Sources:

- YouTube Table data.csv headers: a public walkthrough lists Content, Video title, Video publish time, Duration, Views, Watch time, Subscribers, Average view duration, Impressions, Impressions click-through rate (%). https://www.freecodecamp.org/news/extract-youtube-analytics-data-and-analyze-in-python/ . `Average percentage viewed (%)` appears only when you add that metric to the report in advanced mode. verified: partial.
- Instagram metric names (`views`, `reach`, `likes`, `comments`, `shares`, `saved`, `ig_reels_avg_watch_time`): https://developers.facebook.com/docs/instagram-platform/reference/instagram-media/insights/ . verified: true for API names. The Meta Business Suite CSV header names are verified: false.
- TikTok export headers: no official page lists them. A third-party import guide lists `Video title, Video link, Post time, Total likes, Total comments, Total shares, Total views`. verified: false. UNVERIFIED RULE: check the header row of your own export.

Headers vary by account and app version. Open your file, compare the header row with this table, and rename columns in the CSV if the script reports a missing column.
