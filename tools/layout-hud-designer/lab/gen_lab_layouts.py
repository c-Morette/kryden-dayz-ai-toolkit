"""Generates the test layouts kld_lab_02..08 in KrydenLayoutHudDesigner_Client/gui/layouts/lab/.

Only uses classes, attributes, values, styles, fonts and images that exist in vanilla
(P:\\gui\\layouts, P:\\gui\\looknfeel\\dayzwidgets.styles, P:\\gui\\fonts, dayz_gui.imageset), plus the
mod's own atlas styles (tools/gen_atlas.py) in tests 07 and 08.
Output: UTF-8 without BOM, LF (same as P:\\gui\\layouts\\gameplay\\rangefinder_hud_2.layout:186).

    python lab/gen_lab_layouts.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from kld_layout import W, geo, node, panel, text  # noqa: E402
from kld_tokens import TOKENS, layout_color, oklch_to_srgb  # noqa: E402

OUT = Path(__file__).parent.parent / "KrydenLayoutHudDesigner_Client" / "gui" / "layouts" / "lab"


def root(name, children):
    attrs = [("visible", 1)] + geo(0, 0, 1, 1, 0, 0, 0, 0) + [("priority", 900)]
    return node("Frame", name, attrs, children) + "\n"


RED = "0.9 0.2 0.2 1"
BLUE = "0.2 0.4 0.9 1"
GREEN = "0.2 0.7 0.2 1"
YELLOW = "0.9 0.7 0.1 1"
GREY = "0.25 0.25 0.25 0.9"
DARK = "0.04 0.04 0.04 0.92"


def lab02():
    kids = []
    hs = [("left", "left"), ("center", "center_ref"), ("right", "right_ref")]
    vs = [("top", "top"), ("center", "center_ref"), ("bottom", "bottom_ref")]
    for hn, hv in hs:
        for vn, vv in vs:
            kids.append(panel(f"a_{hn}_{vn}", YELLOW, geo(20, 20, 100, 100), [("halign", hv), ("valign", vv)]))
    kids.append(panel("a_omitted_300_300", GREEN, geo(300, 300, 100, 100)))
    kids.append(panel("a_right_top_zero", RED, geo(0, 0, 60, 60), [("halign", "right_ref"), ("valign", "top")]))
    kids.append(panel("a_left_bottom_noref", BLUE, geo(200, 0, 100, 100), [("halign", "left"), ("valign", "bottom")]))
    kids.append(panel("a_left_bottomref_cmp", RED, geo(320, 0, 100, 100), [("halign", "left"), ("valign", "bottom_ref")]))
    kids.append(panel("a_right_proppos_10pct", GREEN, geo(0.1, 0.3, 100, 100, 0, 0, 1, 1), [("halign", "right_ref"), ("valign", "top")]))
    return root("kld_lab_02_root", kids)


def grid(name, x, y, padding, margin, cols=3, rows=2, nkids=6, extra=None, kid_geo=None):
    attrs = [("visible", 1), ("ignorepointer", 1), ("color", GREY)] + geo(x, y, 420, 220) + [
        ("style", "Colorable"),
        ("Padding", padding),
        ("Margin", margin),
        ("Columns", cols),
        ("Rows", rows),
    ] + (extra or [])
    colors = [RED, BLUE, GREEN, YELLOW, RED, BLUE]
    kg = kid_geo or geo(0, 0, 1, 1, 0, 0, 0, 0)
    kids = [panel(f"{name}_c{i + 1}", colors[i % 6], kg) for i in range(nkids)]
    return W("GridSpacer", name, attrs, kids)


def wrap(name, x, y, padding, margin, nkids=5, extra=None):
    attrs = [("visible", 1), ("ignorepointer", 1), ("color", GREY)] + geo(x, y, 420, 220) + [
        ("style", "Colorable"),
        ("Padding", padding),
        ("Margin", margin),
    ] + (extra or [])
    colors = [RED, BLUE, GREEN, YELLOW, RED]
    kids = [panel(f"{name}_c{i + 1}", colors[i % 5], geo(0, 0, 100, 50)) for i in range(nkids)]
    return W("WrapSpacer", name, attrs, kids)


def lab03():
    kids = [
        grid("g1_pad10_mar0", 40, 40, 10, 0),
        grid("g2_pad0_mar10", 500, 40, 0, 10),
        grid("g3_pad10_mar25", 960, 40, 10, 25),
        wrap("w1_pad10_mar0", 40, 320, 10, 0),
        wrap("w2_pad0_mar10", 500, 320, 0, 10),
        wrap("w3_center", 960, 320, 0, 0, nkids=3, extra=[("content_halign", "center")]),
        grid("g4_sizetocontent_v", 40, 600, 0, 0, cols=2, rows=2, nkids=4,
             extra=[("Size To Content V", 1)], kid_geo=geo(0, 0, 100, 80)),
    ]
    return root("kld_lab_03_root", kids)


def lab04():
    def sq(name, rgba, x, y, prio=None):
        extra = [("priority", prio)] if prio is not None else []
        return panel(name, rgba, geo(x, y, 200, 200), extra)

    kids = [
        sq("l_a1_first_red_noprio", RED, 40, 40),
        sq("l_a2_second_blue_noprio", BLUE, 140, 140),
        sq("l_b1_first_red_p10", RED, 440, 40, 10),
        sq("l_b2_second_blue_p1", BLUE, 540, 140, 1),
        sq("l_c1_first_red_p1", RED, 840, 40, 1),
        sq("l_c2_second_blue_p10", BLUE, 940, 140, 10),
        W("Frame", "l_d_parent_p1", [("visible", 1), ("ignorepointer", 1)] + geo(1240, 40, 200, 200) + [("priority", 1)],
          [sq("l_d1_child_red_p999", RED, 0, 0, 999)]),
        sq("l_d2_sibling_blue_p5", BLUE, 1340, 140, 5),
    ]
    return root("kld_lab_04_root", kids)


def lab05():
    # Round 2: dark background + amber tint to tell the border from the fill (in round 1 white hid the
    # style's drawing). Logo with "src alpha" 1 + mode additive, like vanilla
    # (day_z_ingamemenu.layout:540-553).
    amber = "1 0.75 0 1"
    inner = [
        panel("n1_default_60x30", amber, geo(20, 20, 60, 30), style="DayZDefaultPanel"),
        panel("n2_default_200x100", amber, geo(120, 20, 200, 100), style="DayZDefaultPanel"),
        panel("n3_default_600x300", amber, geo(360, 20, 600, 300), style="DayZDefaultPanel"),
        panel("n7_sides_200x100", amber, geo(1000, 20, 200, 100), style="DayZDefaultPanelSides"),
        panel("n8_uidefault_200x100", amber, geo(1240, 20, 200, 100), style="UIDefaultPanel"),
        panel("n4_outline_200x100", amber, geo(20, 360, 200, 100), style="Outline"),
        panel("n5_dashed_200x100", amber, geo(260, 360, 200, 100), style="dashed"),
        panel("n6_default_prop_20x15", amber, geo(500, 360, 0.2, 0.15, 1, 1, 0, 0), style="DayZDefaultPanel"),
    ]
    logo = [("image0", '"set:dayz_gui image:DayZLogo"'), ("mode", "additive"), ("src alpha", 1)]
    for i, fa in enumerate(["none", "fixwidth", "inside", "outside"]):
        x = 20 + i * 340
        inner.append(panel(f"i{i + 1}_frame_{fa}", amber, geo(x, 560, 300, 100), style="Outline"))
        attrs = [("visible", 1), ("ignorepointer", 1), ("color", "1 1 1 1")] + geo(x, 560, 300, 100) + [("fixaspect", fa)] + logo
        inner.append(W("Image", f"i{i + 1}_logo_{fa}", attrs))
    attrs = [("visible", 1), ("ignorepointer", 1), ("color", "1 1 1 1")] + geo(1400, 520, 444, 208) + logo
    inner.append(W("Image", "i0_logo_native_444x208", attrs))
    bg = panel("n_bg", DARK, geo(20, 20, 1860, 1020), children=inner)
    return root("kld_lab_05_root", [bg])


# Test 06 checks diacritics on purpose (Portuguese accents); the ASCII line is the control.
SAMPLE = "Kryden Ação ÇÃÕ ãõç áéíóú âêô 0123"
ASCII = "Kryden Acao CAO aoc aeiou aeo 0123"


def lab06():
    rows = [
        ("f01_sdfbook24_at16", "sdf_MetronBook24", 16, SAMPLE),
        ("f02_sdfbook24_at24", "sdf_MetronBook24", 24, SAMPLE),
        ("f03_sdfbook24_at32", "sdf_MetronBook24", 32, SAMPLE),
        ("f04_sdflight24_at16", "sdf_MetronLight24", 16, SAMPLE),
        ("f05_sdflight24_at24", "sdf_MetronLight24", 24, SAMPLE),
        ("f06_sdfbook72_at48", "sdf_MetronBook72", 48, SAMPLE),
        ("f07_metron_nosuffix_at16", "Metron", 16, SAMPLE),
        ("f08_metron16_at16", "Metron16", 16, SAMPLE),
        ("f09_metron16_at24", "Metron16", 24, SAMPLE),
        ("f10_metronbook16_at16", "MetronBook16", 16, SAMPLE),
        ("f11_sdflight24_noexact", "sdf_MetronLight24", None, SAMPLE),
        ("f12_sdfbook24_at24_ascii", "sdf_MetronBook24", 24, ASCII),
    ]
    texts = []
    for i, (name, font, size, txt) in enumerate(rows):
        h = 64 if (size or 0) >= 48 else 44
        y = 20 + i * 60 if i < 6 else 20 + 5 * 60 + 84 + (i - 6) * 52
        attrs = [("visible", 1), ("ignorepointer", 1)] + geo(20, y, 1100, h) + [
            ("text", f'"{txt}"'),
            ("font", f'"gui/fonts/{font}"'),
            ("text color", "1 1 1 1"),
            ("text valign", "center"),
        ]
        if size is not None:
            attrs += [("exact text", 1), ("exact text size", size)]
        texts.append(W("Text", name, attrs))
    bg = panel("f_bg", DARK, geo(40, 40, 1160, 800), children=texts)
    return root("kld_lab_06_root", [bg])


# ---- round 4: own atlas (tools/gen_atlas.py) + contract tokens (design contract section 2) ----
# T_PRIMARY / T_PRIMARY_FG are the yellow primary used before D-12; kept so the test reproduces round 4.
T_BG = "0.0394 0.0394 0.0394 1"
T_FG = "0.9803 0.9803 0.9803 1"
T_CARD = "0.0905 0.0905 0.0905 1"
T_PRIMARY = "0.9413 0.6929 0 1"
T_PRIMARY_FG = "0.4505 0.2424 0.0409 1"
T_SECONDARY = "0.1529 0.1529 0.1658 1"
T_MUTED_FG = "0.6302 0.6302 0.6302 1"
T_DESTRUCTIVE = "1 0.3912 0.4039 1"
T_BORDER_BG = "0.1333 0.1333 0.1333 1"
T_BORDER_CARD = "0.1804 0.1804 0.1804 1"
T_INPUT_BG = "0.1843 0.1843 0.1843 1"
BOOK = "gui/fonts/sdf_MetronBook24"
LIGHT = "gui/fonts/sdf_MetronLight24"


def button(name, g, style, rgba, label=None, label_rgba=None, child_label=None):
    """label = text of the ButtonWidget itself (text_proportion); child_label = child TextWidget with
    exact size (ButtonWidget does not accept "exact text size" in vanilla)."""
    attrs = [("visible", 1), ("color", rgba)] + g + [("style", style)]
    if label is not None:
        attrs += [("text", f'"{label}"'), ("text color", label_rgba), ("text_proportion", 0.5), ("font", f'"{BOOK}"')]
    kids = None
    if child_label is not None:
        txt, trgba = child_label
        kids = [text(f"{name}_label", geo(0, 0, 1, 1, 0, 0, 0, 0), txt, 16, trgba, halign="center")]
    return W("Button", name, attrs, kids)


def lab07():
    k = []
    # A - card: fill + 1 px ring on top (declared later)
    k.append(panel("c_card_fill", T_CARD, geo(40, 40, 480, 260), style="kld_fill_r10"))
    k.append(panel("c_card_ring", T_BORDER_CARD, geo(40, 40, 480, 260), style="kld_ring_r10"))
    k.append(text("c_title_18", geo(56, 56, 448, 28), "Card title", 18, T_FG))
    k.append(text("c_desc_16", geo(56, 92, 448, 24), "Description in secondary text", 16, T_MUTED_FG, LIGHT))
    k.append(text("c_caption_14", geo(56, 124, 448, 20), "Caption 14 px", 14, T_MUTED_FG, LIGHT))
    k.append(button("c_btn_primary", geo(56, 252, 120, 32), "kld_btn_fill_r10", T_PRIMARY, "Confirm", T_PRIMARY_FG))
    k.append(button("c_btn_secondary", geo(188, 252, 120, 32), "kld_btn_fill_r10", T_SECONDARY, "Cancel", T_FG))
    # B1 - variants with the button's own text; B2 - with a child TextWidget of exact size 16
    variants = [
        ("primary", "kld_btn_fill_r10", T_PRIMARY, T_PRIMARY_FG),
        ("secondary", "kld_btn_fill_r10", T_SECONDARY, T_FG),
        ("outline", "kld_btn_ring_r10", T_INPUT_BG, T_FG),
        ("ghost", "kld_btn_fill_r10", "0 0 0 0", T_FG),
        ("destructive", "kld_btn_fill_r10", T_DESTRUCTIVE, T_FG),
    ]
    for i, (vn, st, bg, fg) in enumerate(variants):
        x = 40 + i * 136
        k.append(button(f"b1_{vn}", geo(x, 340, 120, 32), st, bg, vn.capitalize(), fg))
        k.append(button(f"b2_{vn}", geo(x, 388, 120, 32), st, bg, child_label=(vn.capitalize(), fg)))
    # C - r6 badges (height 22, text 14)
    badges = [("primary", "kld_fill_r6", T_PRIMARY, T_PRIMARY_FG, "New", 64),
              ("secondary", "kld_fill_r6", T_SECONDARY, T_FG, "Beta", 64),
              ("outline", "kld_ring_r6", T_BORDER_BG, T_FG, "Draft", 96),
              ("destructive", "kld_fill_r6", T_DESTRUCTIVE, T_FG, "Error", 64)]
    x = 40
    for bn, st, bg, fg, label, w in badges:
        k.append(panel(f"badge_{bn}", bg, geo(x, 444, w, 22), style=st,
                       children=[text(f"badge_{bn}_label", geo(0, 0, 1, 1, 0, 0, 0, 0), label, 14, fg, halign="center")]))
        x += w + 12
    # D - corner at several sizes (light color to see the cut)
    for prefix, style, y in [("t_fill_r10", "kld_fill_r10", 40), ("t_ring_r10", "kld_ring_r10", 260)]:
        k.append(panel(f"{prefix}_24x24_min", T_FG, geo(800, y, 24, 24), style=style))
        k.append(panel(f"{prefix}_100x32", T_FG, geo(840, y, 100, 32), style=style))
        k.append(panel(f"{prefix}_600x200", T_FG, geo(960, y, 600, 200), style=style))
    k.append(panel("t_fill_r10_16x16_under_min", T_FG, geo(800, 500, 16, 16), style="kld_fill_r10"))
    # transparent ring center? light ring over solid amber
    k.append(panel("t_amber_base_a", T_PRIMARY, geo(840, 500, 200, 80)))
    k.append(panel("t_ring_r10_over_amber", T_FG, geo(840, 500, 200, 80), style="kld_ring_r10"))
    # translucency: black 50% over amber (sRGB would give ~120,88,0)
    k.append(panel("t_amber_base_b", T_PRIMARY, geo(1080, 500, 200, 80)))
    k.append(panel("t_fill_r10_black50_over_amber", "0 0 0 0.5", geo(1080, 500, 200, 80), style="kld_fill_r10"))
    k.append(panel("t_fill_r6_200x80", T_FG, geo(1320, 500, 200, 80), style="kld_fill_r6"))
    bg = panel("t_bg", T_BG, geo(0, 0, 1920, 1080), children=k)
    return root("kld_lab_07_root", [bg])


def lab08():
    """Showcase of the v0 library: only empty containers; KLD_LabShowcase creates the components from script.
    Containers that receive buttons have NO ignorepointer and sit outside the background panel (not
    measured whether a parent's ignorepointer blocks its children)."""
    fg = layout_color(TOKENS["foreground"])
    muted = layout_color(TOKENS["muted_foreground"])
    k = [
        panel("sc_bg", layout_color(TOKENS["background"]), geo(0, 0, 1920, 1080)),
        text("sc_title", geo(40, 32, 800, 28), "Kryden Layout: components v0", 18, fg),
        # 6 buttons of 128 + 5 x 12 = 828 <= 1000 (slack, lab round 3)
        W("WrapSpacer", "sc_buttons", [("visible", 1)] + geo(40, 80, 1000, 32) + [("Padding", 12), ("Margin", 0)]),
        # 4 badges of 80 + 3 x 8 = 344 <= 600
        W("WrapSpacer", "sc_badges", [("visible", 1)] + geo(40, 132, 600, 24) + [("Padding", 8), ("Margin", 0)]),
        # 2 cards of 400 + 24 = 824 <= 1000
        W("WrapSpacer", "sc_cards", [("visible", 1)] + geo(40, 180, 1000, 220) + [("Padding", 24), ("Margin", 0)]),
        W("Frame", "sc_sep", [("visible", 1), ("ignorepointer", 1)] + geo(40, 424, 824, 1)),
        text("sc_status", geo(40, 440, 824, 24), "Click a button", 16, muted),
        text("cmp_title", geo(40, 488, 1100, 24), "Primary comparison: button (text 16) and badge (text 14)", 16, fg),
    ]
    k += primary_compare(fg, muted)
    return root("kld_lab_08_root", k)


# Round 7: candidates for primary, static (no hover), in the prefab geometry (button 128x32,
# badge 80x24, radius 10). Dark text on a light background comes out thin in DayZ (edge smoothed in
# linear space, round 6); light text on a dark background keeps its weight. Colors from the Tailwind v4
# palette (tailwindcss.com/docs/colors), the same one shadcn uses. Chosen: shadcn bold (D-12). Colors are
# fixed here (not TOKENS) so the row keeps showing the old yellow after D-12.
_FG = TOKENS["foreground"]
YELLOW_500 = oklch_to_srgb(0.795, 0.184, 86.047)   # primary before D-12 = (240,177,0)
D11_FG = (26, 18, 6)                               # #1A1206, D-11 (superseded by D-12)
CANDIDATES = [
    # id,         caption,            background,                        text,                     button / badge font
    ("atual",     "yellow D-11",      YELLOW_500,                        D11_FG,                   None),     # primary before D-12
    ("preto",     "yellow + black",   YELLOW_500,                        (0, 0, 0),                None),
    ("preto_b",   "black bold",       YELLOW_500,                        (0, 0, 0),                ("MetronBook-Bold16", "MetronBook-Bold14")),
    ("shadcn",    "shadcn regular",   oklch_to_srgb(0.922, 0, 0),        oklch_to_srgb(0.205, 0, 0), None),     # shadcn neutral .dark: primary / primary-foreground
    ("shadcn_b",  "shadcn bold",      oklch_to_srgb(0.922, 0, 0),        oklch_to_srgb(0.205, 0, 0), ("MetronBook-Bold16", "MetronBook-Bold14")),  # bitmap, vanilla has no bold SDF
    ("yellow700", "yellow 700",       oklch_to_srgb(0.554, 0.135, 66.442), _FG,                    None),     # yellow-700
    ("amber700",  "amber 700",        oklch_to_srgb(0.555, 0.163, 48.998), _FG,                    None),     # amber-700
    ("neutral600", "neutral 600",     oklch_to_srgb(0.439, 0, 0),        _FG,                      None),     # neutral-600 (monochrome)
]


def primary_compare(fg, muted):
    k = []
    for i, (cid, caption, bg, txt, bold) in enumerate(CANDIDATES):
        x = 40 + i * 152          # 128 + 24 gap
        btn_font = f"gui/fonts/{bold[0]}" if bold else BOOK
        badge_font = f"gui/fonts/{bold[1]}" if bold else BOOK
        k.append(text(f"cmp_{cid}_caption", geo(x, 520, 140, 20), caption, 14, muted))
        k.append(panel(f"cmp_{cid}_btn", layout_color(bg), geo(x, 544, 128, 32), style="kld_fill_r10", children=[
            text(f"cmp_{cid}_btn_label", geo(0, 0, 1, 1, 0, 0, 0, 0), "Confirm", 16, layout_color(txt), btn_font, halign="center")]))
        k.append(panel(f"cmp_{cid}_badge", layout_color(bg), geo(x, 588, 80, 24), style="kld_fill_r10", children=[
            text(f"cmp_{cid}_badge_label", geo(0, 0, 1, 1, 0, 0, 0, 0), "New", 14, layout_color(txt), badge_font, halign="center")]))
    return k


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for fname, fn in [
        ("kld_lab_02_anchors.layout", lab02),
        ("kld_lab_03_spacers.layout", lab03),
        ("kld_lab_04_layers.layout", lab04),
        ("kld_lab_05_nineslice.layout", lab05),
        ("kld_lab_06_fonts.layout", lab06),
        ("kld_lab_07_atlas.layout", lab07),
        ("kld_lab_08_components.layout", lab08),
    ]:
        (OUT / fname).write_text(fn(), encoding="utf-8", newline="\n")
        print("ok", OUT / fname)


if __name__ == "__main__":
    main()
