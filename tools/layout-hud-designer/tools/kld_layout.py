"""Writer for DayZ .layout files (format of P:\\gui\\layouts: `XxxWidgetClass name { attribute value }`,
no comments allowed). Used by tools/gen_components.py and lab/gen_lab_layouts.py.

Output: UTF-8 without BOM, LF - works in-game (lab rounds 1-4); vanilla stores text as UTF-8
(P:\\gui\\layouts\\gameplay\\rangefinder_hud_2.layout:186).
"""


def node(cls, name, attrs, children=None, depth=0):
    pad = " " * depth
    q = f'"{name}"' if " " in name else name
    lines = [f"{pad}{cls}WidgetClass {q} {{"]
    for k, v in attrs:
        key = f'"{k}"' if " " in k else k
        lines.append(f"{pad} {key} {v}")
    if children:
        lines.append(f"{pad} {{")
        for c in children:
            lines.append(c(depth + 2))
        lines.append(f"{pad} }}")
    lines.append(f"{pad}}}")
    return "\n".join(lines)


def W(cls, name, attrs, children=None):
    return lambda depth: node(cls, name, attrs, children, depth)


def geo(x, y, w, h, hpos=1, vpos=1, hsize=1, vsize=1):
    """Position/size; 1 = 1920x1080 reference unit that the engine scales (lab rounds 1-3), 0 = fraction of the parent."""
    return [
        ("position", f"{x} {y}"),
        ("size", f"{w} {h}"),
        ("hexactpos", hpos),
        ("vexactpos", vpos),
        ("hexactsize", hsize),
        ("vexactsize", vsize),
    ]


def panel(name, rgba, g, extra=None, style="rover_sim_colorable", children=None):
    attrs = [("visible", 1), ("ignorepointer", 1), ("color", rgba)] + g + (extra or []) + [("style", style)]
    return W("Panel", name, attrs, children)


def text(name, g, txt, size, rgba, font="gui/fonts/sdf_MetronBook24", halign=None, extra=None):
    """TextWidget: the text color is the `color` attribute - `"text color"` is ignored on TextWidget
    (lab round 4). Size is always exact (D-07/D-08)."""
    attrs = [("visible", 1), ("ignorepointer", 1), ("color", rgba)] + g + [
        ("text", f'"{txt}"'), ("font", f'"{font}"'),
        ("exact text", 1), ("exact text size", size), ("text valign", "center"),
    ]
    if halign:
        attrs.append(("text halign", halign))
    return W("Text", name, attrs + (extra or []))


def write(path, root_node):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(root_node + "\n", encoding="utf-8", newline="\n")
    return path
