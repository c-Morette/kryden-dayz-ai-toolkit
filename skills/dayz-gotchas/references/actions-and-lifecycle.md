# Actions, lifecycle and damage

12 traps · **9 silent** (they don't emit a single log line).

Legend: 🔇 fails in total silence · ⛔ doesn't compile · no mark: fails at runtime with a visible symptom or log line

---

### A custom action without a modded ActionConstructor doesn't exist 🔇

**Symptom** — The action prompt never appears in game, on any item, for any player. The mod compiles, the server starts, and the log is SPOTLESS: zero SCRIPT (E), zero warnings. Nothing points at the problem.

**Detect** — `grep -rn "modded class ActionConstructor" <mod>/Scripts`: if it comes back empty and there's some `AddAction(MyAction)` in a `SetActions()`, the action is dead. Searching the .RPT is useless: there is no line at all.

**Rule** — There are TWO registrations, not one. Global (makes it exist): `modded class ActionConstructor { override void RegisterActions(TTypenameArray actions) { super.RegisterActions(actions); actions.Insert(MyAction); } }`. Per entity (makes it appear on that item/target): `AddAction(MyAction)` in `override void SetActions()`.

<sub>Source: vanilla P:\scripts\4_world\classes\useractionscomponent\actionconstructor.c:3-13 (ActionConstructor.ConstructActions). Real case: a custom single-use action on an item, 2026-08 (in-game)</sub>

---

### OnPlayerLoaded is not a "character ready" hook 🔇

**Symptom** — The code runs more often than it should and on the wrong machine: it also fires on the CLIENT, for each remote proxy of another player. `GetIdentity()` may come back null and the inventory loaded from the DB doesn't exist yet. No error; just wrong/duplicated behavior.

**Detect** — `grep -rn "OnPlayerLoaded" <mod>/Scripts`. To confirm, put `Print("X " + GetGame().IsServer() + " " + GetIdentity())` inside the override and watch the lines that come out in the client log.

**Rule** — Don't use `PlayerBase.OnPlayerLoaded()` as "character ready": it is scheduled from the constructor via CallQueue. Use `MissionServer.StartingEquipSetup(PlayerBase player, bool clothesChosen)` for a NEW character and `MissionServer.OnClientReadyEvent(PlayerIdentity identity, PlayerBase player)` for a RELOG. In both, `GetIdentity()` is already valid, and what tells new from relog is the engine, through the EventType: you don't infer anything.

<sub>Source: vanilla P:\scripts: playerbase.c:2403 (OnPlayerLoaded), missionserver.c:527 and :523 (StartingEquipSetup inside EquipCharacter), missionserver.c:586 (OnClientReadyEvent), :492/:588 (SelectPlayer)</sub>

---

### A magic CallLater to wait for the character 🔇

**Symptom** — Works in the dev's test and fails on a full or laggy server: sometimes the item isn't given, sometimes it's given twice. No log: the wait simply expired before or after the real state.

**Detect** — `grep -rniE "CallLater\(.*(1[0-9]{3}|[2-9][0-9]{3})" <mod>/Scripts`: any round delay (1700, 2000, 5000) near player spawn/equip code is the wrong pattern.

**Rule** — There is no correct delay. `StartingEquipSetup` is synchronous and runs in the same frame as `OnClientNewEvent`, AFTER the `CreateAttachmentEx` of the clothes; `OnClientReadyEvent` runs with `OnStoreLoad`/`AfterStoreLoad` already done. Replace the CallLater with the hook.

<sub>Source: verified against vanilla P:\scripts, 2026-08; replaces the CallLater(1700) pattern used by several mods</sub>

---

### The character is only written to players.db on logout 🔇

**Symptom** — A crash or a hard server restart puts EACH player back exactly at their last-logout state: items received, unlocks activated and session progress are gone. No error in the log: from the script's point of view everything worked.

**Detect** — Give the item / change the state, DON'T log out, kill the server process, start it again and join. If you're back to the previous state, the data depended on the character save. `grep -rn "CharacterSave\|PlayerBase.Save"` in vanilla shows the single chain.

**Rule** — There is no periodic character save in script. Single chain: hive.c:19 `CharacterSave(Man)` <- playerbase.c:7715 `PlayerBase.Save()` <- missionserver.c:697 `MissionServer.PlayerDisconnected()`. For idempotent delivery against rollback, override `PlayerBase.Save()` (it's script and returns bool): it's the only reliable "this went to disk" hook.

<sub>Source: vanilla P:\scripts: hive.c:19, playerbase.c:7715, missionserver.c:697</sub>

---

### Save() refuses a dead or restrained player 🔇

**Symptom** — The player logs out restrained (or dead) and everything the session changed on them is lost, even with a clean logout. Silent: there's no line saying "save refused".

**Detect** — Read playerbase.c:7713 in vanilla: the guard is `GetPlayerState()==ALIVE && !IsRestrained()`. Reproduce by restraining the player before logout.

**Rule** — Never assume logout == saved. If the state must survive, persist it outside the character (own file / own entity) or handle the restrained/dead case explicitly.

<sub>Source: vanilla P:\scripts\...\playerbase.c:7713</sub>

---

### CanDisplayAttachmentSlot doesn't hide the slot 🔇

**Symptom** — The override is written, compiles, and the slot keeps showing in the inventory exactly as before. No log. The method is simply never called by whatever draws the inventory.

**Detect** — `grep -rn "CanDisplayAttachmentSlot" <mod>/Scripts`: if it's there, it's already wrong. Confirm with a Print inside the override: it never comes out.

**Rule** — PlayerContainer never calls `CanDisplayAttachmentSlot`, and `InventorySlots.GetShowForSlotId` is static and global per slot id (it affects everyone). The real hook is `modded class PlayerContainer` (5_Mission layer) in `SetPlayer` (playercontainer.c:661) and `ItemAttached` (:124). The same PlayerContainer serves your own inventory and that of whoever gets knocked out (vicinitycontainer.c:512).

<sub>Source: vanilla P:\scripts: playercontainer.c:661 and :124, vicinitycontainer.c:512</sub>

---

### Death work after the super in EEKilled 🔇

**Symptom** — The death logic (save loot, log, transfer an item) reads state that is already destroyed or already saved as dead: empty or half-done result, no error. And it doesn't fire on the death paths the dev didn't foresee.

**Detect** — `grep -rn "EEKilled" <mod>/Scripts` and check whether the code is BEFORE the super. Test the three paths: normal death, disconnecting while unconscious, and respawn.

**Rule** — Put the death work at the TOP of the EEKilled override, before the super and before `GetHive().CharacterKill()` (playerbase.c:1213). There is no corpse entity: CorpseData keeps a reference to the SAME PlayerBase (corpsedata.c:14) and `ReplaceOnDeath()` is false for players: the body is lootable as soon as health hits zero. Two other paths go through EEKilled: missionserver.c:744 (unconscious disconnect) and :608 (respawn).

<sub>Source: vanilla P:\scripts: playerbase.c:1213, corpsedata.c:14, missionserver.c:744 and :608</sub>

---

### EEHealthLevelChanged runs on the client too 🔇

**Symptom** — Side effect duplicated or run on the client: sound/particle/log/RPC going out twice, or server state being touched from the player's machine. No error in the log.

**Detect** — Put `Print("HLC " + GetGame().IsServer())` at the top of the override and destroy a part with the client connected: a line comes out on both sides.

**Rule** — `EEHealthLevelChanged(old,new,zone)` (entityai.c:1032) only fires once the zone has reached STATE_RUINED and runs ON BOTH SIDES: in vanilla the IsServer guard itself comes AFTER the super (basebuildingbase.c:503). Put the context guard at the top of your override, don't rely on the super. And when comparing the zone, remember zone == part name, in lowercase (basebuildingbase.c:507: `string part_name = zone; part_name.ToLower();`).

<sub>Source: vanilla P:\scripts: 3_game/entities/entityai.c:1032, basebuildingbase.c:503 and :507</sub>

---

### Comparing dmgZone without lowercasing it 🔇

**Symptom** — The per-zone/per-part rule never matches: the whitelisted piece is treated as if it weren't on the list, or vice versa. String comparison fails silently.

**Detect** — `grep -rn "dmgZone ==\|zone ==" <mod>/Scripts` and check for a ToLower before it. Print the raw dmgZone value received in the hook and compare it with the string literal in the code.

**Rule** — zone == construction part name, and vanilla compares in lowercase (basebuildingbase.c:507). Double care in Enforce: `ToLower()` modifies the string IN PLACE and returns int (the length): it does not return a new string. Do `zone.ToLower();` on its own line and only then compare.

<sub>Source: vanilla P:\scripts\...\basebuildingbase.c:507</sub>

---

### FullRepair reverts the damage, it doesn't prevent it

**Symptom** — The "protected" base flickers: the part takes the damage, shows damaged/destroyed for an instant and comes back to normal. Visual and network flicker, and a real window in which the piece was destroyed.

**Detect** — Copied a pattern from someone else's mod? `grep -rn "FullRepair\|SetHealth"` next to `EEHitBy`. Shoot the wall and watch the model: if it gets damaged and restored, it's reverting.

**Rule** — Trap of copying someone else's mod: a popular base-maintenance mod protects bases with `modded class BaseBuildingBase` -> `EEHitBy` + early return without super + a `FullRepair()` that restores SetHealth zone by zone. It works, but it's REVERTING, not preventing: what does the job there is the SetHealth, not the early return. Use `EEOnDamageCalculated`, which does the right thing the first time.

<sub>Source: field comparison against a third-party maintenance mod</sub>

---

### `GetCompEM()` on an item without an EnergyManager: borrowed "electric" action pieces dereference NULL

**Symptom** — A custom action on a non-electric item (a key, card, document, kit) reuses a piece written for electric devices: the vanilla action component `CASingleUseTurnOnPlugged` (alarm clock, kitchen timer, transmitter), or an `ActionCondition` / `CanContinue` copied from an electric action without its guard. On an electric test item it works; on the real item it doesn't. `GetCompEM()` itself never warns: a missing component is just NULL, by design. What you see depends on where the NULL gets dereferenced:
- in an `ActionCondition`, `ActionConditionContinue` or `CanContinue`: a NULL-pointer script error each time it is evaluated for that item, and the action doesn't behave;
- in the action component of a **continuous** or **interact-loop** action: the component's `Execute()` runs on every tick of the loop and hits the NULL there;
- in the action component of a **single-use** action: nothing happens at all. In current vanilla `ActionSingleUseBaseCB` never calls the component's `Execute()` (it only calls `Init()`), so the NULL is latent, and so is any custom logic you put in that `Execute()`. It fires the day the component is reused in a continuous or loop action.

**Detect** —
1. `grep -rn "GetCompEM()\." <mod>/Scripts` and check that every hit has `HasEnergyManager()` (or a null check of `GetCompEM()`) on the same entity before it.
2. `grep -rn "TurnOnPlugged" <mod>/Scripts`: any hit on an item without an EnergyManager is this bug.
3. Config side: does `CfgVehicles <YourItem>` (or an ancestor) declare `class EnergyManager`? The component only exists if it does: the `EntityAI` constructor creates it only when `ConfigIsExisting("CfgVehicles <type> EnergyManager ")` is true.
4. Logs: a NULL dereference shows up as `SCRIPT    (E): Virtual Machine Exception` followed by `Reason: NULL pointer to instance` and a stack trace, in the RPT and in the `crash_*.log` of the profile folder. Search with `SCRIPT\s+\(E\)` or `NULL pointer to instance`, not the literal `SCRIPT (E)` (the log pads it with spaces).

**Rule** — Guard every `GetCompEM()` chain with the vanilla idiom: `item.HasEnergyManager() && item.GetCompEM().CanWork()` (actionturnonwhileinhands.c:52), or check the returned pointer (`!item.GetCompEM() || !item.GetCompEM().IsWorking()`, actionbreaklongwoodenstick.c:32). Don't borrow callbacks or components from electric-device actions for an item without an EnergyManager: a single-use action with no electric meaning keeps the default `ActionSingleUseBaseCB` (component `CASingleUse`) and does its work in `OnExecuteServer`. Where vanilla skips the guard (actionrepositionpluggeditem.c:44, `CanContinue` calls `ent.GetCompEM().GetCordLength()` unguarded) it's because that action's targets always have the component; your item doesn't. The same goes for every `GetComp*()` getter: `GetCompBS()` also returns NULL when the component is missing (entityai.c:3399-3404).

<sub>Source: verified against vanilla source, not confirmed in-game for this entry. Vanilla P:\scripts: 3_game\entities\entityai.c:208-224 (EntityAI constructor creates the component only if the config class exists), :3409-3417 (GetCompEM returns NULL without it), :3420-3423 (HasEnergyManager); 4_world\classes\useractionscomponent\actioncomponents\casingleuseturnonplugged.c:9 (Execute dereferences GetCompEM() with no check); vanilla pairs that component only with electric items: actionturnonalarmclock.c:5, actionturnoffalarmclock.c:5, actionresetkitchentimer.c:5, actionturnontransmitter.c:5; a component's Execute() is only driven by AnimatedActionBase.Do() (animatedactionbase.c:395-454 -> ProgressActionComponent :72-78), which only the continuous and interact-loop callbacks call (actioncontinuousbase.c:23, actioninteractloopbase.c:14); ActionSingleUseBaseCB.InitActionComponent (actionsingleusebase.c:8-21) only calls Init(). Log format of NULL dereferences measured on real client logs, 2026-11. Origin: a real single-use action on a non-electric item was rewritten to drop the borrowed component.</sub>

---

### Damage hooks that don't exist in the engine ⛔

**Symptom** — Compile error in the .RPT (`Method X not found` / `Undefined variable`), or worse: the agent writes the plausible name, the dev accepts it and only finds out at build time.

**Detect** — Before writing, grep the vanilla dump P:\scripts for the exact symbol. If it's not there, it doesn't exist.

**Rule** — Names agents invent that do NOT exist: `OnPartDamaged`, `DestroyConstructionPart`, `GetConstructionPartByDamageZone`, `ComputeDamage`, `DamageDestroyed` as a hook (only the getter `IsDamageDestroyed()` exists, object.c:977) and any setter on `TotalDamageResult`. The real converters are `GetDamageZoneNameByComponentIndex(component)` (object.c:1160) and `DamageSystem.GetDamageZoneFromComponentName(entity, component, out zone)` (damagesystem.c:76, inverse at :104). Careful: `ProcessDirectDamage(..., string componentName, ...)` (object.c:1134) actually receives the DamageZone name: the engine's own doc warns "NOT a component name, actually!".

<sub>Source: vanilla P:\scripts: object.c:977, :1134, :1160, 3_game/damagesystem.c:76 and :104</sub>

---
