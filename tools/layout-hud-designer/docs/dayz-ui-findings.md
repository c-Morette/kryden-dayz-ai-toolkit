# How DayZ lays out and draws widgets (findings, work in progress)

Research and in-game measurement done in October 2026 for this design system. Every item is tagged
**[source]** (read in the vanilla game data under `P:\scripts` / `P:\gui`, with file and line),
**[measured]** (measured with the lab, `lab/README.md`) or **[open]**. Line numbers refer to the game
version current at the time and may drift.

## 1. Format and geometry

- `.layout` is its own text format: `XxxWidgetClass Name { attribute value ... { children } }`. It does
  not accept comments **[source]**. `lab/validate_layout.py` builds the list of valid attributes and
  values from the vanilla layouts on your `P:`.
- **Pixel or proportional, axis by axis**: `hexactpos / vexactpos / hexactsize / vexactsize` 1 =
  "Uses physical resolution" (`P:\scripts\1_core\proto\enwidgets.c:66-71`); 0 = fraction of the
  parent (1.0 = the whole parent). Axes can be mixed **[source]**.
- **Despite that comment, the exact value is NOT physical pixels**: it is scaled from 1920x1080. At
  1600x900, 100 becomes 83.333; at 1280x720, 66.667. Linear in three 16:9 resolutions, for every widget.
  `GetPos` / `GetSize` return the already scaled value **[measured]**.
- `scaled 1` changed nothing on a PanelWidget rectangle **[measured]**.
- **Anchors only in the layout**: `halign left|center_ref|right_ref`, `valign top|center_ref|bottom_ref`.
  There is no anchor setter in script **[source]**. `position` is the offset inward from the anchored
  edge (from the center with `center_ref`); a proportional offset also counts from the anchored edge.
  Without `_ref` only the widget's pivot changes: `valign bottom` with `position 0` put the widget
  above the parent (y = -h). Always use `_ref` **[measured]**.
- **Layer order**: higher `priority` draws on top; on a tie the one declared later draws on top;
  `priority` only compares siblings (a child never escapes its parent). `GetChildren()` returns
  children already sorted by priority **[measured]**. In script: `SetSort / GetSort`
  (`enwidgets.c:129-130`) **[source]**.
- **Automatic containers**: `GridSpacerWidget` (`Columns` / `Rows`), `WrapSpacerWidget`,
  `SpacerWidget`, with `Padding` / `Margin`, `content_halign / valign`, `"Size To Content H/V"`. There
  is no `Spacing` and no column count attribute **[source]**.
- **`Padding` = space between cells; `Margin` = inner inset of the container** (the inverse of CSS).
  Cell = (size - 2*Margin - (n-1)*Padding) / n. GridSpacer stretches the child to the column width;
  `"Size To Content V"` shrinks the grid to its content. WrapSpacer keeps child sizes and wraps when
  the sum passes the width; `content_halign center` works **[measured]**.
- A WrapSpacer whose items fill the exact width wraps differently per resolution (rounding at 720p
  pushed the 4th item to a second line). Leave at least 1 unit of slack **[measured]**.
- Widgets declared in a `.layout` are positioned right after `CreateWidgets`, with no `Update()`.
  Children created from script read (0,0,0,0) in the same frame and are laid out on the next frame,
  still without `Update()` **[measured]**.

## 2. Visual

- **Nine-slice is native**: a `.styles` file is XML `<WidgetStyles>`; each style has states
  `Normal / Focus / Highlight / Pushed / Disabled`, each state with 9 `Item` (`LeftTop` ... `Center`)
  pointing at images of an imageset. Vanilla: `P:\gui\looknfeel\dayzwidgets.styles` **[source]**.
- **Valid styles depend on the widget type** (sections of the `.styles` file). For example
  `PanelWidget` accepts `rover_sim_colorable`, `ColorablePanel`, `DayZDefaultPanel`, `Outline`,
  `dashed`, `blank`; `ButtonWidget` accepts `Default`, `Colorable`, `Empty`, `DayZDefaultButton`;
  `ImageWidget` and `FrameWidget` have no style **[source]**.
- **A mod registers its own styles and imagesets** in `CfgMods > defs > widgetStyles / imageSets`
  (this mod's `config.cpp`) **[source]**, and it works **[measured]**.
- **Solid color**: `PanelWidget` with style `rover_sim_colorable` (or `Colorable` on spacers and
  buttons) + `color` **[source]**.
- **No style or font change at runtime** (no `SetStyle` / `SetFont`). A dynamic theme is only
  `SetColor` over a white sprite **[source]**.
- Vanilla panel styles have an irregular "torn paper" edge: a clean look needs an own atlas
  **[measured]**. Nine-slice borders and corners are drawn in **physical pixels** (`Outline` = 2 px at
  720p, 900p and 1080p; an own r10 corner has the same geometry at all three) **[measured]**.
- Minimum nine-slice size = 2r + 4; below that the corners overlap **[measured]**.
- **Transparency blends in linear space**: black 50% over amber gave (176,129,0), sRGB would give
  (120,88,0). Pre-mix solid colors **[measured]**.
- With a white texture + `color`, the color in a screenshot equals the token exactly **[measured]**.
- **Imageset**: `ImageSetClass { Name, RefSize, Textures { mpix, path }, Images { Pos, Size, Flags },
  Groups }`; vanilla pairs a 1x (`mpix 0`) and an `@2x` (`mpix 1`) texture
  (`P:\gui\imagesets\dayz_gui.imageset:1-13`) **[source]**. A single texture with `mpix 1` and
  `RefSize` = texture size works; a `.paa` without GUID renders **[measured]**.
- **Not native**: border-radius, box-shadow, gradient, flex/gap, CSS. Everything becomes nine-slice
  texture + color.

## 3. Color and typography

- Color in a layout: 4 floats 0..1. In script: `SetColor(int ARGB)` with `ARGB / ARGBF`
  (`P:\scripts\1_core\proto\proto.c:322-335`) **[source]**.
- **`TextWidget` text color is `color`; `"text color"` is ignored.** On `ButtonWidget`, `"text color"`
  works **[measured]**.
- **The alpha of a `ButtonWidget`'s `color` multiplies its own text**: `color 0 0 0 0` hides the
  label. Use a child `TextWidget` **[measured]**.
- A `DayZDefaultButton` tinted white hides its white text until hover; `Colorable` tinted dark works
  **[measured]**.
- Vanilla fonts: Metron family as bitmaps only at 12/14/16/22/28/48/58; SDF `sdf_MetronBook24/72` and
  `sdf_MetronLight24/30/36/42/72`. Size in px through `"exact text" 1` + `"exact text size"`
  (`enwidgets.c:192-193`) **[source]**. SDF is sharp from 16 to 48; a bitmap scaled up blurs
  **[measured]**. Without `"exact text"` the text follows the widget height **[measured]**.
- Vanilla ships a font generator description (`P:\gui\fonts\metronbook.xml`, `.fsdf` files) next to
  the `.ttf`. Which program turns that into a `.fnt` is not documented **[open]**.
- Diacritics: the `.fsdf` lists 96 characters, yet every Portuguese accent tested rendered in every
  vanilla font (SDF and bitmap). The `.fsdf` list is not the effective glyph set **[measured]**.
- **Dark text on a light background looks thin**: the glyph edge blends in linear space, so the
  contrast of a regular-weight dark label on a light fill stays around 2.6 to 2.8 (1080p) whatever
  the text color; light on dark reaches its target. A bitmap bold label fixes it (7.7) **[measured]**.

## 4. Scale

- **The engine does not offer a UI scale setting to scripts**: there is no `GetUIScale` in
  `P:\scripts`. Vanilla scales by hand against 1080 (`inventorymenu.c:69-73`, `tabberui.c:48`) and
  swaps layouts by aspect ratio (`inventorymenu.c:38-52`). The HUD sits in a 0.9 x 0.9 frame
  (`day_z_hud.layout:1-8`) **[source]**.
- Exact units scale linearly from 1920x1080 (section 1) **[measured]**.

## 5. Images

- `ImageWidget` with an imageset image: `mode additive` + `"src alpha" 1` draws (as
  `day_z_ingamemenu.layout:540-553` does); `mode blend` without `"src alpha"` gave a white box
  **[measured]**. Which of the two attributes fixes it was not isolated **[open]**.
- `fixaspect none|fixwidth|inside|outside` had no visible effect with an imageset `image0`
  **[measured]**; not tested with `imageTexture` **[open]**.

## 6. Script lifecycle

- A menu opened through the `MissionGameplay.CreateScriptedMenu` factory + `EnterScriptedMenu` is
  held by the engine (`missionbase.c:327-332`). `ShowScriptedMenu(new ...)` leaves nobody holding
  the ref **[source]**.
- The engine destroys a menu's `layoutRoot` (`uiscriptedmenu.c:161-162`); any other root you create
  must be unlinked by you **[source]**.
- `CreateWidgets` with a null parent creates at the screen root: the widget survives the menu
  **[measured]**.
- `CreateWidgets` with a path that does not exist was observed to crash the client; guard with
  `FileExist` **[measured, single observation]**.

## 7. Importing designs

- There is no import from shadcn / HTML / Figma to `.layout`. Treat design tools as visual reference
  and approval; write the layout through a generator.

## 8. Still open

- Non-16:9 screens (the game does not offer them in its video options): does X scale by W/1920 or
  H/1080?
- 1440p / 4K: corner sharpness, `@2x` texture use, bold bitmap blur.
- Style name collision between two mods (last one wins, or merge?).
- `TextWidget.SetBold` and `"bold text"` on SDF fonts.
- Whether a parent's `ignorepointer` blocks its children's input.
- Numeric values of `WidgetFlags` and the attribute -> flag map (not blocking).
