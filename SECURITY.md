# Security Policy

## Supported Version

The Hackathon release candidate supports version `0.1.0` on the documented local setup.

## Boundary

Codex3D accepts only allowlisted structured Actions. It intentionally has no arbitrary Python, shell, `eval`, or `exec` MCP capability. The Blender bridge binds only to `127.0.0.1`, uses a one-time token, enforces a 2 MiB frame limit, and schedules all Blender access on the main thread. Output and snapshot paths must resolve inside `CODEX3D_ARTIFACT_ROOT`.

The local token grants control of the connected Blender instance. Keep it private, rotate it when reconnecting, and never place it in Git, screenshots, issue reports, or shared terminal history.

## Reporting

Do not include tokens, private `.blend` files, or personal paths in a report. Until a public repository is assigned, report security issues privately to the repository owner through the contact channel listed on the eventual repository page.

## Out of Scope

Codex3D is an alpha hackathon project, not a hardened remote service. LAN/public binding, multi-user isolation, TLS, cloud execution, and untrusted tenant workloads are unsupported.
