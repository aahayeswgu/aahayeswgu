"""Tracecast footer logo generator - animated "signal trace" card (SVG).

Replaces the old static radar PNG. The concept: raw public data comes in as
grey noise, and one thing worth acting on resolves out of it as a cyan spike.
That is the company line ("public data, turned into action") drawn literally,
and it stops the mark from being yet another OSINT radar - tracecast.app's
hero already owns the radar.

Two constraints drive the implementation:

1. Text is baked to outlines. The SVG is consumed through GitHub's image proxy
   via <img>, so it cannot load a webfont - a live <text> element would fall
   back to whatever the viewer happens to have. Every glyph here is a path, so
   the card renders identically everywhere. Brand fonts (Space Grotesk 700 for
   the wordmark, IBM Plex Mono for the labels) match tracecast.app.

2. Animation is SMIL, not CSS. SMIL is the reliable path for a standalone SVG
   rendered as an image (no transform-box quirks, no stylesheet timing). Every
   <animate> shares dur=6s / repeatCount=indefinite and places its events with
   keyTimes, so the whole card stays in lockstep off one clock.

Colors are the live site tokens (src/app/globals.css): bg #0e1116, surface
#161b22, accent #22d3ee.

Run: /home/wzrd/watchtower/.venv/bin/python make_logo.py
     (needs fontTools; fonts are fetched to FONT_DIR on first run)
     writes tracecast-logo.svg in place.
"""
import random
import urllib.request
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

HERE = Path(__file__).resolve().parent
OUT = HERE / "tracecast-logo.svg"
FONT_DIR = HERE / ".fonts"  # build-time only, not committed

FONTS = {
    "grotesk": (
        "https://github.com/google/fonts/raw/main/ofl/spacegrotesk/SpaceGrotesk%5Bwght%5D.ttf",
        "SpaceGrotesk[wght].ttf",
    ),
    "mono": (
        "https://github.com/google/fonts/raw/main/ofl/ibmplexmono/IBMPlexMono-Medium.ttf",
        "IBMPlexMono-Medium.ttf",
    ),
}

W, H = 580, 155

BG = "#0e1116"        # --color-bg
SURFACE = "#161b22"   # --color-surface
LINE = "#232936"      # card border / grid
ACCENT = "#22d3ee"    # --color-accent
FG = "#e6edf3"        # --color-fg
MUTED = "#a3acba"     # --color-muted
FAINT = "#6f7b8a"
NOISE = "#46536a"     # raw data, deliberately not accent-colored

# trace window
TX0, TX1 = 32, 250    # left/right edge
TMID = 86             # noise baseline
GRID_H = 38           # half-height of the window
PEAK_X, PEAK_Y = 186, TMID - GRID_H + 4  # apex sits just inside the top rail
DUR = "6s"


def load_fonts():
    FONT_DIR.mkdir(exist_ok=True)
    out = {}
    for key, (url, name) in FONTS.items():
        path = FONT_DIR / name
        if not path.exists():
            urllib.request.urlretrieve(url, path)
        font = TTFont(path)
        if "fvar" in font:  # Space Grotesk ships variable; pin the bold master
            font = instancer.instantiateVariableFont(font, {"wght": 700})
        out[key] = font
    return out


def text_path(font, text, size, x, y, tracking=0.0):
    """Bake `text` to a single SVG path, baseline-left at (x, y).

    Advances come from hmtx; GPOS kerning is skipped (all-caps wordmark and
    mono labels, where the pairs that matter are handled by `tracking`).
    """
    upem = font["head"].unitsPerEm
    scale = size / upem
    glyphset = font.getGlyphSet()
    cmap = font.getBestCmap()
    parts = []
    pen_x = x
    for ch in text:
        gname = cmap.get(ord(ch))
        if gname is None:
            raise KeyError(f"{ch!r} missing from font")
        glyph = glyphset[gname]
        pen = SVGPathPen(glyphset)
        glyph.draw(pen)
        d = pen.getCommands()
        if d:  # space has no outline
            parts.append(
                f'<path d="{d}" transform="translate({pen_x:.2f} {y:.2f}) '
                f'scale({scale:.5f} {-scale:.5f})"/>'
            )
        pen_x += glyph.width * scale + tracking
    return "".join(parts), pen_x - x - tracking


def noise_path():
    """Deterministic jagged baseline across the trace window."""
    rng = random.Random(7)
    pts = []
    x = TX0
    step = 4.6
    while x <= TX1:
        # amplitude eases down near the edges so the line doesn't start hot
        edge = min(x - TX0, TX1 - x) / 46.0
        amp = 8.5 * min(1.0, edge)
        # keep the peak's own column quiet so the spike reads as isolated
        if abs(x - PEAK_X) < 7:
            amp *= 0.25
        pts.append((x, TMID + rng.uniform(-amp, amp)))
        x += step
    return "M" + " L".join(f"{px:.1f} {py:.1f}" for px, py in pts)


def anim(attr, values, key_times, extra=""):
    return (
        f'<animate attributeName="{attr}" values="{values}" '
        f'keyTimes="{key_times}" dur="{DUR}" repeatCount="indefinite"{extra}/>'
    )


def build():
    fonts = load_fonts()
    grotesk, mono = fonts["grotesk"], fonts["mono"]
    o = []
    a = o.append

    a(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}" role="img" '
        f'aria-label="Tracecast LLC, custom signal engines. Public data, turned into action.">'
    )
    a("<title>Tracecast LLC - custom signal engines</title>")
    a(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
    a(
        f'<rect x="8" y="8" width="{W - 16}" height="{H - 16}" rx="16" '
        f'fill="{SURFACE}" stroke="{LINE}"/>'
    )

    # --- trace window ---------------------------------------------------
    a(f'<g stroke="{LINE}" stroke-width="1">')
    for gy in (TMID - GRID_H, TMID, TMID + GRID_H):
        a(f'<line x1="{TX0}" y1="{gy}" x2="{TX1}" y2="{gy}" opacity="0.55"/>')
    for i in range(6):
        gx = TX0 + i * (TX1 - TX0) / 5
        a(f'<line x1="{gx:.1f}" y1="{TMID - GRID_H}" x2="{gx:.1f}" y2="{TMID + GRID_H}" opacity="0.3"/>')
    a("</g>")

    # noise: draws in left-to-right, then dims once the signal resolves
    a(
        f'<path d="{noise_path()}" fill="none" stroke="{NOISE}" stroke-width="1.6" '
        f'stroke-linejoin="round" pathLength="100" stroke-dasharray="100">'
        + anim("stroke-dashoffset", "100;0;0;100", "0;0.2;0.98;1")
        + anim("opacity", "0;0.85;0.85;0.28;0.28;0", "0;0.2;0.34;0.46;0.94;1")
        + "</path>"
    )

    # spike: rises out of the noise at PEAK_X
    spike = (
        f"M{PEAK_X - 13} {TMID} L{PEAK_X - 5} {PEAK_Y + 6} "
        f"L{PEAK_X} {PEAK_Y} L{PEAK_X + 5} {PEAK_Y + 9} L{PEAK_X + 14} {TMID}"
    )
    a(
        f'<path d="{spike}" fill="none" stroke="{ACCENT}" stroke-width="2.2" '
        f'stroke-linecap="round" stroke-linejoin="round" pathLength="100" '
        f'stroke-dasharray="100">'
        + anim("stroke-dashoffset", "100;100;0;0;100", "0;0.34;0.46;0.98;1")
        + anim("opacity", "0;0;1;1;0", "0;0.34;0.46;0.9;1")
        + "</path>"
    )

    # apex dot + two ping rings
    a(
        f'<circle cx="{PEAK_X}" cy="{PEAK_Y}" r="3" fill="{ACCENT}">'
        + anim("opacity", "0;0;1;1;0", "0;0.44;0.5;0.9;1")
        + "</circle>"
    )
    for start in (0.5, 0.64):
        end = start + 0.16
        # hold r and opacity flat at their start values until `start`, so SMIL
        # cannot interpolate a faint ring in from frame zero.
        a(
            f'<circle cx="{PEAK_X}" cy="{PEAK_Y}" fill="none" stroke="{ACCENT}" '
            f'stroke-width="1.4" opacity="0">'
            + anim("r", "3;3;13;13", f"0;{start};{end:.2f};1")
            + anim("opacity", "0;0;0.7;0;0", f"0;{start - 0.01:.2f};{start};{end:.2f};1")
            + "</circle>"
        )

    # label beside the apex
    label, _ = text_path(mono, "SIGNAL", 9, PEAK_X + 16, PEAK_Y + 3.5, tracking=0.9)
    a(
        f'<g fill="{ACCENT}">'
        + label
        + anim("opacity", "0;0;1;1;0", "0;0.46;0.56;0.9;1")
        + "</g>"
    )
    # standing caption under the window
    caption, _ = text_path(mono, "RAW PUBLIC DATA", 8, TX0, TMID + 48, tracking=0.8)
    a(f'<g fill="{FAINT}" opacity="0.75">{caption}</g>')

    # --- wordmark -------------------------------------------------------
    x = 274
    mark, _ = text_path(grotesk, "TRACECAST", 44, x, 78, tracking=0.6)
    a(f'<g fill="{FG}">{mark}</g>')

    llc, llc_w = text_path(grotesk, "LLC", 15, x + 2, 102, tracking=0.8)
    a(f'<g fill="{ACCENT}">{llc}</g>')
    tag, _ = text_path(grotesk, "·  custom signal engines", 15, x + 2 + llc_w + 9, 102)
    a(f'<g fill="{MUTED}">{tag}</g>')

    sub, _ = text_path(grotesk, "public data, turned into action", 12.5, x + 2, 126)
    a(f'<g fill="{FAINT}">{sub}</g>')

    a("</svg>")
    svg = "".join(o)
    OUT.write_text(svg)
    print(f"wrote {OUT} ({len(svg) // 1024} KB)")


if __name__ == "__main__":
    build()
