# Codex3D Project Tracker

Last updated: 2026-07-19

## Current Status

Current phase: Hackathon Release Candidate

Current round: OpenAI Build Week submission packaging

Overall status: CONDITIONALLY_READY. The public MIT repository, annotated tag, GitHub Release, English judge materials, GPT-5.6 evidence, deterministic release bundles, secrets/path audit, and clean-room reproduction pass. Narrated YouTube URL, entrant display name, and the primary task `/feedback` Session ID remain submission blockers.

## Completion Table

| Milestone | Target | Current status |
|---|---|---|
| Demonstrable prototype | Natural-language prompt to deterministic local modeling demo | Codex controls 23 structured tools and produces validated Blender scene/render/animation/snapshot artifacts |
| Usable MVP | Multi-turn feedback, Scene IR, undo, simple UI, small-scene completion | Not started |
| Internal Alpha | Providers, asset import, validators, transactions, version history | Not started |
| Public Beta | Beginner-friendly UI, reliable rollback, templates, eval reports | Not started |
| Platform V1 | MCP/API/SDK, cloud workers, multiple providers, collaboration/export | Not started |

## First 10 Rounds

| Round | Work item | Status | Acceptance |
|---:|---|---|---|
| 1 | Repo scaffold + docs | DONE | Directory structure, README, docs, tracker, minimal package, smoke test |
| 2 | Protocol/schema | DONE | Scene/Action/Job/Asset/Error schema draft implemented and tested |
| 3 | FastAPI session/job API | DONE | Local API can create sessions, submit messages, and query jobs |
| 4 | Blender connector handshake | DONE | Blender connector can register, heartbeat, ping, and inspect empty/fake scene state |
| 5 | Basic Blender actions | DONE | Create, transform, material, delete, rename, and light actions work through fake backend and guarded bpy backend path |
| 6 | Render preview | DONE | Eevee PNG render, validator statistics, optional MCP image content, and Codex rerender pass |
| 7 | Snapshot/undo | DONE | Artifact-confined snapshot create/list/restore/delete and real Blender fingerprint restore pass |
| 8 | End-to-end mock demo | DONE | Fake demo, real bridge demo, STDIO MCP demo, and Codex natural-language live edit verified |
| 9 | Scene IR stable object identity | PARTIAL | Stable Blender/Fake UUIDs pass rename/save/reload and explicit legacy reconcile; full Scene IR remains open |
| 10 | Multi-turn feedback loop | DONE | Persistent Codex preserves six curve UUIDs, restores the exact accepted fingerprint after rejection, and delivers validated scene/media artifacts |

## Current Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Scope expands into platform too early | Delays the local creative loop | Keep first ten rounds narrow and testable |
| GPT writes arbitrary Blender Python as the main path | Hard to validate, undo, or debug | Prefer structured tools and Scene IR |
| Project memory remains only in chat | Future rounds lose context | Update tracker and round reports every round |
| Blender connector becomes too smart | Logic split becomes hard to maintain | Keep connector focused on execution and inspection |
| Protocol diverges from future API models | API layer may need duplicate schema logic | Keep protocol dependency-free and add adapters only when needed |
| Mock API flow could be mistaken for real execution | Early demos might overstate Blender readiness | Mark mock scene objects/jobs clearly and avoid render claims |
| Optional FastAPI adapter could become a hidden hard dependency | Local tests may fail in clean environments | Keep core service tests independent of FastAPI |
| Connector handshake could be mistaken for Blender action support | Users may expect real scene edits too early | Document that Round 04 only supports registration, ping, heartbeat, and inspection |
| Tests may accidentally require `bpy` | CI or local Python could fail without Blender | Guard `bpy` import and test fake scene inspection in ordinary Python |
| Fake backend demo could be mistaken for real Blender validation | Hackathon readiness may be overstated | Report fake/real backend status separately and mark Blender CLI checks honestly |
| Full Scene IR reconciliation remains absent | Rich relation/history edits still rely on execution state | Use persistent `codex3d_uuid` now; keep full Scene IR scoped to a later round |
| Local bridge token could leak through diagnostics | Unauthorized local actions | Mask token, use `compare_digest`, and exclude it from logs/errors/responses |
| Socket thread could mutate Blender | Blender instability and UI crashes | Queue all requests and execute only through the bounded `bpy.app.timers` pump |
| Internal manifest LicenseRef is not publication-ready | Public release may make an unconfirmed license claim | Keep package local/internal until project ownership confirms release licensing |
| MCP token stored by optional `codex mcp add --env` | Secret may persist in local Codex config | Treat as local secret, avoid logs, and rotate from Blender when needed |
| Tool schemas drift from Action validation | Codex may submit ambiguous or stale parameters | Keep MCP schemas narrow and retain connector validation as authoritative |
| Synthetic success may be mistaken for human usability evidence | Product confidence could exceed what was tested | Keep `SYNTHETIC_PASS` vocabulary and run a moderated novice study before usability claims |
| Long creative turns remain variable | A nine-turn flow still takes about 17.5 minutes | Add observability and turn budgets without changing the novice-language contract |
| Full Scene IR reconciliation remains partial | Cross-session semantic references and history remain limited | Continue using stable UUIDs; scope full Scene IR separately from demo reliability |

## Hackathon Sprints

| Sprint | Scope | Status | Result |
|---|---|---|---|
| Hackathon Sprint 01 | Basic Blender actions + deterministic demo planner | DONE | Prompt -> action store -> dispatcher -> executor -> fake backend -> inspection works |
| Hackathon Sprint 02A1 | Installable Blender Extension + localhost live bridge | PARTIAL | 84 tests, official build, real 31/31 bpy run, 16 objects, clean disconnect passed; visual Panel walkthrough pending |
| Hackathon Sprint 02A2 | Codex MCP adapter + direct natural-language Blender control | DONE | 123 tests; 9 tools; real STDIO MCP and ephemeral Codex natural-language Blender edit passed |
| Demo Gate 0 | Isolated local end-to-end regression and readiness audit | PASS | 123-test baseline; real Blender 5.1.1; 18/18 actions; 8 Gate objects; Codex tool sequence verified; clean port release |
| Hackathon Sprint 02BC | Sol-inspired creative scene + render + animation vertical slice | PARTIAL | 137 tests; 18 MCP tools; 2 validated PNGs; 72-frame sequence; 6 curves; real Codex follow-up; FFmpeg MP4 unavailable |
| Hackathon Sprint 02D | Demo hardening: MP4 boundary, snapshots, stable UUID, visual polish, GUI acceptance | DONE | 144 tests; 23 MCP tools; 14 persistent UUIDs; real restore; polished preview; H.264 MP4; visible 72-frame GUI loop; user-confirmed acceptance |
| Synthetic User Test UT-01 | Persistent novice-language multi-turn creation, feedback, rollback and delivery | SYNTHETIC_PASS | 100/100; 133 MCP calls; exact Turn 6 restore; versioned final `.blend`; composition-safe PNG; valid H.264 MP4; clean shutdown |
| UT-01 Reliability Repair | Approval-safe restore/save, delivery guard, isolated scene, compact inspection and visibility validation | DONE | 153 default tests; real Blender restore regression; unchanged nine-turn rerun passed; inspection payload reduced 91.1% |
| OpenAI Build Week RC | License, repository hygiene, judge documentation, GPT-5.6 evidence, release bundles and clean-room audit | CONDITIONALLY_READY | Public repo and `hackathon-v0.1.0` Release verified; GPT-5.6 Target 100/100; clean-room 153/3 passed |

## Next Actions

1. Run `/feedback` in primary task `019f7749-0bc7-7733-9d9a-17a37e273539` and record the returned Session ID.
2. Record and publish the narrated sub-three-minute YouTube demo using `DEMO_SCRIPT.md` and `docs/youtube_submission.md`.
3. Fill the entrant display name, video URL, and `/feedback` ID in the Devpost draft before the deadline.
4. The entrant must personally confirm Devpost declarations and perform the final Submit action.

## Update Template

```text
Last updated:
Current phase:
Current round:
Round status:
Completed:
Changed files:
Tests:
Open issues:
Next round:
```
