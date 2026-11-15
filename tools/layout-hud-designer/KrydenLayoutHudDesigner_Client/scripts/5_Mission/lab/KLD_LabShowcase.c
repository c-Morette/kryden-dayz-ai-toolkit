// Kryden Layout Lab - test 08: the v0 library built from script (lab/README.md). Also the usage example.
// Holds the KLD_Button refs (without them the handler is collected and the button stops reacting).
// Deliberately does not call Relayout/Update: the "immediate" dump of KLD_LabMenu shows whether the
// WrapSpacer lays out script-created children by itself; "after_update" shows the state after Update().
class KLD_LabShowcase
{
	protected ref array<ref KLD_Button> m_Buttons;
	protected ref array<ref KLD_Badge> m_Badges;
	protected ref array<ref KLD_Card> m_Cards;
	protected TextWidget m_Status;

	void KLD_LabShowcase()
	{
		m_Buttons = new array<ref KLD_Button>;
		m_Badges = new array<ref KLD_Badge>;
		m_Cards = new array<ref KLD_Card>;
	}

	void Build(Widget root)
	{
		if (!root)
			return;

		m_Status = TextWidget.Cast(root.FindAnyWidget("sc_status"));

		// Only build on top of the test 08 tree: in round 5 the tree of test 07 arrived and, without the
		// containers, everything was created loose on the screen.
		Widget buttons = root.FindAnyWidget("sc_buttons");
		Widget badges = root.FindAnyWidget("sc_badges");
		Widget cards = root.FindAnyWidget("sc_cards");
		Widget sep = root.FindAnyWidget("sc_sep");
		if (!buttons || !badges || !cards || !sep)
		{
			Print(KrydenLayoutHudDesignerConst.LAB_LOG_TAG + "ERROR showcase: test 08 containers missing under root " + root.GetName() + "; nothing built");
			return;
		}

		AddButton(buttons, "Confirm", EKLDVariant.PRIMARY);
		AddButton(buttons, "Cancel", EKLDVariant.SECONDARY);
		AddButton(buttons, "Outline", EKLDVariant.OUTLINE);
		AddButton(buttons, "Ghost", EKLDVariant.GHOST);
		AddButton(buttons, "Delete", EKLDVariant.DESTRUCTIVE);
		KLD_Button off = AddButton(buttons, "Disabled", EKLDVariant.PRIMARY);
		off.SetDisabled(true);

		m_Badges.Insert(new KLD_Badge(badges, "New", EKLDVariant.PRIMARY));
		m_Badges.Insert(new KLD_Badge(badges, "Beta", EKLDVariant.SECONDARY));
		m_Badges.Insert(new KLD_Badge(badges, "Draft", EKLDVariant.OUTLINE));
		m_Badges.Insert(new KLD_Badge(badges, "Error", EKLDVariant.DESTRUCTIVE));

		KLD_Card server = new KLD_Card(cards, "Server", "Community server, 64 players");
		m_Cards.Insert(server);
		m_Badges.Insert(new KLD_Badge(server.GetContent(), "Online", EKLDVariant.SECONDARY));
		AddButton(server.GetFooter(), "Join", EKLDVariant.PRIMARY);
		AddButton(server.GetFooter(), "Details", EKLDVariant.OUTLINE);

		KLD_Card danger = new KLD_Card(cards, "Delete base", "This action cannot be undone.");
		m_Cards.Insert(danger);
		AddButton(danger.GetFooter(), "Delete", EKLDVariant.DESTRUCTIVE);
		AddButton(danger.GetFooter(), "Cancel", EKLDVariant.GHOST);

		KLD_Separator.Create(sep);
	}

	protected KLD_Button AddButton(Widget parent, string label, int variant)
	{
		KLD_Button button = new KLD_Button(parent, label, variant);
		button.m_OnClick.Insert(OnButtonClick);
		m_Buttons.Insert(button);
		return button;
	}

	void OnButtonClick(KLD_Button button)
	{
		string msg = "Click: " + button.GetText();
		if (m_Status)
			m_Status.SetText(msg);
		Print(KrydenLayoutHudDesignerConst.LAB_LOG_TAG + msg);
	}
}
