"""Checks .layout files against what exists in vanilla (P:\\gui, the extracted game data).

Catches: an attribute that never appears in vanilla (or never on that widget class), an enum value
that does not exist (halign, valign, fixaspect, mode, content_halign, "text halign/valign"), a style
that does not exist for that class in dayzwidgets.styles or in this mod's .styles, a font with no
file in P:\\gui\\fonts, and unbalanced braces. Passing here does NOT prove it renders: only that
nothing was invented.

    python lab/validate_layout.py "KrydenLayoutHudDesigner_Client/gui/layouts/kld/*.layout"
"""
import collections
import glob
import re
import sys

VANILLA_LAYOUTS = "P:/gui/layouts/**/*.layout"
VANILLA_STYLES = "P:/gui/looknfeel/dayzwidgets.styles"
VANILLA_FONTS = "P:/gui/fonts/"
# the mod's own styles (tools/gen_atlas.py) count as existing
MOD_STYLES = str(__import__("pathlib").Path(__file__).resolve().parent.parent / "KrydenLayoutHudDesigner_Client" / "gui" / "looknfeel" / "*.styles")
ENUM_KEYS = {"halign", "valign", "fixaspect", "mode", "content_halign", '"text valign"', '"text halign"'}


def parse(path):
    out, stack = [], []
    for raw in open(path, encoding="utf-8", errors="replace"):
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^(\w+)WidgetClass\s", line) or re.match(r"^(\w+)Class\s", line)
        if m and line.endswith("{"):
            stack.append(m.group(1))
            continue
        if line == "{":
            stack.append(None)
            continue
        if line == "}":
            if not stack:
                return out, -1
            stack.pop()
            continue
        kv = re.match(r'^("[^"]+"|\S+)\s+(.*)$', line)
        if kv:
            owner = next((s for s in reversed(stack) if s), None)
            out.append((owner, kv.group(1), kv.group(2)))
    return out, len(stack)


def load_vanilla():
    keys_by_class = collections.defaultdict(set)
    values = collections.defaultdict(set)
    for f in glob.glob(VANILLA_LAYOUTS, recursive=True):
        for cls, k, v in parse(f)[0]:
            keys_by_class[cls].add(k)
            values[k].add(v)
    styles = {}
    for styles_file in [VANILLA_STYLES] + glob.glob(MOD_STYLES):
        cur = None
        text = open(styles_file, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r'<Widget\s+Name="([^"]+)"|<Style\s+Name="([^"]+)"', text):
            if m.group(1):
                cur = m.group(1).replace("Widget", "")
                styles.setdefault(cur, set())
            else:
                styles[cur].add(m.group(2))
    return keys_by_class, values, styles


def check(path, keys_by_class, values, styles):
    attrs, depth = parse(path)
    problems = set()
    if depth != 0:
        problems.add(f"unbalanced braces ({depth})")
    all_keys = set().union(*keys_by_class.values())
    for cls, k, v in attrs:
        if k not in all_keys:
            problems.add(f"attribute {k} never appears in vanilla")
        elif k not in keys_by_class.get(cls, set()):
            problems.add(f"attribute {k} never appears on {cls} in vanilla")
        if k in ENUM_KEYS and v not in values[k]:
            problems.add(f"value {k} {v} never appears in vanilla")
        if k == "style" and v not in styles.get(cls, set()):
            problems.add(f"style {v} does not exist for {cls}")
        if k == "font":
            name = v.strip('"').split("/")[-1].lower()
            if not glob.glob(VANILLA_FONTS + name + "*"):
                problems.add(f"font {v} has no file in {VANILLA_FONTS}")
    return sorted(problems)


def main(argv):
    files = [f for pattern in argv for f in glob.glob(pattern)]
    if not files:
        print(__doc__)
        return 2
    vanilla = load_vanilla()
    failed = 0
    for f in files:
        problems = check(f, *vanilla)
        print(f"{'OK  ' if not problems else 'FAIL'} {f}")
        for p in problems:
            print(f"     - {p}")
        failed += bool(problems)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
