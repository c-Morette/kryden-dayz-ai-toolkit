class CfgPatches
{
	class KrydenLayoutHudDesigner_Client
	{
		units[] = {};
		weapons[] = {};
		requiredVersion = 0.1;
		requiredAddons[] = {"DZ_Data", "DZ_Scripts"};
	};
};

class CfgMods
{
	class KrydenLayoutHudDesigner_Client
	{
		dir = "Kryden/KrydenLayoutHudDesigner/KrydenLayoutHudDesigner_Client";
		picture = "";
		action = "";
		hideName = 0;
		hidePicture = 1;
		name = "KrydenLayoutHudDesigner - Client";
		credits = "";
		author = "Kryden";
		authorID = "0";
		version = "0.1.0";
		extra = 0;
		type = "mod";
		// Key binding for the Kryden Layout Lab (UAKLDLabMenu). Development tool: remove before shipping (see README).
		inputs = "Kryden/KrydenLayoutHudDesigner/KrydenLayoutHudDesigner_Client/data/inputs.xml";
		dependencies[] = {"Game", "World", "Mission"};

		// The PBO prefix is "Kryden\KrydenLayoutHudDesigner\KrydenLayoutHudDesigner_Client" ($PBOPREFIX$): every path here uses it.
		class defs
		{
			// Own nine-slice atlas (tools/gen_atlas.py). The .paa is generated, not shipped in this folder.
			class imageSets
			{
				files[] = {"Kryden/KrydenLayoutHudDesigner/KrydenLayoutHudDesigner_Client/gui/imagesets/kld_ui.imageset"};
			};
			class widgetStyles
			{
				files[] = {"Kryden/KrydenLayoutHudDesigner/KrydenLayoutHudDesigner_Client/gui/looknfeel/kld_ui.styles"};
			};
			class gameScriptModule
			{
				value = "";
				files[] = {"Kryden/KrydenLayoutHudDesigner/KrydenLayoutHudDesigner_Client/scripts/3_Game"};
			};
			class worldScriptModule
			{
				value = "";
				files[] = {"Kryden/KrydenLayoutHudDesigner/KrydenLayoutHudDesigner_Client/scripts/4_World"};
			};
			class missionScriptModule
			{
				value = "";
				files[] = {"Kryden/KrydenLayoutHudDesigner/KrydenLayoutHudDesigner_Client/scripts/5_Mission"};
			};
		};
	};
};
