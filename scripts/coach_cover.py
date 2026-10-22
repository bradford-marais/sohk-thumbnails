#!/usr/bin/env python3
"""Coach-call cover: the real coach relit into the navy-and-orange scene, then the
title + name lockup and crest drawn on top.

  python coach_cover.py --photo coach.png --name "Joel Kaplan" \
      --title "Monetization Masterclass" --motif "rising chart with currency symbols"

Re-letter an existing plate for free (no Gemini call):
  python coach_cover.py --plate "<...>-plate.png" --name "..." --title "..."

Tweak a plate ("less glow", "warmer light on the face"):
  python coach_cover.py --photo coach.png --plate "<...>-plate.png" --edit "less glow" \
      --name "..." --title "..."
"""

import argparse
import sys

import common as c

MOTIF_PROMPT = """Image 1 is a finished background for a thumbnail. Keep it EXACTLY as it is: same navy-black, same deep red-orange glow (same size, position, brightness and hue; do not make it bigger, brighter or more yellow), same dot texture.

Add ONE faint motif to it: {motif}.
Draw it as thin, softly glowing red-orange line-art at low opacity (it should almost disappear into the dark), sitting in the middle of the frame between x 35% and 70%, partly fading behind where the glow is. Atmosphere, not a subject. Like a faint chart or icon in the background of a premium cinematic thumbnail.

NO people, NO text, NO letters, NO numbers, NO logos. Keep the left 30% and the bottom-left corner plain."""

RELIGHT_PROMPT = """Image 1 is a real photo of the presenter. Image 2 is an empty background scene.

Place the presenter from Image 1 into the scene in Image 2 so it looks photographed there, not pasted on.

FRAMING: the presenter stands or sits in the RIGHT 42% of the frame, from about the waist or chest up, body slightly angled toward the left, filling most of the frame height. Keep the LEFT 58% of the frame clear of the person (only background there). If Image 1 shows them holding an object (an award, a microphone, a laptop), keep it.

LIGHTING: relight the presenter to match the scene. The red-orange glow in Image 2 sits behind them: it rims their hair, shoulders and the edge of the face with warm red-orange light, and the side of the face toward the left falls into soft shadow. Deep navy ambient fill everywhere else. Moody and low-key, not bright: the face stays natural skin tone, never orange or yellow. Contrast and grain match the background.

BACKGROUND: keep Image 2 exactly: same navy, same deep red-orange glow (do NOT enlarge, brighten or turn it yellow), same faint motif and dot texture.

IDENTITY: keep the presenter's exact face, hair, facial hair, skin tone, body and clothing from Image 1. Do not beautify, slim, de-age or restyle. Same expression.

Keep the background from Image 2: same palette, glow and faint motif. Add NO text, letters, numbers, logos or watermarks anywhere. No second person."""

EDIT_PROMPT = """Image 1 is a real photo of the presenter. Image 2 is the current thumbnail picture (no text).

Edit Image 2: {change}

Keep everything else the same: framing, background, palette, the presenter's exact face and identity from Image 1. Keep the left 58% clear of the person. Add NO text, letters, logos or watermarks."""


def background(motif, refresh=False):
    """Person-free background, made once per motif and cached, so every cover in a
    series (e.g. all 'Daily Content Support' calls) shares the same scene. The base
    (navy + glow + texture) is drawn in code; Gemini only adds the faint motif."""
    path = c.CACHE / "backgrounds" / f"{c.slug(motif)}.png"
    if path.exists() and not refresh:
        print(f"Background: reusing {path.name}")
        return c.open_image(path)
    print(f"Background: adding motif '{motif}' (one-off, then cached)")
    base = c.base_scene()
    for attempt in range(2):
        try:
            img = c.cover_crop(c.generate_image(MOTIF_PROMPT.format(motif=motif), [base]))
            c.save(img, path)
            return img
        except c.Blocked as e:
            print(f"  motif attempt {attempt + 1} returned nothing ({e})", file=sys.stderr)
    print("  using the plain background (no motif)", file=sys.stderr)
    c.save(base, path)
    return base


def best_of(make, photo, tries, min_score):
    """Generate up to `tries` plates, judge each against the real photo, keep the best.
    Stops early once one clears min_score."""
    best, best_j, blocked = None, None, 0
    for i in range(1, tries + 1):
        try:
            img = make()
        except c.Blocked as e:
            blocked += 1
            print(f"  try {i}: Gemini declined ({str(e)[:120]})", file=sys.stderr)
            if blocked >= 2 and best is None:
                break  # two straight refusals on the same photo won't fix themselves
            continue
        j = c.judge_likeness(img, photo)
        if j is None:
            print(f"  try {i}: generated (judge offline, keeping it)")
            return img, None
        note = f" | problem: {j['problems']}" if j["problems"] else ""
        print(f"  try {i}: likeness {j['score']:.0f}/10{note}")
        if best_j is None or j["effective"] > best_j["effective"]:
            best, best_j = img, j
        if j["score"] >= min_score and not j["problems"]:
            break
    if best is None:
        c.die(
            "Gemini refused this photo every time. Fixes, in order: "
            "(1) use a clean photo of just this person on a plain or white background "
            "(not a screenshot or a crop from a busy board), "
            "(2) crop tighter so the face and shoulders fill more of the frame, "
            "(3) try a different photo of them.",
            code=2,
        )
    return best, best_j


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True, help="Coach's name, spelled exactly as it should appear")
    ap.add_argument("--title", required=True, help="Call title, e.g. 'Daily Content Support'")
    ap.add_argument("--photo", help="Clean photo of the coach (white/plain background is best)")
    ap.add_argument("--motif", help="Faint background motif. Defaults to one based on the title.")
    ap.add_argument("--plate", help="Existing plate to re-letter (or to edit with --edit)")
    ap.add_argument("--edit", help="Change to make to --plate, e.g. 'less orange glow on the face'")
    ap.add_argument("--tries", type=int, default=4, help="Max generations to judge (default 4)")
    ap.add_argument("--min-score", type=float, default=9, help="Stop early at this likeness score (default 9)")
    ap.add_argument("--new-background", action="store_true", help="Regenerate the cached background for this motif")
    ap.add_argument("--out", help=f"Output folder (default: {c.DEFAULT_OUT})")
    a = ap.parse_args()

    out = c.out_dir(a.out)
    stem = f"{c.slug(a.name)}-{c.slug(a.title)}"
    plate_path = out / "plates" / f"{stem}-plate.png"

    if a.plate and not a.edit:
        plate = c.open_image(a.plate)
        print("Re-lettering existing plate (no Gemini call).")
    else:
        if not a.photo:
            c.die("--photo is required to make a new plate or edit one.")
        photo = c.open_image(a.photo)
        if a.edit:
            if not a.plate:
                c.die("--edit needs --plate (the plate to change).")
            current = c.open_image(a.plate)
            print(f"Editing plate: {a.edit}")
            plate, j = best_of(
                lambda: c.generate_image(EDIT_PROMPT.format(change=a.edit), [photo, current]),
                photo, min(a.tries, 3), a.min_score)
        else:
            motif = a.motif or f"a simple symbol that suggests '{a.title}'"
            bg = background(motif, a.new_background)
            print("Relighting the coach into the scene:")
            plate, j = best_of(
                lambda: c.generate_image(RELIGHT_PROMPT, [photo, bg]),
                photo, a.tries, a.min_score)
        c.save(plate, plate_path)
        if j and j["score"] < 8:
            print(f"WARNING: best likeness only {j['score']:.0f}/10 ({j['reason']}). "
                  "Look closely before using it; a different photo usually fixes this.")

    cover = c.coach_lockup(plate, a.title, a.name)
    path = c.save(cover, out / f"{stem}.png")
    if not a.plate or a.edit:
        print(f"Plate:  {plate_path}")
    print(f"COVER:  {path}")


if __name__ == "__main__":
    main()
