# Third-Party Notices

Codex3D source is released under the MIT License. This notice identifies external software and interfaces used by the project; it does not relicense them.

## Runtime and Tooling

| Component | Use | Distribution status |
|---|---|---|
| Blender 5.1.1 and Blender Python API | 3D host and execution API | Not bundled in the source release; governed by Blender's licenses |
| Python standard library | Protocol, transport, build, and test orchestration | Supplied by the user's Python distribution |
| pytest | Development test runner | Not bundled; optional development dependency |
| FFmpeg / ffprobe | Optional controlled PNG-to-H.264 packaging and validation | Not bundled; user-installed executable |
| Codex CLI/Desktop | Natural-language planner and build environment | Not bundled; governed by OpenAI terms |
| Model Context Protocol | STDIO tool interoperability design | Protocol used by original adapter code; no third-party server code vendored |

## Vendored Code

The Blender Extension build vendors this repository's own `codex3d_protocol` package so the installed extension does not depend on an absolute development path. No Blender, Codex, OpenAI SDK, FFmpeg, pytest, or third-party Python package is vendored.

## Attribution and Inspiration

The kinetic emblem is an original, unofficial Codex-inspired concept. It does not copy an official OpenAI logo and does not imply OpenAI endorsement. Product and project names belonging to third parties are used only to identify compatibility or integration.

The current audit found no copied third-party source tree. This is a repository-level provenance statement, not a legal opinion; entrants remain responsible for confirming ownership of all material they submit.
