"""Procedural 15s motion-design showreel. Pure pycairo + PangoCairo, 1080p60."""
import math
import cairo
import gi

gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Pango, PangoCairo  # noqa: E402

W, H, FPS, DUR = 1920, 1080, 60, 15.0
CX, CY = W / 2, H / 2
BPM = 120
BEAT = 60 / BPM
TAU = math.tau


def hexc(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


BG = hexc("0B0B0C")
BG2 = hexc("1A1A1D")
INK = hexc("F3EFE6")
ORG = hexc("FF4B1F")
COB = hexc("2F4BFF")
RED = (1.0, 0.1, 0.35)
CYAN = (0.1, 0.9, 1.0)

SANS, SERIF, MONO = "Adwaita Sans", "Noto Serif", "JetBrains Mono"

# ---------------------------------------------------------------- math / easing


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def mixc(c1, c2, t):
    return tuple(lerp(a, b, t) for a, b in zip(c1, c2))


def prog(t, a, b):
    return clamp((t - a) / (b - a))


def frac(x):
    return x - math.floor(x)


class Bezier:
    """CSS-style cubic-bezier easing."""

    def __init__(self, x1, y1, x2, y2):
        self.p = (x1, y1, x2, y2)

    @staticmethod
    def _b(t, a, b):
        return 3 * (1 - t) ** 2 * t * a + 3 * (1 - t) * t * t * b + t ** 3

    def __call__(self, x):
        x = clamp(x)
        x1, y1, x2, y2 = self.p
        lo, hi = 0.0, 1.0
        for _ in range(28):
            m = (lo + hi) / 2
            if self._b(m, x1, x2) < x:
                lo = m
            else:
                hi = m
        return self._b((lo + hi) / 2, y1, y2)


HOUSE = Bezier(0.7, 0, 0.2, 1)
SNAP = Bezier(0.16, 1, 0.3, 1)


def out_expo(x):
    x = clamp(x)
    return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)


def in_expo(x):
    x = clamp(x)
    return 0.0 if x <= 0 else 2 ** (10 * x - 10)


def out_cubic(x):
    return 1 - (1 - clamp(x)) ** 3


def in_cubic(x):
    return clamp(x) ** 3


def inout_cubic(x):
    x = clamp(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def out_back(x, s=1.9):
    x = clamp(x) - 1
    return 1 + x * x * ((s + 1) * x + s)


def spring(x, f=2.6, d=6.5):
    x = clamp(x)
    return 1.0 if x >= 1 else 1 - math.exp(-d * x) * math.cos(TAU * f * x)


def hsh(*args):
    x = 0x345678
    for a in args:
        x = ((x ^ (int(a) * 0x9E3779B1)) * 0x85EBCA6B) & 0xFFFFFFFF
        x ^= x >> 13
    x = (x * 0xC2B2AE35) & 0xFFFFFFFF
    x ^= x >> 16
    return x / 4294967296


# ---------------------------------------------------------------- drawing helpers

_WEIGHTS = {100: Pango.Weight.THIN, 200: Pango.Weight.ULTRALIGHT, 300: Pango.Weight.LIGHT,
            400: Pango.Weight.NORMAL, 500: Pango.Weight.MEDIUM, 600: Pango.Weight.SEMIBOLD,
            700: Pango.Weight.BOLD, 800: Pango.Weight.ULTRABOLD, 900: Pango.Weight.HEAVY}
_FONTOPTS = cairo.FontOptions()
_FONTOPTS.set_hint_style(cairo.HINT_STYLE_NONE)
_FONTOPTS.set_hint_metrics(cairo.HINT_METRICS_OFF)
_FONTOPTS.set_antialias(cairo.ANTIALIAS_GRAY)


def layout(ctx, s, px, font=SANS, weight=400, italic=False, track=0.0):
    L = PangoCairo.create_layout(ctx)
    PangoCairo.context_set_font_options(L.get_context(), _FONTOPTS)
    L.context_changed()
    d = Pango.FontDescription()
    d.set_family(font)
    d.set_weight(_WEIGHTS[weight])
    if italic:
        d.set_style(Pango.Style.ITALIC)
    d.set_absolute_size(px * Pango.SCALE)
    L.set_font_description(d)
    if track:
        a = Pango.AttrList()
        a.insert(Pango.attr_letter_spacing_new(int(track * Pango.SCALE)))
        L.set_attributes(a)
    L.set_text(s, -1)
    return L


def lmetrics(L):
    log = L.get_extents()[1]
    return log.width / Pango.SCALE, log.height / Pango.SCALE, L.get_baseline() / Pango.SCALE


def rgb(ctx, c, a=1.0):
    ctx.set_source_rgba(c[0], c[1], c[2], a)


def text(ctx, s, x, y, px, col, font=SANS, weight=400, italic=False, track=0.0, ax=0.5, alpha=1.0):
    """Draw text with baseline at y; ax = horizontal anchor (0 left, .5 centre, 1 right). Returns width."""
    L = layout(ctx, s, px, font, weight, italic, track)
    w, h, bl = lmetrics(L)
    ctx.move_to(x - w * ax, y - bl)
    rgb(ctx, col, alpha)
    PangoCairo.show_layout(ctx, L)
    return w


def glyphs(ctx, s, px, font=SANS, weight=400, italic=False, track=0.0):
    """Per-character (char, x offset, advance) using full-word layout for kerning; plus total width."""
    L = layout(ctx, s, px, font, weight, italic, track)
    w, _, bl = lmetrics(L)
    xs = [L.index_to_pos(i).x / Pango.SCALE for i in range(len(s))] + [w]
    return [(s[i], xs[i], xs[i + 1] - xs[i]) for i in range(len(s))], w, bl


def split_text(ctx, s, x, y, px, col, amt, **kw):
    """Chromatic-split text: red/cyan ghost copies offset by amt."""
    if amt > 0.4:
        text(ctx, s, x + amt, y, px, RED, alpha=0.85, **kw)
        text(ctx, s, x - amt, y + amt * 0.25, px, CYAN, alpha=0.85, **kw)
    return text(ctx, s, x, y, px, col, **kw)


def fill_bg(ctx, c):
    rgb(ctx, c)
    ctx.paint()


def circle(ctx, x, y, r, c, a=1.0):
    if r <= 0:
        return
    ctx.arc(x, y, r, 0, TAU)
    rgb(ctx, c, a)
    ctx.fill()


def capsule(ctx, x, y, hw, hh, c):
    r = min(hw, hh)
    ctx.new_sub_path()
    ctx.arc(x + hw - r, y, r, -TAU / 4, TAU / 4)
    ctx.arc(x - hw + r, y, r, TAU / 4, 3 * TAU / 4)
    ctx.close_path()
    rgb(ctx, c)
    ctx.fill()


def corner_shape(ctx, s, radii):
    """Square of side s centred at origin with independent corner radii (fractions of s). TL,TR,BR,BL."""
    h = s / 2
    r0, r1, r2, r3 = (clamp(r) * s for r in radii)
    ctx.new_sub_path()
    ctx.move_to(-h + r0, -h)
    ctx.line_to(h - r1, -h)
    if r1:
        ctx.arc(h - r1, -h + r1, r1, -TAU / 4, 0)
    ctx.line_to(h, h - r2)
    if r2:
        ctx.arc(h - r2, h - r2, r2, 0, TAU / 4)
    ctx.line_to(-h + r3, h)
    if r3:
        ctx.arc(-h + r3, h - r3, r3, TAU / 4, TAU / 2)
    ctx.line_to(-h, -h + r0)
    if r0:
        ctx.arc(-h + r0, -h + r0, r0, TAU / 2, 3 * TAU / 4)
    ctx.close_path()


def scaled(ctx, s, cx=CX, cy=CY):
    ctx.translate(cx, cy)
    ctx.scale(s, s)
    ctx.translate(-cx, -cy)


def rise_word(ctx, s, x, baseline, px, col, t0, t, stagger=0.04, dur=0.55, dist=None, font=SANS,
              weight=900, italic=False, track=0.0, ax=0.5, rot=8.0, clip_pad=None):
    """Classic masked per-letter rise from baseline. Returns total width."""
    gl, w, bl = glyphs(ctx, s, px, font, weight, italic, track)
    dist = dist if dist is not None else px * 1.05
    x0 = x - w * ax
    ctx.save()
    pad = clip_pad if clip_pad is not None else px * 0.32
    ctx.rectangle(-W, baseline - px * 1.2, 3 * W, px * 1.2 + pad)
    ctx.clip()
    for i, (ch, gx, adv) in enumerate(gl):
        p = out_expo(prog(t, t0 + i * stagger, t0 + i * stagger + dur))
        if p <= 0:
            continue
        ctx.save()
        ctx.translate(x0 + gx, baseline + (1 - p) * dist)
        ctx.rotate(math.radians((1 - p) * rot))
        text(ctx, ch, 0, 0, px, col, font, weight, italic, ax=0)
        ctx.restore()
    ctx.restore()
    return w


def type_on(ctx, s, x, y, px, col, t0, t, cps=38, ax=0.0, alpha=1.0, cursor=True, track=2.0):
    n = int(clamp((t - t0) * cps, 0, len(s)))
    if t < t0:
        return
    full_w = lmetrics(layout(ctx, s, px, MONO, 500, track=track))[0]
    x0 = x - full_w * ax
    w = text(ctx, s[:n], x0, y, px, col, MONO, 500, track=track, ax=0, alpha=alpha) if n else 0
    if cursor and (n < len(s) or frac(t * 3) < 0.5) and t < t0 + len(s) / cps + 0.6:
        ctx.rectangle(x0 + w + 3, y - px * 0.8, px * 0.55, px * 0.95)
        rgb(ctx, ORG if n < len(s) else col, alpha)
        ctx.fill()


# ---------------------------------------------------------------- HUD chrome

SCENES = [(0.0, "00", "INTRO"), (2.0, "01", "KINETIC TYPE"), (4.5, "02", "SHAPE SYSTEMS"),
          (7.0, "03", "PROCEDURAL 3D"), (9.5, "04", "MONTAGE"), (11.5, "05", "SIGNATURE")]
HUD_COLS = [(0.0, INK), (2.0, BG), (3.3, INK), (3.5, BG), (3.75, INK), (4.0, BG), (4.25, INK),
            (4.5, BG), (7.0, INK), (10.5, BG), (11.0, INK)]


def hud_color(t):
    c = INK
    for ts, col in HUD_COLS:
        if t >= ts:
            c = col
    return c


def timecode(t):
    f = int(t * FPS)
    return f"{f // (FPS * 60):02d}:{(f // FPS) % 60:02d}:{f % FPS:02d}"


def hud(ctx, t):
    c = hud_color(t)
    a = out_cubic(prog(t, 0.05, 0.5)) * (1 - prog(t, 14.45, 14.8))
    if a <= 0:
        return
    ctx.save()
    if 4.5 <= t < 7.0:
        c = INK
        ctx.set_operator(cairo.OPERATOR_DIFFERENCE)
    m, arm = 44, 26
    ctx.set_line_width(2)
    rgb(ctx, c, a)
    k = out_expo(prog(t, 0.05, 0.6))
    for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        x = m if sx > 0 else W - m
        y = m if sy > 0 else H - m
        ctx.move_to(x, y + sy * arm * k)
        ctx.line_to(x, y)
        ctx.line_to(x + sx * arm * k, y)
    ctx.stroke()

    fs, ty, by = 15, 86, H - 72
    text(ctx, "CLAUDE", 84, ty, fs, c, MONO, 800, track=3, ax=0, alpha=a)
    text(ctx, "MOTION REEL '26", 162, ty, fs, c, MONO, 400, track=3, ax=0, alpha=a * 0.7)

    idx = max(i for i, s in enumerate(SCENES) if t >= s[0])
    st, num, name = SCENES[idx]
    p = out_expo(prog(t, st, st + 0.45)) if idx else out_expo(prog(t, 0.2, 0.7))
    ctx.save()
    ctx.rectangle(W - 700, ty - 22, 620, 30)
    ctx.clip()
    off = (1 - p) * 26
    w = text(ctx, name, W - 84, ty + off, fs, c, MONO, 800, track=3, ax=1, alpha=a)
    text(ctx, f"{num} / ", W - 84 - w, ty + off, fs, c, MONO, 400, track=3, ax=1, alpha=a * 0.7)
    ctx.restore()

    blink = 1.0 if frac(t * 1.0) < 0.6 else 0.25
    circle(ctx, 90, by - 5, 5, ORG, a * blink)
    text(ctx, "TC " + timecode(t), 106, by, fs, c, MONO, 500, track=2, ax=0, alpha=a)
    text(ctx, "1920×1080 · 60 FPS · 120 BPM", W - 84, by, fs, c, MONO, 400, track=2, ax=1, alpha=a * 0.7)

    bx0, bx1 = CX - 300, CX + 300
    rgb(ctx, c, a * 0.25)
    ctx.rectangle(bx0, by - 6, bx1 - bx0, 2)
    ctx.fill()
    rgb(ctx, c, a)
    ctx.rectangle(bx0, by - 6, (bx1 - bx0) * clamp(t / DUR), 2)
    ctx.fill()
    for st, _, _ in SCENES:
        x = lerp(bx0, bx1, st / DUR)
        ctx.rectangle(x - 1, by - 12, 2, 14 if t >= st else 8)
        ctx.fill()
    ctx.restore()


# ---------------------------------------------------------------- S1 INTRO 0.0 - 2.0

def s_intro(ctx, t):
    fill_bg(ctx, BG)
    line_y = 560
    retract = HOUSE(prog(t, 1.45, 1.8))
    ga = 1 - prog(t, 1.45, 1.75)

    # layout grid
    ctx.set_line_width(1)
    for k in range(13):
        d = abs(k - 6)
        L = 560 * out_expo(prog(t, 0.5 + d * 0.035, 1.2 + d * 0.035))
        if L > 0:
            x = CX + (k - 6) * 120
            rgb(ctx, INK, 0.13 * ga)
            ctx.move_to(x, line_y - L)
            ctx.line_to(x, line_y + L)
            ctx.stroke()
    for m in range(-4, 5):
        if m == 0:
            continue
        L = 900 * out_expo(prog(t, 0.6 + abs(m) * 0.05, 1.3 + abs(m) * 0.05))
        rgb(ctx, INK, 0.08 * ga)
        ctx.move_to(CX - L, line_y + m * 120)
        ctx.line_to(CX + L, line_y + m * 120)
        ctx.stroke()
    pa = out_cubic(prog(t, 0.95, 1.25)) * ga
    if pa > 0:
        rgb(ctx, INK, 0.45 * pa)
        ctx.set_line_width(1.5)
        for k in range(0, 13, 2):
            for m in (-3, -1, 1, 3):
                x, y = CX + (k - 6) * 120, line_y + m * 120
                ctx.move_to(x - 6, y)
                ctx.line_to(x + 6, y)
                ctx.move_to(x, y - 6)
                ctx.line_to(x, y + 6)
        ctx.stroke()
        for k in range(13):
            text(ctx, f"{k + 1:02d}", CX + (k - 6) * 120 + 6, line_y - 372, 11, INK, MONO, 400, ax=0,
                 alpha=0.35 * pa)

    # dot -> line (squash & stretch)
    if t < 0.3:
        r = 16 * out_back(prog(t, 0.0, 0.3), 2.4)
        circle(ctx, CX, line_y, r, ORG)
    else:
        e = HOUSE(prog(t, 0.28, 0.8))
        hw = lerp(16, 660, e) * (1 - retract) + 0.01
        hh = lerp(16, 1.5, min(1, e * 1.6))
        capsule(ctx, CX, line_y, hw, hh, ORG)

    # mono micro-typography
    type_on(ctx, "SHOWREEL — 2026", CX - 660, line_y - 26, 20, INK, 0.7, t, alpha=ga)
    type_on(ctx, "TYPE / SHAPE / 3D / SYSTEMS", CX + 660, line_y + 46, 20, INK, 0.85, t, ax=1.0,
            alpha=0.7 * ga)

    # HELLO with weight ramp, rising out of the line
    if t >= 0.98:
        wi = min(8, int(prog(t, 1.0, 1.42) * 9))
        weight = (wi + 1) * 100
        p = out_expo(prog(t, 0.98, 1.4))
        px = 250
        ctx.save()
        ctx.rectangle(0, 0, W, line_y - 8)
        ctx.clip()
        L = layout(ctx, "HELLO", px, SANS, weight, track=-6)
        w, _, bl = lmetrics(L)
        base = line_y - 40 + (1 - p) * 280
        x0 = CX - (w + 50) / 2
        ctx.move_to(x0, base - bl)
        rgb(ctx, INK)
        PangoCairo.show_layout(ctx, L)
        ctx.restore()
        dot_x, dot_y = x0 + w + 30, base - 22
        r = 22 * out_back(prog(t, 1.3, 1.5), 3)
        # circle wipe from the full stop
        wr = 2400 * in_cubic(prog(t, 1.52, 2.0)) ** 0.85
        circle(ctx, dot_x, dot_y, max(r, wr), ORG)


# ---------------------------------------------------------------- S2 KINETIC TYPE 2.0 - 4.5

def s_type(ctx, t):
    if t >= 3.5:
        return s_flash(ctx, t)
    fill_bg(ctx, ORG)
    px, base = 360, 668
    split_y = base - 130
    e = HOUSE(prog(t, 3.0, 3.48))
    gap = e * (H + 40)

    def word(dy, top):
        ctx.save()
        if top:
            ctx.rectangle(0, 0, W, split_y)
        else:
            ctx.rectangle(0, split_y, W, H)
        ctx.clip()
        ctx.translate(0, dy)
        scaled(ctx, 1 + 0.06 * out_cubic(prog(t, 2.0, 3.3)))
        w = rise_word(ctx, "MOTION", CX, base, px, BG, 2.0, t, stagger=0.045, dur=0.6, track=-14)
        # underline + captions
        u = HOUSE(prog(t, 2.35, 2.85))
        rgb(ctx, BG)
        ctx.rectangle(CX - w / 2, base + 46, w * u, 12)
        ctx.fill()
        ctx.restore()
        return w

    word(-gap / 2, True)
    w = word(gap / 2, False)
    ca = out_cubic(prog(t, 2.4, 2.7)) * (1 - e)
    type_on(ctx, "[ KINETIC TYPOGRAPHY ]", CX - w / 2, base - 330, 20, BG, 2.4, t, alpha=ca)
    type_on(ctx, "01 — 360PX / HEAVY / -14 TRK", CX + w / 2, base + 110, 18, BG, 2.55, t, ax=1, alpha=ca)

    if gap > 0.5:
        y0, y1 = split_y - gap / 2, split_y + gap / 2
        rgb(ctx, BG)
        ctx.rectangle(0, y0, W, y1 - y0)
        ctx.fill()
        ctx.save()
        ctx.rectangle(0, y0, W, y1 - y0)
        ctx.clip()
        s = lerp(0.75, 1.0, out_expo(prog(t, 3.02, 3.5)))
        scaled(ctx, s, CX, split_y)
        dw = text(ctx, "Design", CX - 30, split_y + 90, 300, INK, SERIF, 300, italic=True, track=lerp(40, -6, e))
        circle(ctx, CX - 30 + dw / 2 + 36, split_y + 72, 20, ORG)
        ctx.restore()


FLASH = [(3.5, "TIMING", INK, BG), (3.75, "SPACING", BG, ORG), (4.0, "WEIGHT", ORG, BG),
         (4.25, "RHYTHM", COB, INK)]


def s_flash(ctx, t):
    st, word, bg, fg = [f for f in FLASH if t >= f[0]][-1]
    fill_bg(ctx, bg)
    lt = t - st
    punch = 1 + 0.16 * (1 - out_expo(lt / 0.25))
    amt = 16 * (1 - out_cubic(lt / 0.14))
    ctx.save()
    scaled(ctx, punch)
    base = 648
    if word == "WEIGHT":
        gl, _, _ = glyphs(ctx, word, 300, SANS, 900, track=-8)
        ws = [100, 300, 500, 600, 800, 900]
        adv = [lmetrics(layout(ctx, ch, 300, SANS, wt))[0] for ch, wt in zip(word, ws)]
        x = CX - sum(adv) / 2
        for i, (ch, wt) in enumerate(zip(word, ws)):
            k = out_expo(prog(lt, i * 0.02, i * 0.02 + 0.2))
            split_text(ctx, ch, x, base + (1 - k) * 60, 300, fg, amt, weight=wt, ax=0)
            x += adv[i]
    elif word == "RHYTHM":
        gl, w, _ = glyphs(ctx, word, 300, SANS, 900, track=-8)
        for i, (ch, gx, _) in enumerate(gl):
            bounce = -abs(math.sin((lt * 4 + i * 0.25) * math.pi)) * 46 * (1 - lt * 2)
            split_text(ctx, ch, CX - w / 2 + gx, base + bounce, 300, fg, amt, weight=900, ax=0)
    elif word == "SPACING":
        tr = lerp(90, -4, out_expo(lt / 0.24))
        split_text(ctx, word, CX, base, 300, fg, amt, weight=900, track=tr)
    else:
        split_text(ctx, word, CX, base, 300, fg, amt, weight=900, track=-8)
    ctx.restore()
    # frame counter tick strip
    rgb(ctx, fg, 0.8)
    for i in range(16):
        on = i < int(lt / 0.25 * 16) + 1
        ctx.rectangle(CX - 16 * 14 / 2 + i * 14, 760, 8, 18 if on else 6)
        ctx.fill()


# ---------------------------------------------------------------- S3 SHAPE SYSTEMS 4.5 - 7.0

PRESETS = [(0, 0, 0, 0), (.5, .5, .5, .5), (1, 0, 0, 0), (1, 0, 1, 0), (.5, .5, 0, 0), (.22, .22, .22, .22),
           (0, 1, 0, 1)]
WAVES = [(4.5, 8, 4), (5.0, 8, 4), (5.5, 0, 0), (6.0, 16, 8), (6.5, 8, 4)]
GCOLS = [BG] * 14 + [ORG] * 4 + [COB]
ZOOM_CELL = (8, 4)


def cell_state(n, i, j):
    if n == len(WAVES) - 1 and (i, j) == ZOOM_CELL:
        return PRESETS[0], 0.0, 1.0, BG
    r = hsh(n, i, j, 1)
    preset = PRESETS[int(hsh(n, i, j, 2) * len(PRESETS))]
    rot = int(hsh(n, i, j, 3) * 4) * 90.0
    sc = 1.0 if r < 0.55 else 0.5 if r < 0.75 else 0.22 if r < 0.9 else 0.0
    col = GCOLS[int(hsh(n, i, j, 4) * len(GCOLS))]
    return preset, rot, sc, col


def s_shapes(ctx, t):
    fill_bg(ctx, INK)
    zp = prog(t, 6.68, 6.96)
    zoom = 40 ** in_cubic(zp)
    cellc = (-60 + ZOOM_CELL[0] * 120 + 60, ZOOM_CELL[1] * 120 + 60)
    ctx.save()
    if zoom > 1.0001:
        ctx.translate(CX, CY)
        ctx.scale(zoom, zoom)
        ctx.rotate(math.radians(12 * in_cubic(zp)))
        ctx.translate(-cellc[0], -cellc[1])
    rgb(ctx, BG, 0.12)
    ctx.set_line_width(1)
    for i in range(18):
        ctx.move_to(-60 + i * 120, 0)
        ctx.line_to(-60 + i * 120, H)
    for j in range(10):
        ctx.move_to(-60, j * 120)
        ctx.line_to(W + 60, j * 120)
    ctx.stroke()

    for j in range(9):
        for i in range(17):
            cx, cy = -60 + i * 120 + 60, j * 120 + 60
            n, pk = 0, 1.0
            for k, (wt, oi, oj) in enumerate(WAVES):
                d = math.hypot(i - oi, j - oj)
                start = wt + d * 0.028
                if t >= start or k == 0:
                    n = k
                    pk = HOUSE(prog(t, start, start + 0.42))
            if n == 0:
                d = math.hypot(i - 8, j - 4)
                ent = out_back(prog(t, 4.5 + d * 0.022, 4.85 + d * 0.022), 2.2)
                a, b = cell_state(0, i, j), cell_state(0, i, j)
            else:
                ent = 1.0
                a, b = cell_state(n - 1, i, j), cell_state(n, i, j)
            radii = [lerp(x, y, pk) for x, y in zip(a[0], b[0])]
            rot = lerp(a[1], b[1] + 90, pk) if n else a[1]
            sc = lerp(a[2], b[2], pk) * ent * (1 - 0.55 * math.sin(math.pi * pk) if n else 1)
            col = a[3] if pk < 0.5 else b[3]
            if (i, j) != ZOOM_CELL or n < len(WAVES) - 1:
                sc *= 1 + 0.05 * math.sin(t * 5 - math.hypot(i - 8, j - 4) * 0.7)
            if sc <= 0.001:
                continue
            ctx.save()
            ctx.translate(cx, cy)
            ctx.rotate(math.radians(rot))
            corner_shape(ctx, 96 * sc, radii)
            rgb(ctx, col)
            ctx.fill()
            ctx.restore()
    ctx.restore()
    easing_card(ctx, t)


def easing_card(ctx, t):
    op = HOUSE(prog(t, 4.95, 5.35))
    cl = HOUSE(prog(t, 6.3, 6.6))
    k = op * (1 - cl)
    if k <= 0:
        return
    cw, chh = 620, 660
    x0, y0 = CX - cw / 2, CY - chh / 2
    ctx.save()
    ctx.rectangle(x0, CY - chh / 2 * k, cw, chh * k)
    ctx.clip()
    rgb(ctx, BG)
    ctx.rectangle(x0, y0, cw, chh)
    ctx.fill()
    text(ctx, "EASING", x0 + 36, y0 + 52, 16, INK, MONO, 800, track=3, ax=0)
    text(ctx, "HOUSE CURVE", x0 + 118, y0 + 52, 16, INK, MONO, 400, track=3, ax=0, alpha=0.6)
    u = frac((t - 5.5) / 1.0) if t > 5.5 else 0.0
    text(ctx, f"t = {u:.2f}", x0 + cw - 36, y0 + 52, 16, ORG, MONO, 500, track=2, ax=1)

    gx, gy, gs = x0 + 110, y0 + 500, 400
    rgb(ctx, INK, 0.12)
    ctx.set_line_width(1)
    for q in range(5):
        ctx.move_to(gx + gs * q / 4, gy)
        ctx.line_to(gx + gs * q / 4, gy - gs)
        ctx.move_to(gx, gy - gs * q / 4)
        ctx.line_to(gx + gs, gy - gs * q / 4)
    ctx.stroke()
    x1, y1, x2, y2 = HOUSE.p
    hp = out_expo(prog(t, 5.25, 5.6))

    def P(x, y):
        return gx + x * gs, gy - y * gs

    rgb(ctx, INK, 0.55 * hp)
    ctx.set_line_width(1.5)
    ctx.move_to(*P(0, 0))
    ctx.line_to(*P(lerp(0, x1, hp), lerp(0, y1, hp)))
    ctx.move_to(*P(1, 1))
    ctx.line_to(*P(lerp(1, x2, hp), lerp(1, y2, hp)))
    ctx.stroke()
    for px_, py_ in (P(lerp(0, x1, hp), lerp(0, y1, hp)), P(lerp(1, x2, hp), lerp(1, y2, hp))):
        ctx.arc(px_, py_, 8, 0, TAU)
        rgb(ctx, BG)
        ctx.fill_preserve()
        rgb(ctx, INK, hp)
        ctx.stroke()

    dp = HOUSE(prog(t, 5.15, 5.6))
    steps = 90
    ctx.move_to(*P(0, 0))
    for s in range(1, int(steps * dp) + 1):
        tt = s / steps
        ctx.line_to(*P(Bezier._b(tt, x1, x2), Bezier._b(tt, y1, y2)))
    rgb(ctx, ORG)
    ctx.set_line_width(5)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()

    if t > 5.5:
        ex, ey = P(u, HOUSE(u))
        rgb(ctx, ORG, 0.5)
        ctx.set_line_width(1)
        ctx.set_dash([4, 6])
        ctx.move_to(ex, gy)
        ctx.line_to(ex, ey)
        ctx.line_to(gx, ey)
        ctx.stroke()
        ctx.set_dash([])
        circle(ctx, ex, ey, 18, ORG, 0.2)
        circle(ctx, ex, ey, 9, ORG)

    # spacing chart: ball + onion skins
    ty = y0 + chh - 72
    rgb(ctx, INK, 0.25)
    ctx.rectangle(gx, ty, gs, 1.5)
    ctx.fill()
    for q in range(13):
        xx = gx + gs * HOUSE(q / 12)
        ctx.rectangle(xx - 0.75, ty - 8, 1.5, 16)
        ctx.fill()
    if t > 5.5:
        for g in range(7, 0, -1):
            uu = u - g * 0.035
            if uu > 0:
                circle(ctx, gx + gs * HOUSE(uu), ty, 12, INK, 0.08 * (8 - g))
        circle(ctx, gx + gs * HOUSE(u), ty, 14, INK)
    text(ctx, "cubic-bezier(.70, 0, .20, 1)", x0 + cw / 2, y0 + chh - 22, 17, INK, MONO, 400, track=1,
         alpha=0.6)
    ctx.restore()


# ---------------------------------------------------------------- S4 PROCEDURAL 3D 7.0 - 9.5

NPTS = 900
GOLD = math.pi * (3 - math.sqrt(5))


def _build_pts():
    sph, tor, cub = [], [], []
    for i in range(NPTS):
        y = 1 - 2 * (i + 0.5) / NPTS
        r = math.sqrt(1 - y * y)
        th = i * GOLD
        p = (r * math.cos(th), y, r * math.sin(th))
        sph.append(p)
        m = max(abs(c) for c in p)
        cub.append(tuple(c / m * 0.68 for c in p))
        u, v = TAU * (i % 45) / 45, TAU * (i // 45) / 20
        R, rr = 0.8, 0.32
        tor.append(((R + rr * math.cos(v)) * math.cos(u), rr * math.sin(v), (R + rr * math.cos(v)) * math.sin(u)))
    return sph, tor, cub


SPH, TOR, CUB = _build_pts()


def rot3(p, yaw, pitch, roll=0.0):
    x, y, z = p
    c, s = math.cos(yaw), math.sin(yaw)
    x, z = x * c + z * s, -x * s + z * c
    c, s = math.cos(pitch), math.sin(pitch)
    y, z = y * c - z * s, y * s + z * c
    c, s = math.cos(roll), math.sin(roll)
    x, y = x * c - y * s, x * s + y * c
    return x, y, z


def s_3d(ctx, t):
    fill_bg(ctx, BG)
    # background outline type
    ctx.save()
    L = layout(ctx, "VOLUME", 440, SANS, 900, track=-10)
    w, _, bl = lmetrics(L)
    ctx.move_to(CX - w / 2 + 120 - (t - 7) * 90, 700 - bl)
    PangoCairo.layout_path(ctx, L)
    rgb(ctx, INK, 0.11 * out_cubic(prog(t, 7.1, 7.6)) * (1 - prog(t, 9.2, 9.45)))
    ctx.set_line_width(1.5)
    ctx.stroke()
    ctx.restore()

    m1 = prog(t, 7.75, 8.35)
    m2 = prog(t, 8.55, 9.15)
    spin = HOUSE(m1) * math.pi / 2 + HOUSE(m2) * math.pi / 2
    yaw = (t - 7) * 0.9 + spin
    pitch = 0.42 + 0.18 * math.sin((t - 7) * 1.3) + HOUSE(m2) * 0.35
    roll = 0.12 * math.sin((t - 7) * 0.9)
    burst = spring(prog(t, 7.0, 7.7), 1.8, 5.5)
    explode = in_expo(prog(t, 9.15, 9.5))
    R = 330 * burst * (1 + explode * 5)
    fade = 1 - explode
    F, zc0 = 3.0, 3.0

    proj = []
    for i in range(NPTS):
        dly = (SPH[i][1] + 1) / 2 * 0.25
        a1 = HOUSE(clamp((m1 * 1.25 - dly)))
        a2 = HOUSE(clamp((m2 * 1.25 - dly)))
        p = tuple(lerp(lerp(s, tt, a1), c, a2) for s, tt, c in zip(SPH[i], TOR[i], CUB[i]))
        x, y, z = rot3(p, yaw, pitch, roll)
        zc = z + zc0
        proj.append((z, CX + x * R * F / zc, CY + y * R * F / zc, F / zc, i))
    proj.sort(key=lambda q: -q[0])

    # orbit rings
    for ring, (tilt, rad, spd) in enumerate(((0.5, 1.45, 1.0), (-0.9, 1.7, -0.7))):
        pts = []
        for s in range(97):
            a = TAU * s / 96
            p = rot3((math.cos(a) * rad, 0, math.sin(a) * rad), yaw * 0.3, pitch + tilt, roll)
            zc = p[2] + zc0 + 0.4
            pts.append((CX + p[0] * R * F / zc, CY + p[1] * R * F / zc, p[2]))
        ctx.set_line_width(1)
        for s in range(96):
            a0 = pts[s]
            rgb(ctx, INK, (0.10 if a0[2] > 0 else 0.3) * fade * burst)
            ctx.move_to(a0[0], a0[1])
            ctx.line_to(pts[s + 1][0], pts[s + 1][1])
            ctx.stroke()
        si = int(frac((t - 7) * 0.5 * spd + ring * 0.37) * 96)
        circle(ctx, pts[si][0], pts[si][1], 6, ORG, fade * burst)

    callout = None
    for z, sx, sy, sc, i in proj:
        depth = clamp(1 - (z + 1) / 2)
        acc = i % 29 == 0
        r = (5.0 if acc else 3.1) * sc * (0.6 + 0.4 * burst)
        col = ORG if acc else mixc(BG2, INK, 0.25 + 0.75 * depth)
        circle(ctx, sx, sy, r, col, fade)
        if i == 377:
            callout = (sx, sy, z)
    if callout and fade > 0.01:
        sx, sy, z = callout
        ca = out_cubic(prog(t, 7.6, 7.9)) * fade
        lx, ly = sx + 140, sy - 110
        rgb(ctx, INK, ca * 0.8)
        ctx.set_line_width(1)
        ctx.move_to(sx, sy)
        ctx.line_to(lx, ly)
        ctx.line_to(lx + 170, ly)
        ctx.stroke()
        circle(ctx, sx, sy, 8, INK, ca * 0.3)
        text(ctx, "VTX_0377", lx + 4, ly - 10, 14, INK, MONO, 800, track=2, ax=0, alpha=ca)
        text(ctx, f"{sx - CX:+07.1f} {CY - sy:+07.1f} {z:+.2f}", lx + 4, ly + 22, 13, INK, MONO, 400,
             ax=0, alpha=ca * 0.7)

    la = out_cubic(prog(t, 7.3, 7.6)) * fade
    shape = "SPHERE" if t < 8.05 else "TORUS" if t < 8.85 else "HEXAHEDRON"
    text(ctx, f"PRIMITIVE  {shape}", 84, CY + 330, 15, INK, MONO, 500, track=3, ax=0, alpha=la)
    text(ctx, f"VERTICES   {NPTS}", 84, CY + 356, 15, INK, MONO, 500, track=3, ax=0, alpha=la * 0.6)
    text(ctx, f"YAW        {math.degrees(yaw) % 360:06.2f}°", 84, CY + 382, 15, INK, MONO, 500, track=3, ax=0,
         alpha=la * 0.6)
    rise_word(ctx, "Depth,", W - 90, CY + 390, 120, INK, 7.35, t, font=SERIF, weight=300, italic=True, ax=1,
              stagger=0.03)
    text(ctx, "procedurally.", W - 90, CY + 430, 22, ORG, MONO, 500, track=2, ax=1,
         alpha=out_cubic(prog(t, 7.6, 7.9)) * fade)


# ---------------------------------------------------------------- S5 MONTAGE 9.5 - 11.5

def m_rings(ctx, t):
    fill_bg(ctx, COB)
    lt = t - 9.5
    ctx.set_line_cap(cairo.LINE_CAP_BUTT)
    for k in range(16):
        r = (k + frac(lt * 2.2)) * 72
        rgb(ctx, INK, 0.9 * clamp(1 - r / 1150))
        ctx.set_line_width(2 + 10 * (0.5 + 0.5 * math.sin(k * 1.3 + lt * 6)))
        ctx.arc(CX, CY, r, 0, TAU)
        ctx.stroke()
    for q, (rad, spd, dash) in enumerate(((150, 1.4, 14), (260, -0.9, 4), (380, 0.6, 30))):
        ctx.save()
        ctx.translate(CX, CY)
        ctx.rotate(lt * spd * 3)
        ctx.set_dash([dash, dash * 0.8])
        ctx.set_line_width(18 if q == 0 else 6)
        rgb(ctx, BG)
        ctx.arc(0, 0, rad, 0, TAU * 0.7)
        ctx.stroke()
        ctx.restore()
    ctx.set_dash([])
    sw = out_expo(prog(t, 9.5, 9.95))
    ctx.set_line_width(26)
    rgb(ctx, ORG)
    ctx.arc(CX, CY, 320, -TAU / 4, -TAU / 4 + TAU * sw)
    ctx.stroke()
    circle(ctx, CX, CY, 34 * out_back(prog(t, 9.52, 9.8)), INK)


def m_harmono(ctx, t):
    fill_bg(ctx, BG)
    lt = t - 10.0
    dp = out_cubic(prog(t, 10.0, 10.55))
    ctx.save()
    ctx.translate(CX, CY)
    ctx.rotate(lt * 0.8)
    n = int(2200 * dp)
    for layer, (col, lw, ph) in enumerate(((INK, 1.2, 0.5), (ORG, 3.0, 0.0))):
        ctx.move_to(0, 0)
        for s in range(n):
            u = s / 2200 * 110
            dec = math.exp(-u * 0.018)
            x = 260 * dec * (math.sin(3.0 * u + ph) + 0.6 * math.sin(2.012 * u + math.pi / 2))
            y = 260 * dec * (math.sin(3.006 * u + math.pi / 2 + ph) + 0.6 * math.sin(2.0 * u))
            if s == 0:
                ctx.move_to(x, y)
            else:
                ctx.line_to(x, y)
        rgb(ctx, col, 0.55 if layer == 0 else 1)
        ctx.set_line_width(lw)
        ctx.stroke()
    ctx.restore()


def m_bars(ctx, t):
    fill_bg(ctx, ORG)
    lt = t - 10.5
    n = 36
    sp = 1500 / n
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_width(sp * 0.52)
    rgb(ctx, BG)
    kick = math.exp(-(lt % 0.25) * 14)
    for i in range(n):
        x = CX - 750 + sp * (i + 0.5)
        env = math.sin(math.pi * (i + 0.5) / n)
        h = (0.25 + 0.75 * abs(math.sin(i * 0.61 + lt * 9) * math.cos(i * 0.23 - lt * 5))) * env
        h = h * (0.55 + 0.45 * kick) * out_expo(prog(lt, abs(i - n / 2) * 0.006, 0.25 + abs(i - n / 2) * 0.006))
        hh = max(1, h * 330)
        ctx.move_to(x, CY - hh)
        ctx.line_to(x, CY + hh)
        ctx.stroke()


def m_tunnel(ctx, t, spd=1.0):
    fill_bg(ctx, BG)
    lt = t - 11.0
    ctx.save()
    ctx.translate(CX, CY)
    base = lt * 3.2 * spd
    for k in range(31):
        z = k - frac(base)
        s = 2600 * 0.84 ** z
        if s < 4:
            continue
        idx = k + int(math.floor(base))
        ctx.save()
        ctx.rotate(math.radians(idx * 6 + lt * 25))
        ctx.rectangle(-s / 2, -s / 2, s, s)
        rgb(ctx, ORG if idx % 6 == 0 else BG2 if idx % 2 else BG)
        ctx.fill()
        ctx.restore()
    ctx.restore()


MONTAGE = [(9.5, m_rings, "LOOPS", INK), (10.0, m_harmono, "CURVES", INK), (10.5, m_bars, "SYSTEMS", BG),
           (11.0, m_tunnel, "ILLUSION", INK)]


def s_montage(ctx, t):
    i = max(k for k, m in enumerate(MONTAGE) if t >= m[0])
    st, fn, word, col = MONTAGE[i]
    wipe = prog(t, st, st + 0.14) if i else 1.0
    if wipe < 1:
        MONTAGE[i - 1][1](ctx, t)
        ctx.save()
        nb = 8
        for b in range(nb):
            e = SNAP(clamp(wipe * 1.35 - b * 0.045))
            y0 = H * b / nb
            if b % 2:
                ctx.rectangle(W * (1 - e), y0, W * e, H / nb + 1)
            else:
                ctx.rectangle(0, y0, W * e, H / nb + 1)
        ctx.clip()
    ctx.save()
    scaled(ctx, 1 + 0.07 * (1 - out_expo(prog(t, st, st + 0.4))))
    fn(ctx, t)
    ctx.restore()
    rise_word(ctx, word, 84, H - 130, 150, col, st + 0.03, t, stagger=0.025, dur=0.4, ax=0, track=-6,
              clip_pad=10)
    text(ctx, f"04.{'ABCD'[i]}", 90, H - 318, 16, col, MONO, 800, track=3, ax=0,
         alpha=out_cubic(prog(t, st + 0.05, st + 0.2)))
    if wipe < 1:
        ctx.restore()
    fl = 1 - prog(t, 9.5, 9.6)
    if fl > 0:
        rgb(ctx, INK, fl)
        ctx.paint()


# ---------------------------------------------------------------- S6 SIGNATURE 11.5 - 15.0

NAME = "Claude Opus 5.5"
NAME_PX, NAME_BASE, DOT_R = 300, 590, 26


def name_geom(ctx):
    L = layout(ctx, NAME, NAME_PX, SANS, 900, track=-14)
    w, _, bl = lmetrics(L)
    px = min(NAME_PX, NAME_PX * (W * 0.8) / w)
    if px != NAME_PX:
        L = layout(ctx, NAME, px, SANS, 900, track=-14)
        w, _, bl = lmetrics(L)
    tot = w + 22 + DOT_R * 2
    x0 = CX - tot / 2
    return px, w, bl, x0, (x0 + w + 22 + DOT_R, NAME_BASE - DOT_R)


def dot_pos(t, x0, fx, fy):
    if t < 12.0:
        return CX, CY
    a = HOUSE(prog(t, 12.0, 12.3))
    b = HOUSE(prog(t, 12.3, 12.8))
    x = lerp(lerp(CX, x0 - 60, a), fx, b)
    y = lerp(CY, fy, HOUSE(prog(t, 12.0, 12.45)))
    # exit: wipe the name back out, then return home to centre (loops into the intro)
    x = lerp(x, x0 - 40, HOUSE(prog(t, 14.45, 14.72)))
    h = HOUSE(prog(t, 14.72, 14.9))
    return lerp(x, CX, h), lerp(y, CY, h)


def s_signature(ctx, t):
    fill_bg(ctx, BG)
    px, w, bl, x0, (fx, fy) = name_geom(ctx)
    if t < 12.0:
        e = HOUSE(prog(t, 11.5, 12.0))
        r = lerp(1200, DOT_R, e)
        ctx.save()
        ctx.arc(CX, CY, r, 0, TAU)
        ctx.clip()
        m_tunnel(ctx, t, 1 + e * 3)
        ctx.restore()
        ctx.set_line_width(lerp(3, 0, e))
        circle(ctx, CX, CY, r, ORG, prog(t, 11.82, 11.98))
        ctx.arc(CX, CY, r, 0, TAU)
        rgb(ctx, ORG)
        ctx.set_line_width(4)
        ctx.stroke()
        return

    push = 1 + 0.035 * out_cubic(prog(t, 12.0, 15.0))
    ctx.save()
    scaled(ctx, push)

    # faint grid returns (bookend)
    ga = 0.07 * out_cubic(prog(t, 12.6, 13.4)) * (1 - prog(t, 14.4, 14.8))
    if ga > 0:
        ctx.set_line_width(1)
        rgb(ctx, INK, ga)
        for k in range(13):
            ctx.move_to(CX + (k - 6) * 120, 0)
            ctx.line_to(CX + (k - 6) * 120, H)
        ctx.stroke()

    dx, dy = dot_pos(t, x0, fx, fy)
    # name, painted by the dot
    reveal = dx - DOT_R * 0.3
    if t < 12.3 or t >= 14.72:
        reveal = -1
    elif t >= 14.45:
        reveal = dx
    ctx.save()
    ctx.rectangle(0, 0, max(0, reveal), H)
    ctx.clip()
    gl, _, _ = glyphs(ctx, NAME, px, SANS, 900, track=-14)
    for i, (ch, gx, adv) in enumerate(gl):
        k = out_expo(prog(t, 12.32 + i * 0.06, 12.8 + i * 0.06))
        text(ctx, ch, x0 + gx, NAME_BASE + (1 - k) * 40, px, INK, SANS, 900, ax=0)
    ctx.restore()

    # role + meta
    sub = 1 - HOUSE(prog(t, 14.3, 14.55))
    lw = 980 * HOUSE(prog(t, 12.7, 13.2)) * sub
    rgb(ctx, INK, 0.35)
    ctx.rectangle(CX - lw / 2, NAME_BASE + 64, lw, 1.5)
    ctx.fill()
    if t < 14.55:
        rise_word(ctx, "Motion Designer", CX, NAME_BASE + 170, 78, ORG, 12.85, t, font=SERIF, weight=300,
                  italic=True, stagger=0.022, dur=0.5, rot=0, clip_pad=26)
        type_on(ctx, "TYPE  ·  SHAPE  ·  3D  ·  SYSTEMS  ·  RHYTHM", CX, NAME_BASE + 250, 18, INK, 13.25, t,
                ax=0.5, cps=60, alpha=0.65 * sub, track=4)
        text(ctx, "AVAILABLE FOR COMMISSIONS — 2026", CX, NAME_BASE - 330, 15, INK, MONO, 500, track=5,
             alpha=out_cubic(prog(t, 13.4, 13.8)) * sub)

    # the dot with squash & stretch from velocity
    p0, p1 = dot_pos(t - 1 / 240, x0, fx, fy), dot_pos(t + 1 / 240, x0, fx, fy)
    vx, vy = (p1[0] - p0[0]) * 120, (p1[1] - p0[1]) * 120
    st = clamp(math.hypot(vx, vy) / 9000, 0, 1.4)
    r = DOT_R * lerp(1, 16 / DOT_R, prog(t, 14.72, 14.9))
    if t >= 14.88:
        r *= lerp(1, 1.4, out_cubic(prog(t, 14.88, 14.93))) * (1 - in_cubic(prog(t, 14.93, 14.99)))
    ctx.save()
    ctx.translate(dx, dy)
    ctx.rotate(math.atan2(vy, vx))
    ctx.scale(1 + st, 1 / (1 + st * 0.6))
    circle(ctx, 0, 0, r, ORG)
    ctx.restore()
    for pt in (12.8, 14.0):
        pp = prog(t, pt, pt + 0.8)
        if 0 < pp < 1:
            ctx.set_line_width(2)
            rgb(ctx, ORG, 1 - pp)
            ctx.arc(dx, dy, DOT_R + out_expo(pp) * 90, 0, TAU)
            ctx.stroke()
    ctx.restore()


# ---------------------------------------------------------------- master timeline

TIMELINE = [(0.0, s_intro), (2.0, s_type), (4.5, s_shapes), (7.0, s_3d), (9.5, s_montage),
            (11.5, s_signature)]


def draw(ctx, t):
    fn = [f for st, f in TIMELINE if t >= st][-1]
    ctx.save()
    fn(ctx, t)
    ctx.restore()
    hud(ctx, t)


def render_frame(i, samples=1, shutter=0.5):
    acc = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    actx = cairo.Context(acc)
    for k in range(samples):
        t = (i + shutter * k / samples) / FPS
        if samples == 1:
            draw(actx, t)
            break
        s = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
        draw(cairo.Context(s), t)
        actx.set_source_surface(s)
        actx.paint_with_alpha(1 / (k + 1))
    acc.flush()
    return acc
