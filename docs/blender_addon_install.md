# Blender Extension Installation

Target verified in Sprint 02A1: Blender 5.1.1 on macOS arm64.

## Build

From the project root:

```bash
python scripts/build_blender_extension.py
```

The installable ZIP is created at:

```text
dist/codex3d_blender_connector-0.1.0.zip
```

The build uses a temporary staging directory, copies the connector source, vendors `codex3d_protocol`, excludes tests and caches, and validates the ZIP root. The package has no absolute workspace dependency.

The Blender CLI can also validate the result:

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --command extension validate \
  dist/codex3d_blender_connector-0.1.0.zip
```

## Install From Disk

1. Open Blender Preferences.
2. Open Extensions.
3. Choose `Install from Disk`.
4. Select the ZIP from `dist/`.
5. Enable `Codex3D Blender Connector`.
6. In a 3D View, press `N` and open the `Codex3D` tab.

The extension requests network permission for the localhost socket and clipboard permission for copying connection details. It does not connect to the Blender Extensions Platform.

## Connect

The Panel shows status, fixed host `127.0.0.1`, port, masked token, pending count, last request, and last error.

1. Keep the default port `9876` unless it is occupied.
2. Click Connect. An empty token is generated locally.
3. Click Copy Connection Info.
4. Run the external client or demo with those values.
5. Click Disconnect before disabling or upgrading the extension.

Connect never starts automatically. Repeated clicks do not create a second listener.

## Troubleshooting

- `Port occupied`: choose another local port and use the same port in the client.
- `Wrong token`: copy fresh connection info from the Panel.
- `Offline`: enable the extension, open the Panel, and click Connect.
- `Extension import error`: rebuild the ZIP and confirm `vendor/codex3d_protocol` exists inside it.
- `Permission denied`: allow the extension's localhost network permission in Blender.

## Upgrade Or Uninstall

Disconnect first, then disable or uninstall the extension in Blender Preferences. `unregister()` performs the same complete shutdown path, including timer removal and thread cleanup.

The manifest currently uses `SPDX:LicenseRef-Codex3D-Internal` for local Hackathon packaging. Project ownership must confirm publication licensing before any public extension release.
