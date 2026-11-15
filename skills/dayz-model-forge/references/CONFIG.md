# `config.cpp` for the item

`build_vest.py` does not write the class: the stats are a design decision. This vest class was validated in-game:

```cpp
class CfgPatches
{
	class MyMod_Client
	{
		units[] = {"MY_Vest"};
		weapons[] = {};
		requiredVersion = 0.1;
		requiredAddons[] = {"DZ_Data", "DZ_Scripts", "DZ_Characters_Vests"};
	};
};
class CfgVehicles
{
	class Clothing;
	class MY_Vest: Clothing
	{
		scope = 2;
		displayName = "...";
		descriptionShort = "...";
		model = "\<pbo path>\<name>_g.p3d";
		inventorySlot[] = {"Vest"};
		itemInfo[] = {"Clothing", "Vest"};
		weight = 14000;
		itemSize[] = {5, 5};
		quickBarBonus = 1;
		varWetMax = 0.49;
		heatIsolation = 0.8;
		repairableWithKits[] = {3, 8};
		repairCosts[] = {75, 50};
		visibilityModifier = 0.95;
		hiddenSelections[] = {"camo"};
		hiddenSelectionsTextures[] = {"<pbo path>\<name>_co.paa"};
		hiddenSelectionsMaterials[] = {"<pbo path>\<name>.rvmat"};
		class ClothingTypes
		{
			male = "\<pbo path>\<name>_m.p3d";
			female = "\<pbo path>\<name>_f.p3d";
		};
		class DamageSystem
		{
			class GlobalHealth
			{
				class Health
				{
					hitpoints = 250;
					transferToAttachmentsCoef = 0.5;
					healthLevels[] =
					{
						{1.0, {"<pbo path>\<name>.rvmat"}},
						{0.7, {"<pbo path>\<name>.rvmat"}},
						{0.5, {"<pbo path>\<name>_damage.rvmat"}},
						{0.3, {"<pbo path>\<name>_damage.rvmat"}},
						{0.0, {"<pbo path>\<name>_destruct.rvmat"}}
					};
				};
			};
			// GlobalArmor: copy it from the vanilla PlateCarrierVest (P:\DZ\characters\vests\config.cpp) and adjust.
			// Only Projectile, Melee, Infected and FragGrenade exist.
		};
	};
};
```

- `<pbo path>` = what the build prints in `config: ... | pbo path ...`.
- Variant (another model with the same stats): `class MY_Vest2: MY_Vest`, overriding `model`, `ClothingTypes`,
  `hiddenSelections*` and only `healthLevels` (implicit form `class DamageSystem { class GlobalHealth {...} }`).
- No attachment proxies (holster/pouch) for now: do not declare `attachments[]` the model does not show.
- Validate: `CfgConvert.exe -bin -dst x.bin config.cpp` (in `DayZ Tools\Bin\CfgConvert`).

## Other kinds

Start from the vanilla class of the same kind in your extracted `P:\DZ\characters\...\config.cpp` and keep the
`model`, `ClothingTypes` and `hiddenSelections*` lines as above.

| `--kind` | slot | vanilla class to copy | extra `requiredAddons` | notes |
|---|---|---|---|---|
| `vest` | `Vest` | `PlateCarrierVest` | `DZ_Characters_Vests` | the class above |
| `top` | `Body` | `BomberJacket_ColorBase` | `DZ_Characters_Tops` | replaces the bare torso: the garment must cover it |
| `backpack` | `Back` | `CoyoteBag_ColorBase` | `DZ_Characters_Backpacks` | `rotationFlags = 16`; cargo size is yours to set; no attachment proxies yet |
