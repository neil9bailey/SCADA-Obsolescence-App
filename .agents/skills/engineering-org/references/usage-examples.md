# Worked example — a feature from request to release

Request from human: *"Add SSO login to the customer portal."*

### G0 — Delivery Lead (intake & alignment)
Confirms the epic ("Portal auth modernisation") and success criteria (users sign in via
corporate IdP; existing sessions unaffected; sign-in journey p95 < 2s). Decomposes into
increments. Routes to CTO because auth is cross-cutting.
→ validate `{ handoff: { to_role: "cto", gate: "G0_intake", user_facing: true,
drift_check: { aligned_to_epic: true, design_altering: true, requires_arb: true }, ... },
completed_gates: [] }`.

### G1 — CTO + Enterprise Architect (governance checkpoint)
Adding SSO changes the auth boundary → **design-altering**. CTO convenes the ARB; EA requires
an ADR. EA authors `governance/adr/ADR-0007-sso-oidc.md` (chooses OIDC, lists options/risks,
defines the verification plan including a **live end-user sign-in journey**). EA approves.
→ validate `{ handoff: { to_role: "principal-engineer", gate: "G1_architecture",
status: "approved", payload: { adr: { ref: "ADR-0007", status: "Approved" }, ... },
drift_check: { design_altering: true, requires_arb: true, aligned_to_epic: true }, ... },
completed_gates: ["G0_intake"] }`.

*(If a Principal had tried to implement SSO without this ADR, `team_validate_handoff` would
have blocked it and routed back to the EA.)*

### G2 — Principal Engineer (implementation)
Per the coding contract: states plan + success criteria, then small diffs.
Increment 1: add OIDC client + config. States files, risks, verification. Implements.
Runs tests/linters. Reports diff summary + verification output.
Increment 2: wire callback + session bridge. Same discipline.
→ handoff `to_role: qa-engineer`, `gate: G2_implementation`, with `payload.verification` and
`completed_gates: ["G0_intake", "G1_architecture"]`.

### G3 — QA / Verification Engineer
Runs unit + integration tests, type checks, build. Checks edge cases (expired token,
IdP timeout). All green.
→ handoff `to_role: uat-lead`, `gate: G3_verification`, `payload.verification.result: pass`.

### G4 — UX / End-User Test Lead (REAL end-user acceptance)
Defines journeys (first-time SSO sign-in, returning user, denied access). Runs them **live**
against the running portal against a real IdP — not mocks. Captures session evidence.
→ handoff `to_role: security-reviewer`, `gate: G4_uat`,
`payload.uat.evidence: live_end_user`.

*(If UAT had only synthetic evidence, `team_validate_handoff` blocks the move to G5/G6.)*

### G5 — Security & Compliance Reviewer
Secret scan, dependency audit, token-handling review. Clean.
→ handoff `to_role: human`, `gate: G5_security`, `payload.verification.result: pass`.

### G6 — Human (release)
All gates green; human makes the production-release decision. Delivery Lead synthesizes the
final status. Done — high-grade, on-epic, architecturally governed, real-user-accepted.
