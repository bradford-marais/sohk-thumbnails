#!/usr/bin/env python3
"""Setup check: run after install, or whenever something breaks.

Checks the Python packages, the bundled fonts and crest, the Gemini key (one tiny
text call, a fraction of a cent), then renders a sample cover with no image
generation so you can see the text layout works.
"""

import sys

import common as c


def main():
    ok = True
    try:
        import google.genai  # noqa: F401
        import PIL  # noqa: F401
        print("OK   Python packages")
    except ImportError as e:
        print(f"FAIL Python packages missing ({e}). Run the install step again.")
        return 1

    for f in ("crest.png", "fonts/Anton-Regular.ttf", "fonts/Montserrat-Black.ttf",
              "fonts/Montserrat-ExtraBold.ttf", "style/07_monetization.jpg"):
        if not (c.ASSETS / f).exists():
            print(f"FAIL missing asset: assets/{f}")
            ok = False
    if ok:
        print("OK   Brand assets (crest, fonts, style references)")

    c.load_env()
    try:
        resp = c.client().models.generate_content(model=c.JUDGE_MODEL, contents="Reply with the word ready.")
        print(f"OK   Gemini key works ({(resp.text or '').strip()[:20]})")
    except Exception as e:
        msg = str(e)
        if "API_KEY_INVALID" in msg or "API key not valid" in msg:
            print("FAIL Gemini key is wrong. Copy it again from https://aistudio.google.com/apikey")
        elif "billing" in msg.lower() or "FAILED_PRECONDITION" in msg:
            print("FAIL Gemini key works but billing isn't on. Image generation needs a paid key: "
                  "https://aistudio.google.com/apikey -> Set up billing")
        else:
            print(f"FAIL Gemini call failed: {msg[:300]}")
        ok = False

    sample = c.coach_lockup(c.base_scene(), "Daily Content Support", "Sample Coach")
    path = c.save(sample, c.out_dir() / "_setup-check-sample.png")
    print(f"OK   Sample layout rendered: {path}")

    print("\nAll good. Ready to make covers." if ok else "\nFix the FAIL lines above, then run this again.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
