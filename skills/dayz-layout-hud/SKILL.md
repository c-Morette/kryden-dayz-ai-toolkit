---
name: dayz-layout-hud
description: >-
  WORK IN PROGRESS. Build DayZ UI (menus, HUD panels, dialogs) with the Kryden Layout HUD Designer,
  a shadcn/ui-style design system in Enforce Script: color tokens, own nine-slice atlas with rounded
  corners, generated .layout prefabs and the KLD_Button / KLD_Badge / KLD_Card / KLD_Separator
  components, plus the widget rules that fail silently (TextWidget color, ButtonWidget alpha,
  Padding vs Margin, _ref anchors, exact units that are not pixels, linear alpha blending). Use when
  writing or reviewing a DayZ .layout, .styles or .imageset, a UIScriptedMenu, rounded corners or
  nine-slice, colors or fonts in DayZ UI, or when the user mentions shadcn for DayZ, KLD_, kld_ui,
  "Kryden Layout", GridSpacerWidget, WrapSpacerWidget, TextWidget, ButtonWidget or CreateWidgets.
---

# DayZ layout and HUD design system (work in progress)

**Status: work in progress, not finished.** Button, Badge, Card and Separator were tested in-game at
1280x720, 1600x900 and 1920x1080 (16:9). The bold primary variant (decision D-12), 1440p/4K,
non-16:9 screens and every component not listed here (Input, Dialog, Text, focus ring, icons) are
not tested or not built. Say so when you rely on them.

## Where the source is

The mod source, generators and full docs live in the toolkit at
`${CLAUDE_PLUGIN_ROOT}/tools/layout-hud-designer` (if that variable is not expanded, use
`../../tools/layout-hud-designer` relative to this skill folder). Below, `<tool>` means that folder.
Start with `<tool>/README.md`.

## Read before writing UI code

- [references/widget-rules.md](references/widget-rules.md): DayZ widget behavior that fails without a
  log line. Read it for ANY DayZ `.layout` or widget script, with or without this design system.
- [references/tokens.md](references/tokens.md): colors, radii, type scale, spacing, and what a design
  may not use.
- [references/components.md](references/components.md): the component API and the rules the caller
  must follow.

## How to work with it

1. **Reuse before you draw.** A screen is built from the components (`KLD_Button`, `KLD_Badge`,
   `KLD_Card`, `KLD_Separator`) and from `PanelWidget`s using the `kld_fill_r10 / kld_ring_r10 /
   kld_fill_r6 / kld_ring_r6` styles, tinted with token colors. The tested usage example is
   `<tool>/KrydenLayoutHudDesigner_Client/scripts/5_Mission/lab/KLD_LabShowcase.c`.
2. **Generated files are not edited by hand**: `scripts/3_Game/kld/KLD_Tokens.c`, `gui/layouts/kld/*`,
   `gui/imagesets/kld_ui.imageset`, `gui/looknfeel/kld_ui.styles`. Change `<tool>/tools/kld_tokens.py`
   or `<tool>/tools/gen_components.py` and run the generators (`<tool>/README.md`, "Regenerate").
3. **Write new layouts in 1920x1080 units** with `hexact*/vexact*` 1, on the 4 px grid, anchored with
   `_ref` alignments. To generate layouts from Python, reuse `<tool>/tools/kld_layout.py`
   (`node`, `W`, `geo`, `panel`, `text`).
4. **Validate** every `.layout` you write:
   `python <tool>/lab/validate_layout.py "<path>/*.layout"` (needs the extracted game data on `P:`).
   It rejects invented attributes, values, styles and fonts. Passing it does not prove it renders.
5. **When a rule is uncertain, measure it** with the lab (`<tool>/lab/README.md`) instead of guessing:
   it writes every widget rectangle to the client log.
6. **Report in two columns**: what compiles and loads (log without `SCRIPT (E)`) and what only an
   in-game look confirms (colors, corners, text weight, hover). A clean log is necessary, never
   sufficient.

## Using it inside another mod

- Preferred: load the PBO as its own mod and add `"KrydenLayoutHudDesigner_Client"` to your
  `requiredAddons[]`. Strip the lab (Insert key menu) before shipping to players.
- Copying it into another PBO means changing the prefix in every path and renaming the `KLD_*`
  classes, the `kld_ui` imageset and the `kld_*` styles to avoid collisions. Steps in `<tool>/README.md`.
- The PBO prefix must equal the paths in `config.cpp`, the imageset `path` and the script constants,
  or zero files load without a log line. Check with `ExtractPbo -P -L <pbo>`.
- `type = "mod"`, never `servermod`.
