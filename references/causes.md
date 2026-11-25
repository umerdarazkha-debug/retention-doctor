# Retention drop causes: checklist

The script matches these by rule. The numbers it uses (3-second hook window, 3 words per second reading speed, 70% CTA line) are adjustable rules of thumb, not platform facts. Change them with `--hook-seconds` and `--wps`.

| Cause | How the script spots it | One fix |
|---|---|---|
| Slow hook | The drop starts before second 3. | Open on the payoff or the problem in the first second. Cut intros and logos. |
| Text too long to read in time | A caption of 4+ words was on screen for less time than words / reading speed. | Cut to 5 words or fewer, or hold it longer. |
| Cut to a static frame | A scene starts within 0.3 s before the drop and has no text, or its label says static, still, freeze, blank or black. | Add motion, a zoom or a new element in the first half second. |
| Cut that lines up with the drop | A scene boundary sits inside the drop window. | Start the new scene with a clear promise or a visible change. |
| Music or audio drop | The scene has an `audio_note` such as "music stops", "silence", "fade". | Keep a music bed or a sound effect running through the cut. |
| CTA too early | A scene label or text says follow, subscribe, save, like, share, link in bio, comment or part 2, and it is less than 70% into the video. | Move the call to action to the last 2 seconds, after the payoff. |

Causes the script cannot see (check by watching the clip with sound off, then on):

- The promise made in the hook is not delivered by the next scene.
- Audio is quiet, clipped or out of sync.
- Captions cover the subject or sit in an unsafe zone of the app.
- The topic itself is wrong for the audience that saw it (check the audience and traffic source tabs).
- Loop-friendly endings: a video that ends early can show a drop at the very end that is normal.

Reading the numbers:

- "Points" are percentage points of the starting audience, not a percent of the people left.
- A drop is flagged when its loss per second is at least `--factor` times the video's own average loss per second (default 2) and at least `--min-loss` points (default 3).
- Average loss per second = (first value - last value) / length. Every video is compared with itself.
