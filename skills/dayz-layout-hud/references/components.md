# Components (v0, work in progress)

All in `scripts/3_Game/kld/` of the tool folder, usable from 3_Game, 4_World and 5_Mission. Tested
in-game: Button, Badge, Card, Separator. Not tested yet: the bold primary prefabs (D-12).

| component | size (1920x1080 units) | API |
|---|---|---|
| `KLD_Button(Widget parent, string label, int variant)` | 128x32, radius 10, label 16 | `ref ScriptInvoker m_OnClick` (`Invoke(KLD_Button)`), `SetText`, `GetText`, `SetDisabled(bool)`, `IsDisabled`, `GetRoot` |
| `KLD_Badge(Widget parent, string label, int variant)` | 80x24, radius 10, label 14 | `GetRoot` |
| `KLD_Card(Widget parent, string title, string description)` | 400x220; content area 368x72; footer 368x32 | `GetContent`, `GetFooter`, `Relayout`, `GetRoot` |
| `KLD_Separator.Create(Widget parent)` | parent width x 1 | returns the `Widget` |

Variants: `EKLDVariant.PRIMARY`, `SECONDARY`, `OUTLINE`, `GHOST`, `DESTRUCTIVE` (badge has no GHOST).

```c
protected ref array<ref KLD_Button> m_Buttons = new array<ref KLD_Button>;

void Build(Widget holder)
{
	KLD_Button ok = new KLD_Button(holder, "Confirm", EKLDVariant.PRIMARY);
	ok.m_OnClick.Insert(OnConfirm);
	m_Buttons.Insert(ok);

	KLD_Card card = new KLD_Card(holder, "Server", "Community server, 64 players");
	m_Buttons.Insert(new KLD_Button(card.GetFooter(), "Join", EKLDVariant.PRIMARY));
}

void OnConfirm(KLD_Button button) {}
```

## Caller rules

- **Keep a `ref` to every `KLD_Button`** (an array on the menu). Without it the handler is collected
  and the button stops reacting, with no log. Badge, card and separator need no ref.
- **Always pass a parent.** A null parent is refused and logged (`[KLD] ... without parent`).
- **Put components inside a container that lays them out**, usually a `WrapSpacerWidget` (gap =
  `Padding`). Its rectangles are ready on the next frame, not in the same one.
- **Widths are fixed** (button 128, badge 80, card 400): long labels do not grow the widget.
- **Do not put `ignorepointer 1` on containers that hold buttons** (not measured whether it blocks
  the children).
- Colors are pre-mixed over the page `background`: outline/ghost/destructive inside a card show the
  page tone, not the card tone.

## Adding a component or variant

Paths are relative to the tool folder (`<tool>`, see SKILL.md for where it is).

1. Add colors to `<tool>/tools/kld_tokens.py` and the prefab function to `<tool>/tools/gen_components.py`.
2. Run `python <tool>/tools/gen_components.py` and validate the new layout with `<tool>/lab/validate_layout.py`.
3. Write the class in `<tool>/KrydenLayoutHudDesigner_Client/scripts/3_Game/kld/` following `KLD_Button.c`: create the layout inside the
   parent, find children by name, refuse a null parent, set colors through `KLD_Theme`.
4. Add it to `KLD_LabShowcase.c` (lab test 08) and look at it in-game at 1080p and 720p before calling
   it done.
