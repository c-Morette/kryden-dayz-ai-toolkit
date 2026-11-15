# Base building, pieces, hologram and p3d

45 traps · **40 silent** (they don't emit a single log line).

Legend: 🔇 fails in total silence · ⛔ doesn't compile · no mark: fails at runtime with a visible symptom or log line

---

### The piece's config can't inherit from Fence 🔇

**Symptom** — The custom gate never opens. And building one of YOUR parts marks a Fence part as built: the sync state gets corrupted (parts appear/disappear wrongly). Not one log line.

**Detect** — `grep -n "class .*: *Fence" config.cpp`: if the piece's CONFIG inherits from Fence, Fence's `class Construction` merges with yours. Check whether any of your `id` values falls in 1-11 (Fence's ids).

**Rule** — The config inherits from `BaseBuildingBase` (which has no Construction) and defines everything from scratch with clean ids 1..N: attachments[], GUIInventoryAttachmentsProps, AnimationSources, DamageSystem, physLayer/carveNavmesh/createProxyPhysicsOnInit/createdProxiesOnInit. Only the SCRIPT does `extends Fence`. Config and script can have different parents (just like FenceKit: config Inventory_Base, script KitBase). An inherited config subclass CANNOT be deleted.

<sub>Source: field case; vanilla P:\scripts\4_world\entities\itembase\basebuilding\basebuildingbase.c (mask = 1<<(id-1)) and fence.c (wall_gate = is_gate, id 5)</sub>

---

### Two is_gate parts: GetGateConstructionPart picks the wrong one 🔇

**Symptom** — With a door AND a gate on the same wall, the gate logic always operates on the first `is_gate` part DECLARED, not the built one: it opens/locks the wrong leaf.

**Detect** — Count how many parts have `is_gate=1` in `class Construction`. Two or more = bug. `GetGateConstructionPart()` (construction.c) returns the FIRST.

**Rule** — `override int CheckGateState()` in the pieces' base class, iterating the names of the is_gate parts (a virtual `GetGatePartNames()`) and using the one that is `IsBuilt()` (computing FULL/PARTIAL the way vanilla does). `GetGateRotateSelections()` returns the rotate selections of all leaves. Mutually exclusive leaves (wood x metal) use crossed `conflicted_parts` and ONE single rotation source (same `source` and `axis`, different `selection`): zero extra code.

<sub>Source: field case; vanilla construction.c, fence.c</sub>

---

### The CheckFenceOpened poll runs forever with your own selection 🔇

**Symptom** — After the first Open, the server keeps a `CallLater(...,0,true)` running forever per opened piece. No log; it degrades the tick over time.

**Detect** — grep for `CheckFenceOpened`/`CheckFenceClosed` in the piece's class. If they're not overridden and the p3d doesn't have the `Wall_Gate_Rotate` selection, `GetAnimationPhase("Wall_Gate_Rotate")` never reaches 100.

**Rule** — Two ways out. (a) A reference base-building mod's pattern: `OpenFence()/CloseFence()` only call your own `AnimateGate(bool)`, WITHOUT `super`, and `CheckFenceOpened(){}` / `CheckFenceClosed(){}` stay EMPTY (without super the poll is never registered); the client animates on its own via `Fence.OnVariablesSynchronized`. (b) Keep `super.OpenFence()` and override both checks to poll YOUR selection. Never leave the vanilla poll active with your own p3d.

<sub>Source: field case; vanilla fence.c (OpenFence fires 11 hardcoded SetAnimationPhase calls; GATE_ROTATION_ANGLE_DEG=100 at fence.c:13)</sub>

---

### model.cfg: source is the part name, never "user" 🔇

**Symptom** — The piece spawns with ALL parts visible; `SetAnimationPhase(part, 1)` hides nothing. No error at all.

**Detect** — In model.cfg, in the `type="hide"` animation, read `source=`. If it says `source="user"`, it binds to nothing. With `initPhase=1` the part should be born hidden WITHOUT script: if everything shows on spawn, the culprit is model.cfg/selection/binarize, not the construction logic.

**Rule** — The SAME string in 4 places: `class <part_name>` in the config's `AnimationSources` (inheriting `AnimSourceHidden` -> `source="user"`, `initPhase=1`) == `source` in model.cfg == the argument of `SetAnimationPhase` == the part name in `class Construction` == the `selection` in the p3d. `"user"` is the source TYPE in the config, not a NAME. The animation's class name in model.cfg is free. Validate the hide/show in Object Builder before packing.

<sub>Source: field case; vanilla construction.c (Show/HideConstructionPart)</sub>

---

### A CfgModels class is a global namespace (Door.p3d) 🔇

**Symptom** — The piece stops hiding/animating parts (or animates them wrong) depending on which mods are loaded. Last to load wins. Nothing in the log.

**Detect** — `grep -n "^class " model.cfg`: if the class is `Door`, `Wall`, `Floor`, `Roof`, it collides with vanilla and with every other mod, because the CfgModels namespace is global.

**Rule** — Prefix the p3d FILE (`MiniDoor.p3d`, not `Door.p3d`). The rename costs 2 lines: the `class` in model.cfg and the entity's `model =` in config.cpp; then `CfgConvert -bin` on both. It doesn't touch proxies/holograms that already have their own name, nor the folder, nor the `skeletonName`.

<sub>Source: field case</sub>

---

### lockable=1 locks the slot, it doesn't consume material 🔇

**Symptom** — After building the part, the player can no longer take that material out of the construction (not even the surplus) and the `ActionTakeMaterialToHands*` actions disappear.

**Detect** — `grep -n "lockable" config.cpp`: it may only appear inside the `is_base` part.

**Rule** — `Construction.TakeMaterialsServer` reads the flag and, if set, SKIPS the quantity deduction and does `GetParent().GetInventory().SetSlotLock(slot, true)`. That's the mechanism that holds the logs in the base and returns them on dismantle: correct there, a bug in any other part (leaf, floor, hatch, metal tier). Without the flag the `else` branch applies: quantity deducted on build and returned on dismantle by `ReceiveMaterialsServer`. It sneaks in by copying the base's `Materials` block.

<sub>Source: field case; vanilla construction.c:692-703 (with flag) and :706-719 (without flag)</sub>

---

### Fence.IsPlayerInside blocks the custom piece's inventory 🔇

**Symptom** — The piece is visible in the world but has no inventory on TAB, materials don't show up, it doesn't build and doesn't dismantle. Easy to confuse with "a LOD is missing": it's not the LOD.

**Detect** — The class does `extends Fence` and does NOT override `IsPlayerInside`? Then it inherits hardcoded geometry (`GetCollisionBox()` + `GetDirection()` + a 0.2-2.2 m height window) calibrated for the vanilla fence's shape. `BaseBuildingBase` returns true on all 4 checks; it's `Fence` that hardens them.

**Rule** — Centralize the overrides in the pieces' BASE class (not just the flat ones, or wall/half-wall/ramp won't build). Vertical: `IsPlayerInside` = `!IsFacingPlayer` + distance to the `center` memory point < 1.0 m. Flat/irregular: distance < 1.5 m only, plus `IsFacingPlayer`->false, `IsFacingCamera`->false, `HasProperDistance`->true. Don't loosen the distances (players would dismantle from far away / from the opposite side). Without the `center` memory point in the p3d the check becomes permissive. Signatures: `IsPlayerInside(PlayerBase,string)`, `IsFacingPlayer(PlayerBase,string)`, `IsFacingCamera(string)`, `HasProperDistance(string,PlayerBase)`.

<sub>Source: field case; vanilla fence.c:615, vicinitycontainer.c:380/552, miscgameplayfunctions.c:951, actiondismantlepart.c:175</sub>

---

### The DamageZone name must be the part name 🔇

**Symptom** — The part takes damage and reaches "ruined" but is never destroyed, or it destroys the wrong part (the one inherited from Fence).

**Detect** — Compare 1:1 each `class <zone>` in `DamageZones` with the part name in `class Construction` (lowercase, identical string). Inheriting from Fence brings a `DamageSystem` with the FENCE's part names.

**Rule** — `EEHealthLevelChanged` uses the name of the ruined zone as the part name for `Construction.DestroyPartServer`: zone name == part name. `componentNames[]` must list real p3d components. Weapon immunity = zone PRESENT with `damage=0` on all three types (Projectile/Melee/FragGrenade), never omit the zone. A piece with damage=0 on every part is indestructible on purpose (build/dismantle keep working): note it in the test script, or it becomes a false positive.

<sub>Source: field case; vanilla construction.c (DestroyPartServer)</sub>

---

### A selection whose name differs between the p3d's LODs 🔇

**Symptom** — The unbuilt part disappears visually but keeps stopping bullets and blocking raycasts; the DamageZone's `componentNames[]` doesn't match. No log.

**Detect** — Read the MLOD p3d straight from the binary and list the named selections per LOD (TAGG tags whose name doesn't start with `#`). Cheap shortcut: `grep -a -o "[ -~]\{3,\}" file.p3d` and check that the string appears in every LOD. Real case: `stairs` in View/Fire and `stair` in the rest.

**Rule** — Each part of `class Construction` has a selection with the EXACT name and the SAME string in ALL LODs (Visual, Geometry, View Geometry, Fire Geometry). MLOD format: "MLOD"|version|numLods, each LOD "P3DM"|header|nPoints|nNormals|nFaces|flags, points 16B, normals 12B, faces (u32 numVerts + 64B + u32 flags + asciiz texture + asciiz material), TAGG {u8 active, asciiz name, u32 len, data} up to "#EndOfFile#", and finally the resolution float.

<sub>Source: measured by parsing MLOD files</sub>

---

### A p3d without Geometry/View/Fire is not a raycast target 🔇

**Symptom** — The piece is VISIBLE but "doesn't interact": the snap doesn't lock, the cursor picks the kit or nothing, only the kit's action shows.

**Detect** — Compare the size of the exported p3d with the working one (`-Edit`): an export that's too lean = a lost LOD. Or list the LODs by the resolution float at the end of each: 0=Visual, 1e13=Geometry (proxies and part selections), 1e15=Memory (`center`, `kit_spawn_position`, `snap_0..N`, boundingbox, invview), 3e15=Roadway, 6e15=ViewGeometry, 7e15=FireGeometry.

**Rule** — The EXPORTED p3d needs Geometry + View Geometry + Fire Geometry WITH the selections. `snap_0..N` in the Memory LOD alone doesn't solve it. Roadway is NOT required to walk on top: what holds the step is the Geometry (a floor proxy validated in-game has no Roadway).

<sub>Source: field case, measured by parsing MLOD files</sub>

---

### gate_interact: View Geometry and every variant 🔇

**Symptom** — The "Open" action simply doesn't show on the gate. No log.

**Detect** — Differentiator: if NO tier works, the selection is in the wrong LOD or the ray hits a PROXY (`RaycastRVResult.hierLevel > 0` -> `ActionTarget.GetObject()` returns the proxy and `ActionOpenFence`'s `Fence.Cast(targetObject)` fails). If ONE tier works and the other doesn't, that tier is missing the selection.

**Rule** — `gate_interact` belongs to the VIEW GEOMETRY of the MAIN p3d (the action cursor does `RaycastRVProxy` with `type = ObjIntersectView` and resolves the name via `GetActionComponentNameList` without passing a LOD). It must exist in EACH leaf variant (wood and metal), or be an independent component of the opening, OUTSIDE the selections that get `hide`. No risk of it leaking onto a piece without a leaf: `CanOpenFence()` already blocks via `HasHinges()`.

<sub>Source: field case; vanilla dayzphysics.c:88, actiontargets.c:214, object.c:198, actionopenfence.c:4,28-35</sub>

---

### Animations on the same source need the same maxValue 🔇

**Symptom** — With two leaves (or the camonet slice) driven by the same source, one selection jumps straight to the final angle while the other animates smoothly.

**Detect** — In model.cfg, list `maxValue` for ALL animations that share the same `source`. Any value below 100 clamps.

**Rule** — `maxValue = 100` on every animation that shares the source, because the script sends `GATE_ROTATION_ANGLE_DEG = 100`. Sharing the source is the right technique for mutually exclusive leaves: only one exists at a time, so driving the single source always rotates the right one, with zero extra code.

<sub>Source: field case; vanilla fence.c:13</sub>

---

### Lock-dial actions are commented out in Fence.SetActions 🔇

**Symptom** — The vanilla `CombinationLock` attaches normally to the piece, but NO dial action appears: only "Attach".

**Detect** — Open fence.c:832-833: `ActionDialCombinationLockOnTarget` and `ActionNextCombinationLockDialOnTarget` are COMMENTED OUT. In vanilla they come from `combinationlock.c:509-510`, i.e. they only show when aiming at the lock ENTITY (which requires the lock rendered as a proxy).

**Rule** — `AddAction` for both in the piece's `SetActions()` + a `modded class` on both widening `ActionCondition` to accept the PIECE, using `IsLocked()` and `GetCombinationLock()`, both vanilla on Fence (fence.c:115,137), with `super` as the fallback. No new p3d contract, no lock proxy. `ActionDestroyCombinationLock` is `//!DEPRECATED` and nothing in vanilla registers it: ignore the `wall_interact` selection it asks for.

<sub>Source: field case; vanilla fence.c:832-833, combinationlock.c:509-510</sub>

---

### CanDisplayAttachmentSlot(string) is a dead overload 🔇

**Symptom** — The override compiles and does absolutely nothing: the slot keeps appearing/disappearing per the vanilla logic.

**Detect** — Check the overridden signature: the `string` one is at entityai.c:1737 and is NEVER called; the live one is the `int` one at fence.c:176.

**Rule** — Override the `int` overload.

<sub>Source: field case; vanilla entityai.c:1737, fence.c:176</sub>

---

### GUIInventoryAttachmentsProps.selection must exist 🔇

**Symptom** — The action to attach material or a lock simply doesn't show on the piece.

**Detect** — `ConstructionActionData.GetAttachmentSlotFromSelection` compares the config's `selection` with `GetActionComponentName()` under the crosshair; without a match it returns -1. Check that the string (e.g. `wall_build`, `door_build`) really exists in the p3d: `grep -a -o` on the file.

**Rule** — The `selection` of `GUIInventoryAttachmentsProps > class Attachments` must be a real p3d selection. It's part of the model contract, not just cosmetic.

<sub>Source: field case; vanilla constructionactiondata.c:250-298</sub>

---

### kit_spawn_position is the only name vanilla reads 🔇

**Symptom** — The kit returned when building the base and the unlocked combination lock spawn INSIDE the geometry, at the model's center.

**Detect** — `grep -a -o "kit_spawn_position" file.p3d`. Alternative names (`lock_spawn_pos`, from a reference mod) are ignored by vanilla.

**Rule** — Model `kit_spawn_position` in the Memory LOD. `Fence.GetKitSpawnPosition()` (fence.c:162) serves TWO consumers: `basebuildingbase.c:592-597` (CreateConstructionKit when the part is is_base) and `combinationlock.c:327` (SetPosition on unlock). For "kit at the player's feet", cache the `player` that `OnPartBuiltServer(notnull Man player, ...)` already receives and read the cache inside `GetKitSpawnPosition`: the `GetHierarchyRootPlayer()` trick from an older community base-building mod does NOT work on a piece planted in the world (the piece is its own root, the cast to `Man` gives null; tested in-game). The Code Lock mod always ignores the memory point.

<sub>Source: field case + Code Lock source; vanilla fence.c:162, basebuildingbase.c:592-597, combinationlock.c:327</sub>

---

### collision_data[] with a nonexistent point is tolerated 🔇

**Symptom** — Nothing happens. The filled-in field gives the impression that there's a collision check, and there isn't: vanilla checks the memory point exists before using it.

**Detect** — Check that the memory points listed in `collision_data[]` really exist in the p3d (`grep -a -o` on the file). Real case: `{"wall_min","wall_max"}` without the points, running in-game without complaint.

**Rule** — If you won't model the points, leave `collision_data[] = {}`: more honest than pointing at nothing.

<sub>Source: field case</sub>

---

### Per-part collision: proxy and Geometry LOD vs visual 🔇

**Symptom** — Either "my head goes through the piece and sees the other side", or geometry that keeps colliding after the part is dismantled.

**Detect** — Geometry in the MAIN p3d (outside a proxy/selection) has permanent collision and doesn't go through the system. For the see-through case, order of suspicion: (1) Geometry LOD shrunk relative to the visual: the 1st-person near plane is 0.04 m (dayzplayercamera1stperson.c:58), so a surface closer than 4 cm to the eye gets clipped and the backface shows; (2) zero thickness (slab/step as a single surface, no core); (3) an opening edge the exact size of the hole. If after enlarging ONE point still goes through, it's (2), not (1).

**Rule** — A part that needs physics when built must be a PROXY, inside the selection with the part's name, in the Geometry LOD. `createProxyPhysicsOnInit = "false"` in the config: the proxy is born without physics and gains it when built, via `Construction.UpdatePhysics` -> `AddProxyPhysics(part_name)` / `RemoveProxyPhysics`, only for `IsBuilt()` parts. Enlarge the Geometry without going past the visual (otherwise it becomes an invisible collision catching your step); Geometry needs a CLOSED volume.

<sub>Source: field case, measured by parsing MLOD files; vanilla construction.c:207-226 and :591-599, dayzplayercamera1stperson.c:58</sub>

---

### The "deployed" selection doesn't hold permanent geometry 🔇

**Symptom** — Geometry placed in the `deployed` selection disappears (or loses its physics) as soon as the base is built.

**Detect** — `ANIMATION_DEPLOYED = "Deployed"` (basebuildingbase.c:4). Vanilla gives it physics only while `!HasBase()` and removes it when the base is built (:856-869), and hides the selection in `InitVisuals`/`UpdateVisuals` (:774-781, :797-800).

**Rule** — `deployed` is the temporary stub of the deploy: don't put a ladder/permanent structure in it. If you use `createdProxiesOnInit[]={"Deployed"}`, declare the source in `class AnimationSources`: without it `SetAnimationPhase("Deployed",...)` finds nothing, the visual doesn't hide but the physics disappears (a point of attention, not an active bug in the mod where it was found).

<sub>Source: field case; vanilla basebuildingbase.c:4, :774-781, :797-800, :856-869</sub>

---

### healthLevels[] with rvmats doesn't swap the texture 🔇

**Symptom** — A damaged piece doesn't change its look, even with the 5 rvmat bands declared in the damage zone.

**Detect** — Hit a VANILLA FENCE in-game and look: it doesn't degrade either. The engine doesn't apply it; what's in BI's config is a historical leftover. Before reintroducing it, re-confirm exactly this way.

**Rule** — Leave `healthLevels[] = {{1.0,{}},{0.7,{}},{0.5,{}},{0.3,{}},{0.0,{}}}`: the bands still count for the part's damage/destruction state, they just don't swap the material. Reference base-building mods (one of them with 45 zones) leave them empty. Visual degradation only via script (`SetObjectMaterial`) or separate pieces/selections per state. Ruled out with evidence: it's not the order of `sections[]`, it's not "a proxy doesn't receive the swap" (the vanilla wall is a proxy too), it's not missing model.cfg on the proxies.

<sub>Source: field case (in-game comparison with the vanilla fence)</sub>

---

### Camonet: the source must have the slot's name 🔇

**Symptom** — The camouflage net attaches but doesn't appear/disappear. `SetAnimationPhase("Wall_Camonet",...)` finds nothing and does nothing: no error, no conflict with another hide.

**Detect** — Check that `class Wall_Camonet: AnimSourceHidden{}` exists in the config's `AnimationSources`. It's the ONLY condition.

**Rule** — `BaseBuildingBase.EEItemAttached/EEItemDetached` -> `UpdateVisuals()` -> `UpdateAttachmentVisuals(slot,locked)` does `SetAnimationPhase(<SLOT NAME>, 0)` when attached and `1` when not: for free, if the animation source is named EXACTLY like the slot. The p3d `selection` can have another name; the source is what binds it. Don't reimplement a `RefreshCamonet()` the way an older community mod does (it was ITS selections that didn't match). On a piece with a leaf, use 2 DISJOINT selections (fixed + the leaf's slice), otherwise a net is left floating in the opening when the leaf is destroyed.

<sub>Source: field case; vanilla basebuildingbase.c:805-836, fence.c:386 and :815</sub>

---

### An item without an IK profile makes the player lie on the ground 🔇

**Symptom** — It's NOT the item crooked in the hand: it's the CHARACTER lying on the ground to play any animation while holding the item (the classic "drinking a soda lying down"). It hits every item derived from `Inventory_Base`.

**Detect** — Hold the new item and play any animation (drink/eat). In the code: does the mod have a `modded class ModItemRegisterCallbacks`? If not, no custom item has a profile.

**Rule** — `modded class ModItemRegisterCallbacks` in 4_World (class declared in P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:305). Override the `Register*` of the right category, call `super` first and do `pType.AddItemInHandsProfileIK("<YourBaseClass>", "<asi>", pBehavior, "<anm>")`. Matching is by INHERITANCE: registering only the base class covers all its descendants. Base-building kit = the vanilla FenceKit profile (:809): `player_main_1h.asi` + `fence_kit_folded.anm`, inside `RegisterOneHanded`, reusing the `pBehavior` passed in. Copy the profile of the equivalent VANILLA item, don't pick a pose by appearance. An item crooked IN THE HAND is the p3d's origin/pivot, not code; a kit p3d doesn't need a model.cfg.

<sub>Source: field case; vanilla dayzplayercfgbase.c:305, :373 (Inventory_Base fallback), :809 (FenceKit), :830 (WoodenCrate heavy), :1469/:1477 (call sites)</sub>

---

### Hologram.PlaceEntity creates a second object 🔇

**Symptom** — "The hologram doesn't go away" + a DUPLICATED, crooked object, at the projection's position and without your orientation.

**Detect** — The kit projects a class DIFFERENT from the item in hands (via `ProjectionBasedOnParent`) and the mod creates the object on its own? Then hologram.c:1044 detects that the projection isn't KindOf the item and does its own `CreateObjectEx(m_Projection.GetType(), m_Projection.GetPosition(), ECE_OBJECT_SWAP)`, and the swap breaks the kit/hologram.

**Rule** — `override EntityAI PlaceEntity(EntityAI entity_for_placing)` -> if the item in hands is your kit, `return entity_for_placing;` without calling `super` (don't let vanilla create anything). It's NOT the orientation method that causes the crooked/duplicate object: `obj.SetPosition/SetOrientation/Update` and `Math3D.YawPitchRollMatrix + SetTransform` are equivalent (same [yaw,pitch,roll] convention).

<sub>Source: field case, checked against a working placeable-item mod's Hologram override; vanilla hologram.c:1044</sub>

---

### A stale hologram position locks the deploy forever 🔇

**Symptom** — A "sticky" block: after ONE denied deploy attempt inside the forbidden area, EVERY deploy by that player gets denied anywhere on the map.

**Detect** — Does the deploy rule read the hologram's position / `LocalProjectionPosition` inside `ActionCondition`? `PlacingStartServer` (which CREATES `m_HologramServer`) only runs in `OnStartServer` (actiondeployobject.c:141), AFTER `ActionCondition`: before that the hologram is the one from the previous attempt, or null. And `PlacingCancelServer` (playerbase.c:2517) deletes the hologram but does NOT reset `LocalProjectionPosition`; only `PlacingCompleteServer` resets it (:2557).

**Rule** — In `ActionCondition` use ONLY `player.GetPosition()` (a safe, more restrictive approximation). The exact position is only reliable in `OnFinishProgressServer`, via `PlaceObjectActionData.m_Position`.

<sub>Source: field case; vanilla actiondeployobject.c:141, playerbase.c:2517 and :2557</sub>

---

### Denying in OnPlacementComplete makes the player lose the kit 🔇

**Symptom** — The deploy is refused and the kit DISAPPEARS from the player's inventory.

**Detect** — `ActionDeployBase.OnFinishProgressServer:125` sets `m_AlreadyPlaced = true` ONE LINE before calling `OnPlacementComplete`, and `ActionDeployObject.OnEndServer:230` does `if (m_MainItem.IsBasebuildingKit()) Delete()`.

**Rule** — Deny in two places, never in `OnPlacementComplete`. (a) `modded ActionDeployObject.ActionCondition`, the `IsDedicatedServer()` branch, which vanilla leaves as a bare `return true;`: returning false makes the action not be accepted and the kit isn't touched (it runs once per attempt; that's where the notification goes). (b) `OnFinishProgressServer`, refusing BEFORE `super`: `m_AlreadyPlaced` stays false, `OnEndServer` falls into `PlacingCancelServer` and `OnEndClient` returns the item to the hand: the same path vanilla takes when the hologram collides.

<sub>Source: field case; vanilla actiondeployobject.c (OnFinishProgressServer:125, OnEndServer:230), actionbase.c:898, kitbase.c:5</sub>

---

### OnPlacementComplete runs on the client too 🔇

**Symptom** — Desync: the kit "comes back" or flickers in the inventory: the client deleted its local replica while the server still has the kit.

**Detect** — `ActionDeployObject.OnFinishProgressClient` (actiondeployobject.c:164) calls `entity_for_placing.OnPlacementComplete(...)` ON THE CLIENT, and `OnFinishProgressServer` does the equivalent on the server. Every mod copied from a third party inherits the risk.

**Rule** — `if (GetGame().IsServer())` is mandatory inside `OnPlacementComplete`, with the kit's `Delete()` INSIDE the guard. Complement: the one that deletes the kit by itself is `OnEndServer` (:230-233), but ONLY when `IsBasebuildingKit()` is true (`KitBase` and descendants, kitbase.c:5): a kit that inherits from `Inventory_Base`/`WoodenCrate` isn't caught and must delete itself by hand. Clean vanilla template: fencekit.c:19-34.

<sub>Source: field case; vanilla actiondeployobject.c:164, :230-233, kitbase.c:5, fencekit.c:19-34</sub>

---

### CanBePlaced receives the hologram's position 🔇

**Symptom** — A territory rule written as if `position` were the player's behaves unexpectedly, and the message written in `CanBePlacedFailMessage` never shows to anyone.

**Detect** — actiondeployobject.c:45 (client, builds the menu) and :67 (server, ActionConditionContinue) call `item.CanBePlaced(player, hologram.GetProjectionEntity().GetPosition())`. And `CanBePlacedFailMessage` (entityai.c:637) is declared and NEVER called by vanilla: a dead hook.

**Rule** — Treat `ItemBase.CanBePlaced` as UX: it removes the Deploy option and, because it uses the hologram's position, it respects the PIN (a hologram pinned inside the forbidden area with the player far away stays blocked). It's not security: a tampered client ignores it; security lives in `ActionCondition`/`OnFinishProgressServer`. A rule based on `player.GetPosition()` can be bypassed by construction when there's pin/floating placement, and also gives false positives in the opposite direction.

<sub>Source: field case; vanilla actiondeployobject.c:45 and :67, entityai.c:637</sub>

---

### ActionConditionContinue leaves a ghost hologram 🔇

**Symptom** — A hologram stuck on the client, without physics, that only its owner sees.

**Detect** — `SetupAction` freezes the hologram (`SetUpdatePosition(false)`) and the server's hologram is born already at the final position and never moves: the position does NOT change during the action, so there's nothing to re-evaluate.

**Rule** — Don't use `ActionConditionContinue` to re-evaluate the deploy position: it just aborts the action midway and leaves the ghost.

<sub>Source: field case; vanilla actiondeployobject.c</sub>

---

### A kit selected by variable doesn't integrate with third-party shops 🔇

**Symptom** — A kit bought at a third-party shop/trader (or spawned by command) is born generic and doesn't project the right object.

**Detect** — Does the kit item distinguish its target by an instance variable instead of by its own class? Third-party shops deliver by CLASS NAME and don't set variables.

**Rule** — One kit type = one CLASS. Identify it by `GetType()`, with a method like `RequiredHologram()` returning the target class to project (consumed by the modded Hologram's `ProjectionBasedOnParent`). A generic item + a kit variable does NOT integrate with an external shop.

<sub>Source: field case</sub>

---

### A plain RaycastRV hits the gap, not the piece 🔇

**Symptom** — "The snap only locks when aiming at that little square": the lock only catches the single solid, always-visible box (e.g. the `wall_build`, bottom-center).

**Detect** — grep for `DayZPhysics.RaycastRV(` without flags: the default is `CollisionFlags.NEARESTCONTACT`, which returns ONLY the nearest contact. In an open frame (a grid with gaps) and with collision in proxies, the ray hits the ground/gap first and the piece is left out. `ObjIntersectView` is not the difference: a reference mod uses the same.

**Rule** — Use the vanilla ACTION crosshair mechanism (the same one that makes build/dismantle work on the whole piece): `RaycastRVProxy` + `RaycastRVParams` with `flags = CollisionFlags.ALLOBJECTS` and proxy handling (`RaycastRVResult.hierLevel > 0` -> the real piece is `res.parent`), choosing the nearest piece. `RaycastRVParams(vBeg,vEnd,ignore,radius)`, default `type=ObjIntersectView`; if reach is lacking, `type` can go to `ObjIntersectFire`.

<sub>Source: field case; vanilla actiontargets.c:214</sub>

---

### The engine has no vertical side (floor only from above) 🔇

**Symptom** — A player dismantles/builds the ceiling from above or the floor from below: from the wrong side. You can't fix it by tweaking the vanilla checks.

**Detect** — `Fence.IsFacingPlayer` (fence.c:660,663) and `IsFacingCamera` (fence.c:685,688) ZERO the Y (`ref_dir[1]=0`) before computing the angle: the engine's "side" is horizontal only, and up x down is exactly the axis that gets discarded. And distance to a memory point is a sphere: a sphere has no side; moving `center` translates, it never separates.

**Rule** — Cheap solution (works, but tight): place `center` so that the 1.5 m radius only reaches the legal side; the same radius governs horizontal reach AND side, and crouching/jumping/standing on a half-wall moves the result. Structural solution: a box from 2 memory points in the style of `Watchtower.IsPlayerInside` (watchtower.c:508-544, `interact_min`/`interact_max`), with 3 corrections when copying: (a) use all 3 axes (vanilla compares only X and Z at :538 and discards the return of `CheckLevelVerticalDistance` at :512); (b) use `WorldToModel` (object.c:870) instead of negating the points and rotating by hand with VectorToAngles; (c) test the body point that touches: floor = feet (`GetPosition()`), ceiling = head (`GetBoneIndexByName("Head")` + `GetBonePositionWS`, guard `idx<0`). `Watchtower.PerformRoofCheckForBase` (:133-195) does NOT fit despite its name (it's IsBoxCollidingGeometry filtering Building). The `is_base` part stays immune: actiondismantlepart.c:172-173 skips IsPlayerInside AND the camera check.

<sub>Source: field case; vanilla fence.c:660,663,685,688, watchtower.c:508-544 and :133-195, object.c:870 and :244, actiondismantlepart.c:172-173</sub>

---

### An attached lock or flag blocks the dismantle 🔇

**Symptom** — The player can't dismantle ANY part of the piece, and it's not clear why.

**Detect** — actiondismantlepart.c:153-154: vanilla dismantle blocks dismantling any part while an `Att_CombinationLock` OR a `Material_FPole_Flag` is attached.

**Rule** — Count on this when designing your own flag/territory system: the interaction already exists in vanilla and isn't your mod's. If you need to change it, it's `modded class ActionDismantlePart`.

<sub>Source: field case; vanilla actiondismantlepart.c:153-154</sub>

---

### An optional mod in requiredAddons skips your PBO 🔇

**Symptom** — For anyone who does NOT have the third-party mod installed, YOUR PBO simply doesn't load: no error visible to the player.

**Detect** — `grep -n requiredAddons config.cpp`: the optional addon (e.g. `CodeLock`) must not be there. If the `#ifdef` wraps only part of the usage, the symptom is different: `SCRIPT (E) Unknown type` in the log.

**Rule** — The `#ifdef` symbol is the other mod's `CfgPatches` class name (`#ifdef CodeLock`) and does NOT go into `requiredAddons[]` (it would become a hard dependency). Wrap EVERY use of the external type in the `#ifdef`, including variable declarations and `Cast`. The symbol always exists, but the other mod's CLASSES only exist if it compiles first (order = requiredAddons, then the ASCII order of the name in CfgMods), so the safest option is a separate OPTIONAL PBO with `requiredAddons[]={"MyMod","CodeLock"}` and a `modded class` inside. To expose YOUR symbol, `#define` it in a file listed FIRST in each module's `files[]`.

<sub>Source: field case + Code Lock source</sub>

---

### Code Lock already mods Fence: don't duplicate it 🔇

**Symptom** — Work rewritten for nothing. And, if your `SetActions()` doesn't call `super`, the lock's actions vanish from your piece without a single log line.

**Detect** — Extract `@Code Lock/addons/CodeLock.pbo` and open `scripts/4_world/Entities/Fence.c`: it's `modded class Fence`. All of the mod's actions cast `Fence.Cast(target.GetObject())`, so they aim at the PIECE, not at a lock proxy.

**Rule** — A piece whose SCRIPT inherits `Fence` gets for free, without `#ifdef`: `ActionInteractLockOnFence`/`ActionManageLockOnFence`/`ActionLockAdminOnFence` (just `super` in SetActions), `CanOpenFence()` blocking while a lock is active, `CanReceiveAttachment()` requiring `HasFullyConstructedGate()` (which uses YOUR CheckGateState) and the drop in `OnPartDismantledServer`. `IsCodeLocked()`/`GetCodeLock()` live in their `modded class ItemBase`. `#ifdef CodeLock` only pays off at 2 points the mod does NOT cover: (1) a leaf destroyed DIRECTLY by a raid with gunfire/explosives (their override has the same condition as vanilla, `IsGate() && destroyed_by_connected_part`, so it doesn't release the lock) and (2) `AfterStoreLoad` (the piece comes back from the save without a built gate and with a lock hanging on it). API: `CodeLock cl = GetCodeLock(); cl.NewUnlockServer(null, this);`.

<sub>Source: Code Lock source, verified by extracting the PBO, 2026-07</sub>

---

### Code Lock's wall_interact depends on the server's JSON 🔇

**Symptom** — The lock's actions work on one server and vanish on another, with the same mod and the same p3d.

**Detect** — Read the server's `Profiles/CodeLock/CodeLockConfig.json`: `CanOpenAnywhere` (default `"true"`). With `false`, `ActionInteractLockOnFence` requires the `wall_interact` selection under the crosshair. Same idea with `CanCloseAnywhere` for `ActionCloseFence`.

**Rule** — With the default you don't need `wall_interact` in the model, but if you want to survive an admin who turns the flag off, model the selection. Other hooks in the same JSON that affect your piece: `CanAttachToGates`, `CanRaidGates` (enables `ActionDestroyCodeLockOnFence`, which only requires Fence + lock, no selection) and `OwnerOnlyDismantle` (their `modded ActionDismantlePart` refuses dismantle from anyone who isn't the lock's owner; it interacts with your own territory system).

<sub>Source: Code Lock source</sub>

---

### Don't copy a reference mod's modded ActionBuildPart 🔇

**Symptom** — The reference mod's JSON tool whitelist starts applying to ALL base building on the server, vanilla and other mods included.

**Detect** — `modded class ActionBuildPart` / `ActionDismantlePart` without a filter on the piece's class = a global effect, by definition.

**Rule** — A base-building mod can be the best reference for gate and lock animation and still ship `modded ActionBuildPart`/`ActionDismantlePart` overrides and a `ModdedClass/MiscGameplayFunctions.c` (deprecated overloads) that are for STUDYING, not copying. The same rule applies to older community base-building mods (2021-era, imperfect): study only, never copy-paste. Before lifting an action override from another mod, check whether it filters by your piece's class.

<sub>Source: field case</sub>

---

### A cleanup scan on Container_Base deletes other people's crates 🔇

**Symptom** — Vanilla crates and PLAYERS' crates inside the event radius disappear at server startup.

**Detect** — In the leftover scan (`GetObjectsAtPosition3D`), look for `IsInherited(Container_Base)`. Widening it THERE is destructive.

**Rule** — Distinguish two places. (a) Internal TRACKING (the runtime's array of containers, `DeleteContainers`, `FindRuntimeByContainer`, the foreach loops): widening to `Container_Base` is SAFE: those arrays only hold what YOU spawn. (b) The world SCAN at startup: NEVER widen to `Container_Base`; match by concrete CLASS with `IsInherited(A) || IsInherited(B)`. You can't filter by the "event container" flag: it's runtime-only and doesn't persist, so a crate restored from persistence comes back without it.

<sub>Source: field case on a dynamic-events mod</sub>

---

### An external event crate disappears once looted 🔇

**Symptom** — The event crate disappears as soon as the last item is taken, before the scheduled despawn.

**Detect** — Check whether the external crate has an `OnCEUpdate` that deletes it when `open && empty`: the `modded class` PRESERVES its native behavior.

**Rule** — It's intentional in the mod the crate comes from. If you want it to persist until the despawn, suppress it only for crates flagged as event containers. Sibling detail: that crate usually accepts cargo WHILE CLOSED (its `CanReceiveItemIntoCargo` only blocks once it's open), so fill it BEFORE opening: no need for `SetAllowSystemCargoInsert` as with the native event containers.

<sub>Source: field case on a dynamic-events mod using a third-party crate</sub>

---

### isDiscrete=1 is not what decides the binarize 🔇

**Symptom** — None: the risk here is applying a rule that's too rigid and "fixing" a p3d that already works.

**Detect** — In a real base-building mod, the TWO pieces validated in-game use different values: the wall with `isDiscrete = 1` and `sections[]` listing only the fills (without `deployed`/`base`/`camonet`, even though they have a `hide` animation), and the window with `isDiscrete = 0` and a complete `sections[]`. Both binarize and work.

**Rule** — What decides is whether the p3d has disjoint vertices per bone; the flag only imposes (or not) the requirement. An incomplete `sections[]` doesn't stop `hide` from working. `isDiscrete = 0` is the safe choice for a NEW piece (it imposes nothing), but don't touch a p3d that already works with 1.

<sub>Source: field case (checked in the repository, 2026-07)</sub>

---

### 1e15 in float32 doesn't compare with equality 🔇

**Symptom** — A p3d parser classifies the Memory LOD wrongly and the selection audit comes out incomplete, without flagging anything.

**Detect** — `1e15` read as float32 is 999999986991104, not 1000000000000000.

**Rule** — Compare the resolution float with a TOLERANCE, never with exact equality. And don't state as fact the values 2e15 (LandContact), 4e15 (Paths) and 5e15 (HitPoints): they didn't show up in the pieces read and weren't confirmed.

<sub>Source: measured by parsing MLOD files</sub>

---

### A piece without is_gate becomes "Gate" and null-derefs

**Symptom** — A wall/ramp/foundation starts being called "Gate" in game. `m_GateState` holds a bogus value.

**Detect** — Does the piece have any part with `is_gate=1` in `class Construction`? If not, and the class doesn't override `CheckGateState`, the bug exists. In-game: aim at the piece and read the name on the crosshair.

**Rule** — `Fence.CheckGateState()` does `GetGateConstructionPart().IsBuilt()` WITHOUT a null check, and it's called on EVERY build (`OnPartBuiltServer`), on dismantle/destroy and in `AfterStoreLoad`. Fix: in the `CheckGateState` override, if `GetGatePartNames().Count()==0` return `GATE_STATE_NONE` directly: never `super`. Plus `override bool NameOverride(out string output){ return false; }` in the pieces' base class (`Fence.NameOverride` renames to "#str_cfgvehicles_construction_part_gate" whenever `m_GateState != GATE_STATE_NONE`).

<sub>Source: field case; vanilla fence.c (CheckGateState, NameOverride), construction.c:280 (GetGateConstructionPart)</sub>

---

### Dial on the piece: null-deref when the combination is guessed

**Symptom** — Error/crash at the EXACT moment the player gets the lock's combination right.

**Detect** — The Dial action's `OnFinishProgressServer` does `UnlockServer(player, target_entity.GetHierarchyParent())` assuming the target is the lock. With the PIECE as the target that's null, and `UnlockServer` does `Fence.Cast(parent).GetInventory()` without a null check.

**Rule** — When widening the dial actions to accept the piece (see "Lock-dial actions are commented out in Fence.SetActions"), you MUST also override `OnFinishProgressServer`, passing the piece itself as the parent. The two changes go together.

<sub>Source: field case; vanilla combinationlock.c:299-309</sub>

---

### Inherited GateAttachmentConditions null-derefs

**Symptom** — An error when opening the inventory or trying to attach to the piece while the gate is in `GATE_STATE_PARTIAL`.

**Detect** — fence.c:789-812 does `GetConstructionPart("wall_base_down").IsBuilt()`: a part that doesn't exist on the custom piece, and `GetConstructionPart` returns null (construction.c:280). It's called by `CanDisplayAttachmentSlot` and `CanReceiveAttachment`.

**Rule** — Override `GateAttachmentConditions` returning `true` (or rewriting it with your own parts). It applies to every piece that inherits Fence and doesn't replicate the vanilla fence's part names.

<sub>Source: field case; vanilla fence.c:789-812, construction.c:280</sub>

---

### rapify: inherit class AnimSourceHidden does not exist ⛔

**Symptom** — A pack error: `inherit class 'AnimSourceHidden' does not exist`.

**Detect** — The piece declares `class wall_base: AnimSourceHidden` inside `AnimationSources`, but `AnimSourceHidden` only exists in the config's parent class.

**Rule** — rapify resolves the base of a NESTED class at PARSE time, before applying the outer class's inheritance. Define `AnimSourceShown`/`AnimSourceHidden`/`AnimRotate` INSIDE the `class AnimationSources` of EACH piece (self-contained). `class DamageZones` doesn't suffer from it (zones don't inherit from anything). Inheriting a MEMBER of a nested class works (DamageSystem pulling GlobalHealth from the parent); only BASE resolution fails.

<sub>Source: field case (fix on an older community base-building mod's wall base class)</sub>

---

### Rapify -L hangs the session; use CfgConvert

**Symptom** — The model.cfg validation command never returns: it stops at "Press the ANY key" even with stdin closed or redirected (it reads straight from the console).

**Detect** — `Rapify.exe -L model.cfg` is the only mode it accepts for model.cfg (without `-L` it answers "lintable only use option -L" and exits 1), and it's interactive.

**Rule** — Validate with `CfgConvert.exe -bin -dst out.bin model.cfg` (exit 0 = syntax OK), which is non-interactive and works for `config.cpp` too. And `Rapify` run on config.cpp writes a `config.bin` at the repository ROOT as a side effect (besides warning `cfgPatches.<name>.units[]= has been altered`, which is normal): delete it afterwards so you don't pack junk into the PBO.

<sub>Source: field case</sub>

---
