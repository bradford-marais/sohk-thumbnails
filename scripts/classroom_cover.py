#!/usr/bin/env python3
"""Classroom / module cover (no person): a glowing orange 3D object on navy-black,
then the centered title, the '>_ TAG' pill and the crest drawn on top.

  python classroom_cover.py --title "Monetization Framework" --tag framework \
      --motif "a glowing rising line chart with currency symbols"

Re-letter an existing plate for free:
  python classroom_cover.py --plate "<...>-plate.png" --title "..." --tag "..."
"""

import argparse
import sys

import common as c

PLATE_PROMPT = """A 16:9 cover image for an online course module. NO text, NO letters, NO numbers, NO logos, NO people.

Subject, centered in the frame: {motif}. Render it as a glossy 3D object / glass-and-neon line-art glowing warm orange (#e0592f to soft peach highlights), floating in a dark scene.

Palette and mood: deep navy-black background (#08111e) with a faint dark grid texture, a warm orange glow pooling on the floor under the object, soft cinematic haze. Study Images 1-2: match their palette, glow, material and finish exactly. Copy their style, NOT their objects.

Layout: the object sits in the middle of the frame and may run behind the center, because a big title will sit across the middle (y 40-60%) on top of it. Keep the top-right corner dark and empty (a badge goes there). Keep the object's brightest parts above and below the middle band so a title stays readable.

Clean, premium, minimal. One object, not a collage."""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--title", required=True, help="Module title, e.g. 'Short-Form Blueprint'")
    ap.add_argument("--tag", required=True, help="Pill label, e.g. 'blueprint', 'replays', 'start here'")
    ap.add_argument("--motif", help="The object to show. Defaults to one based on the title.")
    ap.add_argument("--plate", help="Existing plate to re-letter (no Gemini call)")
    ap.add_argument("--variants", type=int, default=2, help="How many plates to generate to pick from (default 2)")
    ap.add_argument("--out", help=f"Output folder (default: {c.DEFAULT_OUT})")
    a = ap.parse_args()

    out = c.out_dir(a.out)
    stem = f"class-{c.slug(a.title)}"

    if a.plate:
        plates = [(c.open_image(a.plate), None)]
        print("Re-lettering existing plate (no Gemini call).")
    else:
        motif = a.motif or f"a single iconic object that represents '{a.title}'"
        style = [c.open_image(c.ASSETS / "style" / n) for n in ("07_monetization.jpg", "04_billion.jpg")]
        plates, refused = [], 0
        for i in range(1, a.variants + 1):
            try:
                img = c.generate_image(PLATE_PROMPT.format(motif=motif), style)
            except c.Blocked as e:
                refused += 1
                print(f"  variant {i}: Gemini returned nothing ({str(e)[:100]})", file=sys.stderr)
                continue
            p = c.save(img, out / "plates" / f"{stem}-plate-{i}.png")
            plates.append((img, p))
            print(f"  variant {i}: done")
        if not plates:
            c.die("No plate came back. Reword the motif to something simpler and try again.")

    for i, (img, p) in enumerate(plates, 1):
        cover = c.classroom_lockup(img, a.title, a.tag)
        name = f"{stem}.png" if len(plates) == 1 else f"{stem}-{i}.png"
        path = c.save(cover, out / name)
        if p:
            print(f"Plate:  {p}")
        print(f"COVER:  {path}")


if __name__ == "__main__":
    main()
