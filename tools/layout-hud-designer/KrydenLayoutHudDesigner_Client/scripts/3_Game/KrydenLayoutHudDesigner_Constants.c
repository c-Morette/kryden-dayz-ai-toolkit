// KrydenLayoutHudDesigner - shared constants. 3_Game loads before 4_World and 5_Mission,
// and this PBO loads on client AND server (type = "mod"): what is here exists on both sides.
class KrydenLayoutHudDesignerConst
{
	static const string MOD_NAME = "KrydenLayoutHudDesigner";
	static const string VERSION  = "0.1.0";
	static const string LOG_TAG  = "[KrydenLayoutHudDesigner] ";

	// Kryden Layout Lab (lab/README.md): in-game UI measurement menu. Development tool.
	static const int    MENU_KLD_LAB       = 914120;   // id for the MissionGameplay.CreateScriptedMenu factory; must not collide with other mods' menu ids
	static const string LAB_INPUT          = "UAKLDLabMenu";   // data/inputs.xml, rebindable in Options > Controls
	static const string LAB_LAYOUT_DIR     = "Kryden/KrydenLayoutHudDesigner/KrydenLayoutHudDesigner_Client/gui/layouts/lab/";
	static const string LAB_MENU_LAYOUT    = "Kryden/KrydenLayoutHudDesigner/KrydenLayoutHudDesigner_Client/gui/layouts/lab/kld_lab_menu.layout";
	static const string LAB_LOG_TAG        = "[KLD_LAB] ";
	static const int    LAB_DUMP_DELAY_MS  = 250;
}
