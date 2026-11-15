// Kryden Layout - button (docs/components.md). Same pattern as the vanilla DropdownPrefab
// (P:\scripts\5_mission\gui\newui\dropdownprefab\dropdownprefab.c:18-33): creates the layout inside the
// parent and becomes its handler. The label is a child TextWidget (exact size; ButtonWidget does not accept
// "exact text size", and the alpha of its own color erases its own text - lab round 4).
//
// THE CALLER KEEPS THE REFERENCE (ref KLD_Button): SetHandler does not hold the object. Without the ref it
// is garbage collected and the button stops reacting, with no log.
class KLD_Button extends ScriptedWidgetEventHandler
{
	protected Widget m_Root;
	protected Widget m_Border;
	protected TextWidget m_Label;
	protected string m_Text;
	protected int m_Variant;
	protected bool m_Hover;
	protected bool m_Pressed;
	protected bool m_Disabled;

	//! Invoke(KLD_Button) on left click; does not fire while disabled.
	ref ScriptInvoker m_OnClick = new ScriptInvoker();

	void KLD_Button(Widget parent, string label, int variant)
	{
		m_Variant = variant;
		m_Text = label;

		// Without a parent, CreateWidgets creates at the screen root, outside any tree: the widget stays on
		// screen after its owner closes (lab round 5). Refuse and log.
		if (!parent)
		{
			Print("[KLD] KLD_Button without parent, nothing created: " + label);
			return;
		}

		// D-12: primary has its own prefab with a bold label (TextWidget cannot change font from script).
		string path = KLD_Paths.BUTTON;
		if (variant == EKLDVariant.PRIMARY)
			path = KLD_Paths.BUTTON_PRIMARY;

		m_Root = GetGame().GetWorkspace().CreateWidgets(path, parent);
		if (!m_Root)
		{
			Print("[KLD] KLD_Button: layout did not load: " + path);
			return;
		}

		m_Border = m_Root.FindAnyWidget("kld_button_border");
		m_Label = TextWidget.Cast(m_Root.FindAnyWidget("kld_button_label"));
		if (m_Label)
			m_Label.SetText(label);

		m_Root.SetHandler(this);
		Refresh();
	}

	Widget GetRoot()
	{
		return m_Root;
	}

	string GetText()
	{
		return m_Text;
	}

	void SetText(string label)
	{
		m_Text = label;
		if (m_Label)
			m_Label.SetText(label);
	}

	void SetDisabled(bool disabled)
	{
		m_Disabled = disabled;
		m_Hover = false;
		m_Pressed = false;
		if (m_Root)
			m_Root.Enable(!disabled);
		Refresh();
	}

	bool IsDisabled()
	{
		return m_Disabled;
	}

	override bool OnMouseEnter(Widget w, int x, int y)
	{
		if (w != m_Root)
			return false;
		m_Hover = true;
		Refresh();
		return true;
	}

	override bool OnMouseLeave(Widget w, Widget enterW, int x, int y)
	{
		if (w != m_Root)
			return false;
		m_Hover = false;
		m_Pressed = false;
		Refresh();
		return true;
	}

	override bool OnMouseButtonDown(Widget w, int x, int y, int button)
	{
		if (w != m_Root || button != MouseState.LEFT)
			return false;
		m_Pressed = true;
		Refresh();
		return false;
	}

	override bool OnMouseButtonUp(Widget w, int x, int y, int button)
	{
		if (w != m_Root || button != MouseState.LEFT)
			return false;
		m_Pressed = false;
		Refresh();
		return false;
	}

	override bool OnClick(Widget w, int x, int y, int button)
	{
		if (w != m_Root)
			return false;
		if (m_Disabled)
			return true;
		m_OnClick.Invoke(this);
		return true;
	}

	protected void Refresh()
	{
		if (!m_Root)
			return;

		int state = EKLDState.NORMAL;
		if (m_Disabled)
			state = EKLDState.DISABLED;
		else if (m_Pressed)
			state = EKLDState.PRESSED;
		else if (m_Hover)
			state = EKLDState.HOVER;

		m_Root.SetColor(KLD_Theme.ButtonBg(m_Variant, state));
		if (m_Label)
			m_Label.SetColor(KLD_Theme.ButtonFg(m_Variant, state));

		if (m_Border)
		{
			int border = KLD_Theme.ButtonBorder(m_Variant, state);
			m_Border.Show(border != KLD_Theme.NONE);
			m_Border.SetColor(border);
		}
	}
}
