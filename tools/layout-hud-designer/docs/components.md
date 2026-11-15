# Component library v0 (work in progress)

State: Button, Badge, Card and Separator were **tested in-game in lab rounds 5 and 6** (hover, click,
disabled, exact colors, nothing left on screen after closing). The last change, the bold primary
(D-12), **was not tested in-game as a component yet**. Design rules: `docs/design-contract.md`.

## Pieces

| file | what it is |
|---|---|
| `tools/kld_tokens.py` | single source of the colors and of the button/badge variants, already pre-mixed over `background` in sRGB |
| `tools/gen_components.py` | writes `scripts/3_Game/kld/KLD_Tokens.c` (ARGB colors + prefab paths) and the prefabs `gui/layouts/kld/*.layout` |
| `tools/gen_atlas.py` | writes the nine-slice atlas (`gui/textures/kld_ui_atlas.paa`, `gui/imagesets/kld_ui.imageset`, `gui/looknfeel/kld_ui.styles`) |
| `tools/kld_layout.py` | `.layout` writer used by the generators and by the lab |
| `scripts/3_Game/kld/KLD_Theme.c` | `EKLDVariant`, `EKLDState` and the color of each variant/state |
| `scripts/3_Game/kld/KLD_Button.c`, `KLD_Badge.c`, `KLD_Card.c`, `KLD_Separator.c` | the components |

Nothing in `KLD_Tokens.c` or `gui/layouts/kld/` is edited by hand: change `kld_tokens.py` or
`gen_components.py` and regenerate.

## Usage

Everything is in `3_Game`, so it serves `4_World` and `5_Mission` as well.

```c
class MyMenu extends UIScriptedMenu
{
	protected ref array<ref KLD_Button> m_Buttons = new array<ref KLD_Button>;   // REQUIRED: keep the refs

	protected void Build(Widget holder)
	{
		KLD_Button ok = new KLD_Button(holder, "Confirm", EKLDVariant.PRIMARY);
		ok.m_OnClick.Insert(OnConfirm);
		m_Buttons.Insert(ok);

		KLD_Card card = new KLD_Card(holder, "Server", "Community server, 64 players");
		KLD_Button join = new KLD_Button(card.GetFooter(), "Join", EKLDVariant.PRIMARY);
		m_Buttons.Insert(join);

		new KLD_Badge(holder, "New", EKLDVariant.PRIMARY);
		KLD_Separator.Create(holder);
	}

	void OnConfirm(KLD_Button button) {}
}
```

A complete, tested example is `scripts/5_Mission/lab/KLD_LabShowcase.c` (lab test 08).

| component | prefab (1920x1080 units) | API |
|---|---|---|
| `KLD_Button(parent, label, variant)` | 128x32, radius 10, label 16 (primary: `kld_button_primary.layout`, label `MetronBook-Bold16`) | `m_OnClick` (`Invoke(KLD_Button)`), `SetText`, `GetText`, `SetDisabled`, `IsDisabled`, `GetRoot` |
| `KLD_Badge(parent, label, variant)` | 80x24, radius 10, label 14 (primary: `kld_badge_primary.layout`, label `MetronBook-Bold14`) | `GetRoot` |
| `KLD_Card(parent, title, description)` | 400x220, radius 10, title 18, description 16, content 368x72, footer 368x32 | `GetContent`, `GetFooter`, `Relayout`, `GetRoot` |
| `KLD_Separator.Create(parent)` | parent width x 1 | returns the `Widget` |

Variants: `EKLDVariant.PRIMARY`, `SECONDARY`, `OUTLINE`, `GHOST`, `DESTRUCTIVE` (badge: no `GHOST`).
Button states: hover and pressed use the shadcn hover color (the web's `active` only shifts 1 px);
disabled = 50% opacity, pre-mixed.

## Rules the code follows (and why)

- **Never without a parent**: with a null `parent` the component logs `[KLD] ... without parent` and
  creates nothing. Without a parent `CreateWidgets` creates at the screen root and the widget stays
  on screen after the menu closes (lab round 5).
- **Rectangles only on the next frame**: a child created by script reads (0,0,0,0) in the same frame;
  the WrapSpacer lays it out by itself on the next frame, without `Update()` (lab round 5).
- **Keep the `KLD_Button` ref**: `SetHandler` does not hold the object (same as the vanilla
  `DropdownPrefab`, which its owner keeps). Without the ref the button stops reacting, with no log.
  Badge, card and separator have no handler.
- **Label = child `TextWidget` with its color in `color`**: `"text color"` is ignored on `TextWidget`,
  `ButtonWidget` does not accept an exact text size, and the alpha of its `color` erases its own text
  (lab round 4).
- **Color through `SetColor` on a white texture** (D-10); web colors with transparency come pre-mixed,
  because DayZ blends in linear space (lab round 4).
- **Font cannot change at runtime**: there is no `SetFont`, so a different font needs a different
  prefab (that is why primary has its own).

## Conscious deviations from shadcn in v0

- Fixed widths (button 128, badge 80, card 400): there is no "width from text".
- Card without the `muted/50` footer background (it would need a style with only the bottom corners rounded).
- Badge with radius 10 at height 24 (the web badge is a pill).
- No focus ring.
- Colors pre-mixed over `background`: an outline/ghost/destructive button inside a card shows the
  tone computed for the page background, not for the card.

## Measured

- Round 5 (test 08): WrapSpacer lays out script children on the next frame, without `Update()`;
  hover, disabled and click work with exact token colors; the 1-unit separator shows at 1080p and
  at 720p.
- Round 6 (test 08 after fixes): zero `SCRIPT (E)`, no `without parent` line, the right root on every
  opening at 1080p, 720p and 900p, nothing left on screen after closing the menu.
- Round 7 (static comparison row): bold shadcn primary chosen, see D-12 in `docs/design-contract.md`.
  The bitmap bold comes out about 10% smaller than the SDF; 1440p/4K not measured.
- The lab labels were Portuguese when measured; this copy uses English labels (same widgets and sizes).
