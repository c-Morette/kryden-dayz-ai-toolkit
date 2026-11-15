"""Generates the own nine-slice atlas (validated in lab round 4; docs/design-contract.md section 8).

Outputs:
  build/atlas/kld_ui_atlas.png                                   source (outside the PBO, build/ is git-ignored)
  KrydenLayoutHudDesigner_Client/gui/textures/kld_ui_atlas.paa   ImageToPAA (DXT5, no suffix)
  KrydenLayoutHudDesigner_Client/gui/imagesets/kld_ui.imageset
  KrydenLayoutHudDesigner_Client/gui/looknfeel/kld_ui.styles
  build/atlas/kld_ui_atlas_roundtrip.png + max alpha error       PAA -> PNG check

Requirements: Python 3 with Pillow, and DayZ Tools (ImageToPAA) installed through Steam.

Rules that come from measurement/source:
  - WHITE texture, only alpha varies; color comes in through `color`/SetColor (D-05, design contract section 2)
  - corners are drawn in physical pixels (lab rounds 1-3) -> corner piece = radius in px
  - power of 2 (ImageToPAA refuses other sizes); do NOT use the _8888 suffix (ARGB1555, 1-bit alpha)
  - single texture with mpix 1 and RefSize = texture size; vanilla uses mpix 0 (1x) + mpix 1 (@2x) as a pair
  - radii 6 and 10 (D-06); 1 px border

    python tools/gen_atlas.py
"""
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CLIENT = ROOT / "KrydenLayoutHudDesigner_Client"
OUT = ROOT / "build" / "atlas"
PREFIX = "Kryden/KrydenLayoutHudDesigner/KrydenLayoutHudDesigner_Client"
IMAGE_TO_PAA = Path(r"C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools\Bin\ImageToPAA\ImageToPAA.exe")

ATLAS = 64          # texture side (power of 2)
EDGE = 4            # width of the edge piece and of the center
SS = 16             # supersampling per axis for corner anti-aliasing
IMAGESET_NAME = "kld_ui"

# (name, radius, kind, x, y) - blocks aligned on multiples of 4 and separated by >= 8 transparent px
BLOCKS = [
    ("fill_r10", 10, "fill", 0, 0),
    ("ring_r10", 10, "ring", 32, 0),
    ("fill_r6", 6, "fill", 0, 32),
    ("ring_r6", 6, "ring", 32, 32),
]
PIECES = ["LeftTop", "Top", "RightTop", "Left", "Center", "Right", "LeftBottom", "Bottom", "RightBottom"]


def inside_rrect(x, y, x0, y0, x1, y1, r):
    if x < x0 or x > x1 or y < y0 or y > y1:
        return False
    cx = min(max(x, x0 + r), x1 - r)
    cy = min(max(y, y0 + r), y1 - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def coverage(px, py, x0, y0, x1, y1, r):
    hit = 0
    for i in range(SS):
        for j in range(SS):
            if inside_rrect(px + (i + 0.5) / SS, py + (j + 0.5) / SS, x0, y0, x1, y1, r):
                hit += 1
    return hit / (SS * SS)


def block_alpha(size, r, kind):
    rows = []
    for py in range(size):
        row = []
        for px in range(size):
            outer = coverage(px, py, 0, 0, size, size, r)
            if kind == "ring":
                inner = coverage(px, py, 1, 1, size - 1, size - 1, r - 1)
                a = max(0.0, outer - inner)
            else:
                a = outer
            row.append(round(a * 255))
        rows.append(row)
    return rows


def pieces(r, bx, by):
    """Pos/Size of the 9 pieces in RefSize space: corner r x r, edges EDGE, center EDGE x EDGE."""
    c = [bx, bx + r, bx + r + EDGE]
    rr = [by, by + r, by + r + EDGE]
    w = [r, EDGE, r]
    h = [r, EDGE, r]
    out = {}
    for row in range(3):
        for col in range(3):
            out[PIECES[row * 3 + col]] = (c[col], rr[row], w[col], h[row])
    return out


def build_png():
    img = Image.new("RGBA", (ATLAS, ATLAS), (255, 255, 255, 0))
    for name, r, kind, bx, by in BLOCKS:
        size = 2 * r + EDGE
        for py, row in enumerate(block_alpha(size, r, kind)):
            for px, a in enumerate(row):
                img.putpixel((bx + px, by + py), (255, 255, 255, a))
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "kld_ui_atlas.png"
    img.save(path)
    return path, img


def to_paa(png):
    paa = CLIENT / "gui" / "textures" / "kld_ui_atlas.paa"
    paa.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(IMAGE_TO_PAA), str(png), str(paa)], check=True)
    if not paa.exists():
        raise SystemExit(f"ImageToPAA did not produce {paa}")
    return paa


def roundtrip_error(paa, src):
    back = OUT / "kld_ui_atlas_roundtrip.png"
    subprocess.run([str(IMAGE_TO_PAA), str(paa), str(back)], check=True)
    got = Image.open(back).convert("RGBA")
    worst = 0
    for y in range(ATLAS):
        for x in range(ATLAS):
            worst = max(worst, abs(got.getpixel((x, y))[3] - src.getpixel((x, y))[3]))
    return worst


def write_imageset():
    lines = [
        "ImageSetClass {",
        f' Name "{IMAGESET_NAME}"',
        f" RefSize {ATLAS} {ATLAS}",
        " Textures {",
        "  ImageSetTextureClass {",
        "   mpix 1",
        f'   path "{PREFIX}/gui/textures/kld_ui_atlas.paa"',
        "  }",
        " }",
        " Images {",
    ]
    for name, r, kind, bx, by in BLOCKS:
        for piece, (x, y, w, h) in pieces(r, bx, by).items():
            img = f"kld_{name}_{piece}"
            lines += [
                f"  ImageSetDefClass {img} {{",
                f'   Name "{img}"',
                f"   Pos {x} {y}",
                f"   Size {w} {h}",
                "   Flags 0",
                "  }",
            ]
    lines += [" }", " Groups {", " }", "}", ""]
    path = CLIENT / "gui" / "imagesets" / "kld_ui.imageset"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path


def style_xml(style_name, block, states, font=""):
    out = [f'        <Style Name="{style_name}" Font="{font}" ImageSet="{IMAGESET_NAME}" Color="4294967295">']
    for state in states:
        out.append(f'            <State Name="{state}">')
        for piece in PIECES:
            out.append(f'                <Item Name="{piece}" Image="kld_{block}_{piece}" />')
        out.append("            </State>")
    out.append("        </Style>")
    return out


def write_styles():
    panel_states = ["Normal", "Disabled"]                                     # like rover_sim_colorable
    button_states = ["Normal", "Highlight", "Pushed", "Disabled", "Focus"]   # like Colorable (Button)
    lines = ["<WidgetStyles>", '    <Widget Name="PanelWidget">']
    for name, *_ in BLOCKS:
        lines += style_xml(f"kld_{name}", name, panel_states)
    lines += ["    </Widget>", '    <Widget Name="ButtonWidget">']
    for name, *_ in BLOCKS:
        lines += style_xml(f"kld_btn_{name}", name, button_states, "gui/fonts/sdf_MetronBook24")
    lines += ["    </Widget>", "</WidgetStyles>", ""]
    path = CLIENT / "gui" / "looknfeel" / "kld_ui.styles"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path


def main():
    png, img = build_png()
    paa = to_paa(png)
    err = roundtrip_error(paa, img)
    print("png       ", png)
    print("paa       ", paa, paa.stat().st_size, "bytes")
    print("roundtrip  max alpha error", err, "/ 255")
    print("imageset  ", write_imageset())
    print("styles    ", write_styles())


if __name__ == "__main__":
    main()
