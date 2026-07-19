# Development Plan

Codex3D should start with a narrow Blender-first MVP and grow only after the local creative loop works.

## First 10 Rounds

| Round | Focus | Status |
|---:|---|---|
| 1 | Repo scaffold + docs | DONE |
| 2 | Protocol/schema | DONE |
| 3 | FastAPI session/job API | DONE |
| 4 | Blender connector handshake | DONE |
| 5 | Basic Blender actions | DONE |
| 6 | Render preview | DONE |
| 7 | Snapshot/undo | DONE |
| 8 | End-to-end mock demo | DONE |
| 9 | Scene IR stable object identity | PARTIAL |
| 10 | Multi-turn feedback loop | DONE |

## Execution Strategy

The project should optimize for visible, local progress:

- Keep each round small and testable.
- Store project memory in files.
- Avoid external providers until the provider phase.
- Avoid building platform features before the Blender loop is convincing.
- Prefer deterministic validation for geometry and state checks.

## Hackathon Sprints

| Sprint | Focus | Status |
|---|---|---|
| 01 | Basic Blender actions + deterministic demo planner | DONE |
| 02A1 | Installable Blender Extension + localhost live bridge | PARTIAL |
| 02A2 | Codex MCP adapter + direct natural-language Blender control | DONE |
| Demo Gate 0 | Isolated real Blender, MCP, Codex, cleanup, and readiness audit | PASS |
| 02BC | Creative geometry + materials + camera + render + animation vertical slice | PARTIAL |
| 02D | Demo hardening: packaging, snapshot restore, UUID, polish, GUI acceptance | DONE |
| Synthetic UT-01 | Persistent novice feedback, rollback, delivery and safety evaluation | SYNTHETIC_PASS |
| UT-01 Reliability Repair | Approval-safe rollback/save, accepted-state delivery, compact inspection and composition guard | DONE |
| OpenAI Build Week RC | License, repository hygiene, GPT-5.6 evidence, judge materials, curated bundles and clean-room reproduction | CONDITIONALLY_READY |

Sprint 02A1 implementation, automated tests, official Blender build, real bridge execution, and clean shutdown passed. It remains PARTIAL until the manual Install from Disk and visual Panel walkthrough are recorded. Rounds 6 and 7 remain open.

Sprint 02A2 adds the first direct natural-language Codex control path through a local STDIO MCP server. The next sprint should expand structured creative capabilities and complete Round 06 render preview while preserving the current safety boundaries.

Demo Gate 0 confirms that foundation in an isolated Blender 5.1.1 process: the 123-test baseline, structured MCP creation and follow-up edits, ephemeral Codex control, saved scene artifact, configuration integrity, and process cleanup all pass. Sprint 02B may proceed; missing curve, camera, render, advanced material, and world-lighting capabilities are explicit implementation inputs rather than Gate failures.

Sprint 02BC completes Round 06 and the accelerated creative vertical slice: curves, advanced materials, camera, lights, World, render validation, keyframes, a real Codex rerender, and a saved scene all pass in isolated Blender 5.1.1. Status remains PARTIAL because this Blender build has no FFmpeg, so the validated animation is a complete 72-frame PNG sequence, and live GUI Timeline playback remains manual acceptance.

Sprint 02D completes the minimal Round 07 snapshot boundary and the Blender execution portion of stable identity: every created object receives `codex3d_uuid`, UUIDs survive rename and `.blend` save/reload, legacy `C3D_` objects can be explicitly reconciled, and a real Blender mutation is recovered to an identical canonical fingerprint. The polished 14-object scene, real Codex follow-up, independently probed H.264 MP4, and user-confirmed visible GUI Timeline loop all pass. Sprint 02D is DONE.

Synthetic UT-01 now passes the unchanged nine-turn script at 100/100. The repair makes restore reversible through an automatic safety snapshot and dual fingerprint checks, makes final checkpoint saves versioned/non-overwriting, blocks delivery outside a verified accepted state, starts in a truly empty isolated Scene, reduces Target inspection context by 91.1%, and rejects cropped/overexposed/unwanted final compositions. Round 10 is DONE. The next validation should involve real novice participants; full Scene IR remains a separate partial milestone.

The OpenAI Build Week RC freezes product capability. A real `gpt-5.6-sol` Target Codex rerun completed the isolated nine-turn MCP/Blender flow in 397 seconds with 146 successful tool calls, exact restore and final media delivery. Release work is limited to licensing, evidence, documentation, packaging, audit, Git and submission operations. Remaining work is user-owned publication metadata and media, not product expansion.
