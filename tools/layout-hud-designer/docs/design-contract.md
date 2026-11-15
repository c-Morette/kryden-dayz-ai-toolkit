# Design contract (v0, work in progress)

What a screen design may use so it can be built in DayZ without loss. Tags on each rule:

- **[measured]** measured in-game with the lab (`lab/README.md`), 16:9 at 1280x720, 1600x900 and 1920x1080.
- **[source]** read in vanilla files (`P:\scripts`, `P:\gui`) or public docs.
- **[decision]** a choice recorded in the decision log at the end.
- **[open]** not confirmed; needs a test.

## 1. Canvas and unit

- Artboard **1920x1080**. 1 design unit = 1 px at 1080p. The engine scales linearly in 16:9:
  x2/3 at 720p, x0.833 at 900p **[measured]**. Write positions and sizes in px with
  `hexactpos/vexactpos/hexactsize/vexactsize 1`.
- Non-16:9 screens: whether X scales by W/1920 or H/1080 is **[open]**. Anchor to edges with the
  `_ref` alignments and do not depend on the full screen width.
- 4 px grid. Spacing only from `4 8 12 16 20 24 32 40 48 64`.

## 2. Color

Dark theme (UI on top of the 3D scene), shadcn/ui based, with the monochrome shadcn primary (D-12).
Layouts use the floats in `color`; scripts use `ARGB(a, r, g, b)` or the `KLD_Tokens` constants.

| token | use | `color` (layout) | `ARGB` (script) |
|---|---|---|---|
| background | screen/page background | `0.0394 0.0394 0.0394 1` | `ARGB(255, 10, 10, 10)` |
| foreground | main text | `0.9803 0.9803 0.9803 1` | `ARGB(255, 250, 250, 250)` |
| card / popover | surfaces | `0.0905 0.0905 0.0905 1` | `ARGB(255, 23, 23, 23)` |
| primary | action fill (shadcn neutral `.dark`, `oklch(0.922 0 0)`) | `0.8980 0.8980 0.8980 1` | `ARGB(255, 229, 229, 229)` |
| primary-foreground | text on primary, **bold** (`oklch(0.205 0 0)`) | `0.0902 0.0902 0.0902 1` | `ARGB(255, 23, 23, 23)` |
| secondary | secondary button | `0.1529 0.1529 0.1658 1` | `ARGB(255, 39, 39, 42)` |
| muted / accent | hover, subtle background | `0.1494 0.1494 0.1494 1` | `ARGB(255, 38, 38, 38)` |
| muted-foreground | secondary text | `0.6302 0.6302 0.6302 1` | `ARGB(255, 161, 161, 161)` |
| destructive | destructive action | `1 0.3912 0.4039 1` | `ARGB(255, 255, 100, 103)` |
| ring | focus | `0.4515 0.4515 0.4515 1` | `ARGB(255, 115, 115, 115)` |
| border over background | divider/outline | `0.1333 0.1333 0.1333 1` | `ARGB(255, 34, 34, 34)` |
| border over card | card outline | `0.1804 0.1804 0.1804 1` | `ARGB(255, 46, 46, 46)` |
| input over background | field outline | `0.1843 0.1843 0.1843 1` | `ARGB(255, 47, 47, 47)` |
| input over card | field outline | `0.2275 0.2275 0.2275 1` | `ARGB(255, 58, 58, 58)` |

- On the web `border` / `input` are white at 10% / 15%. In DayZ they are **solid colors pre-mixed**
  per surface (table above), because DayZ blends transparency in **linear space**: black 50% over
  amber gave (176,129,0); sRGB blending would give (120,88,0) **[measured]**.
- Never bake color into a texture: white texture + `color` / `SetColor`. With a white texture the
  token comes out exact in a screenshot **[measured]**.
- `primary` only as a fill, never as text or border; one primary action per region **[decision]**.
- **Dark text on a light background gets thin in DayZ**, whatever the text color: the glyph edge is
  blended in linear space. With the regular SDF font every dark-on-light pair measured gave the same
  mean glyph contrast (2.6 to 2.8 at 1080p; 2.4 to 2.5 at 720p). Light text on a dark background does
  not suffer from this **[measured]**. That is why the label on primary is bold (D-12).
- Surfaces are opaque by default. Translucency only with an alpha recomputed for linear blending
  (the web's 50% becomes another value) **[measured]**.

## 3. Radius and border

- Nine-slice corners and borders are drawn in **physical pixels**: the vanilla `Outline` style is
  2 px at 720p, 900p and 1080p **[measured]**. The radius is the same in px at any resolution (at
  720p it looks about 1.5x bigger relative to the rest).
- Allowed radii: **0, 6, 10 px** **[decision D-06]**. Each radius is one set of textures.
- 1 px border.
- Minimum size of any nine-slice piece = 2r + 4 (24 px for r10, 16 px for r6). Below that the corners
  overlap and the shape breaks **[measured]**.
- A surface with a border = **two layers**: a rounded fill (tinted with the surface color) and a
  rounded 1 px ring on top (tinted with the border color). The one with higher `priority` draws on
  top; on a tie, the one declared later **[measured]**.
- Vanilla panel styles (`DayZDefaultPanel*`, `UIDefaultPanel`) have an irregular "torn paper" edge
  **[measured]**: do not use them for a clean look. Use the own atlas (section 8).
- No shadow, no gradient (not native in DayZ) **[source]**.

## 4. Typography

- **SDF fonts only**: `gui/fonts/sdf_MetronBook24` (regular/medium) and `gui/fonts/sdf_MetronLight24`
  (light), always with `"exact text" 1` + `"exact text size"` **[measured]** (SDF stays sharp from 16
  to 48; a scaled bitmap font blurs). Portuguese diacritics render in all of them **[measured]**.
- Custom fonts (for example Inter) are not in v0: a custom font needs a `.fnt` generated from the
  `.ttf`, and the tool for that was not identified **[open]**. Metron replaces Inter; the metrics differ.
- Do not upload or redistribute the game's font files.
- Scale **[decision D-07]**: title 18, body 16, caption 14 (the web +2). At 720p a 12 becomes 8 px;
  with +2 the smallest text is about 9.3 px at 720p. Text also scales by 2/3 **[measured]**.
- Without `"exact text"` the text follows the widget height **[measured]**: always declare it.
- **Text color:** on `TextWidget` it is the `color` attribute; `"text color"` is ignored
  **[measured]**. On `ButtonWidget` it is `"text color"` **[measured]**. `ButtonWidget` does not accept
  `"exact text size"` (only `text_proportion`): a label with an exact size = child `TextWidget`.
- **Bold (D-12):** vanilla has no bold SDF. A label on a light background (primary) uses the bitmap
  `gui/fonts/MetronBook-Bold16` (button) / `MetronBook-Bold14` (badge): mean glyph contrast 7.7 at
  1080p and 4.9 at 720p, against 2.8 / 2.5 for SDF Book; the glyphs come out about 10% smaller
  **[measured]**. At 1440p/4K the bitmap is scaled up and may blur **[open]**. `TextWidget.SetBold`
  and the `"bold text"` attribute on SDF were not tested **[open]**.

## 5. Spacing and layout

- Density: control height 32 px (Button/Input), menu item 32, header 40, content padding 24, card
  inner spacing 16.
- Anchoring: always `halign/valign` with `_ref`; `position` is the offset inward from the anchored
  edge (from the center for `center_ref`) **[measured]**. Without `_ref` the widget goes outside
  (y = -h).
- Grid: `GridSpacerWidget` with **`Padding` = gap and `Margin` = inner padding** (the inverse of CSS).
  Cell = (size - 2*Margin - (n-1)*Padding) / n; the child is stretched to the column width;
  `"Size To Content V" 1` shrinks the height to the content **[measured]**.
- Wrapping list: `WrapSpacerWidget`, same Padding/Margin, with **at least 1 px of slack** in the sum
  of the items (at 720p, items filling the exact width wrapped differently) **[measured]**.
- Layout-declared widgets are positioned right after `CreateWidgets`, without `Update()`. Children
  created from script read (0,0,0,0) in the same frame and are laid out on the next one **[measured]**.
- `.layout` files with LF line endings work **[measured]**.

## 6. States and interaction

- A white texture does not change color per style state: hover, pressed, disabled and focus are a
  `SetColor` swap in script, as the vanilla main menu does (`OnMouseEnter` -> `ColorHighlight` ->
  `SetColor`, `P:\scripts\5_mission\gui\newui\mainmenu\mainmenu.c:275-298,611-675`) **[source]**.
  `KLD_Theme` applies the token color per state **[decision D-10]**.
- Focus: a separate ring (outline nine-slice, `ring` color) is planned, not built.
- A button with the `Colorable` style tinted works and its text shows **[measured]**; with
  `DayZDefaultButton` tinted white the text disappears **[measured]**.
- The alpha of a `ButtonWidget`'s `color` multiplies its own text: a ghost button with `color 0 0 0 0`
  loses its label **[measured]**. Ghost button = label in a child `TextWidget`.

## 7. Icons and images

- Planned: Lucide icons (ISC) rasterized into a white atlas and tinted; 16 px in controls. Not built.
- `ImageWidget` from an imageset: `mode additive` + `"src alpha" 1` draws; `mode blend` without
  `"src alpha"` gave a white box **[measured]** (which of the two fixes it: **[open]**). `fixaspect`
  had no effect with an imageset `image0` **[measured]**.

## 8. Texture pipeline (own atlas)

`tools/gen_atlas.py` does all of this:

1. White PNG, only alpha varies, power-of-2 sides.
2. `DayZ Tools\Bin\ImageToPAA\ImageToPAA.exe atlas.png atlas.paa`. Without a suffix and with alpha it
   comes out DXT5. **Do not use the `_8888` suffix**: it produces ARGB1555 (1-bit alpha) and destroys
   the corner anti-aliasing **[source]**.
3. `.imageset` with the 9 pieces per radius (corner r x r, edges 4 wide, center 4x4).
4. `.styles`: `<WidgetStyles><Widget Name="PanelWidget"><Style ...><State Name="Normal">` + 9 `<Item>`;
   the style's `ImageSet` is the imageset's internal `Name` **[source]**.
5. `config.cpp` -> `CfgMods > defs > imageSets / widgetStyles` **[source]**.

Confirmed **[measured]**: a `.paa` without GUID inside an imageset renders; a single texture with
`mpix 1` and `RefSize` = texture size works; registration through `imageSets` / `widgetStyles` works;
a transparent center piece shows what is underneath. **[open]**: corners above 1080p; when the engine
uses an `@2x` texture.

## 9. What a design may NOT use

Shadow, gradient, blur/backdrop, a radius outside {0, 6, 10}, a rounded piece smaller than 2r+4, a
border other than 1 px, a font other than Metron Book/Light (exception: the bold bitmap label on
primary, D-12), text without a fixed size, a color outside the table in section 2, translucency (until
measured), a width that depends on a non-16:9 screen, list items filling the exact width, relative
units (rem, %, vw). Everything in px of 1920x1080 on the 4 px grid.

## 10. From a design tool to the game

- There is no importer from HTML / Figma / design tools to `.layout`.
- Source of truth = the tokens and components in this folder, written by the generators. A design
  tool can compose and approve screens using only what this contract allows; the approved screen is
  translated through the generator, not imported **[decision D-09]**.
- Idea, nothing tested: an exporter that renders a restricted HTML in a browser and reads the
  rectangles (`getBoundingClientRect`) to write the `.layout`.

## 11. Component roadmap

1. Surface/Card · 2. Button (primary, secondary, outline, ghost, destructive; 32 px) · 3. Badge (r10
at height 24; the web badge is a pill) · 4. Separator · 5. Text (title/body/caption) · 6. Input
(`EditBoxWidget`, not tested in the lab) · 7. Dialog.

1 to 4 exist (`docs/components.md`). 5 to 7 do not.

## Decision log

A recorded decision is not reopened silently: a change gets a new entry and the old one is marked
superseded.

| id | date | decision |
|---|---|---|
| D-01 | 2026-10-03 | One folder per mod with `<Mod>_Client/` inside. The PBO prefix equals the folder path from the `P:` root (`Kryden\KrydenLayoutHudDesigner\KrydenLayoutHudDesigner_Client`) and every path in `config.cpp` uses it, so packers, file patching and Workbench find the files without junctions. Precedent: Community Framework (`JM\CF\Scripts`). The mod name is in the folder name so tools that name the PBO after the folder do not produce a colliding `Client.pbo`. |
| D-02 | 2026-10-03 | `type = "mod"`. `servermod` breaks a client that loads the PBO. |
| D-03 | 2026-10-03 | Names: PBO `KrydenLayoutHudDesigner_Client.pbo`, distribution folder `@KrydenLayoutHudDesigner`, `CfgPatches` / `CfgMods` class `KrydenLayoutHudDesigner_Client`. |
| D-04 | 2026-10-03 | Build with a prefix lock: `build.ps1` passes `-@=<prefix>` explicitly, checks `$PBOPREFIX$` before and reads the built PBO (`ExtractPbo -P -L`) after; a different prefix aborts. A wrong prefix loads zero files without a log line. |
| D-05 | 2026-10-04 | Use the dark theme of the author's shadcn/ui-based web design system. Tokens with transparency become solid colors pre-mixed per surface. |
| D-06 | 2026-10-04 | Only radii 0, 6 and 10 px; the Card uses 10 (14 on the web) to save texture sets. Nine-slice corners are physical pixels, so the radius is the same in px at any resolution. |
| D-07 | 2026-10-04 | Text scale 18 / 16 / 14 (the web +2) in 1920x1080 units, because at 720p the web's 12 would be 8 px. |
| D-08 | 2026-10-04 | Metron SDF (`sdf_MetronBook24`, `sdf_MetronLight24`) instead of Inter in v0, always with `"exact text"`. Inter only once a tool to generate `.fnt` is confirmed. |
| D-09 | 2026-10-04 | Tokens and components are generated by script in this folder. Design tools compose and approve inside this contract; the approved screen is translated by the generator, not imported. |
| D-10 | 2026-10-04 | Textures are white; hover, pressed, disabled and focus swap `SetColor` from script through a theme helper (`KLD_Theme`), like the vanilla menu. |
| D-11 | 2026-10-04 | ~~Text on the (yellow) primary uses the near-black `#1A1206` instead of brown.~~ Superseded by D-12. |
| D-12 | 2026-10-04 | Monochrome shadcn primary with a bold label: primary = `oklch(0.922 0 0)` (229,229,229), primary-foreground = `oklch(0.205 0 0)` (23,23,23), label in `MetronBook-Bold16` / `MetronBook-Bold14` (bitmap) in its own prefab (`kld_button_primary.layout`, `kld_badge_primary.layout`), because `TextWidget` cannot change font from script. Measured (lab rounds 6 and 7): bold shadcn gives a mean glyph contrast of 7.7 / 4.9 (1080p / 720p) against 2.6 to 2.8 / 2.4 to 2.5 for every regular-weight dark-on-light option. Open risk: the bitmap scaled up at 1440p/4K may blur (not measured); fallback = neutral 600 fill with light text (5.3 / 5.1). |
