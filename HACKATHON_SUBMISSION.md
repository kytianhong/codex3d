# OpenAI Build Week Submission Draft

## Submission Metadata

- **Title:** Codex3D
- **Tagline:** Create, refine, validate, and safely restore Blender scenes through natural language.
- **Track:** Apps for Your Life
- **Entrant:** Individual
- **Entrant display name:** TO BE PROVIDED
- **Repository URL:** https://github.com/kytianhong/codex3d
- **Release URL:** https://github.com/kytianhong/codex3d/releases/tag/hackathon-v0.1.0
- **Public YouTube URL:** TO BE PROVIDED
- **Primary `/feedback` Session ID:** TO BE PROVIDED

## Problem

Blender gives creators extraordinary control, but its interface assumes familiarity with 3D coordinates, object hierarchies, materials, lighting, cameras, keyframes, rendering, and file recovery. A beginner often has a clear visual intention but cannot translate it into safe, precise operations or confidently undo a bad direction.

## Solution

Codex3D is a local-first natural-language 3D agent. Codex translates ordinary creative feedback into typed MCP tools. An authenticated localhost bridge queues those actions for Blender's main thread, then returns compact scene inspection and render validation. Persistent object identity and fingerprinted snapshots let users iterate, reject a direction, and recover the version they approved.

## Features

- Natural-language, multi-turn Blender control through twenty-three structured MCP tools.
- Primitive and cyclic-curve creation, advanced materials, lights, camera, world, animation, render, and checkpoint delivery.
- Stable object UUIDs across rename and `.blend` reload.
- Session-bound snapshots with automatic pre-restore safety snapshots.
- Composition validation for crop, center, unwanted objects, curve visibility, luminance, and overexposure.
- Versioned `.blend`, validated PNG, and controlled H.264 MP4 delivery.
- Installable Blender Extension and no-Blender fake-backend judge smoke path.

## How It Works

```text
User feedback
  -> Codex with GPT-5.6
  -> local STDIO MCP adapter
  -> authenticated 127.0.0.1 bridge
  -> bounded Blender main-thread pump
  -> structured bpy backend
  -> inspection / validation / snapshot result
  -> next feedback turn
```

Codex3D never exposes arbitrary Python or shell execution. The MCP/API layers do not import `bpy`; the socket worker never mutates Blender.

## Codex Use

Codex collaborated throughout the project, from the initial monorepo and protocol to the live Blender bridge, typed MCP schemas, tests, isolated acceptance runners, release audit, and documentation. It accelerated repetitive implementation and test generation while helping diagnose concrete failures such as socket/main-thread separation, long inspection payloads, unsafe path semantics, approval-cancelled restore/save, and camera composition regressions.

Key human-directed decisions were Blender-first local execution, structured tools instead of generated scripts, localhost-only authentication, artifact confinement, stable identity, reversible recovery, and honest separation of synthetic evidence from human usability evidence.

## GPT-5.6 Use

The primary build task is `019f7749-0bc7-7733-9d9a-17a37e273539`. Local session metadata records `gpt-5.6-sol` throughout core implementation work beginning July 18, 2026. GPT-5.6 was used meaningfully to reason across protocol, transport, Blender lifecycle, safety, validation, and multi-turn recovery boundaries. The release evidence includes a sanitized model/session summary and a GPT-5.6-targeted real MCP workflow result; it excludes tokens and private configuration.

## Challenges

- Blender allows scene access only on its main thread, while the external client is a separate process.
- Unattended approval semantics initially cancelled restore and checkpoint delivery.
- Basic nonblack render checks missed cropped, off-center, overexposed, and unwanted objects.
- Long scene inspections polluted multi-turn context and slowed creative feedback.

## Accomplishments

- `153 passed, 3 skipped` in the default suite.
- An unchanged nine-turn synthetic novice-language test reached `SYNTHETIC_PASS 100/100`.
- Exact accepted-state restore, persistent UUIDs, validated PNG, H.264 MP4, and versioned `.blend` passed in isolated Blender 5.1.1.
- Compact inspection reduced response characters by 91.1% in the repaired test.

## What I Learned

A creative agent is not only a planner. It also needs a disciplined execution language, state identity, observable feedback, and a recovery model that lets a user safely say, "I don't like that version." For novice workflows, trust comes from controllable iteration more than from one-shot generation.

## What Is Next

Run moderated novice usability studies, profile the current 17.5-minute long flow, and design a simple progress UI. Full Scene IR reconciliation and long-term version history remain separate future work.

## Testing Instructions

Use the prebuilt Blender Extension ZIP and `docs/blender_addon_install.md`, then follow `docs/codex_mcp.md`. For a quick repository-only check:

```bash
python -m pytest
PYTHONPATH=packages/protocol:apps/api:connectors/blender_addon \
python examples/hackathon_sprint_01_demo.py
```

The smoke path uses the same Action/executor boundaries with a deterministic fake backend and requires no Blender or external provider.

## Limitations

The full nine-turn synthetic flow takes about 17.5 minutes. Broad mutation batches may require approval. There is no Web UI, no cloud provider, and no full Scene IR reconciliation. The synthetic test demonstrates functional repeatability, not real-user satisfaction or trust.
