# Agents for OpenAI Codex

Codex loads the skills of this plugin (`skills/*/SKILL.md`) but not the Claude Code agents in
`agents/*.md`. The two files here are the same agents in Codex's format.

## Install

1. Install the plugin in Codex so the skills are available (see the main README).
2. Copy the agent files to your Codex agents folder:

   ```sh
   mkdir -p ~/.codex/agents
   cp codex/agents/*.toml ~/.codex/agents/
   ```

   On Windows (PowerShell):

   ```powershell
   New-Item -ItemType Directory -Force "$HOME\.codex\agents" | Out-Null
   Copy-Item codex\agents\*.toml "$HOME\.codex\agents\"
   ```

3. Start a new Codex session.

| File | Agent |
|---|---|
| `agents/dayz-modder.toml` | DayZ mod code (Enforce Script), uses the `dayz-gotchas` skill |
| `agents/dayz-model-forge.toml` | External 3D model to wearable DayZ item, uses the `dayz-model-forge` skill |

The agents refer to the skills by name, so they need the plugin installed. Updating the plugin does not
update these copies: copy them again after an update.
