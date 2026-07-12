# Worked example — Adobe Photoshop MCP (the origin instance)

The Photoshop MCP is where this method was **born** (before it was generalized against Blender and
extracted into this skill). Instance repo: `~/mcp-servers/adobe-mcp/` (fork of
`stewberticus/adobe-mcp`, itself a fork of `mikechambers/adb-mcp`). It has the full artifact set —
`test-photoshop.sh`, `probe-capabilities.py`, `PHOTOSHOP-MCP-CAPABILITIES.md`, `PROJECT-NOTES.md`,
and (now) `interactive-guide.md` built by instantiating this skill.

## Placeholder values (where they map cleanly)

| Token | Photoshop value |
|---|---|
| `MCP_SERVER_ARGV` | `["<repo>/.venv/bin/adobe-photoshop"]` (a venv console-script, not `uvx`) |
| `MCP_SERVER_ENV` | `{"PATH": "/usr/bin:/bin", "PROXY_URL": "http://localhost:3001", "APPLICATION": "photoshop"}` |
| `STDERR_LOG` | `/tmp/probe-mcp-stderr.log` |
| `SMOKE_CALL` | `get_documents` |
| `INSTANCE_REPO` | `~/mcp-servers/adobe-mcp` |
| `APP_CONFIG_DIR` | *(diverges)* Photoshop has no per-user config-version dir; version detection instead globs `/Applications` for `Adobe Photoshop*.app` and reads `CFBundleShortVersionString` (flag `< 26.0`). |

## Where Photoshop diverges from the single-socket shape (honest edges of the generalization)

- **3-tier transport, not one socket.** Claude → `adobe-photoshop` MCP server → **Node proxy on
  `:3001`** → in-app **UXP panel**. So the prereq ladder has an extra rung (proxy *and* panel), and
  the connectivity check is `get_documents` returning something other than `No clients registered`.
- **Reload loop is the UXP Developer Tool**, not an add-on checkbox: after a plugin-code edit the
  user Reloads in UXP DT and re-Connects the panel (the analogue of Blender's add-on reload).
- **The probe spawns a venv console-script**, and passes `PROXY_URL`/`APPLICATION` env (vs Blender's
  bare `uvx` + PATH-only env). The engine (stderr-to-file drain, reader thread, retry/fail-fast,
  functional before/after asserts) is identical.
- **Sensei cutouts may depend on network** (`select_subject`/`remove_background` can call Adobe
  cloud) — mark INCONCLUSIVE on a restricted network rather than BROKEN, and check the Select
  Subject Device-vs-Cloud setting. See the instance's `PHOTOSHOP-MCP-CAPABILITIES.md`.

## Status of the Photoshop instance (2026-07-12)

- Probe last clean run (home wifi): **31 WORKS / 3 PARTIAL / 3 BROKEN**. Cutouts work on a smart
  object; BROKEN: `clear_selection`, `create_gradient_layer_style`, `group_layers`.
- Local branch `fix/place-image-and-capability-tooling` (unpushed) holds a `place_image` fix + the
  packaging fixes + the probe/manual/tooling. Publish route (upstream PR vs doctor tool) is a
  pending decision. Corporate-wifi cutout re-test is pending (needs that network).
