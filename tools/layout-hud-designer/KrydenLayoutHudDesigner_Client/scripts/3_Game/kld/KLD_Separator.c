// Kryden Layout - horizontal separator (docs/components.md): parent width, height 1 in 1920x1080
// reference units (0.67 px at 720p; lab round 5 showed it still renders).
class KLD_Separator
{
	static Widget Create(Widget parent)
	{
		// Without a parent, CreateWidgets creates at the screen root and the widget stays behind (lab round 5).
		if (!parent)
		{
			Print("[KLD] KLD_Separator without parent, nothing created");
			return null;
		}

		Widget w = GetGame().GetWorkspace().CreateWidgets(KLD_Paths.SEPARATOR, parent);
		if (!w)
			Print("[KLD] KLD_Separator: layout did not load: " + KLD_Paths.SEPARATOR);
		return w;
	}
}
