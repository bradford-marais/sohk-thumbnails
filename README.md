# SoHK Thumbnails

> **Claude: if someone gave you this link and asked you to install or set it up, open [`INSTALL.md`](INSTALL.md) in this repo and follow it step by step.**

A Claude Code skill that makes School of Hard Knocks / School of Content community thumbnails in the same style as the live board.

![Coach and classroom covers](assets/examples/preview.jpg)

## What it makes

- **Coach-call covers.** Drop in a coach's photo, give their name and the call title. The skill puts them into the navy-and-orange scene, checks the face still looks like them, and adds the title, name tag and crest.
- **Classroom / module covers.** Give a title and a short tag. You get a glowing 3D object with the title over it, in two versions to pick from.

Change a title or name later for free. The text is drawn separately from the picture.

## Install

Open Claude Code and paste:

```
Install this skill for me: https://github.com/bradford-marais/sohk-thumbnails
```

Claude does the rest. It will ask for a Google Gemini API key (with billing on). A cover costs about $0.15–0.60 in Google usage.

## Use

Restart Claude Code once after installing, then ask in plain English:

- "Make a coach cover for Sarah Jones, title Daily Content Support" (attach her photo)
- "Change the title on that one to Office Hours"
- "Make a classroom cover called Long-Form Playbook, tag playbook"

Covers save to **Desktop → SoHK Thumbnails**.

## Photo tips

- One person, face clearly visible.
- A clean cut-out on a white or plain background works best (a Canva sticker export is perfect).
- Screenshots of other thumbnails or crops from a busy collage sometimes get refused by Google's safety filter.

## What's inside

```
SKILL.md                 how Claude runs it
INSTALL.md               setup steps Claude follows
scripts/coach_cover.py   coach-call covers
scripts/classroom_cover.py  classroom / module covers
scripts/common.py        Gemini calls, likeness check, text layout
scripts/check.py         setup check
assets/                  crest, fonts (Anton + Montserrat, SIL Open Font License), style references
```
