// Kryden Layout - badge (docs/components.md). No events: the caller does not need to keep a reference;
// the widget lives in the parent's tree.
class KLD_Badge
{
	protected Widget m_Root;
	protected Widget m_Border;
	protected TextWidget m_Label;

	void KLD_Badge(Widget parent, string label, int variant)
	{
		// Without a parent, CreateWidgets creates at the screen root, outside any tree: the widget stays on
		// screen after its owner closes (lab round 5). Refuse and log.
		if (!parent)
		{
			Print("[KLD] KLD_Badge without parent, nothing created: " + label);
			return;
		}

		// D-12: primary has its own prefab with a bold label (TextWidget cannot change font from script).
		string path = KLD_Paths.BADGE;
		if (variant == EKLDVariant.PRIMARY)
			path = KLD_Paths.BADGE_PRIMARY;

		m_Root = GetGame().GetWorkspace().CreateWidgets(path, parent);
		if (!m_Root)
		{
			Print("[KLD] KLD_Badge: layout did not load: " + path);
			return;
		}

		m_Border = m_Root.FindAnyWidget("kld_badge_border");
		m_Label = TextWidget.Cast(m_Root.FindAnyWidget("kld_badge_label"));
		if (m_Label)
		{
			m_Label.SetText(label);
			m_Label.SetColor(KLD_Theme.BadgeFg(variant));
		}

		m_Root.SetColor(KLD_Theme.BadgeBg(variant));
		if (m_Border)
		{
			int border = KLD_Theme.BadgeBorder(variant);
			m_Border.Show(border != KLD_Theme.NONE);
			m_Border.SetColor(border);
		}
	}

	Widget GetRoot()
	{
		return m_Root;
	}
}
