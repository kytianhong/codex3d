# OpenAI Build Week Submission Sprint Report

Date: 2026-07-19  
Status: CONDITIONALLY_READY  
Track: Apps for Your Life  
Entrant: Individual; display name TO BE PROVIDED

## Completed

- Verified the official OpenAI Build Week Rules and mapped deadline, model, repository, video, README, `/feedback`, judge path, and English-language requirements.
- Confirmed the primary build task id `019f7749-0bc7-7733-9d9a-17a37e273539`; persisted settings record `gpt-5.6-sol` throughout core implementation.
- Ran a fresh isolated real-Blender Target Codex workflow with explicit `gpt-5.6-sol`: 100/100, 146 MCP calls, zero failed calls, exact snapshot restore, PNG, H.264 MP4, and `.blend` delivery.
- Added the authorized MIT License, third-party notices, security policy, English judge README, architecture narrative, Devpost draft, and 2:45 narrated video script.
- Added whitelist-only deterministic release builder and machine-readable preflight.
- Excluded raw artifacts, frame sequences, reruns, logs, traces, caches, tokens, `dist/`, and release outputs from Git.
- Initialized a local `main` Git repository and reviewed the staged set before the initial commit.

## GPT-5.6 Evidence

- Primary task model: `gpt-5.6-sol`.
- Target acceptance session: `019f7c8d-f534-7ef3-a6ce-69ca7fbc7cd2`.
- Elapsed: 397.152 seconds.
- Restore fingerprint before/after: `25d3c41dda15480f2d9e5d168f62c01b5d9f8871c55cbd47eaf5dc8dc3d20120`.
- Final `.blend` SHA-256: `4d9e81f9886e0959d856e6f80e753243adace62ea76b2cfdf1bf575a704f2e7c`.
- Final PNG SHA-256: `5f0f585ac928172624e2748d6d25ccf65e6d2df2d4f42c23dee076a81dd52c05`.
- Final MP4 SHA-256: `a5eb2b267be378c32a0facbecaa9419d57d972ba647018d896e71edc5d99d5ae`.
- Token leakage, user `.blend` mutation, global Codex config change, residual Blender process, and occupied Bridge port: none.

The rejected-edit visual heuristic was false in this evidence run; this is retained in the public evidence notes. The rejected fingerprint differed from the accepted one, restore matched exactly, and all required delivery checks passed.

## Tests and Reproduction

- Workspace default suite: `153 passed, 3 skipped`.
- Compile smoke: PASSED.
- Extension build and ZIP validation: PASSED, 29 files.
- `/tmp` clean-room source extraction: PASSED.
- Clean-room default suite: `153 passed, 3 skipped`.
- Clean-room Extension rebuild: PASSED.
- Clean-room fake judge demo: 31 planned, 31 succeeded, 16 objects.
- ZIP traversal, symlink, unsafe permission, secrets, token and private absolute path scan: PASSED.

## Release Bundles

| Bundle | Size target |
|---|---:|
| `codex3d-hackathon-0.1.0-source.zip` | under 10 MiB |
| `codex3d-blender-extension-0.1.0.zip` | under 1 MiB |
| `codex3d-demo-assets-0.1.0.zip` | under 10 MiB |

Final byte sizes and SHA-256 values are generated after documentation is frozen and recorded only in `release/SHA256SUMS` and `release/preflight.json`; the source archive deliberately does not embed its own checksum.

No 72-frame sequence, historical rerun, raw conversation/tool trace, Blender log, local token, or private path is included.

## Publication Status

- Local Git repository: prepared on `main`.
- Repository strategy: public GitHub is recommended for the shortest judge path.
- Remote and push: NOT RUN; no URL was provided and `gh` is not installed.
- Suggested tag after remote review: `hackathon-v0.1.0`.
- Narrated public YouTube demo: USER_RECORDING_REQUIRED.
- `/feedback` Session ID: NOT FOUND. The ordinary task id is intentionally not substituted.
- Entrant display name: TO BE PROVIDED.

## Remaining Submission Blockers

1. Run `/feedback` in the primary build task and record its returned Session ID.
2. Provide the entrant display name used on Devpost.
3. Create/confirm the public GitHub repository and push after reviewing `origin` and visibility.
4. Record and upload the narrated public YouTube video under three minutes.
5. Replace all `TO BE PROVIDED` fields and submit the English Devpost form before the deadline.
