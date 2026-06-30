---
name: engineering-org
description: Run a governed multi-agent software engineering organisation (CTO, Enterprise Architect, Delivery Lead, Principal Engineers, QA, UX/End-User Test Lead, Security Reviewer) to deliver high-grade code right-first-time with minimal drift. Use this skill WHENEVER a coding task is non-trivial, multi-step, spans design + build + test, touches architecture, or needs to stay aligned to planned epics and end-to-end deliverables — even if the user does not say "use the team". Especially trigger when the user mentions architecture review, governance, ADRs, design changes, acceptance/UAT, real end-user testing, release gates, or wants work checkpointed and approved before proceeding.
---

# Engineering Org (Agentic Team)

A governed team-of-agents that turns a request into a delivered, accepted, released change
while protecting six prime directives:

1. Highest grade of code, right first time.
2. Minimise drift from approved design and planned epics.
3. Stay focused on the end-to-end deliverable.
4. Mandatory EA architecture governance — design-altering changes pass Gate G1 and are
   approved via an ADR before work proceeds.
5. Final acceptance is **real, live end-user testing — never synthetic-only** (Gate G4).
6. Correctness and safety over speed.

## How to use this skill

1. **Read `ORCHESTRATOR.md`** (in the team root) — it is the conductor. It tells you to adopt
   one role at a time and pass work via handoffs.
2. **Read `registry.json`** for the roles, gate sequence (G0→G6), and escalation map.
3. **Adopt roles** by reading `agents/<role>.md`. Act strictly within each role's mandate,
   authority, and tool permissions. Only the Principal Engineer writes product code.
4. **Validate every transition** with the handoff contract (`contracts/handoff.schema.json`).
   Call `team_validate_handoff` with `{ "handoff": <canonical handoff>, "completed_gates": [...] }`.
   Always evaluate `drift_check`. If `design_altering` is true, route to the EA gate (G1) and
   require `payload.adr.status: "Approved"` before implementation advances past G1.
5. **Never clear acceptance synthetically.** A user-facing change reaches release only after
   the UAT Lead validates it with live end-user journeys (G4).

## The gate sequence (enforce in order)

```
G0 intake (Delivery Lead) → G1 architecture (EA, if design-altering) →
G2 implementation (Principal) → G3 verification (QA) →
G4 real end-user acceptance (UAT Lead) → G5 security (Security Reviewer) →
G6 release (Human)
```

## Roles at a glance

| Role | Owns | Escalates to |
|------|------|--------------|
| CTO | strategy, standards, ARB | human |
| Enterprise Architect | architecture gate (G1), ADRs | CTO |
| Delivery Lead | intake (G0), routing, drift radar | CTO |
| Principal Engineer (generic) | implementation (G2), small diffs | EA |
| Principal — Platform | infra, K8s/topology, deploy, observability | EA |
| Principal — Governance Engine | DIIaC core: decision packs, signing, ledger, scoring | EA |
| Principal — Frontend | UI, dashboards, decision-pack visualisation | EA |
| QA / Verification | technical verification (G3) | Principal |
| UX / End-User Test Lead | real end-user acceptance (G4) | Delivery Lead |
| Security Reviewer | security/compliance (G5) | CTO |

**Routing to domain Principals:** the Delivery Lead routes work to the Principal that owns the
domain (platform / governance-engine / frontend). A change to an interface one domain exposes and
another consumes is **design-altering by definition** and goes to the EA gate (G1) — not directly
between Principals. This keeps parallel domain work from drifting each other's contracts.

## Two ways to run it

- **Prompt-as-resource**: read the markdown specs directly (this skill + the `agents/` files).
  Zero infrastructure; works in any agent runtime including Codex.
- **MCP server** (`mcp-server/`): connect over MCP and drive the team through structured tools
  (`team_list_roles`, `team_adopt_role`, `team_get_gates`, `team_validate_handoff`,
  `team_resolve_escalation`). The server enforces the handoff contract, gate sequence,
  governance, verification, and acceptance rules in code.

See `references/codex-integration.md` for wiring this into Codex specifically.
See `references/usage-examples.md` for worked end-to-end flows.
