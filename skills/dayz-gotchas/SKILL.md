---
name: dayz-gotchas
description: >-
  Catalog of SILENT DayZ / Enforce Script traps measured on real mods: what fails without
  emitting a single log line. Load it for ANY DayZ modding work, alongside (not instead of)
  a general DayZ API skill such as `dayz-modding`: this one covers what that one doesn't.
  Triggers: DayZ, Enforce Script, mod, PBO, MakePbo, config.cpp, model.cfg, ActionConstructor,
  GetCompEM, EnergyManager, EEOnDamageCalculated, OnStoreSave, FileSerializer, hologram,
  base building, CfgPatches, requiredAddons, SetSynchDirty, RPT, "compiles but doesn't work",
  "clean log".
---

# DayZ: traps that fail in silence

## The thesis

> **In DayZ, a clean log proves nothing.**

Of the **129** traps catalogued here, **108 (84%) don't emit a single line**: no
`SCRIPT (E)`, no RPT warning. The mod compiles, starts clean, and the feature simply isn't there.

That's why the format here is always **observable symptom -> how to detect -> the rule**, in
that order. The rule alone doesn't help: against a silent failure, what saves you is knowing
where to look.

When they were catalogued, all of them were checked against the third-party `dayz-modding`
skill: what it already covered was dropped. This is a complement, not a replacement.

## Before you say it's done: mandatory checklist

Always separate **"compiles and starts"** from **"works"**. Before handing anything over:

- [ ] Custom action registered in `modded class ActionConstructor` (the item's `SetActions()` **is not enough**)
- [ ] Script class with **the same name** as a class in `config.cpp` (otherwise every `Class.CastTo` returns false, silently)
- [ ] PBO prefix is **exactly the one your `config.cpp` paths expect** (multi-segment like `JM\CF\Scripts` is fine; a prefix MakePbo derived from a nested P: folder is not): check with `ExtractPbo.exe -P -L <file.pbo>`
- [ ] Target `.pbo` **exists and is newer than the source** (MakePbo exits 0 without packing)
- [ ] The component exists before `GetComp*` (`GetCompEM()` on an item without an EnergyManager)
- [ ] `SetSynchDirty()` called wherever the client needs to see the change
- [ ] Slot declared in `playerSlots` / `requiredAddons` spelled right
- [ ] RPT without script errors: **necessary, never sufficient**. Search with a regex, `SCRIPT\s+\(E\)`: real logs pad the tag (`SCRIPT    (E)`), so a literal `SCRIPT (E)` search can come back empty on a log that has errors
- [ ] **Tested in-game.** If it wasn't, say "this hasn't been proven yet"

Saying "this hasn't been proven yet" up front is worth more than having the tester find out.

## Where to look

| Reference | Traps | Silent |
|---|---|---|
| [`build-and-packaging`](references/build-and-packaging.md): build, PBO and packaging | 17 | 11 |
| [`language-and-parser`](references/language-and-parser.md): Enforce Script parser, types and class binding | 11 | 7 |
| [`actions-and-lifecycle`](references/actions-and-lifecycle.md): actions, lifecycle and damage | 12 | 9 |
| [`persistence`](references/persistence.md): persistence, save and economy | 13 | 12 |
| [`basebuilding-and-models`](references/basebuilding-and-models.md): base building, pieces, hologram and p3d | 45 | 40 |
| [`ui-network-and-integration`](references/ui-network-and-integration.md): HUD, inventory, network and external integration | 31 | 29 |
| **Total** | **129** | **108** |

Each reference uses the same legend: 🔇 fails in total silence · ⛔ doesn't compile · no mark:
fails at runtime with a visible symptom or log line.

**About the line numbers.** Vanilla citations (`fence.c:176`, `entityai.c:3409`) point at the
unpacked game scripts (`P:\scripts`) at the time each trap was measured. Game updates shift
them: grep the symbol, not the line.

## Method rules (always apply)

1. **Reuse vanilla.** Find the real hook/action in `P:\scripts` and mod the minimum. Don't
   recreate the engine or a flow from scratch. A workaround that feels too heavy for the
   problem usually means the supported hook hasn't been found yet.
2. **Grep the corpus that already compiles** before suspecting the engine. The total absence
   of a pattern in `P:\scripts` and in mods that work is a strong signal.
3. **`type="mod"` on both sides**, client and server. `servermod` breaks if the client loads
   it. The split is logical (`IsServer` guards + hooks), not a packaging split.
4. **Don't pack, binarize or sign unless the user asks.** Many modders pack by hand and
   want to control when a build happens.
5. When you confirm a new trap in-game, record it **in this same format** (symptom -> detect
   -> rule), and label the evidence honestly: "confirmed in-game" only if it was observed in
   game; otherwise "verified against vanilla source" or "field case, not reproduced".
