"""GitHub profile banner generator - animated ASCII F-15E over a terminal intro.

The jet is NOT re-rendered: every frame's dense halftone ASCII jet is kept
verbatim from banner-dense-source.gif (the original art, recovered from git
history commit 2b44f52 after a regeneration degraded it). Only the left text
block is erased and redrawn with the current copy (Tracecast LLC, no tool
names).

Erase strategy per frame:
- terminal / name / rule bands: box erase (measured - no jet pixels there)
- subtitle band: the old tool-name line interleaves with jet contrail dots in
  x, and neither color nor temporal variance separates them cleanly (measured
  7/11). So: box-erase the whole old-text extent, then patch the jet portion
  by copying the contrail texture from the band directly above - same streaky
  pattern, copied per frame so the shimmer stays live.

Run: python make_banner.py   (needs Pillow; writes banner.gif in place)
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
SRC = HERE / "banner-dense-source.gif"   # original dense art - do not lose again
OUT = HERE / "banner.gif"

BG = (8, 11, 16)
CYAN = (86, 204, 242)      # sampled from the original terminal line
WHITE = (238, 244, 250)    # sampled from the original name
GREY = (122, 132, 143)     # sampled from the original subtitle

DURATION = 70

# measured text bands in the original (see repo history for the survey)
BOX_ERASE = [
    (40, 134, 420, 162),   # terminal line + cursor (jet starts x~436 here)
    (40, 170, 425, 234),   # Alan Hayes (jet leftmost is x~434)
    (40, 235, 200, 245),   # rule
]
SUB_BAND = (40, 250, 660, 278)  # old subtitle extent: box-erased then patched
PATCH_X0 = 430                  # jet content starts here inside the band

MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def erase_old_text(im):
    d = ImageDraw.Draw(im)
    for x0, y0, x1, y1 in BOX_ERASE:
        d.rectangle([x0, y0, x1, y1], fill=BG)
    x0, y0, x1, y1 = SUB_BAND
    band_h = y1 - y0
    # patch strip: contrail texture from directly above the band (clean jet,
    # no old text lives up there - name block ends y234, x<=425)
    patch = im.crop((PATCH_X0, y0 - band_h, x1, y0))
    d.rectangle([x0, y0, x1, y1], fill=BG)
    im.paste(patch, (PATCH_X0, y0))


def draw_new_text(im, i):
    d = ImageDraw.Draw(im)
    f_mono = ImageFont.truetype(MONO_BOLD, 20)
    f_name = ImageFont.truetype(SANS_BOLD, 52)
    f_sub = ImageFont.truetype(MONO, 21)

    term_full = "alan@tracecast:~$ whoami"
    typed_start = len("alan@tracecast:~$ ")
    typed = min(len(term_full), typed_start + max(0, i - 3))
    line = term_full[:typed]
    d.text((70, 138), line, font=f_mono, fill=CYAN)
    if typed < len(term_full) or (i // 4) % 2 == 0:   # blink after typing
        cx = 70 + d.textlength(line, font=f_mono) + 6
        d.rectangle([cx, 138, cx + 12, 160], fill=CYAN)

    d.text((66, 170), "Alan Hayes", font=f_name, fill=WHITE)
    d.rectangle([70, 238, 145, 241], fill=CYAN)
    d.text((70, 254), "T r a c e c a s t   L L C", font=f_sub, fill=GREY)


def main():
    src = Image.open(SRC)
    frames = []
    for i in range(src.n_frames):
        src.seek(i)
        im = src.convert("RGB").copy()
        erase_old_text(im)
        draw_new_text(im, i)
        frames.append(im)
    frames[0].save(OUT, save_all=True, append_images=frames[1:],
                   duration=DURATION, loop=0, optimize=True)
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB, {len(frames)} frames)")


if __name__ == "__main__":
    main()
