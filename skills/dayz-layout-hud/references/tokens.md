# Design tokens (v0, work in progress)

Source of truth: `tools/kld_tokens.py` in the tool folder (see SKILL.md for the path); generated into
`KLD_Tokens.c`. Full contract: `docs/design-contract.md` in the tool folder.

## Unit and grid

- Artboard 1920x1080; 1 unit = 1 px at 1080p, scaled linearly in 16:9.
- 4 px grid. Spacing only `4 8 12 16 20 24 32 40 48 64`.
- Control height 32 (button, input), menu item 32, header 40, content padding 24, card inner spacing 16.

## Color (dark theme, shadcn/ui based)

| token | `color` (layout) | script constant |
|---|---|---|
| background | `0.0394 0.0394 0.0394 1` | `KLD_Tokens.BACKGROUND` |
| foreground | `0.9803 0.9803 0.9803 1` | `KLD_Tokens.FOREGROUND` |
| card | `0.0905 0.0905 0.0905 1` | `KLD_Tokens.CARD` |
| primary (fill only) | `0.8980 0.8980 0.8980 1` | `KLD_Tokens.PRIMARY` |
| primary-foreground (bold label) | `0.0902 0.0902 0.0902 1` | `KLD_Tokens.PRIMARY_FOREGROUND` |
| secondary | `0.1529 0.1529 0.1658 1` | `KLD_Tokens.SECONDARY` |
| muted / accent | `0.1494 0.1494 0.1494 1` | `KLD_Tokens.MUTED` |
| muted-foreground | `0.6302 0.6302 0.6302 1` | `KLD_Tokens.MUTED_FOREGROUND` |
| destructive | `1 0.3912 0.4039 1` | `KLD_Tokens.DESTRUCTIVE` |
| ring | `0.4515 0.4515 0.4515 1` | `KLD_Tokens.RING` |
| border over background | `0.1333 0.1333 0.1333 1` | `KLD_Tokens.BORDER` |
| border over card | `0.1804 0.1804 0.1804 1` | (layout only) |
| input over background | `0.1843 0.1843 0.1843 1` | `KLD_Tokens.INPUT` |
| input over card | `0.2275 0.2275 0.2275 1` | (layout only) |

Button and badge per-variant colors (normal, hover, disabled, border) are `KLD_Tokens.BTN_*` and
`KLD_Tokens.BADGE_*`, applied by `KLD_Theme`. All are solid colors pre-mixed over `background`.

Rules: one primary action per region; primary never as text or border; surfaces opaque; no color
baked into textures.

## Radius, border, surfaces

- Radii 0, 6, 10 only. Styles: `kld_fill_r10`, `kld_ring_r10`, `kld_fill_r6`, `kld_ring_r6`
  (PanelWidget) and `kld_btn_fill_r10`, `kld_btn_ring_r10`, `kld_btn_fill_r6`, `kld_btn_ring_r6`
  (ButtonWidget).
- 1 px border. Minimum rounded piece 2r + 4 (24 for r10, 16 for r6).
- Surface with border = fill panel (`kld_fill_r10`, surface color) + ring panel on top (`kld_ring_r10`,
  border color), declared later or with higher `priority`.

## Type

- Fonts: `gui/fonts/sdf_MetronBook24` (regular), `gui/fonts/sdf_MetronLight24` (light); always
  `"exact text" 1` + `"exact text size"`. Bold label on primary: `gui/fonts/MetronBook-Bold16` (button)
  / `MetronBook-Bold14` (badge), bitmap.
- Scale: title 18, body 16, caption 14.

## A design may NOT use

Shadow, gradient, blur, radius outside {0, 6, 10}, rounded piece smaller than 2r+4, border other than
1 px, fonts other than Metron Book/Light (plus the bold primary label), text without a fixed size,
colors outside the table, translucency, widths that depend on a non-16:9 screen, list items filling
the exact width, relative units (rem, %, vw).
