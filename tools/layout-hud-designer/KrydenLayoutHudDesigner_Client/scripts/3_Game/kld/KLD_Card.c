// Kryden Layout - card (docs/components.md): `card` fill + 1 px ring, title, description, content area
// and footer (WrapSpacer, buttons side by side with a gap of 8).
// No events of its own; footer buttons are KLD_Button and the caller keeps their refs.
class KLD_Card
{
	protected Widget m_Root;
	protected TextWidget m_Title;
	protected TextWidget m_Desc;
	protected Widget m_Content;
	protected Widget m_Footer;

	void KLD_Card(Widget parent, string title, string description)
	{
		// Without a parent, CreateWidgets creates at the screen root, outside any tree: the widget stays on
		// screen after its owner closes (lab round 5). Refuse and log.
		if (!parent)
		{
			Print("[KLD] KLD_Card without parent, nothing created: " + title);
			return;
		}

		m_Root = GetGame().GetWorkspace().CreateWidgets(KLD_Paths.CARD, parent);
		if (!m_Root)
		{
			Print("[KLD] KLD_Card: layout did not load: " + KLD_Paths.CARD);
			return;
		}

		m_Title = TextWidget.Cast(m_Root.FindAnyWidget("kld_card_title"));
		m_Desc = TextWidget.Cast(m_Root.FindAnyWidget("kld_card_desc"));
		m_Content = m_Root.FindAnyWidget("kld_card_content");
		m_Footer = m_Root.FindAnyWidget("kld_card_footer");

		if (m_Title)
			m_Title.SetText(title);
		if (m_Desc)
			m_Desc.SetText(description);
	}

	Widget GetRoot()
	{
		return m_Root;
	}

	//! Parent for free widgets inside the card (368 x 72 reference units).
	Widget GetContent()
	{
		return m_Content;
	}

	//! Parent of the footer buttons.
	Widget GetFooter()
	{
		return m_Footer;
	}

	//! Recomputes the footer after creating buttons from script. Lab round 5 showed the WrapSpacer lays out
	//! script-created children by itself on the next frame; this stays as the vanilla habit
	//! (dropdownprefab.c:136-138 calls Update() after changing its list).
	void Relayout()
	{
		if (m_Footer)
			m_Footer.Update();
		if (m_Root)
			m_Root.Update();
	}
}
