# HUD, inventory, network and external integration

31 traps · **29 silent** (they don't emit a single log line).

Legend: 🔇 fails in total silence · ⛔ doesn't compile · no mark: fails at runtime with a visible symptom or log line

---

### rotationFlags doesn't straighten the inventory icon 🔇

**Symptom** — The item shows crooked/sideways in the inventory icon. You change `rotationFlags` in config.cpp, re-binarize, join the game and the icon is exactly the same. Not one log line.

**Detect** — `grep -ri "rotationFlags" P:\scripts` -> 0 results. If Enforce never reads it, changing it changes nothing in script/UI.

**Rule** — `rotationFlags` is a bitmask consumed ONLY by the engine when settling the entity on a surface (loot placement in the world). It doesn't touch the icon. The inventory icon has no config parameter: the fix is in the p3d (boundingbox_min/max + the `invview` memory point).

<sub>Source: P:\DZ\data\basicdefines.hpp:342-354 (defines), P:\scripts\3_game\entities\entityai.c:2835 (comment on PlaceOnSurfaceRotated)</sub>

---

### SetModelOrientation is wiped on the inventory icon 🔇

**Symptom** — You call `preview.SetModelOrientation(...)` to straighten the item in the inventory grid. The code runs, no error, and the icon stays crooked.

**Detect** — `grep -n "SetModelOrientation" P:\scripts\5_mission\gui\inventorynew\containeditems\icon.c` -> the vanilla UI calls `SetModelOrientation("0 0 0")` every time before `SetView`.

**Rule** — No script straightens the vanilla inventory icon: icon.c:1382-1388 and slotsicon.c:471-477 reset the orientation on every refresh. `SetModelOrientation` only works in your OWN ItemPreviewWidget (shop, inspect: inspectmenunew.c:92-104). For the inventory, fix the model.

<sub>Source: P:\scripts\5_mission\gui\inventorynew\containeditems\icon.c:1382-1388 and slotsicon.c:471-477</sub>

---

### invView2 only kicks in if the memory point exists in the p3d 🔇

**Symptom** — You create the 2nd camera expecting a different framing per slot and the game always uses camera 0. No warning.

**Detect** — Open the p3d at the Memory LOD (resolution 1e15) and check whether the `invview2` point exists. `EntityAI.GetViewIndex()` only enters the second-camera branch if `MemoryPointExists("invView2")`.

**Rule** — With invView2 present the index comes from the InventoryLocation: CARGO=0, ATTACHMENT=1, HANDS=0, GROUND=1 (console always 1). Without the memory point the index is always 0 and boundingbox_min2/max2/invView2 are ignored. Vanilla uses this in tentbase.c:425, flag_base.c:90, spotlight.c:376, claymoremine.c:239, trap_tripwire.c:282.

<sub>Source: P:\scripts\3_game\entities\entityai.c:3733-3775 and P:\scripts\3_game\gameplay.c:276-297</sub>

---

### Switching the preview camera: override GetViewIndex, not SetViewIndex 🔇

**Symptom** — You call `SetViewIndex(1)` and the preview doesn't change, or it changes and reverts on its own at the next refresh.

**Detect** — `grep -rn "SetViewIndex" P:\scripts` -> nobody in vanilla calls it. `grep "GetViewIndex"` -> overriding is the pattern.

**Rule** — The vanilla pattern is to override `GetViewIndex()` in the item class. For a runtime switch there's `RegisterNetSyncVariableInt("m_ViewIndex",0,99)` (entityai.c:229) and the invoker `GetOnViewIndexChanged()` (entityai.c:1288).

<sub>Source: P:\scripts\3_game\entities\entityai.c:229, :1288, :3733-3775</sub>

---

### grep for invView in the p3d gives a false negative 🔇

**Symptom** — You scan the p3d for `invView`, find nothing and conclude the model doesn't have the memory point. Wrong conclusion; an agent already fell for it.

**Detect** — The name stored in the file is LOWERCASE: `invview`. Search case-insensitive (`grep -i invview file.p3d`) or parse the Memory LOD.

**Rule** — Always search p3d files case-insensitive. A mod's p3d is usually MLOD (magic `MLOD`/`P3DM`) and can be parsed directly; vanilla in P:\DZ is binarized ODOL (a string search is inconclusive). LOD resolutions: Memory 1e15, Geometry 1e13, LandContact 2e15, Roadway 3e15, ViewGeometry 6e15, FireGeometry 7e15.

<sub>Source: measured on MLOD files</sub>

---

### A boundingbox with inverted Z misaligns the preview 🔇

**Symptom** — The icon is off-center or too far away even with `invview` placed by hand. Nothing in the log.

**Detect** — Read boundingbox_min and boundingbox_max in the Memory LOD and compare axis by axis: min must be < max on ALL THREE axes.

**Rule** — The boundingbox_min/max pair goes into the framing math together with invview. min > max on any axis breaks the framing by itself. Measured references (camera distance / model size): a clipboard model, camera above at ~0.5x; a small stair kit, three-quarters from above at ~1x.

<sub>Source: measured on real models</sub>

---

### A pixel card inside a proportional container 🔇

**Symptom** — "The container holds but the card doesn't adjust": at your resolution it looks right, at another the card overflows or leaves empty space. Real case: a 154x196 px card in a proportional strip that came out at ~552x131 px in 1080p.

**Detect** — In the .layout, compare `hexactsize`/`vexactsize` of the container with those of the child. If one is 0 (proportional) and the other 1 (pixel), it's this bug.

**Rule** — Match the card's UNIT with the container's. If the card is in pixels, put the container in pixels too (e.g. a 330 px column for 154 px cards). The proportional container stretches with the resolution and the pixel card doesn't.

<sub>Source: field case</sub>

---

### The NoScrollBar style erases the listbox selection highlight 🔇

**Symptom** — "I selected the name and I can't tell whether it got selected." Clicking a row of the TextListboxWidget gives no visual feedback at all. The code is right (AddItem/GetSelectedRow work), there's no log.

**Detect** — Open P:\gui\looknfeel\dayzwidgets.styles and read the `<Item Name="Highlight">` of the style the widget uses. In NoScrollBar it's `Image=""` in all THREE states; in Default it's ListboxHighlightMain in Normal and Focus.

**Rule** — The engine draws the highlight from the style, not from script. Switching to Default fixes it but ALSO changes the list font (Default = MetronBook, NoScrollBar = AmorSerifPro-Bold). If you want no scrollbar AND feedback: `SetItemColor(row, column, colorARGB)` in `OnItemSelected`. Before blaming the code, open the .styles: that holds for any widget with visual state.

<sub>Source: proven 2026-08; P:\gui\looknfeel\dayzwidgets.styles; SetItemColor in 1_core/proto/enwidgets.c:457</sub>

---

### The painted-row index survives ClearItems 🔇

**Symptom** — After rebuilding the list, a row shows painted wrong or the repaint call does nothing. No log.

**Detect** — Look for the field that stores the previous row index and check whether it's reset in the same place where the list calls `ClearItems()`.

**Rule** — When using SetItemColor to simulate selection, reset the stored index EVERY time the list is rebuilt. ClearItems deletes the rows; repainting the old index paints a row that no longer exists.

<sub>Source: field case, 2026-08</sub>

---

### A missing userID on the card root kills the hover 🔇

**Symptom** — The same card, in a new .layout, has a dead hover (name always visible, highlight never appears) without any change in the code.

**Detect** — Compare the two .layout files: look for the `userID` attribute on the card's rootFrame and for `if (w.GetUserID() == N)` in the menu's OnMouseEnter/OnMouseLeave.

**Rule** — The hover gate is the userID declared in the layout. Omitting the userID turns the hover off without touching the script: use that on purpose when you want different behavior per layout, and remember it when the hover "disappears" on its own.

<sub>Source: field case</sub>

---

### Sibling panels anchored to the same corner don't push each other 🔇

**Symptom** — You increase the height of a HUD panel and it shows through / overlaps the neighboring panel. No warning.

**Detect** — In the .layout, find two children with the same `halign`/`valign` `_ref` and a `position` in px: each one only knows its own anchor, there's no flow layout.

**Rule** — When changing the height of an anchored panel, check and reposition the neighbors in the SAME pass (real case: the lower one moved from position `12 0` to `12 10`). A key legend with absolute position and a manual grid: adding a line requires recomputing the panel height AND the neighbors' step.

<sub>Source: validated 2026-08 on a placement HUD</sub>

---

### Workbench reorders attributes and swaps the style on save 🔇

**Symptom** — A huge, messy diff in a .layout you barely touched; and sometimes the style changed on its own (DayZDefaultPanel -> rover_sim_colorable, Default -> NoScrollBar).

**Detect** — `git diff` of the .layout after opening it in Workbench: color/position/size/style jump to the top in the editor's order.

**Rule** — It's not corruption. Re-read the file BEFORE editing any .layout that has been through Workbench: besides the order, the editor swaps the style according to what was picked in the UI. Agree on who edits what, or text written by hand comes back reformatted (and may drag along the previous item's style swap).

<sub>Source: validated 2026-08</sub>

---

### Comments don't exist in .layout 🔇

**Symptom** — You comment out a .layout line as if it were C and the file starts behaving strangely: the widget doesn't load or attributes disappear, with no useful message.

**Detect** — `grep -n "//"` in the .layout: any occurrence outside a string is suspect.

**Rule** — The .layout format is not C and doesn't support comments. Document outside the file.

<sub>Source: field case</sub>

---

### Bitmap fonts blur when scaled; there are only 2 SDF weights 🔇

**Symptom** — HUD text is sharp on your monitor and blurry at another resolution / another HUD size.

**Detect** — Read the widget's `font` attribute: if it doesn't start with `sdf_` (metron, metron-bold, metronblack) it's bitmap and will blur when scaled.

**Rule** — Use `gui/fonts/sdf_MetronBook24` (regular, most legible, the 2nd most used by BI) or `sdf_MetronLight24` (thin). There's no SDF bold/medium: use `"bold text" 1` for fake-bold. A custom font from another mod creates a dependency on that mod.

<sub>Source: field case</sub>

---

### RichText accepts `<color rgba>` in 0-255 🔇

**Symptom** — You need one yellow word in the middle of grey text, see that TextWidget has a single color and conclude you need several widgets or that it can't be done.

**Detect** — Switch TextWidgetClass to RichTextWidgetClass in the .layout and emit `<color rgba="255, 194, 46, 255">piece</color>` in SetText.

**Rule** — RichTextWidget inherits TextWidget, so `TextWidget.Cast(...)` + `SetText(...)` keep working: only the .layout changes. The rgba values are 0-255, NOT 0-1. Text outside the tag inherits the widget's color. There's also an inline `<image set="x" name="y" scale="0.9"/>`.

<sub>Source: confirmed in vanilla newscarousel.c</sub>

---

### Default QueryFlags DYNAMIC misses static base pieces 🔇

**Symptom** — The "is there a base nearby?" check comes back empty with a base built right on top of the point. No log, just the wrong decision (the event spawns inside the player's base).

**Detect** — Look for calls to `SceneGetEntitiesInBox` without the 4th argument: the default is `QueryFlags.DYNAMIC`, which ignores whatever is classified as static.

**Rule** — Pass `QueryFlags.STATIC|QueryFlags.DYNAMIC` as a catch-all (that's what vanilla uses, e.g. environment.c). Full enum in dayzplayerutils.c: NONE/STATIC/DYNAMIC/ORIGIN_DISTANCE/ONLY_ROADWAYS.

<sub>Source: P:\scripts\4_world\entities\dayzplayerutils.c</sub>

---

### SceneGetEntitiesInBox is an AABB box, not a sphere 🔇

**Symptom** — A "50 m radius" query picks up things at ~86 m on the diagonal. No error: the result is simply bigger than expected.

**Detect** — Check the signature: `SceneGetEntitiesInBox(vector min, vector max, out array<EntityAI>, int flags)` takes min/max, not center+radius.

**Rule** — To approximate a sphere of radius R: `min = pos - Vector(R,R,R)`, `max = pos + Vector(R,R,R)`. It over-covers the corners, which is the safe side for "is there a base nearby?" but wrong for "is it inside the radius": in that case filter by distance afterwards. Prefer this call to `GetObjectsAtPosition3D` when you only care about EntityAI: it already leaves out terrain/trees/rocks/buildings, so the filter loop iterates a handful instead of hundreds in a city. There's also `PhysicsGetEntitiesInBox(min,max,out)` and `GetEntitiesInCone(...)`. Server-side.

<sub>Source: P:\scripts\4_world\entities\dayzplayerutils.c</sub>

---

### CreateRestApi() must be called before GetRestApi() 🔇

**Symptom** — `GetRestApi()` comes back null and the whole integration does nothing. If the code degrades silently (the recommended pattern), there isn't a single log line.

**Detect** — `grep -n "CreateRestApi"` in the mod's scripts. If it isn't there, that's the bug. Vanilla NEVER calls it: don't expect someone else to have initialized it.

**Rule** — Call `CreateRestApi()` once at mod boot before any `GetRestApi()`. The timeout is global via `RestApi.SetOption`, limited to 3-120 s.

<sub>Source: measured in P:\scripts\3_game\http\restapi.c, 2026-08</sub>

---

### Enforce doesn't send custom HTTP headers 🔇

**Symptom** — You design auth with Bearer / X-Api-Key and can't find the method. Or you POST JSON without SetHeader and the API refuses it without the mod noticing (script doesn't see the status). MEASURED 2026-09 against a .NET minimal API: the refusal is NOT 415, it's 403 (origin/CSRF guard) or 404, because routing filters the candidates by accepted Content-Type, no endpoint matches, `GetEndpoint()` comes back null and any endpoint exemption becomes invisible. Whoever looks for the defect in auth/CSRF finds nothing.

**Detect** — `grep -n "SetHeader\|AddHeader\|SetHeaders" P:\scripts\3_game\http\restapi.c`: the ONLY thing is `RestContext.SetHeader(string)` (restapi.c:141), and the engine doc says it sets the Content-Type.

**Rule** — There is no key/value header pair. Authentication only through the URL (querystring) or the POST body: prefer the body, the querystring ends up in proxy and CDN logs. `SetHeader("application/json")` WORKS and is MANDATORY before a POST with JSON: the engine default is `application/octet-stream`, and a production mod relies on it. What does NOT exist is AddHeader. Without SetHeader the API refuses with 403/404, never with 415 (see Symptom). Verbs: only GET and POST (plus FILE, which is GET to a file); there's no PUT/PATCH/DELETE.

<sub>Source: P:\scripts\3_game\http\restapi.c:141; backend behavior measured 2026-09</sub>

---

### Script doesn't see the HTTP status, and OnError repeats 🔇

**Symptom** — 401 and 409 reach the mod identical, so the message to the player comes out wrong. Worse: the same request fires OnError more than once and the handling runs twice (double message, double attempt, double delivery if the retry hands out an item).

**Detect** — Read the RestCallback signature in P:\scripts\3_game\http\restapi.c: `OnSuccess(body,size)`, `OnError(int)` with coarse buckets (EREST_ERROR_CLIENTERROR/SERVERERROR), `OnTimeout()`. No status code.

**Rule** — Don't design fine-grained error codes for the mod to consume: put the error in the JSON BODY and parse it (pattern: `if raw.Contains("\"error\"")` first, then success, always with a generic fallback). And make the OnError handler idempotent / guarded by an already-handled flag.

<sub>Source: P:\scripts\3_game\http\restapi.c</sub>

---

### GET_now/POST_now freeze the whole server 🔇

**Symptom** — The server freezes for seconds when someone uses the feature. Rubber-banding for everyone. It doesn't show up as an error, it shows up as "server lag".

**Detect** — `grep -n "_now("` in the mod's scripts. The engine's own doc marks it as "thread blocking operation!".

**Rule** — On a game server, use the asynchronous variant with a callback. Keep the RestCallback in a `ref` field until it fires.

<sub>Source: P:\scripts\3_game\http\restapi.c:106, :116, :126</sub>

---

### Enforce has no crypto: no HMAC on the backend 🔇

**Symptom** — You spec the backend asking for an HMAC signature of the payload ("the right way") and only find out when implementing the mod that there's no way to sign.

**Detect** — `grep -ri "HMAC\|SHA256\|MD5" P:\scripts` -> zero (verified 2026-08 on the unpacked vanilla).

**Rule** — Don't ask for HMAC in the API contract. Substitute used in a real game-server API: a per-server key sent in the POST body (Enforce can't set custom headers, see the trap above), with the backend storing a HASH of the key with the subscriber id embedded in the text; against replay, a `sentAt` from the game server with a 5-minute window both ways and a stamp in the database that only moves forward; payload as a full SNAPSHOT ("who is logged in now") instead of join/leave events, so that a restart or a lost packet corrects itself in the next snapshot.

<sub>Source: verified against vanilla P:\scripts, 2026-08</sub>

---

### OnRPC on PlayerBase accepts an RPC from ANOTHER player 🔇

**Symptom** — None. Works perfectly in testing. A modified client sends the RPC pointing at another player's PlayerBase and claims/spends on the target's behalf.

**Detect** — In the `OnRPC(sender, rpc_type, ctx)` override of PlayerBase, look for the comparison `sender.GetPlainId() == GetIdentity().GetPlainId()`. If there's only `if (!sender) return;`, it's open.

**Rule** — In `modded class PlayerBase.OnRPC`: (1) `if (!GetGame().IsServer()) return;` (2) `if (!sender || !GetIdentity()) return;` (3) `if (sender.GetPlainId() != GetIdentity().GetPlainId()) return;`. The handler's `this` is the target, the sender is whoever sent it: they are not the same player by construction. Keep RPC IDs in constants with a high value (e.g. 914001) so they don't collide with vanilla/other mods.

<sub>Source: field pattern from a real rewards mod (4_World/PlayerBase.c)</sub>

---

### BasicMap doesn't sync a custom group on connect 🔇

**Symptom** — A player joins the server and doesn't see your mod's markers. They appear later, on their own, the first time the group is changed. No error.

**Detect** — Check whether the mod calls `SetMarkersRemote` in `InvokeOnConnect`. BasicMap's automatic sync at client init pulls ONLY the default group `SERVER_KEY` (from the ServerMarkers.json files).

**Rule** — Explicit re-broadcast on connect: `InvokeOnConnect -> BasicMap().SetMarkersRemote(myGroup, markers, player.GetIdentity())`. Confirmed signature (BasicMapController.c:410): `void SetMarkersRemote(string group, array<autoptr BasicMapMarker> markers, PlayerIdentity toPlayer = NULL)`; `toPlayer` NULL broadcasts to everyone. Use a unique group key per mod: two mods on the same key, one overwrites the other.

<sub>Source: BasicMap source, https://github.com/DaemonForge/DayZ-BasicMap</sub>

---

### Expansion: SetColor on a marker doesn't sync 🔇

**Symptom** — You change the color of an event marker (e.g. green -> red when it activates) and on the server the object changes, but on the player's map the color stays the old one. No log.

**Detect** — grep for `SetColor` in your event manager. In the Expansion source (salutesh/DayZ-Expansion-Scripts), ExpansionMapSettings only has `RPC_AddServerMarker` and `RPC_RemoveServerMarker`: there's no update RPC, and `ExpansionMarkerModule.UpdateMarker()` rejects a SERVER-type marker (falls into Error).

**Rule** — To change a property live: `RemoveServerMarker(uid)` + `CreateServerMarker(name, icon, pos, newColor, marker3D, SAME uid)`, rebuilding via the getters `GetUID/GetName/GetIconName/GetPosition/Is3D`. At least one third-party event mod ships this bug (it only calls SetColor); a real event mod fixed it with remove + recreate.

<sub>Source: Expansion source, https://github.com/salutesh/DayZ-Expansion-Scripts</sub>

---

### VideoWidget doesn't play .mp4, only .mov 🔇

**Symptom** — The video loads and copies without any error, and simply never appears on screen. Zero log lines.

**Detect** — Check the real extension of the file passed to `Load()`. If it's .mp4, that's it.

**Rule** — Convert to .mov. Confirmed in a real loading-screen mod.

<sub>Source: field case (in-game)</sub>

---

### VideoWidget.Load() doesn't read from inside the PBO 🔇

**Symptom** — Works from the unpacked folder and stops working when the mod becomes a PBO. The video never appears, no error.

**Detect** — Look at the path passed to `Load()`: if it starts with `<YourMod>/...` instead of `$profile:`, that's the bug.

**Rule** — `Load()` reads from the real filesystem. `CopyFile("<Mod>/.../x.mov", "$profile:x.mov")` first, then `Load("$profile:x.mov", ...)`. It's client-side.

<sub>Source: field case (in-game)</sub>

---

### Video plays muted without `Play(); Stop(); Play();` 🔇

**Symptom** — The picture plays normally, no sound comes out. No error.

**Detect** — Look at the sequence right after `Load()`: if it's just `Play()`, the cycle is missing.

**Rule** — Emit `Play(); Stop(); Play();` in sequence right after `Load()`, the pattern used by a working video mod. In the .layout: `VideoWidgetClass Name { ... "stretch mode" stretch_w_h }`. To play once and close, a Timer checking `GetState() == VideoState.FINISHED`; to loop, `Load(name, true)` and do NOT close on FINISHED.

<sub>Source: field case (in-game)</sub>

---

### LoadingScreen is reused: the video only plays the 1st time 🔇

**Symptom** — The loading screen background video plays on the first load and on the following ones the screen is black or frozen. No log.

**Detect** — Check whether there's a `Show()` override restarting the video. LoadingScreen lives in 3_game/dayzgame.c and is NOT a UIScriptedMenu: it's created ONCE by DayZGame and shown again via Inc/Dec/Show/EndLoading.

**Rule** — `modded class LoadingScreen` in 3_Game, redefining the constructor `LoadingScreen(DayZGame game)` mirroring vanilla but with `CreateWidgets` pointing at a clone of `gui/layouts/loading.layout`. Re-cast ALL the `m_*` widgets (the root changed). Start the video in the constructor AND restart it in `override Show()`. A fullscreen VideoWidget as the FIRST child of the panel (it sits behind the HUD). Always keep a fallback to the vanilla ImageBackground if the video doesn't reach PLAYING, otherwise you get a black screen.

<sub>Source: P:\scripts\3_game\dayzgame.c; field case (in-game)</sub>

---

### A RestCallback collected before the response crashes the game

**Symptom** — Intermittent crash a few seconds after an HTTP call: rarely during testing, almost always in production under latency.

**Detect** — Look for `new <YourCallback>()` inside the method that does the POST/GET. If the callback is local (it doesn't go into a field of the object), that's the bug.

**Rule** — The RestApi POST is asynchronous and the RestCallback must be Managed AND stay alive. Keep it in a field (e.g. `m_RestCallback`) instead of creating one per call, as a working server-restart mod does. Wrap it in a small helper that also validates the target URL before calling and degrades quietly when the RestApi isn't available.

<sub>Source: field case (crash in production)</sub>

---

### LBmaster_Rework replaced Get() with a Get property ⛔

**Symptom** — Doesn't compile in one of the two LBmaster builds. Whoever tested only one of them sees nothing.

**Detect** — Look for `LBStaticMarkerManager.Get()` in the code and check whether there's an `#ifdef LBmaster_Rework` sub-guard.

**Rule** — Mandatory sub-guard inside `#ifdef LBGROUP_SYSTEM_NEW`: with `LBmaster_Rework` use `LBStaticMarkerManager.Get.AddTempServerMarker(...)`, without it `LBStaticMarkerManager.Get().AddTempServerMarker(...)`.

<sub>Source: field case with the LBmaster group system</sub>

---
