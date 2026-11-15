// Kryden Layout Lab: the UAKLDLabMenu key (data/inputs.xml, default Insert) opens/closes KLD_LabMenu.
//
// Factory + EnterScriptedMenu, same as vanilla (missionbase.c:185-332): the engine creates the menu
// through CreateScriptedMenu and HOLDS the reference. Do not use ShowScriptedMenu(new ...):
// nobody holds the ref and the menu is garbage collected.
modded class MissionGameplay
{
	override void OnUpdate(float timeslice)
	{
		super.OnUpdate(timeslice);

		UAInput labInput = GetUApi().GetInputByName(KrydenLayoutHudDesignerConst.LAB_INPUT);
		if (labInput && labInput.LocalPress())
			KLD_ToggleLabMenu();
	}

	override UIScriptedMenu CreateScriptedMenu(int id)
	{
		if (id == KrydenLayoutHudDesignerConst.MENU_KLD_LAB)
		{
			KLD_LabMenu menu = new KLD_LabMenu();
			menu.SetID(id);
			return menu;
		}
		return super.CreateScriptedMenu(id);
	}

	// Closes the lab if it is already open; does not open on top of another menu (inventory etc.).
	protected void KLD_ToggleLabMenu()
	{
		UIManager ui = GetGame().GetUIManager();
		UIScriptedMenu top = ui.GetMenu();
		if (top)
		{
			if (KLD_LabMenu.Cast(top))
				ui.HideScriptedMenu(top);
			return;
		}
		ui.EnterScriptedMenu(KrydenLayoutHudDesignerConst.MENU_KLD_LAB, null);
	}
}
