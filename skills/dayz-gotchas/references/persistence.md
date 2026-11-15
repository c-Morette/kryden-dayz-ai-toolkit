# Persistence, save and economy

13 traps · **12 silent** (they don't emit a single log line).

Legend: 🔇 fails in total silence · ⛔ doesn't compile · no mark: fails at runtime with a visible symptom or log line

---

### OnStoreSave doesn't save cargo or attachments 🔇

**Symptom** — You capture the blob of a loaded weapon or of a container and restore it: the entity comes back, but without scope, without magazine, without ammo, without contents. No SCRIPT (E). A test that only checks "wrote and read back without error" PASSES and reveals nothing.

**Detect** — `grep -rn "OnStoreSave"` in your mod and see whether the blob is being used as an item snapshot. In game: capture a weapon with scope+magazine, delete it, restore it: if it comes back bare, this is it. In vanilla, read P:\scripts\4_world\entities\itembase.c:3221 and confirm there's nothing about children.

**Rule** — The blob covers only the item itself (quickbar bind, agents, RemotelyActivatedItemBehaviour and, via SaveVariables/WriteVarsToCTX: quantity, wet, liquid type, color, cleanness, temperature, frozen; on Weapon_Base also muzzle, fire modes, jam and FSM). The inventory hierarchy is persisted by the ENGINE outside the hook. To save contents, walk the tree by hand: per item store classname + position in the parent (slot for an attachment; GetOwnerCargoIndex/row/col/GetFlipCargo for cargo) + that item's blob, and recreate recursively with `CreateEntityInCargoEx` / `CreateAttachmentEx` / `CreateInInventory`.

<sub>Source: vanilla P:\scripts\4_world\entities\itembase.c:3221, P:\scripts\3_game\entities\entityai.c:2930</sub>

---

### OnStoreSave doesn't save health/damage or cartridges 🔇

**Symptom** — The restored item comes back at full health (or the config default) and the weapon comes back with no round chambered and the magazine as it came from the factory. No log. Misleading because quantity and wet DO come back (those are free), so it looks like "the blob saves state".

**Detect** — Capture a Rag with altered health and a Glock with a round chambered; restore and compare `GetHealth01("","Health")` and `GetCartridgeInfo`. If health came back 1.0 and the chamber empty, the blob doesn't cover it. Confirm by reading magazine.c:38: Magazine doesn't override OnStoreSave.

**Rule** — Copy by hand: health per zone with `GetHealth01(zone,"Health")`/`SetHealth01`, following `MiscGameplayFunctions.TransferEntityHealth` (miscgameplayfunctions.c:399), applying the global zone ("") LAST. Cartridges: read with `GetCartridgeInfo` / `GetInternalMagazineCartridgeInfo`, push with `PushCartridgeToChamber` / `PushCartridgeToInternalMagazine`. Magazine: `GetCartridgeAtIndex` on capture and `ServerStoreCartridge` on restore: `GetAmmoCount` alone loses the type and damage of each cartridge.

<sub>Source: vanilla P:\scripts\4_world\entities\manbase\..., weapon_base.c:2085 (CopyWeaponStateFrom), miscgameplayfunctions.c:399, magazine.c:38 (corrects an earlier version of this note)</sub>

---

### OnStoreLoad needs the ENGINE version, not yours 🔇

**Symptom** — You call `item.OnStoreLoad(ctx, myVersion)` with a small number (1, 2, 3). No error at the time, the item even shows up. On the next server start the entity is gone: the stream desynchronized.

**Detect** — `grep -rn "OnStoreLoad("` in your mod and look at the 2nd argument. If it isn't the value returned by `g_Game.SaveVersion()` (142 as of 2026-08, P:\scripts\3_game\global\game.c:434), it's wrong. ItemBase.OnStoreLoad branches: version >= 114 reads the quickbar bind, version < 140 re-reads the variables: a small number lands in a legacy branch and reads fields the modern OnStoreSave never wrote.

**Rule** — Store TWO versions in the file: your format's (which validates the file) and the engine's (`GetGame().SaveVersion()` at capture time), handed back to OnStoreLoad exactly as it was. Never reuse your own format counter as the `version` parameter.

<sub>Source: vanilla P:\scripts\3_game\global\game.c:434, P:\scripts\1_core\proto\serializer.c:103</sub>

---

### One blob per item: a single sequential file is a trap 🔇

**Symptom** — One item in the batch can't be recreated (classname removed, mod uninstalled) and ALL the rest of the file turns into garbage: the next restore reads shifted fields and the entities vanish on the following start. One lost item takes the whole batch with it.

**Detect** — Check whether your manifest writes N blobs into a single FileSerializer. FileSerializer has NO seek and the OnStoreSave blob has no known size: there's no way to skip the bytes of an item that failed.

**Rule** — One file per item. That makes desynchronization structurally impossible: a failure in one item doesn't contaminate the others. (The same logic holds for lists in JSON: one JSON per entity in `$profile:Mod/Dir/<id>.json`, never one shared file.)

<sub>Source: vanilla P:\scripts\1_core\proto\serializer.c:103</sub>

---

### Restore order outside the engine's flow 🔇

**Symptom** — Restore "works", with no error at all, but the weapon comes back without its selection state, the health you applied disappears, or AfterStoreLoad doesn't find the magazine. Zero log in every case.

**Detect** — Run a full round-trip (capture, DESTROY everything, re-read from disk, restore) and compare the 4 nodes field by field: position, health, quantity, ammo and chamber. If any field comes back default despite you having written it, the order is wrong.

**Rule** — Order proven in-game (2026-08): 1) create the entity; 2) push cartridges BEFORE OnStoreLoad (that's what `Weapon_Base.CopyWeaponStateFrom` does); 3) OnStoreLoad with the engine version stored in the blob; 4) children, so the magazine exists before AfterStoreLoad; 5) AfterStoreLoad (on a weapon it does SyncSelectionState and queries GetMagazine); 6) health and ammo LAST, so they aren't undone by a damage system reinit.

<sub>Source: validated in-game 2026-08; vanilla P:\scripts\4_world\entities\itembase\weapon_base.c:2085</sub>

---

### The blob carries the previous owner's quickbar and PersistentID 🔇

**Symptom** — A restored item shows up bound to a quickbar slot of ANOTHER character, or the EnergyManager references a power source that no longer exists. Nothing visibly breaks, it just gets weird.

**Detect** — `ItemBase.OnStoreSave` branches on `GetHierarchyRootPlayer()`: if the item was in a player's hierarchy it writes true + quickbar index, otherwise it writes false. Capture an item from a player's HANDS and restore it on the ground: the index travels with it. `EntityAI.OnStoreSave` stores the power source's `GetPersistentID`.

**Rule** — The stream is self-describing, so this does NOT corrupt anything, but clear/ignore the quickbar bind and the energy reference after OnStoreLoad when the item changes owner. Prefer capturing items outside the player's hierarchy when you get to choose.

<sub>Source: vanilla P:\scripts\4_world\entities\itembase.c:3221, P:\scripts\3_game\entities\entityai.c:2930</sub>

---

### A container inside cargo refuses ANY item 🔇

**Symptom** — You restore an inventory tree: the first-level container goes into the safe, but the nested content never appears. `CreateEntityInCargoEx` returns null and `CreateInInventory` fails: no log, no exception. The player can't drag an item in either.

**Detect** — Call `container.GetInventory().AreChildrenAccessible()` right before inserting. If it's 0, this is it. Measured at 6 moments (same frame, +0ms, +500ms, +1700ms, +5000ms, and after 2 logins): it REFUSED every time, the value NEVER changed. It's not a race: CallLater doesn't fix it.

**Rule** — Build the subtree WHERE the children are accessible (ground, hands or attachment) and only then move the container ALREADY FULL into the destination cargo: moving a full container into cargo is allowed, only inserting into a nested container is blocked. APIs: `GameInventory.TakeEntityToTargetCargoEx(mode, cargo, item, row, col)` (inventory.c:1115), `TakeEntityToTargetCargo` without position, `CreateObjectEx` to create loose.

<sub>Source: measured in-game; vanilla P:\scripts\4_world\entities\itembase\container_base.c:19 (CanReceiveItemIntoCargo), entityai.c:1662 (AreChildrenAccessible), inventory.c:1115</sub>

---

### Backpacks and vests are not Container_Base 🔇

**Symptom** — You made a Container_Base blacklist thinking it covered the nested-cargo problem, and the contents of backpacks/vests keep vanishing silently on restore.

**Detect** — Backpacks and vests inherit from Clothing_Base, not Container_Base. `Clothing_Base.CanReceiveItemIntoCargoClothingConditions` (clothing_base.c) returns `!hierarchyParent || hierarchyParent.IsMan() || SmershException(hierarchyParent)`, i.e. they only accept cargo if the parent is the PLAYER. Test `IsInherited(Container_Base)` on a backpack: it's false.

**Rule** — Don't use a per-class blacklist. The correct rule is structural: refuse (or divert to the build-outside path) any item whose tree contains cargo content, including the grandchild under an attachment (a vest with full pouches).

<sub>Source: vanilla P:\scripts\4_world\entities\itembase\clothing_base.c</sub>

---

### SteamID64 doesn't fit in a NetSyncVariableInt 🔇

**Symptom** — The synchronized owner/member reaches the client truncated or as garbage: the menu shows the wrong owner, or nobody. No compile error and no log: int is 32-bit and a SteamID64 has 17 digits.

**Detect** — On the client, compare the value from `OnVariablesSynchronized` with the real `GetPlainId()`. If the number was cut, this is it. Any `RegisterNetSyncVariableInt` holding a SteamID is suspect.

**Rule** — Split it into 2 ints, as several community mods do: `part1 = id.Substring(0,8).ToInt()`, `part2 = id.Substring(8,9).ToInt()`; rebuild with pad-to-9 on part 2. Register BOTH ints with `RegisterNetSyncVariableInt` in the constructor, `SetSynchDirty()` on change, rebuild the cache in `OnVariablesSynchronized` (client) and after `OnStoreLoad` (server). Persist the 2 ints in the binary OnStoreSave/OnStoreLoad: super FIRST, same order, starting with an int of your own version, and default + `return true` if bytes are missing, never `return false`.

<sub>Source: validated in-game 2026-07 in a base flag/ownership system</sub>

---

### EEInit runs BEFORE OnStoreLoad 🔇

**Symptom** — You register the entity in a global index/registry in EEInit and on server boot the index holds empty or default data: the rule that depends on it (e.g. "one base per player") starts accepting everything. No log.

**Detect** — Put a Print of the persisted field inside EEInit and inside OnStoreLoad and compare the order in the RPT: EEInit comes first, with the field still zeroed. `grep -rn "EEInit"` in your mod and see whether any of them reads state that came from OnStoreSave.

**Rule** — Register at boot in `EEOnAfterLoad`, never in `EEInit`. Create the data only on the explicit action (claim), clean it up in `EEDelete` (server-guarded), and reconcile orphans via CallLater.

<sub>Source: measured in-game (RPT order)</sub>

---

### TimeLogout lives in globals.xml and only reloads on restart 🔇

**Symptom** — You edit the logout timer, save, and nothing changes in game. You waste time looking for the key in serverDZ.cfg, cfggameplay.json and init.c: none of the three has it.

**Detect** — The file is `mpmissions/<mission>/db/globals.xml`: `<var name="TimeLogout" type="0" value="15"/>` (together with TimeLogin, TimeHopping, TimePenalty). The EFFECTIVE value appears in the vanilla log: `[Logout]: New player <uid> with logout time 15` (missionserver.c:640).

**Rule** — Edit globals.xml and RESTART: the Central Economy reads it at server start. There's no script API to read that file; script discovers the value at runtime through the `logoutTime` parameter of `ClientDisconnectedEventParams = Param4<PlayerIdentity, Man, int logoutTime, bool authFailed>` (P:\scripts\3_game\gameplay.c:426). A mod should capture that value instead of relying on the admin to cross-check two files. Common range on real servers: 15 to 30 s; don't assume.

<sub>Source: vanilla P:\scripts\3_game\gameplay.c:426, missionserver.c:640</sub>

---

### LogoutRequestTime() doesn't create the countdown screen 🔇

**Symptom** — The timer starts on the server, but the player sees no countdown and has no cancel button. They simply get dropped to the menu when the mod calls `AbortMission()`. No error.

**Detect** — `MissionGameplay.StartLogoutMenu(time)` starts with `if (m_Logout)` and does nothing without it. What creates `m_Logout` is `CreateLogoutMenu()`, called ONLY by the Exit button of the in-game menu (P:\scripts\5_mission\gui\ingamemenu.c:259,270), passing the menu as parent.

**Rule** — If the mod needs a visible countdown and/or Cancel, it has to build its own UI: the vanilla Cancel lives inside the LogoutMenu and only exists through the Exit button path. `LogoutRequestTime()` alone is just the request to the server.

<sub>Source: vanilla P:\scripts\5_mission\gui\ingamemenu.c:259,270</sub>

---

### A forced logout with N greater than TimeLogout deletes the body

**Symptom** — The player watches their own character VANISH in front of them and gets disconnected from the server: the opposite of the "polite logout" the mod wanted.

**Detect** — In the RPT, `Finish script disconnect` comes out exactly TimeLogout seconds after `Start script disconnect`: the timer counts from the REQUEST, not from the client leaving. If your AbortMission is scheduled for later than that, `UpdateLogoutPlayers` has already run the whole `PlayerDisconnected`: Save, CharacterExit, HandleBody (which DELETES the body) and DisconnectPlayer, with the player still in the world.

**Rule** — A mod that calls `LogoutRequestTime()` and then `AbortMission()` after N seconds needs N SMALLER than the effective TimeLogout. With a smaller N the client leaves first and the server only finishes saving afterwards. Read TimeLogout from the log or capture it at runtime before choosing N.

<sub>Source: field case in a server-restart mod (in-game)</sub>

---
