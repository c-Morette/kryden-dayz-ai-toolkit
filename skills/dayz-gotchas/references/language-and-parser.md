# Enforce Script: parser, types and class binding

11 traps · **7 silent** (they don't emit a single log line).

Legend: 🔇 fails in total silence · ⛔ doesn't compile · no mark: fails at runtime with a visible symptom or log line

---

### CF_TypeConverterDate.SetString() does nothing 🔇

**Symptom** — A date read from a string stays at the default value (epoch 0 / 1970) and there's no error and no log. CF accepts the string and discards it silently.

**Detect** — `grep -rn "StringToDate"` over the Community Framework script source (extract `@CF/addons/scripts.pbo`, or read the public CF repository): it appears in exactly ONE place in all of CF, and the call is commented out inside `SetString()`: `//date.StringToDate(value);` (CF_TypeConverterDate.c:35).

**Rule** — CF_Date only goes date -> string (`Format(CF_Date.DATETIME)`) and fields -> epoch (`CreateDateTime(...).GetTimestamp()`). There is no string -> date. Slice the string by hand, end in `CF_Date.CreateDateTime(...).GetTimestamp()` and validate by round-trip (format it back and compare). Don't duplicate the constants' length in a literal of your own: derive it with `.Length()` of `CF_Date.DATETIME` / `DATE` / `TIME`.

<sub>Source: verified in the CF source, 2026-08 (JM/CF/Scripts/3_Game/CommunityFramework/TypeConverter/Converters/CF_TypeConverterDate.c:35)</sub>

---

### CF_Date.Now(false) returns the epoch of local time 🔇

**Symptom** — Timestamps stored with a timezone offset: time comparisons, cooldowns and sorting come out shifted by hours, with no error at all.

**Detect** — Compare `CF_Date.Now(false).GetTimestamp()` with `CF_Date.Now(true).GetTimestamp()` on the server: the difference is the machine's timezone offset.

**Rule** — Always `CF_Date.Now(true)` for any timestamp that is persisted or compared.

<sub>Source: verified in the CF source (JM/CF/Scripts/3_Game/.../Utils)</sub>

---

### CF_Date with a date-only format returns an empty string 🔇

**Symptom** — The date field comes out empty in the log, the HTTP payload or the UI. No error, just a blank string.

**Detect** — Format with `CF_Date.DATE` and print: you get `""`. With `CF_Date.DATETIME` it comes out filled.

**Rule** — Always format with `CF_Date.DATETIME` (`"YYYY-MM-DD hh:mm:ss"`) and cut the piece you want using `.Length()` of the constants, never a hardcoded length.

<sub>Source: measured with CF</sub>

---

### The config class must match the script class 🔇

**Symptom** — The item spawns and works in game (shows in the inventory, the config cargo applies, the player uses it normally), but EVERY `Class.CastTo(MyClass, entity)` returns false. Not one SCRIPT (E). Getters return null, the class's overrides never fire, and the code that "makes sure it exists" creates a second copy on the next login.

**Detect** — Compare the name of the BASE class in config.cpp with the script class name in the .c: they must be identical. Sign in the log: the line from a function's FAILURE branch is there but the success line of the same function isn't => the problem is the cast, not the creation. Before investigating scope/slot/null, look at the inventory in game: if the entity showed up, creation worked and what failed was recognition (a screenshot settles it in seconds, no log will).

**Rule** — The engine looks for a script class with the same name as the config class; if it doesn't find one, it walks up the config inheritance chain and stops at the first one that has it, typically the vanilla one (Container_Base, Inventory_Base). Make the config base have the exact name of the script class:
config: `class MyMod_SafeBox: Container_Base`
config: `class MyMod_SafeBox_A: MyMod_SafeBox`
script: `class MyMod_SafeBox extends Container_Base`
The concrete variants (`_A`, `_B`, `_Lv2`) do NOT need their own script class: they inherit through the config chain.

<sub>Source: verified 2026-08 on a real mod, checked against a working mod with the same structure</sub>

---

### JsonFileLoader serializes protected fields too 🔇

**Symptom** — Protected working members (`m_ExpiresAtUtc`, `m_Unreadable`) show up in the written .json file, alongside the public ones. A file meant for admins gets polluted and there are now two sources for the same value: whoever edits the file may see the stale derived value win.

**Detect** — Open the .json actually written (not the code) and look for the `m_*` members declared as protected. If they're there, this is happening.

**Rule** — Every declared member goes to the file: you can't hide working state inside a serialized class. Don't store the derived value: compute it on the fly from the field that is the source of truth. If you need a state signal (e.g. "corrupted record"), make it a FUNCTION that re-evaluates, not a field: functions don't serialize.

<sub>Source: verified 2026-08 on a file actually written by the game</sub>

---

### Delete() is deferred: use ObjectDelete to recreate in the slot 🔇

**Symptom** — `Delete()` followed by `CreateAttachmentEx` on the same slot fails. Only the mod's own error message shows ("Failed to create"); the engine logs nothing. It looks like a race condition, and it is one: the slot is still occupied by the dying entity.

**Detect** — `grep -nE 'Delete\(\)'` in the mod's .c files and see whether a `Create*` follows right after in the same block. Confirm in vanilla: object.c, `void Delete() { g_Game.GetCallQueue(CALL_CATEGORY_SYSTEM).Call(g_Game.ObjectDelete, this); }`: it only QUEUES.

**Rule** — When you'll recreate right after in the same slot, delete immediately:
`if (current_attachment_object) g_Game.ObjectDelete(current_attachment_object);`
`playerInventory.CreateAttachmentEx(attachment_type, slot_ID);`
(vanilla pattern in gameplay.c:1062). `Delete()` is still right when nothing is created afterwards; `DeleteSafe()` is the variant synchronized with the client for an item in a living player's hierarchy.

<sub>Source: verified against vanilla source 2026-08; vanilla P:\scripts: object.c (Delete), gameplay.c:1062</sub>

---

### A marketplace update wipes your edits to an installed plugin's skill 🔇

**Symptom** — Notes you appended to a third-party skill you installed as a plugin (in the original case, two damage-interception traps: only EEOnDamageCalculated prevents damage; explosions carry no damage zone) vanish from its SKILL.md without warning: the file lives in the plugin cache and a marketplace update overwrites whatever was written on top.

**Detect** — grep for your additions in the cached copy, e.g. `grep -nE 'EEOnDamageCalculated' ~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/skills/<skill>/SKILL.md`. Zero lines => they were lost.

**Rule** — Your own notes are the canonical record, not the plugin cache. Keep additions in a skill you own (this catalog exists for that) and rewrite them from there if they disappear. Don't edit only the cache thinking it persists.

<sub>Source: happened 2026-08 with an installed DayZ skill plugin</sub>

---

### Two backslashes kill the whole module ⛔

**Symptom** — `CParser: quoted string not closed on line 735`, followed by `Can't compile "Mission" script module!`: the whole module fails to compile because of one string. The compiler points at the line of the Replace, not at the cause.

**Detect** — In PowerShell (not Git Bash, whose grep escaping makes backslash searches unreliable): `Select-String -Path <mod>\*.c -SimpleMatch '\\'` (recurse with `Get-ChildItem -Recurse -Filter *.c | Select-String -SimpleMatch '\\'`). If a string has two backslashes in a row before a closing quote, that's it.

**Rule** — `escaped.Replace("\\", "\\\\")` and `escaped.Replace("\"", "\\\"")` break. But `\"` and `\n` ALONE are valid: building `"{\"embeds\":[...]}"` is safe and vanilla uses `"\n"` freely. In a comment the backslash is safe (P:\scripts\5_mission\... passes); the problem is only inside a string.

<sub>Source: cost a server restart, 2026-08</sub>

---

### An if condition can't break the line with `||` or `&&` ⛔

**Symptom** — `SCRIPT (E): Expected ')', not a '...'` on an if that would be valid in C or C#: `if (a == X` newline `|| a == Y)`.

**Detect** — `grep -nE '^[[:space:]]*(\|\||&&)' *.c` in the mod: any line that starts with a logical operator.

**Rule** — The Enforce parser closes the condition at the end of the line. A compound condition goes on one line, or splits into nested ifs / an intermediate boolean variable.

<sub>Source: verified 2026-08</sub>

---

### A script enum member must be qualified ⛔

**Symptom** — `Can't find variable ERESTOPTION_CONNECTION` even with the enum declared and in scope. Confusing because some UPPERCASE constants are written bare.

**Detect** — Find the DECLARATION of the symbol (grep in P:\scripts and in the mod): `enum X {` => qualified; `const int NAME = n;` => bare. Measured examples: `ECE_PLACE_ON_SURFACE` (const int, centraleconomy.c:37) and `CALL_CATEGORY_SYSTEM` (const int, tools.c:8) are bare; `EWeatherPhenomenon.OVERCAST` (enum, weather.c:10) and `ERestOption.ERESTOPTION_CONNECTION` (enum, restapi.c:28) are qualified.

**Rule** — If the declaration is `enum X { ... }`, use `X.MEMBER`. If it's `const int NAME = n;`, use `NAME` bare. `api.SetOption(ERestOption.ERESTOPTION_CONNECTION, 10);`

<sub>Source: vanilla P:\scripts: centraleconomy.c:37, tools.c:8, weather.c:10, 3_game\http\restapi.c:28</sub>

---

### Non-ASCII character in a .c file ⛔

**Symptom** — Compile failure pointing at a comment line, with no apparent cause in the code: an em dash, curly quotes or an accented letter pasted from another editor.

**Detect** — PowerShell: `Select-String -Pattern '[^\x00-\x7F]'` over the mod's .c files. Counter-check: no working mod in the corpus has a single character outside ASCII.

**Rule** — Write comments without accents and without em dashes: that's what the corpus does. Text shown to the player goes through the stringtable, not as a literal in the .c.

<sub>Source: cost server restarts, 2026-08</sub>

---
