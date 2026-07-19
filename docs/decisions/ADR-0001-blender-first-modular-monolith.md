# ADR-0001: Blender-First Modular Monolith

Date: 2026-07-18

Status: Accepted

## Context

Codex3D aims to become a beginner-friendly natural-language 3D creation tool for creative workflows. The long-term system may include APIs, UI, Blender integration, providers, validators, asset systems, and agentic feedback loops.

The early project needs a small architecture that can prove the local creative loop before becoming a larger platform.

## Decision

Codex3D will start as a Blender-first modular monolith with local-first development.

The backend will stay API-first so later UI, CLI, connector, and automation surfaces can use the same local project model.

The Blender connector will not carry Agent Runtime, provider, or business logic. It will execute structured commands, inspect scene state, render previews, and return results or errors.

## Rationale

- Blender is local, scriptable, capable, and widely used.
- A modular monolith keeps early development simple while preserving clear package boundaries.
- Local-first files make progress auditable across Codex rounds.
- API-first boundaries reduce the chance of coupling the UI directly to Blender internals.
- A dumb connector is easier to test, replace, and reason about.

## Consequences

- The project will delay cloud, provider, and platform features until the local loop is useful.
- Scene IR and structured tools become central architecture pieces.
- MCP can be added later as an adapter, but it is not the internal core.
- Arbitrary Python remains an escape hatch rather than the main execution path.

