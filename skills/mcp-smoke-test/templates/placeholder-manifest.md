# Placeholder manifest

Every placeholder token used across the templates in this directory, its meaning, and the value it
takes for the worked Blender instance (see `../examples/blender.md`). When instantiating for a new
MCP, fill each token with your app's value. The test suite enforces that this manifest documents
**exactly** the tokens the templates actually use — no undocumented tokens, no unused ones.

| Token | Meaning | Blender example |
|---|---|---|
| `MCP_SERVER_ARGV` | The stdio MCP server spawn argv (Python list literal) used by the probe's `subprocess.Popen`. | `["uvx", "blender-mcp"]` |
| `MCP_SERVER_ENV` | The minimal env dict passed to the spawned server (Python dict literal). Keep only what the server needs to launch. | `{"PATH": "/opt/homebrew/bin:/usr/local/bin:" + HOME + "/.local/bin:/usr/bin:/bin"}` |
| `STDERR_LOG` | Path of the FILE the server's stderr is drained to (never an unread pipe). | `/tmp/blender-probe-mcp-stderr.log` |
| `SMOKE_CALL` | Name of the cheap, read-only tool the launcher calls to prove connectivity. | `get_scene_info` |
| `APP_CONFIG_DIR` | The app's per-user config root the launcher enumerates for installed versions. | `/Users/bra0002h/Library/Application Support/Blender` |
| `INSTANCE_REPO` | The instance repo path referenced in PROJECT-NOTES (where the artifacts live). | `~/mcp-servers/blender-mcp` |

## Notes

- The **probe engine** (reader thread, handshake, `call`/retry/`_abort_stall`, cleanup) and the
  **launcher structure** (`set -euo pipefail`, version detect, smoke vs `--capabilities`) are
  MCP-agnostic and are NOT tokenized — they carry over unchanged.
- `run_probe`'s per-tool assertions in `probe-capabilities.py.tmpl` are a **worked Blender example**;
  rewrite them for your app's tools (the engine stays as-is).
- The capabilities manual and interactive guide ship as **structural skeletons** — copy them, then
  fill the app-specifics and seed the manual from your first probe run.
