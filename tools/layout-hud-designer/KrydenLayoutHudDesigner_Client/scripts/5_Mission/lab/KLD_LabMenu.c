// Kryden Layout Lab (client): one button per test layout in gui/layouts/lab/ (protocol in lab/README.md).
// Each opened test writes to the client log the rectangles the engine computed, at 3 moments:
// immediately, LAB_DUMP_DELAY_MS later, and after Update() on every widget.
//
// Lifecycle: opened through the factory (MissionGameplay.CreateScriptedMenu + EnterScriptedMenu, see
// KLD_LabMission.c) -> the engine holds the menu reference (missionbase.c:327-332). The engine destroys
// layoutRoot (uiscriptedmenu.c:161-162); the TEST root is not layoutRoot, so CloseTest() tears it down,
// called on ESC, on OnHide and in the destructor.
class KLD_LabMenu extends UIScriptedMenu
{
	protected Widget m_Panel;
	protected Widget m_BtnClose;
	protected Widget m_TestRoot;
	protected string m_TestId;
	protected ref array<Widget> m_TestButtons;
	protected ref array<string> m_TestIds;
	protected ref KLD_LabShowcase m_Showcase;   // test 08: holds the KLD_Button refs

	void ~KLD_LabMenu()
	{
		CloseTest();
	}

	override Widget Init()
	{
		layoutRoot = GetGame().GetWorkspace().CreateWidgets(KrydenLayoutHudDesignerConst.LAB_MENU_LAYOUT);
		if (!layoutRoot)
		{
			Print(KrydenLayoutHudDesignerConst.LAB_LOG_TAG + "menu layout did not load: " + KrydenLayoutHudDesignerConst.LAB_MENU_LAYOUT);
			return null;
		}

		m_Panel = layoutRoot.FindAnyWidget("kld_lab_panel");
		m_BtnClose = layoutRoot.FindAnyWidget("kld_lab_btn_close");

		m_TestButtons = new array<Widget>;
		m_TestIds = new array<string>;
		RegisterTest("kld_lab_btn_01", "01_sizing");
		RegisterTest("kld_lab_btn_02", "02_anchors");
		RegisterTest("kld_lab_btn_03", "03_spacers");
		RegisterTest("kld_lab_btn_04", "04_layers");
		RegisterTest("kld_lab_btn_05", "05_nineslice");
		RegisterTest("kld_lab_btn_06", "06_fonts");
		RegisterTest("kld_lab_btn_07", "07_atlas");
		RegisterTest("kld_lab_btn_08", "08_components");

		return layoutRoot;
	}

	override void OnShow()
	{
		super.OnShow();

		// Locks: player control and camera off, cursor on, HUD hidden.
		GetGame().GetMission().PlayerControlDisable(INPUT_EXCLUDE_ALL);
		GetGame().GetUIManager().ShowUICursor(true);
		GetGame().GetMission().GetHud().Show(false);

		SetFocus(layoutRoot);
		Print(KrydenLayoutHudDesignerConst.LAB_LOG_TAG + "menu opened");
	}

	override void OnHide()
	{
		super.OnHide();

		Print(KrydenLayoutHudDesignerConst.LAB_LOG_TAG + "menu closed");
		CloseTest();

		GetGame().GetMission().PlayerControlEnable(true);
		GetGame().GetUIManager().ShowUICursor(false);
		GetGame().GetMission().GetHud().Show(true);
	}

	override void Update(float timeslice)
	{
		super.Update(timeslice);

		// ESC: with a test open, go back to the buttons; with no test, close the menu.
		if (GetGame().GetInput().LocalPress_ID(UAUIBack, false))
		{
			if (m_TestRoot)
			{
				CloseTest();
				return;
			}
			GetGame().GetUIManager().HideScriptedMenu(this);
		}
	}

	override bool OnClick(Widget w, int x, int y, int button)
	{
		if (w == m_BtnClose)
		{
			GetGame().GetUIManager().HideScriptedMenu(this);
			return true;
		}

		int index = m_TestButtons.Find(w);
		if (index != -1)
		{
			// Diagnostic for the round 5 bug (test 08 received the tree of test 07): which button opened which test.
			Print(KrydenLayoutHudDesignerConst.LAB_LOG_TAG + "click button=" + w.GetName() + " -> test=" + m_TestIds[index]);
			OpenTest(m_TestIds[index]);
			return true;
		}

		return super.OnClick(w, x, y, button);
	}

	// -------- tests --------

	protected void RegisterTest(string buttonName, string testId)
	{
		Widget button = layoutRoot.FindAnyWidget(buttonName);
		if (!button)
		{
			Print(KrydenLayoutHudDesignerConst.LAB_LOG_TAG + "button not found in layout: " + buttonName);
			return;
		}
		m_TestButtons.Insert(button);
		m_TestIds.Insert(testId);
	}

	protected void OpenTest(string testId)
	{
		CloseTest();

		string path = KrydenLayoutHudDesignerConst.LAB_LAYOUT_DIR + "kld_lab_" + testId + ".layout";
		// CreateWidgets with a path that does not exist was observed to crash the client;
		// FileExist (ensystem.c:397) is the guard.
		if (!FileExist(path))
		{
			Print(KrydenLayoutHudDesignerConst.LAB_LOG_TAG + "layout does not exist: " + path);
			return;
		}

		// Child of the menu layoutRoot: the buttons in test 08 must receive the mouse (the full-screen menu
		// root could sit on top of a separate root). Rectangles do not change: layoutRoot covers the whole
		// screen.
		m_TestRoot = GetGame().GetWorkspace().CreateWidgets(path, layoutRoot);
		if (!m_TestRoot)
		{
			Print(KrydenLayoutHudDesignerConst.LAB_LOG_TAG + "layout did not load: " + path);
			return;
		}

		m_TestId = testId;
		if (m_Panel)
			m_Panel.Show(false);

		// The root of each test layout is named kld_lab_<NN>_root; if it does not match, the requested file
		// is not the one that loaded (round 5).
		string rootName = m_TestRoot.GetName();
		string expected = "kld_lab_" + testId.Substring(0, 2) + "_root";
		Print(KrydenLayoutHudDesignerConst.LAB_LOG_TAG + "open test=" + testId + " root=" + rootName + " path=" + path);
		if (rootName != expected)
			Print(KrydenLayoutHudDesignerConst.LAB_LOG_TAG + "ERROR: root " + rootName + " does not match test " + testId + " (expected " + expected + ")");

		if (testId == "08_components")
		{
			m_Showcase = new KLD_LabShowcase();
			m_Showcase.Build(m_TestRoot);
		}

		Dump("immediate");
		GetGame().GetCallQueue(CALL_CATEGORY_GUI).CallLater(DumpDelayed, KrydenLayoutHudDesignerConst.LAB_DUMP_DELAY_MS, false);
	}

	protected void CloseTest()
	{
		if (GetGame())
			GetGame().GetCallQueue(CALL_CATEGORY_GUI).Remove(DumpDelayed);

		if (m_TestRoot)
		{
			Print(KrydenLayoutHudDesignerConst.LAB_LOG_TAG + "close test=" + m_TestId + " root=" + m_TestRoot.GetName());
			m_TestRoot.Unlink();
			m_TestRoot = null;
		}
		m_Showcase = null;
		m_TestId = "";

		if (m_Panel)
			m_Panel.Show(true);
	}

	protected void DumpDelayed()
	{
		if (!m_TestRoot)
			return;

		Dump("delayed");
		UpdateTree(m_TestRoot);
		Dump("after_update");
	}

	protected void UpdateTree(Widget w)
	{
		w.Update();
		Widget child = w.GetChildren();
		while (child)
		{
			UpdateTree(child);
			child = child.GetSibling();
		}
	}

	// -------- log --------
	// One line per widget, prefix [KLD_LAB], for lab/README.md:
	// [KLD_LAB] test=01_sizing phase=immediate screen=1920x1080 depth=1 name=s01_px_100x100 type=PanelWidget vis=1 x=40 y=40 w=100 h=100 decl_pos=40 40 decl_size=100 100

	protected void Dump(string phase)
	{
		int screenW;
		int screenH;
		GetScreenSize(screenW, screenH);

		string head = string.Format("%1test=%2 phase=%3 screen=%4x%5", KrydenLayoutHudDesignerConst.LAB_LOG_TAG, m_TestId, phase, screenW, screenH);
		Print(head + " BEGIN");
		DumpNode(m_TestRoot, head, 0);
		Print(head + " END");
	}

	protected void DumpNode(Widget w, string head, int depth)
	{
		float sx;
		float sy;
		float sw;
		float sh;
		float px;
		float py;
		float pw;
		float ph;
		w.GetScreenPos(sx, sy);
		w.GetScreenSize(sw, sh);
		w.GetPos(px, py);
		w.GetSize(pw, ph);

		string who = string.Format(" depth=%1 name=%2 type=%3 vis=%4", depth, w.GetName(), w.GetTypeName(), w.IsVisible());
		string rect = string.Format(" x=%1 y=%2 w=%3 h=%4", sx, sy, sw, sh);
		string decl = string.Format(" decl_pos=%1 %2 decl_size=%3 %4", px, py, pw, ph);
		Print(head + who + rect + decl);

		Widget child = w.GetChildren();
		while (child)
		{
			DumpNode(child, head, depth + 1);
			child = child.GetSibling();
		}
	}
}
