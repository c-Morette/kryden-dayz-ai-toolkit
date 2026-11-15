# Kryden DayZ AI Toolkit

Skills, agents and tools for making DayZ mods with AI, packaged as a plugin for Claude Code and OpenAI Codex. I use them on my own mods. They cover Enforce Script code, wearable items built from 3D models, and DayZ UI.

By Morette (Kryden). Em português: [README.pt-BR.md](README.pt-BR.md)

## A clean log doesn't prove it works

A DayZ mod can load without a single `SCRIPT (E)` and still be broken. Of the 129 traps in `dayz-gotchas`, 84% fail without writing one line to the log. Each entry gives you the symptom you'll see, how to detect it and the rule that avoids it.

The AI helps you write and review code. Testing in game is still your job.

## What's in the package

| Part | Type | What it does |
|---|---|---|
| `dayz-gotchas` | skill | 129 DayZ and Enforce Script traps, 108 of them silent. Format: symptom, how to detect, rule. Measured in real projects. |
| `dayz-modder` | agent | Writes and reviews Enforce Script (`.c`, `config.cpp`, `model.cfg`) with `dayz-gotchas` loaded. |
| `dayz-model-forge` | skill and agent | Drives Model Forge: license check, build, reading the output, in-game test loop. |
| Model Forge | Python tool | Builds a wearable DayZ item from a 3D model, without Object Builder. See below. |
| `dayz-layout-hud` | skill, work in progress | Builds DayZ menus and HUD panels with Layout HUD Designer, and knows the widget rules that fail silently. |
| Layout HUD Designer | tool, work in progress | A shadcn/ui-style design system for DayZ UI, written in Enforce Script. See below. |

## Install

### Claude Code

```
/plugin marketplace add c-Morette/kryden-dayz-ai-toolkit
/plugin install kryden-dayz-ai-toolkit@kryden-dayz-ai-toolkit
```

### OpenAI Codex

```
codex plugin marketplace add c-Morette/kryden-dayz-ai-toolkit
codex plugin add kryden-dayz-ai-toolkit@kryden-dayz-ai-toolkit
```

Or, after adding the marketplace, open `/plugins` inside Codex and install `kryden-dayz-ai-toolkit` from there.

The skills work in Codex. The two agents, `dayz-modder` and `dayz-model-forge`, are Claude Code agents. Optional Codex versions are in `codex/agents/`. To use them, copy them to `~/.codex/agents/` (steps in [codex/README.md](codex/README.md)).

### Without the plugin

Copy the folders inside `skills/` to:

- `~/.agents/skills/` for Codex
- `.claude/skills/` for Claude Code

The `dayz-model-forge` and `dayz-layout-hud` skills look for their tools at `../../tools/` from the skill folder. Copy `tools/` next to the `skills` folder you copied into: `~/.agents/tools/` for Codex, `.claude/tools/` for Claude Code.

## Model Forge

Model Forge takes a 3D model (`.glb` or a Sketchfab `.zip`) and builds the wearable DayZ item without Object Builder.

Output: MLOD `.p3d` files for male, female and ground, `.paa` textures, `.rvmat` and `model.cfg`.

What it does:

- fits the item to the vanilla male and female bodies
- weights it to the character bones
- builds the LODs
- checks that `binarize` accepts the result
- renders a proof image from the files it wrote

Status:

- tested in game: vests, and jackets (male and female)
- backpacks: about 90%, tested on the male character
- trousers, helmets, masks and other items: not supported yet

A clean build and a good render don't prove the item works in game. Test it with the checklist in [INGAME-TEST.md](skills/dayz-model-forge/references/INGAME-TEST.md).

### Requirements

- Windows
- Blender 4.4
- Python 3 with Pillow
- DayZ Tools
- the `P:` drive mounted
- the vanilla bodies (`character_male.p3d` and `character_female.p3d`), downloaded from Bohemia's official [DayZ-Misc](https://github.com/BohemiaInteractive/DayZ-Misc) repository
- a character rig `.blend` that you set up yourself. It isn't shipped because of its license. The [Model Forge README](tools/model-forge/README.md) lists what it needs.

### Model and output licenses

- Only use models whose license allows it: CC0 or CC-BY with download allowed, or bought with a license for game mods. CC-BY requires credit to the author in your mod description.
- `.p3d` files built from the vanilla bodies are derivative material of Bohemia's files. They fall under the [ADPL-SA](https://www.bohemia.net/community/licenses/arma-and-dayz-public-license-share-alike-adpl-sa) (non-commercial, Arma and DayZ only, share-alike), not under this toolkit's license.

## Layout HUD Designer (work in progress)

**This tool is still in development and isn't finished.** Names, tokens and APIs may change.

A shadcn/ui-style design system for DayZ UI, written in Enforce Script. It has:

- color tokens
- its own nine-slice atlas with rounded corners
- the `Button`, `Badge`, `Card` and `Separator` components
- an in-game lab that logs the size and position of every widget

Those four components were tested in game at 1280x720, 1600x900 and 1920x1080. What's still untested or not built is listed in the [tool README](tools/layout-hud-designer/README.md).

## Recommended (not included)

Both are third-party projects under the MIT license.

- [StarDZ-Team/Dayz-Modding-Skills](https://github.com/StarDZ-Team/Dayz-Modding-Skills), skill `dayz-modding`: covers the general DayZ API. `dayz-gotchas` leaves out what that skill already covers, so use the two together.
- [willy92wins/dayz-mcp](https://github.com/willy92wins/dayz-mcp): an MCP server that controls DayZDiag, so the AI can run tests in game.

## My mods

The mods themselves aren't in this package. My open mods are listed, with GitHub and Steam Workshop links, in [DayZ-OpenSource](https://github.com/c-Morette/DayZ-OpenSource).

## License

MIT + Commons Clause. You can use, study and change this toolkit, on your server and in your mods, free of charge. You can't sell it, or sell a service whose value comes from it. Full text in [LICENSE](LICENSE).
