# Wiring the Engineering Org into Codex

Codex consumes this team in one of three ways. You can use all three together.

## Option A — Prompt-as-resource (no infrastructure)

Put the `agent-team/` folder in your repo (or a path Codex can read). Then add an
instruction to Codex's configuration / prompt surface (e.g. an `AGENTS.md`, a custom
instructions block, or the task prompt itself):

```
For any non-trivial coding task, operate as the governed engineering org defined in
./agent-team. Start by reading ./agent-team/ORCHESTRATOR.md and ./agent-team/registry.json.
Adopt one role at a time from ./agent-team/agents/, pass work using
./agent-team/contracts/handoff.schema.json, and enforce the G0–G6 gate sequence. Do not
make design-altering changes without an approved ADR (Gate G1), and do not clear acceptance
without real live end-user testing (Gate G4).
```

Codex then "wears the hats" by loading the relevant spec file at each step. Fully portable.

## Option B — MCP server (structured, enforced, reusable)

Build and register the server so Codex drives the team through tools rather than prose.

```bash
cd agent-team/mcp-server
npm install
npm run build      # produces dist/index.js
```

Codex stores MCP config in `~/.codex/config.toml` (shared by the app, IDE extension, and CLI).
Local servers must use **stdio** transport. Add a `[mcp_servers.<name>]` table:

```toml
[mcp_servers.agentTeam]
command = "node"
args = ["/absolute/path/to/agent-team/mcp-server/dist/index.js"]
startup_timeout_sec = 30
```

**On Windows**, use the absolute path to `node.exe` and doubled backslashes (see
`WINDOWS-CODEX-GUIDE.md`):

```toml
[mcp_servers.agentTeam]
command = "C:\\Program Files\\nodejs\\node.exe"
args = ["C:\\Users\\<you>\\agent-team\\mcp-server\\dist\\index.js"]
startup_timeout_sec = 30
```

Restart Codex, then run `/mcp` to confirm `agentTeam` is connected.

Codex now has these tools:
- `team_list_roles` — discover the team.
- `team_adopt_role` — load a role's full spec to act as it.
- `team_get_gates` — the G0–G6 sequence and requirements.
- `team_validate_handoff` — **the enforcement tool**: call on every transition; it blocks
  drift, skipped gates, invalid role routing, missing/unapproved ADRs, failed verification, and
  synthetic-only acceptance on release paths. Pass `{ "handoff": <handoff.schema.json object>,
  "completed_gates": [...] }`.
- `team_resolve_escalation` — who owns a given decision (or 'human').

The server reads the same `registry.json`, `agents/`, and `contracts/` — so Options A and B
never diverge.

## Option C — Skill packaging

Install `skills/engineering-org` as a Skill in any skills-aware runtime. Its description is
tuned to trigger on non-trivial coding, architecture, governance, ADR, UAT, and release-gate
language, so the team is invoked automatically when appropriate. The skill simply points the
runtime at the same `ORCHESTRATOR.md` + `agents/` + `mcp-server/`.

## Recommended setup for Codex

Use **A + B together**: the markdown gives Codex rich role behaviour; the MCP server gives
it hard, code-enforced governance (`team_validate_handoff`) so the directives can't be
quietly skipped under time pressure. Add C if your runtime supports skills, for automatic
triggering.
