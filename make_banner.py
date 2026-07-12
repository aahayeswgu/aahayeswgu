"""GitHub profile banner generator - animated ASCII F-15E over a terminal intro.

Regenerates banner.gif so the ASCII art stays dense and the look stays
reproducible (the original generator was lost; this one is committed).

The jet silhouette is sampled from the previous banner.gif (last frame, right
region) as a brightness stencil, gap-filled with a 3x3 max filter, and
re-rendered with characters drawn from the TRACECAST stream. Left block:
typed 'whoami' terminal line, name, rule, company.

Run: python make_banner.py   (needs Pillow; writes banner.gif in place)
"""
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
SRC = HERE / "banner.gif"        # previous banner = shape stencil (first run only)
STENCIL = HERE / "jet-stencil.png"  # persisted stencil - survives banner overwrites
OUT = HERE / "banner.gif"

W, H = 1280, 380
BG = (7, 11, 16)
CYAN = (61, 214, 245)
WHITE = (238, 242, 246)
GREY = (154, 165, 177)

FRAMES = 29
DURATION = 70

CELL_W, CELL_H = 10, 13          # ASCII grid cell (px)
JET_X0 = 430                     # left edge of the jet region (old text block ends ~x400)
STREAM = "TRACECAST"             # fill characters - the easter egg
BG_LEVEL = 11 / 255              # the navy background's own luminance - subtract it
NOISE_FLOOR = 0.008              # post-subtract floor: true background, killed
FILL_THRESHOLD = 0.03            # min boosted brightness that gets a char
GAMMA = 0.55                     # <1 boosts faint surviving cells: the "refill" knob
SHIMMER = 0.18                   # per-frame brightness jitter amplitude

MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def stencil_from_previous():
    """Brightness grid for the jet. Prefers the persisted jet-stencil.png;
    falls back to sampling the previous banner.gif and persists the result
    (banner.gif gets overwritten by this script, the stencil must not)."""
    cols = (W - JET_X0) // CELL_W
    rows = H // CELL_H
    if STENCIL.exists():
        cell = Image.open(STENCIL).convert("L")
        if cell.size != (cols, rows):
            cell = cell.resize((cols, rows), Image.BOX)
    else:
        g = Image.open(SRC)
        g.seek(g.n_frames - 1)
        jet = g.convert("L").crop((JET_X0, 0, W, H))    # jet region only, no text block
        cell = jet.resize((cols, rows), Image.BOX)      # mean brightness per cell
        cell.save(STENCIL)
    px = cell.load()
    # subtract the background's own luminance, floor the residual noise, boost the rest
    def _b(v):
        raw = max(0.0, v / 255.0 - BG_LEVEL) / (1.0 - BG_LEVEL)
        return raw ** GAMMA if raw >= NOISE_FLOOR else 0.0
    grid = [[_b(px[c, r]) for c in range(cols)] for r in range(rows)]
    # radius-2 max filter with decay: refill the holes the old sparse render
    # left in the body (2-cell gaps close; the outer edge only gains a dim halo)
    out = [[0.0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            m1 = m2 = 0.0
            for dr in (-2, -1, 0, 1, 2):
                for dc in (-2, -1, 0, 1, 2):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < rows and 0 <= cc < cols:
                        ring = max(abs(dr), abs(dc))
                        if ring <= 1:
                            m1 = max(m1, grid[rr][cc])
                        else:
                            m2 = max(m2, grid[rr][cc])
            # keep the original where strong, borrow neighbors where weak
            out[r][c] = max(grid[r][c], 0.85 * m1, 0.6 * m2)
    return out


def shade(b):
    """brightness 0..1 -> dim navy to bright cyan-white."""
    b = max(0.0, min(1.0, b))
    lo, hi = (24, 52, 82), (168, 228, 250)
    return tuple(int(l + (h - l) * b) for l, h in zip(lo, hi))


def render_frames():
    grid = stencil_from_previous()
    rows, cols = len(grid), len(grid[0])
    rng = random.Random(15)  # E-model tail number, and deterministic output

    # pre-pick a character per cell so letters do not crawl between frames
    chars = [[STREAM[rng.randrange(len(STREAM))] for _ in range(cols)] for _ in range(rows)]
    jitter_seed = [[rng.random() for _ in range(cols)] for _ in range(rows)]

    f_mono = ImageFont.truetype(MONO_BOLD, 20)
    f_cell = ImageFont.truetype(MONO, 13)
    f_name = ImageFont.truetype(SANS_BOLD, 52)
    f_sub = ImageFont.truetype(MONO, 22)

    term_full = "alan@tracecast:~$ whoami"
    typed_start = len("alan@tracecast:~$ ")

    frames = []
    for i in range(FRAMES):
        im = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(im)

        # ASCII jet: stable chars, shimmering brightness
        t = i / FRAMES
        for r in range(rows):
            for c in range(cols):
                b = grid[r][c]
                if b < FILL_THRESHOLD:
                    continue
                phase = jitter_seed[r][c]
                wobble = SHIMMER * (0.5 - abs(((phase + t) % 1.0) - 0.5)) * 2
                d.text((JET_X0 + c * CELL_W, r * CELL_H), chars[r][c],
                       font=f_cell, fill=shade(b + wobble - SHIMMER / 2))

        # terminal line types 'whoami', then the cursor blinks
        typed = min(len(term_full), typed_start + max(0, i - 3))
        line = term_full[:typed]
        d.text((70, 128), line, font=f_mono, fill=CYAN)
        if typed < len(term_full) or (i // 4) % 2 == 0:
            cx = 70 + d.textlength(line, font=f_mono) + 6
            d.rectangle([cx, 128, cx + 12, 150], fill=CYAN)

        d.text((66, 162), "Alan Hayes", font=f_name, fill=WHITE)
        d.rectangle([70, 244, 130, 247], fill=CYAN)
        d.text((70, 258), "T r a c e c a s t   L L C", font=f_sub, fill=GREY)

        frames.append(im)
    return frames


def main():
    frames = render_frames()
    frames[0].save(OUT, save_all=True, append_images=frames[1:],
                   duration=DURATION, loop=0, optimize=True)
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB, {len(frames)} frames)")


if __name__ == "__main__":
    main()
