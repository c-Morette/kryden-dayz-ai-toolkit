"""Single source of the design system colors (D-05, D-09). Read by gen_components.py (layouts +
KLD_Tokens.c) and by the lab generator.

Base: the dark theme of the author's shadcn/ui-based web design system, values in sRGB 0-255 converted from oklch
(conversion below). primary and primary-foreground come from the shadcn neutral theme (D-12).
Button and badge variants follow the shadcn/ui `button` and `badge` component classes.

Everything that has transparency on the web (`/80`, `/30`, `foreground/10`...) goes in PRE-MIXED over
`background` in sRGB, which is what the browser shows: DayZ blends alpha in linear space (measured,
lab round 4), so an alpha copied from the web would give a different color.
"""
import math

BASE = {
    "background": (10, 10, 10),
    "foreground": (250, 250, 250),
    "card": (23, 23, 23),
    # D-12 (replaces the earlier yellow primary and D-11): monochrome shadcn primary, neutral .dark theme
    # (ui.shadcn.com/docs/theming: --primary oklch(0.922 0 0), --primary-foreground oklch(0.205 0 0)).
    # Dark text on a light background gets thin in DayZ (glyph edge blended in linear space); the
    # primary label uses a bold bitmap font (gen_components.py). Lab round 7: mean glyph contrast
    # 7.7 at 1080p and 4.9 at 720p, against 2.6 / 2.4 for the earlier yellow with #1A1206.
    "primary": (229, 229, 229),
    "primary_foreground": (23, 23, 23),
    "secondary": (39, 39, 42),
    "muted": (38, 38, 38),
    "muted_foreground": (161, 161, 161),
    "destructive": (255, 100, 103),
    "ring": (115, 115, 115),
}
WHITE = (255, 255, 255)


def over(fg, a, bg):
    """fg with alpha a over bg, in sRGB (like the browser)."""
    return tuple(round(f * a + b * (1 - a)) for f, b in zip(fg, bg))


def oklch_to_srgb(L, C, h):
    """CSS Color 4 oklch -> sRGB conversion, clipped per channel."""
    a = C * math.cos(math.radians(h))
    b = C * math.sin(math.radians(h))
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    rgb = (
        4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )

    def enc(x):
        return 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055

    return tuple(round(max(0.0, min(1.0, enc(v))) * 255) for v in rgb)


B = BASE
BG = B["background"]

# Surfaces and lines
TOKENS = dict(BASE)
TOKENS.update({
    "border": over(WHITE, 0.10, BG),            # --border (white 10%) over background = 34
    "input": over(WHITE, 0.15, BG),             # --input (white 15%) over background = 47
    "card_ring": over(B["foreground"], 0.10, BG),   # Card: ring-1 ring-foreground/10 (outside the card)
})

# Button (shadcn button). PRESSED uses the hover color: on the web "active" only shifts 1 px.
# Disabled = opacity-50 of the whole group over background.
TRANSPARENT = None


def _disabled(c):
    return TRANSPARENT if c is TRANSPARENT else over(c, 0.5, BG)


_secondary_hover = oklch_to_srgb(0.274 * 0.95 + 0.985 * 0.05, 0.006 * 0.95, 286.033)  # color-mix(oklch, secondary, foreground 5%)

BUTTON = {
    #             bg normal,                     bg hover,                         fg,                    border
    "PRIMARY":     (B["primary"],                over(B["primary"], 0.80, BG),     B["primary_foreground"], TRANSPARENT),   # bg-primary, hover:bg-primary/80
    "SECONDARY":   (B["secondary"],              _secondary_hover,                 B["foreground"],       TRANSPARENT),   # hover: color-mix 5% foreground
    "OUTLINE":     (over(WHITE, 0.15 * 0.30, BG), over(WHITE, 0.15 * 0.50, BG), B["foreground"],      TOKENS["input"]),  # dark:bg-input/30 (input = white 15%), hover:bg-input/50, dark:border-input
    "GHOST":       (TRANSPARENT,                 over(B["muted"], 0.50, BG),       B["foreground"],       TRANSPARENT),   # dark:hover:bg-muted/50
    "DESTRUCTIVE": (over(B["destructive"], 0.20, BG), over(B["destructive"], 0.30, BG), B["destructive"],  TRANSPARENT),   # dark:bg-destructive/20, hover /30, text-destructive
}

# Badge (shadcn badge): no hover (only on <a>).
BADGE = {
    #              bg,                                fg,                     border
    "PRIMARY":     (B["primary"],                     B["primary_foreground"], TRANSPARENT),
    "SECONDARY":   (B["secondary"],                   B["foreground"],         TRANSPARENT),
    "OUTLINE":     (TRANSPARENT,                      B["foreground"],         TOKENS["border"]),   # border-border text-foreground
    "DESTRUCTIVE": (over(B["destructive"], 0.20, BG), B["destructive"],        TRANSPARENT),        # dark:bg-destructive/20 text-destructive
}


def argb(c):
    """Enforce Script literal (format of P:\\scripts\\3_game\\colors.c: 0xffd70d11)."""
    if c is TRANSPARENT:
        return "0x00000000"
    return "0xff%02x%02x%02x" % c


def layout_color(c):
    """`color` attribute of a .layout (4 floats 0..1)."""
    if c is TRANSPARENT:
        return "0 0 0 0"
    return " ".join(f"{v / 255:.4f}" for v in c) + " 1"


if __name__ == "__main__":
    for k, v in TOKENS.items():
        print(f"{k:20} {v}  {argb(v)}  {layout_color(v)}")
    for name, table in (("BUTTON", BUTTON), ("BADGE", BADGE)):
        for k, row in table.items():
            print(name, k, [argb(c) for c in row])
