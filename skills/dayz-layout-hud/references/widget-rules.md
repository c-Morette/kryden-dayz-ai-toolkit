# DayZ widget rules that fail silently

Measured in-game in October 2026 (16:9 at 1280x720, 1600x900, 1920x1080) unless marked. Each rule:
what you see, then the rule.

## Geometry

- **Exact units are not pixels.** `hexactsize 1` with 100 gives 66.667 px at 720p and 83.333 at 900p.
  The engine scales linearly from 1920x1080. Design in 1920x1080 units. `GetPos/GetSize` already return
  the scaled value. (Non-16:9 not measured.)
- **`valign bottom` / `halign right` without `_ref` puts the widget outside the parent** (y = -h): it
  only moves the pivot. Use `left|center_ref|right_ref` and `top|center_ref|bottom_ref`. `position`
  is then the offset inward from that edge (from the center for `center_ref`).
- **`Padding` and `Margin` are the inverse of CSS** on `GridSpacerWidget` / `WrapSpacerWidget`:
  `Padding` = gap between cells, `Margin` = inner inset. Cell = (size - 2*Margin - (n-1)*Padding)/n.
  GridSpacer stretches children to the column width.
- **A WrapSpacer whose items fill the exact width wraps differently per resolution** (rounding at
  720p). Leave at least 1 unit of slack.
- **Layer order**: higher `priority` on top; tie = declared later on top; only between siblings.
- **Script-created children read (0,0,0,0) in the same frame.** The spacer lays them out on the next
  frame by itself. Read rectangles later (`CallLater`), do not assume `Update()` is needed.
- `scaled 1` does nothing to a PanelWidget rectangle.

## Text

- **`TextWidget` ignores `"text color"`**: its text color is the `color` attribute (and `SetColor`).
  On `ButtonWidget`, `"text color"` works.
- **The alpha of a `ButtonWidget`'s `color` multiplies its own text**: a ghost button with
  `color 0 0 0 0` has an invisible label. Put the label in a child `TextWidget`.
- **`ButtonWidget` has no exact text size** (only `text_proportion`): exact-size label = child `TextWidget`.
- **Without `"exact text" 1` + `"exact text size"`, text follows the widget height.** Always declare both.
- **No `SetFont` and no `SetStyle` at runtime.** A different font or style needs a different layout/prefab.
- **Use SDF fonts** (`gui/fonts/sdf_MetronBook24`, `sdf_MetronLight24`): sharp from 16 to 48. Bitmap
  fonts blur when scaled. Vanilla has no bold SDF; `MetronBook-Bold16/14` are bitmaps.
- **Dark text on a light fill looks thin** whatever the dark color (glyph edges blend in linear
  space). Use a bold bitmap label or light text on a darker fill.
- Portuguese accents render in all vanilla fonts tested, despite the `.fsdf` listing 96 characters.

## Color and textures

- **Alpha blends in linear space**: black 50% over amber = (176,129,0), not sRGB (120,88,0). Web
  colors with transparency must be pre-mixed into solid colors.
- **Never bake color into a texture**: use a white texture and `color` / `SetColor`; the screenshot
  then matches the token exactly.
- **Vanilla panel styles (`DayZDefaultPanel*`, `UIDefaultPanel`) have torn-paper edges.** Clean
  rounded corners need an own nine-slice atlas.
- **Nine-slice corners and borders are physical pixels** (do not scale): the radius is the same in px
  at every resolution. **Minimum piece size = 2r + 4**, below that the corners overlap.
- `DayZDefaultButton` tinted white hides its white text; use `Colorable` tinted dark.
- `ImageWidget` from an imageset: `mode additive` + `"src alpha" 1` draws; `mode blend` without
  `"src alpha"` showed a white box.
- `ImageToPAA` with the `_8888` suffix gives 1-bit alpha (ARGB1555) and destroys anti-aliased corners.
  No suffix + alpha = DXT5. Texture sides must be powers of 2.
- An own imageset/styles registers in `CfgMods > defs > imageSets / widgetStyles` with the mod prefix
  path. A `.paa` without GUID works; one texture with `mpix 1` and `RefSize` = texture size works.

## Lifecycle

- **`CreateWidgets(path, null)` creates at the screen root**: the widget survives the menu that made
  it. Always pass a parent.
- **`SetHandler` does not hold the handler object**: keep a `ref` to it or clicks stop working with
  no log.
- Open menus through the `MissionGameplay.CreateScriptedMenu` factory + `EnterScriptedMenu` (the
  engine holds the ref). `ShowScriptedMenu(new ...)` leaves nobody holding it.
- The engine destroys a menu's `layoutRoot`; any other root you created must be `Unlink()`ed by you.
- `CreateWidgets` with a missing path was observed to crash the client (single observation): guard
  with `FileExist`.
- `.layout` files accept no comments. LF line endings work.
