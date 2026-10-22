---
name: sohk-thumbnails
description: Makes School of Hard Knocks / School of Content community thumbnails in the locked board style. Coach-call covers put the real coach (from their photo) into the navy-and-orange scene with the title, name pill and crest. Classroom covers are a glowing orange 3D object with a centered title and tag pill. Use when someone asks for a SoHK or School of Content thumbnail, a coach cover, a call cover, a module or classroom cover, a community cover, or to change the text or look of one already made. Does NOT make YouTube thumbnails for personal channels.
---

# SoHK Thumbnails

Two kinds of cover, both 1280×720, both matching the board already live in the community:

| Cover | What's on it | Script |
|---|---|---|
| **Coach call** | Real coach on the right, lit by a red-orange glow. Cream title top-left, orange name pill, crest bottom-left | `coach_cover.py` |
| **Classroom / module** | Glowing orange 3D object, centered white title, `>_ TAG` pill, crest top-right | `classroom_cover.py` |

Every cover is a **plate** (the picture, no words) plus a **text lockup** drawn in code. Gemini never draws the words, so names and titles are always spelled right, every cover lines up identically, and changing the text later costs nothing.

## Paths

```
SK=~/.claude/skills/sohk-thumbnails
PY=$SK/.venv/bin/python            # Windows: %USERPROFILE%\.claude\skills\sohk-thumbnails\.venv\Scripts\python.exe
```

Run the scripts from anywhere: `$PY $SK/scripts/coach_cover.py ...`

Finished covers go to `~/Desktop/SoHK Thumbnails/` (plates in its `plates/` subfolder). Pass `--out <folder>` to change that.

## Step 0: is it set up?

If `$SK/.env` or `$SK/.venv` is missing, stop and follow `$SK/INSTALL.md` first. If anything fails later in a way that looks like setup (missing module, bad key), run `$PY $SK/scripts/check.py`. It names the problem.

## Coach-call cover

### 1. Get the inputs (ask for anything missing, one question at a time)

- **The photo.** The user drags the file into the chat or gives a path.
- **The coach's name, exactly as it should appear.** Always ask. **Never guess who someone is from a photo.** A wrong name on a coach's cover is the one mistake that can't ship.
- **The title.** 2–4 words, e.g. "Daily Content Support", "YouTube Mastery", "Office Hours". Over 4 words, suggest a shorter one.
- **Motif (optional).** A faint background symbol, e.g. "rising chart with currency symbols", "YouTube play button", "chat bubbles". If they don't care, leave it out: the script picks one from the title.

**Photo rules.** Check the photo before spending money on it:
- One person, face clearly visible, decent resolution (face at least ~300px tall).
- Best: a clean cut-out on a white or plain background (a Canva "sticker" export). Gemini sometimes refuses crops taken from a busy collage or from someone else's thumbnail.
- Whatever they hold (an award, a mic) stays in the picture.

### 2. Run it

```bash
$PY $SK/scripts/coach_cover.py --photo "<photo>" --name "<Exact Name>" --title "<Title>" [--motif "<motif>"]
```

What happens: the background for that motif is made once and cached (the same title/motif reuses it, so a series like every "Daily Content Support" cover shares one scene). Then Gemini relights the coach into it, up to 4 times. Each try gets a likeness score (0–10) from a second model and the best one is kept. It stops early at 9+.

Takes 30–90 seconds. Tell the user it's running.

### 3. Show it

Open the finished PNG with the Read tool so you can see it, then show the user the path. Mention the likeness score from the output. If you see anything off (face doesn't look like the photo, odd hands, the person covering the title area), say so plainly before they ask.

### 4. Changes

| They want | Do this | Cost |
|---|---|---|
| Different title or name / typo fix | `--plate "<the plate path>" --name ... --title ...` (no `--photo`) | free |
| Tweak the picture ("less glow", "warmer face", "move him right") | `--photo ... --plate "<plate>" --edit "<the change>" --name ... --title ...` | ~$0.15–0.45 |
| Start the picture again | Run step 2 again | ~$0.15–0.60 |
| New background for this motif | Add `--new-background` | +~$0.15 |

## Classroom / module cover

### 1. Get the inputs

- **Title**: e.g. "Short-Form Blueprint", "Monthly Call Replays". Up to ~5 words.
- **Tag** (the small pill): one or two words, e.g. `start here`, `blueprint`, `playbook`, `replays`, `framework`, `bonus`, `resources`.
- **Motif (optional)**: the object in the middle, e.g. "a smartphone wireframe blueprint", "an open glowing door", "a looping replay arrow". Without one, the script picks from the title.

### 2. Run it

```bash
$PY $SK/scripts/classroom_cover.py --title "<Title>" --tag "<tag>" [--motif "<object>"] [--variants 2]
```

Makes 2 versions by default (~$0.30 total) so they can pick.

### 3. Show both, let them pick, then change text for free with `--plate "<chosen plate>" --title ... --tag ...`.

## Several covers at once

Run them **one after another**, never in parallel (parallel calls hit Gemini's rate limit). After each one, show it before moving on, unless the user says to do the whole batch and show at the end. For a series (same title, different coaches), use the same title and motif every time so they share a background.

## When it goes wrong

| Message | What it means | Fix |
|---|---|---|
| "Gemini refused this photo every time" | Google's safety filter blocked the photo | Use a clean photo of just that person on a plain background, cropped closer. Don't retry the same photo more than twice. |
| "best likeness only N/10" | The face drifted | Look at it. Usually a different, sharper photo fixes it. |
| "spend cap reached" | Their Google AI Studio monthly cap was hit | They raise it at https://aistudio.google.com/spend |
| "over capacity" | Google is busy | Wait 2–3 minutes, run again. |
| "Title is too long" | Doesn't fit the layout | Shorten it. |
| Missing module / key errors | Setup problem | `$PY $SK/scripts/check.py` |

If the same call fails twice in a row with the same error, stop and tell the user what's happening. Don't keep re-running it.

## Rules

1. **Never guess a coach's name.** Ask, and use exactly what they type.
2. **Never put real people's names in an image prompt.** The scripts never do; don't add names to `--motif` or `--edit` either (Google blocks those). Say "the presenter".
3. **Show every cover** before calling it done.
4. **Don't change the layout, colours, fonts or crest.** They're locked to match the live board. If someone wants a different style, that's a design decision for the SoHK team, not a tweak.
5. **One cover at a time** against the API.
