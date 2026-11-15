# Build, PBO and packaging

17 traps · **11 silent** (they don't emit a single log line).

Legend: 🔇 fails in total silence · ⛔ doesn't compile / doesn't pack · no mark: fails at runtime with a visible symptom or log line

---

### MakePbo in a P: subfolder writes an unintended prefix 🔇

**Symptom** — The mod loads ZERO files at runtime and emits not a single line: no SCRIPT (E), no warning. The PBO exists, is signed, is in `-mod=`, and simply does not exist for the engine.

**Detect** — `ExtractPbo.exe -P -L <file.pbo>`: the first line is `prefix=...`. It must be exactly the prefix your `config.cpp` paths expect. Multi-segment prefixes work (CF ships `JM\CF\Scripts`); what breaks is a prefix MakePbo derived from a nested folder that nobody chose. In the RPT, compare `Module: X; loaded N files; N classes` with a good run: the delta matches exactly the number of .c files in the mod.

**Rule** — The condition is NESTING, not being "outside P:" (the mod is always inside P:). If the source lives BELOW THE FIRST LEVEL of P: (e.g. `P:\MyWorkspace\MyMod`), MakePbo derives the prefix from the path relative to the P: root and writes `MyWorkspace\MyMod`; the `files[]` in config.cpp no longer resolve. `P:\MyMod` (first level) does NOT need anything. Put a `$PBOPREFIX$` file at the root of the folder that becomes the PBO, containing THE NAME THE MOD HAS INSIDE THE PBO, not the path to it (verified 2026-09: `P:\MyProject\MyMod\$PBOPREFIX$` contains `MyMod`), which is what working mods do, and pass `-@=<Prefix>` equal to the mod folder name. Setting the prefix in Mikero's own config fixes it on your machine but doesn't travel with the project. The build script must ABORT if the prefix of the generated PBO differs from the expected one.

<sub>Source: verified 2026-08 on a real nested mod; MakePbo.exe default install in C:\Program Files (x86)\Mikero\DePboTools\bin</sub>

---

### Invalid MakePbo flag: exits 0 without writing a PBO 🔇

**Symptom** — An invented flag (e.g. `-NUP`) makes MakePbo print its syntax and quit WITHOUT packing, and in one of its forms with exit code 0. The build script reports "success" and the deploy ships the old PBO.

**Detect** — After every MakePbo, test the .pbo for existence AND timestamp. If the process output is the help/syntax text, nothing was packed.

**Rule** — Never trust MakePbo's exit code. Mandatory guard in the script: fail if the .pbo doesn't exist or isn't newer than the source.

<sub>Source: measured on MakePbo (Mikero DePboTools)</sub>

---

### A custom PBO writer can produce a PBO the engine silently ignores 🔇

**Symptom** — DayZ doesn't mount the PBO: the mod registers no CfgPatches, doesn't show up in the defines, zero prints, zero errors. The engine simply ignores it.

**Detect** — In the RPT, the mod's CfgPatches is never mentioned. The mod's `#ifdef` doesn't resolve. Pack the same source with MakePbo: if that one loads, the problem is the custom writer.

**Rule** — Tested 2026-07 on a real base-building mod with an in-house packer: only its obfuscating output path was validated in-game; its plain writer produced PBOs the engine ignored (probably a structural bug in the writer). Until a homemade or third-party packer has been validated in-game, ship plain PBOs with Mikero MakePbo or AddonBuilder. The raw (non-binarized) config.cpp is not the problem: the working path also used it raw. A prefix is mandatory in both cases: without it the `files[]` in config.cpp don't resolve.

<sub>Source: field test, 2026-07 (in-game)</sub>

---

### CfgConvert -bin doesn't compile .c: exit 0 doesn't validate script 🔇

**Symptom** — The build piles up months of "CfgConvert exit 0" and the mod never compiled a single line of Enforce Script. Script errors slip through; the false validation only shows when the server starts.

**Detect** — `CfgConvert.exe -bin -dst out.bin in.cpp` only proves that config.cpp/model.cfg are syntactically valid. The only validation of script is starting the server and searching the RPT / script log for `SCRIPT (E)` (the log pads it: grep `SCRIPT\s+\(E\)`). There is no offline shortcut in the standard workflow.

**Rule** — Never say "validated" based on CfgConvert; say "config validated, script not tested". The acceptance criterion for any .c change is an RPT clean of SCRIPT (E).

<sub>Source: field practice, 2026-08; CfgConvert ships with DayZ Tools (default C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools\Bin\CfgConvert\)</sub>

---

### Binarizing is not encryption 🔇

**Symptom** — A binarized mod is extracted and re-edited by third parties anyway. No sign in game: the false sense of security only shows when the content leaks.

**Detect** — config.bin starts with the RAP header (`\0raP`) and goes back to text with `CfgConvert.exe -txt -dst out.cpp in.bin` (faithful roundtrip). An ODOL .p3d reverts with DeP3d (Mikero), P3D-Debinarizer and browser converters (lossy). p3d header: MLOD = editable, ODOL = binarized.

**Rule** — Treat binarization as a complementary layer: it removes plain text from the config and raises the bar, it does not prevent extraction. If the requirement is real protection, use a PBO obfuscator and assume even that is not final.

<sub>Source: tested with the DayZ Tools converters (DayZ Tools\Bin\)</sub>

---

### `+=` on a vanilla class without its addon in requiredAddons 🔇

**Symptom** — The item doesn't attach to the slot and NOTHING complains: no RPT error, no script log line. The slot simply doesn't exist.

**Detect** — In-game symptom: "the item can't be attached and nothing complains". To find the right addon: search `^\tclass <Class>: ` in the config.cpp files under `P:\DZ\**` and read the FIRST `class <Name>` of that file's CfgPatches.

**Rule** — When the config does `class WoodenPlank: Inventory_Base { inventorySlot[] += {"MySlot"}; }`, the `+=` only adds if the VANILLA entry is read BEFORE yours, and load order is decided by `requiredAddons[]`. For EACH vanilla class you reopen, list the addon that defines it. Useful map: Container_Base/Inventory_Base -> DZ_Data; WoodenCrate -> DZ_Gear_Camping; SledgeHammer/Shovel -> DZ_Gear_Tools; Pickaxe/WoodAxe -> DZ_Weapons_Melee_Blade (not _Blunt!); WoodenPlank/WoodenLog/Nail/MetalPlate -> DZ_Gear_Consumables; ItemBook -> DZ_Gear_Books. Better still: reuse a vanilla slot and don't reopen any class.

<sub>Source: field case, 2026-08 (the original mod listed DZ_Weapons_Melee_Blunt instead of _Blade)</sub>

---

### Empty `class Cargo {}` inherits the parent's cargo 🔇

**Symptom** — A kit that "has no cargo" becomes a phantom backpack with 50 slots, carriable in hand. No error: the config compiles and the comment in the code says the opposite of the behavior.

**Detect** — Walk the inheritance chain up to the root looking for whoever declares `itemsCargoSize[]`. Real finding: a `MyMod_Workbench_Kit: WoodenCrate` inherited `itemsCargoSize[]={10,5}` from P:\DZ\gear\camping\config.cpp:10178-10183. In game: open the item's inventory and see whether it accepts cargo.

**Rule** — In Arma/Enfusion config, redeclaring a subclass with no content implicitly inherits the same-named subclass of the parent. To really zero it: `class Cargo { itemsCargoSize[]={0,0}; };`. Deleting `class Cargo` only works when NO ancestor declares itemsCargoSize (the case of Container_Base/Inventory_Base, P:\DZ\data\config.cpp:3302 and :3145). General rule: check the inheritance chain, never assume.

<sub>Source: field case, 2026-08; vanilla P:\DZ\gear\camping\config.cpp:10178-10183 and P:\DZ\data\config.cpp:3302/:3145</sub>

---

### `static const int = ARGB(...)` initializes as 0 🔇

**Symptom** — The color comes out as 0 = alpha 0 = transparent/invisible. Seen in a real dynamic-events mod: map markers with color=0, invisible in game. Compiles without a warning.

**Detect** — Print the constant at runtime: it comes out 0. grep the repo for `static const int .*=.*\(`: any static const initialized with a FUNCTION CALL is suspect.

**Rule** — `ARGB(a,r,g,b)` is a NATIVE function, not a constant expression: the static const initializer doesn't run it. Compute the color at runtime (inside a method) or use an int literal. Apply the same suspicion to any static const initialized with a function call.

<sub>Source: field case (in-game)</sub>

---

### `RegisterRecipies` without super wipes the vanilla recipes 🔇

**Symptom** — Without the super, the game loses ALL hand-crafting recipes: no error, nothing is craftable anymore. With the name spelled `RegisterRecipes` (the correct English spelling), the override doesn't take and your recipe is never registered, also silently.

**Detect** — `grep -rn "RegisterRecip" --include=*.c` in the repo: it must be `RegisterRecipies` (with the extra "i", as in vanilla) and the first line of the body must be `super.RegisterRecipies();`. In-game test: does any vanilla recipe (tearing rags) still work?

**Rule** — `modded class PluginRecipesManagerBase { override void RegisterRecipies() { super.RegisterRecipies(); RegisterRecipe(new X); } }`. Modding the BASE covers the concrete PluginRecipesManager, which only inherits from it. `RegisterRecipe` is protected, but a modded class sees protected members. Template recipe for a base-building kit: CraftFenceKit.

<sub>Source: vanilla P:\scripts\4_world\classes\recipes\...\pluginrecipesmanagerbase.c:14 and P:\scripts\4_world\classes\recipes\recipes\craftfencekit.c</sub>

---

### Material_* slot with a selection: the attached item is invisible 🔇

**Symptom** — The item attaches normally to the vanilla slot but doesn't show on the model: it's invisible. Breaks nothing and logs nothing.

**Detect** — Read the slot's CfgSlots entry in P:\scripts\config.cpp and check whether it has `selection="..."`; check whether your p3d has that selection. In game: attach and look at the model.

**Rule** — Before declaring your own CfgSlots + `inventorySlot[] +=`, look for a vanilla slot that fits: it comes with capacity, ghostIcon and a localized displayName for free, and it removes the reopening of a vanilla class (and so the load-order dependency). `stackMax` is a property of CfgSlots, not of the item class (both limits exist; the smaller wins). For bulk material use the truck ones: Truck_01_WoodenPlanks 100 (P:\scripts\config.cpp:1548), Truck_01_WoodenLogs 50 (:1541), Truck_01_MetalSheets 40 (:1555), Material_Nails 99 (:2264). The fence ones are tiny (Material_WoodenPlanks 20, Material_WoodenLogs 2). A vanilla slot is SHARED: if you need exclusivity, then declare your own slot.

<sub>Source: validated in-game 2026-08; slots in P:\scripts\config.cpp (addon DZ_Scripts)</sub>

---

### WorkDrive /Mount exits with code 82 but did mount P: 🔇

**Symptom** — Two chained problems: (a) after a reboot P: is gone and every `P:\...` path stops existing, breaking the build and every lookup in vanilla; (b) when mounting from the terminal, WorkDrive exits with code 82 throwing an InvalidOperationException, and the script treats it as a failure, but the drive IS ALREADY mounted.

**Detect** — `Get-PSDrive P` (or `Test-Path P:\scripts`) after running the mount. Don't use the exit code as the criterion.

**Rule** — Mount without opening the GUI, without admin: `& "C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools\Bin\WorkDrive\WorkDrive.exe" /Mount`. It mounts the project-drive source folder configured in DayZ Tools, and the exception (Console.ReadKey in a process with no console) happens at the END, after the mount. Verify with Get-PSDrive, never with the exit code.

<sub>Source: measured 2026-08. Vanilla: code in P:\scripts\ and configs in P:\DZ\</sub>

---

### MakePbo without -P hangs on "Press the ANY key"

**Symptom** — In a non-interactive session the command finishes its work and stays stuck waiting for a key; the agent hits the timeout and concludes the build failed, when the PBO may already have been written.

**Detect** — The process doesn't return and there's no more output after the file listing. Check whether the target .pbo exists despite the timeout.

**Rule** — Always pass `-P` (P = Don't pause): `& "C:\Program Files (x86)\Mikero\DePboTools\bin\MakePbo.exe" -P "-@=<Prefix>" <sourceDir> <dest.pbo>`

<sub>Source: measured on MakePbo (Mikero DePboTools)</sub>

---

### AddonBuilder.exe opens its GUI and never ends from the CLI

**Symptom** — Even with `source dest -clear -packonly -prefix=X`, it opens the "Addon Builder" window and waits. The process responds, never ends, the command hits the timeout and produces nothing.

**Detect** — Command with no return + no .pbo at the target. If there's a graphical session, the Addon Builder window shows up.

**Rule** — Don't use AddonBuilder.exe from an agent or a session without UI. Use MakePbo.exe (Mikero) with `-P`.

<sub>Source: verified 2026-08</sub>

---

### PowerShell 5.1: `2>&1` on MakePbo kills a build that succeeded

**Symptom** — The PBO is generated correctly, but the PowerShell script dies with NativeCommandError and reports failure.

**Detect** — A NativeCommandError right after MakePbo, with the .pbo present and updated at the target.

**Rule** — In PowerShell 5.1, don't redirect a native executable's output with `2>&1`: each stderr line becomes an ErrorRecord and `$?` turns `$false` even with exit 0. stderr is already captured; don't redirect it.

<sub>Source: measured on Windows PowerShell 5.1</sub>

---

### ConfigIsExisting only in CfgVehicles rejects weapons and ammo

**Symptom** — A guard for "this classname is gone, the mod was removed" flags an item that is perfectly present: `[CRITICAL] Class Glock19 no longer exists` with the Glock19 in game. The log lies and the item disappears from the system.

**Detect** — Test the check with three classes: an item (CfgVehicles), a weapon (Glock19, CfgWeapons) and a magazine/ammo (CfgMagazines). If only the item passes, the guard is wrong. grep the repo for `ConfigIsExisting("CfgVehicles`.

**Rule** — A DayZ class can live under three roots. Check all three, in the order vanilla uses in object.c:430 (Object.HasAnimation): CfgVehicles, then CfgWeapons, then CfgMagazines. Weapons in CfgWeapons; magazines and ammo in CfgMagazines; items, containers, clothing and flashlights in CfgVehicles. Other places where vanilla assumes the right root without warning: weapon_base.c:200 (ConfigGetFloat CfgMagazines ... weight), magazine.c:29, dayzgame.c:3823 (ConfigGetText CfgWeapons ... chamberableFrom).

<sub>Source: cost a full test cycle on a real mod, 2026-08; vanilla P:\scripts\...\object.c:430</sub>

---

### `type=servermod` breaks the client that loads the PBO

**Symptom** — With `type = "servermod"`, the PBO only loads on the dedicated server; if a player puts that mod in, it breaks. The setup proven in practice is `mod` on both sides.

**Detect** — `grep -rn 'type\s*=\s*"servermod"'` in the config.cpp files of the Client/Server pair. Careful: the header COMMENT of the server repo's config.cpp may say servermod and be outdated; what counts is `CfgMods.type`.

**Rule** — In mods split into Client + Server, BOTH CfgMods use `type = "mod"`, including the server repo. The split is logical (authority on the server via modded class + `IsServer()` guards + hooks), not by type. Both PBOs load everywhere; what hides the sensitive logic from the client is the code organization, not servermod.

<sub>Source: field practice across client+server split mods, 2026-07</sub>

---

### Variable named out/local/in breaks with a ";" error ⛔

**Symptom** — Error `Broken expression (missing ';'?)` pointing at a declaration line that is obviously correct (e.g. `vector local = ...;` or `string out;`). The programmer wastes time hunting for a semicolon.

**Detect** — `grep -rnE "\b(int|float|bool|string|vector|auto)\s+(local|out|inout|owned|proto|native|event|sealed)\s*[=;]" --include=*.c` in the repo.

**Rule** — `out`, `inout`, `in` and `local` are reserved words in Enforce and can't be a local variable name (`out`/`inout` are only valid as a PARAMETER modifier in a signature). Rename (`outStr`, `localPos`). Rule of thumb: if the compiler complains about ";" on a declaration that is correct, the variable name is a reserved word.

<sub>Source: seen in two real base-building mods, 2026-07</sub>

---
