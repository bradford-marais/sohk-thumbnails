"""Shared helpers: config, Gemini calls, the likeness judge, and the text lockups.

Every cover is a "plate" (the picture, no words) plus a fixed text lockup drawn
in code. The model never draws the title or the name, so spelling is always
right and every cover in the set lines up the same way.
"""

import json
import os
import re
import sys
import time
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SKILL_DIR = Path(__file__).resolve().parent.parent
ASSETS = SKILL_DIR / "assets"
CACHE = SKILL_DIR / "cache"
DEFAULT_OUT = Path.home() / "Desktop" / "SoHK Thumbnails"

IMAGE_MODEL = "gemini-3-pro-image-preview"
JUDGE_MODEL = "gemini-2.5-flash"

W, H = 1280, 720
NAVY = (8, 17, 30)          # #08111e, the board background
CREAM = (243, 237, 224)     # coach titles
COOL_WHITE = (234, 239, 244)  # classroom titles
ORANGE = (211, 69, 37)      # coach name pill
ORANGE_BRIGHT = (224, 89, 47)  # classroom tag pill + underline
INK = (16, 16, 18)


# ---------- config ----------------------------------------------------------

def load_env():
    """Read GEMINI_API_KEY from the skill's .env (falls back to the shell env)."""
    env = SKILL_DIR / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        die("No Gemini API key. Add GEMINI_API_KEY=... to "
            f"{SKILL_DIR / '.env'} (see INSTALL.md, step 3).")
    return key


def die(msg, code=1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "cover"


def out_dir(path=None):
    d = Path(path).expanduser() if path else DEFAULT_OUT
    d.mkdir(parents=True, exist_ok=True)
    return d


_CLIENT = None


def client():
    # One shared client: a throwaway Client gets garbage-collected mid-request
    # and the SDK then fails with "client has been closed".
    global _CLIENT
    if _CLIENT is None:
        from google import genai
        _CLIENT = genai.Client(api_key=load_env())
    return _CLIENT


# ---------- images -----------------------------------------------------------

def open_image(path, max_edge=2048):
    p = Path(path).expanduser()
    if not p.exists():
        die(f"File not found: {p}")
    head = p.read_bytes()[:256]
    if b"<html" in head.lower() or b"<!doctype" in head.lower():
        die(f"{p.name} is a web page, not an image. Save the actual image file.")
    img = Image.open(p)
    img.load()
    if img.mode in ("RGBA", "LA", "P"):
        # Flatten transparent stickers onto white: Gemini handles a clean
        # white-background cutout far better than an alpha channel.
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    img = img.convert("RGB")
    if max(img.size) > max_edge:
        img.thumbnail((max_edge, max_edge), Image.LANCZOS)
    return img


def cover_crop(img, size=(W, H)):
    """Scale to fill size, center-crop the overflow."""
    tw, th = size
    s = max(tw / img.width, th / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    x = (img.width - tw) // 2
    y = (img.height - th) // 2
    return img.crop((x, y, x + tw, y + th))


class Blocked(Exception):
    """Gemini refused or returned no image."""


class Busy(Exception):
    """Quota, rate limit or overload: waiting helps, rewording doesn't."""


def generate_image(prompt, images=(), retries_on_busy=2):
    """One Gemini image call. Returns a PIL image or raises Blocked / Busy."""
    from google.genai import types

    ai = client()
    for attempt in range(retries_on_busy + 1):
        try:
            resp = ai.models.generate_content(
                model=IMAGE_MODEL,
                contents=[prompt, *images],
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio="16:9"),
                ),
            )
        except Exception as e:  # SDK raises its own error types; classify by text
            low = str(e).lower()
            if any(s in low for s in ("429", "quota", "resource_exhausted", "rate", "overloaded", "503", "unavailable")):
                if "spend" in low or "billing" in low:
                    raise Busy("Gemini spend cap reached. Raise it at https://aistudio.google.com/spend") from e
                if attempt < retries_on_busy:
                    time.sleep(20 * (attempt + 1))
                    continue
                raise Busy("Gemini is over capacity right now. Try again in a few minutes.") from e
            if any(s in low for s in ("safety", "blocked", "prohibited", "person")):
                raise Blocked(str(e)) from e
            raise
        cand = (resp.candidates or [None])[0]
        parts = getattr(getattr(cand, "content", None), "parts", None) or []
        for part in parts:
            if getattr(part, "inline_data", None) is not None:
                return Image.open(BytesIO(part.inline_data.data)).convert("RGB")
        reason = getattr(cand, "finish_reason", None) if cand else getattr(resp, "prompt_feedback", None)
        raise Blocked(f"no image returned ({reason})")
    raise Busy("Gemini is over capacity right now.")


JUDGE_PROMPT = (
    "Image 1 is an AI-edited picture. Image 2 is a real photo of one person. "
    "Judge ONLY whether the main person in Image 1 is immediately recognizable as the person in "
    "Image 2: face shape, eyes, nose, mouth, skin tone, hair, facial hair, distinguishing features. "
    "Ignore lighting, background, crop and image quality. Also check Image 1 for problems: any "
    "visible text or letters, a second person, extra or broken hands/fingers, or the person "
    "looking pasted on. Return ONLY JSON: "
    '{"score": <0-10, 10 = unmistakably the same person, 7 = clearly them with minor drift, '
    '4 = resembles them but noticeably off, 0 = different person>, '
    '"problems": "<empty string, or the worst visible problem in a few words>", '
    '"reason": "<one sentence on the biggest match or mismatch>"}'
)


def judge_likeness(candidate, real):
    """Score 0-10 for 'is this still them?'. Returns dict or None on judge outage."""
    try:
        resp = client().models.generate_content(
            model=JUDGE_MODEL,
            contents=[_small(candidate), _small(real), JUDGE_PROMPT],
            config={"response_mime_type": "application/json"},
        )
        raw = "".join(p.text or "" for p in resp.candidates[0].content.parts)
        data = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
        score = max(0.0, min(10.0, float(data.get("score", 0))))
        problems = str(data.get("problems") or "").strip()
        # A visible defect costs points so a clean, slightly-less-perfect face wins.
        effective = score - (2 if problems else 0)
        return {"score": score, "effective": effective, "problems": problems,
                "reason": str(data.get("reason", ""))}
    except Exception as e:
        print(f"  (judge unavailable: {e})", file=sys.stderr)
        return None


def _small(img, edge=1024):
    img = img.copy()
    img.thumbnail((edge, edge))
    return img


# ---------- text lockups -----------------------------------------------------

def font(name, size):
    return ImageFont.truetype(str(ASSETS / "fonts" / name), size)


def _text_w(draw, text, f, tracking=0):
    if not text:
        return 0
    w = draw.textlength(text, font=f)
    return w + tracking * (len(text) - 1)


def _draw_tracked(draw, xy, text, f, fill, tracking=0):
    x, y = xy
    if not tracking:
        draw.text((x, y), text, font=f, fill=fill)
        return
    for ch in text:
        draw.text((x, y), ch, font=f, fill=fill)
        x += draw.textlength(ch, font=f) + tracking


def _cap_box(f):
    """Top offset and height of capital letters for a font (for exact placement)."""
    l, t, r, b = f.getbbox("H")
    return t, b - t


def _wrap(draw, words, f, max_w, max_lines):
    """Greedy wrap into at most max_lines; returns lines or None if it can't fit."""
    lines, cur = [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if _text_w(draw, trial, f) <= max_w:
            cur = trial
        else:
            if not cur:
                return None
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines if len(lines) <= max_lines else None


def _balanced(draw, title, f, max_w, max_lines):
    """Prefer two even lines over one long line + one orphan word."""
    words = title.split()
    lines = _wrap(draw, words, f, max_w, max_lines)
    if lines and len(lines) == 2 and len(words) >= 3:
        best = lines
        best_diff = abs(_text_w(draw, lines[0], f) - _text_w(draw, lines[1], f))
        for i in range(1, len(words)):
            a, b = " ".join(words[:i]), " ".join(words[i:])
            if _text_w(draw, a, f) <= max_w and _text_w(draw, b, f) <= max_w:
                d = abs(_text_w(draw, a, f) - _text_w(draw, b, f))
                if d < best_diff:
                    best, best_diff = [a, b], d
        lines = best
    return lines


def _shadow_layer(size, draw_fn, blur=14, opacity=150):
    layer = Image.new("L", size, 0)
    draw_fn(ImageDraw.Draw(layer))
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    return layer.point(lambda v: v * opacity // 255)


def paste_crest(img, x, y, d):
    crest = Image.open(ASSETS / "crest.png").convert("RGBA").resize((d, d), Image.LANCZOS)
    img.paste(crest, (x, y), crest)


def coach_lockup(plate, title, name):
    """Coach-call board layout, measured off the shipped covers (1280x720):
    Anton cream title top-left (cap height ~110px, 130px line pitch, x=63),
    orange name pill 33px under it (65px tall, tracked caps), crest bottom-left."""
    img = cover_crop(plate).convert("RGB")
    draw = ImageDraw.Draw(img)
    title = " ".join(title.upper().split())
    name = " ".join(name.upper().split())

    max_w = 660
    size, lines = 150, None
    while size >= 70:
        f = font("Anton-Regular.ttf", size)
        lines = _balanced(draw, title, f, max_w, 2 if size > 100 else 3)
        if lines:
            break
        size -= 4
    if not lines:
        die("Title is too long for a cover. Keep it to about 2-4 words.")
    cap_top, cap_h = _cap_box(f)
    pitch = round(cap_h * 1.18)

    nf = font("Montserrat-Black.ttf", 38)
    tracking = 3.5
    n_top, n_h = _cap_box(nf)
    pill_h, pad_x = 65, 24
    pill_w = round(_text_w(draw, name, nf, tracking) + pad_x * 2)

    block_h = cap_h + pitch * (len(lines) - 1) + 33 + pill_h
    y0 = round(305 - block_h / 2)   # the shipped board centers the block on y~305
    x0 = 63

    def draw_title(d, fill):
        for i, line in enumerate(lines):
            d.text((x0, y0 + i * pitch - cap_top), line, font=f, fill=fill)

    shadow = _shadow_layer(img.size, lambda d: draw_title(d, 255))
    img.paste((0, 0, 0), (0, 0, W, H), shadow)
    draw = ImageDraw.Draw(img)
    draw_title(draw, CREAM)

    py = y0 + cap_h + pitch * (len(lines) - 1) + 33
    px = 69
    draw.rounded_rectangle((px, py, px + pill_w, py + pill_h), radius=6, fill=ORANGE)
    _draw_tracked(draw, (px + pad_x, py + (pill_h - n_h) / 2 - n_top), name, nf, CREAM, tracking)

    paste_crest(img, 50, 568, 113)
    return img


def classroom_lockup(plate, title, tag):
    """Classroom / module layout (faceless board): centered cool-white Anton title,
    rounded orange '>_ TAG' pill above it, short orange rule below, crest top-right."""
    img = cover_crop(plate).convert("RGB")
    draw = ImageDraw.Draw(img)
    title = " ".join(title.upper().split())
    tag = " ".join(tag.upper().split())

    # The shipped board's title face is Anton squeezed to ~78% width (cap height
    # ~106px). Lay it out at full width, then compress the rendered mask.
    squeeze = 0.82
    size, lines = 126, None
    while size >= 64:
        f = font("Anton-Regular.ttf", size)
        lines = _wrap(draw, title.split(), f, 1040 / squeeze, 1 if size > 96 else 2)
        if lines:
            break
        size -= 4
    if not lines:
        die("Title is too long for a cover. Keep it to about 2-5 words.")
    cap_top, cap_h = _cap_box(f)
    pitch = round(cap_h * 1.18)
    text_h = cap_h + pitch * (len(lines) - 1)
    y_title = round(364 - text_h / 2)  # shipped covers: caps span y 311-417

    wide = round(W / squeeze)
    mask = Image.new("L", (wide, H), 0)
    md = ImageDraw.Draw(mask)
    for i, line in enumerate(lines):
        lw = _text_w(md, line, f)
        md.text(((wide - lw) / 2, y_title + i * pitch - cap_top), line, font=f, fill=255)
    mask = mask.resize((W, H), Image.LANCZOS)
    shadow = mask.filter(ImageFilter.GaussianBlur(16)).point(lambda v: v * 170 // 255)
    img.paste((0, 0, 0), (0, 0, W, H), shadow)
    img.paste(COOL_WHITE, (0, 0, W, H), mask)
    draw = ImageDraw.Draw(img)

    # pill: 37px tall, fully rounded, dark ink text, sits 32px above the caps
    tf = font("Montserrat-ExtraBold.ttf", 20)
    label = f">_  {tag}"
    t_top, t_h = _cap_box(tf)
    pill_h = 37
    pill_w = round(_text_w(draw, label, tf, 1.2) + 44)
    px = round((W - pill_w) / 2)
    py = y_title - 32 - pill_h
    draw.rounded_rectangle((px, py, px + pill_w, py + pill_h), radius=pill_h // 2, fill=ORANGE_BRIGHT)
    _draw_tracked(draw, (px + 22, py + (pill_h - t_h) / 2 - t_top), label, tf, INK, 1.2)

    ry = y_title + text_h + 37
    draw.rectangle((W // 2 - 94, ry, W // 2 + 94, ry + 3), fill=ORANGE_BRIGHT)

    paste_crest(img, 1147, 27, 106)
    return img


def base_scene(glow_center=(820, 320), glow_radius=560, seed=7):
    """The coach board's empty scene, drawn in code so the palette never drifts:
    navy #08111e, a deep red-orange glow behind where the coach stands, a faint
    dot grid that shows mostly inside the glow, and light film grain."""
    import random

    gx, gy = glow_center
    # glow: radial falloff into a single-channel mask, then tinted
    small = Image.new("L", (W // 4, H // 4), 0)
    px = small.load()
    for y in range(small.height):
        for x in range(small.width):
            d = (((x * 4 - gx) / glow_radius) ** 2 + ((y * 4 - gy) / (glow_radius * 0.95)) ** 2) ** 0.5
            px[x, y] = int(255 * max(0.0, 1 - d) ** 1.25)
    glow = small.resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(6))

    img = Image.new("RGB", (W, H), (4, 13, 23))
    img.paste((178, 64, 26), (0, 0, W, H), glow)

    # dot grid, strongest inside the glow
    dots = Image.new("L", (W, H), 0)
    dd = ImageDraw.Draw(dots)
    for y in range(4, H, 9):
        for x in range(4, W, 9):
            dd.point((x, y), fill=255)
    dots = Image.composite(dots, Image.new("L", (W, H), 0), glow.point(lambda v: min(255, 40 + v)))
    img.paste((40, 30, 34), (0, 0, W, H), dots.point(lambda v: v * 70 // 255))

    # grain
    rnd = random.Random(seed)
    noise = Image.new("L", (W // 2, H // 2))
    noise.putdata([rnd.randint(0, 255) for _ in range(noise.width * noise.height)])
    noise = noise.resize((W, H))
    img = Image.blend(img, Image.merge("RGB", (noise, noise, noise)), 0.025)
    return img


def save(img, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path
