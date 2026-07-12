# Worked example — Blender MCP

The **first** fully-worked instance of this skill. The Blender MCP (`ahujasid/blender-mcp`, driven
via `uvx blender-mcp`) was onboarded end-to-end with these templates.

- **Instance repo:** `~/mcp-servers/blender-mcp/` (branch `tooling/mcp-smoke-test`) — holds the
  instantiated `test-blender.sh`, `probe-capabilities.py`, `probe_helpers.py`, the manual, project
  notes, and interactive guide.
- **Upstream fix PR:** the `set_texture` Blender-4.0+ version-guard fix →
  `https://github.com/ahujasid/blender-mcp/pull/280` (a *novel-additions-vs-upstreamable-fix* split
  in action: only the fix went upstream; the probe/manual/guide stayed local and generalized here).
- **Latest probe result:** 9 WORKS, 1 FIXED-PENDING-RELOAD (Blender 5.1.2).

## Every placeholder → its Blender value

| Token | Blender value |
|---|---|
| `MCP_SERVER_ARGV` | `["uvx", "blender-mcp"]` |
| `MCP_SERVER_ENV` | `{"PATH": "/opt/homebrew/bin:/usr/local/bin:" + HOME + "/.local/bin:/usr/bin:/bin"}` |
| `STDERR_LOG` | `/tmp/blender-probe-mcp-stderr.log` |
| `SMOKE_CALL` | `get_scene_info` |
| `APP_CONFIG_DIR` | `/Users/bra0002h/Library/Application Support/Blender` |
| `INSTANCE_REPO` | `~/mcp-servers/blender-mcp` |

## Blender-specific gotchas (learned during the instantiation)

- **The running add-on is a separate installed COPY** (`~/Library/Application Support/Blender/5.1/
  scripts/addons/addon.py`), distinct from the source clone. Editing the source does not change the
  running add-on.
- **Add-ons don't hot-reload**, and the running add-on can't be safely reloaded over its own MCP
  socket (that drops the `:9876` channel). So a just-applied fix reads `FIXED-PENDING-RELOAD` until
  the user reloads the add-on + re-clicks **Connect to Claude**.
- **Every tool requires a `user_prompt` argument** (server-side pydantic); a bare `{}` errors.
- **`get_viewport_screenshot` returns an inline image**, not a filepath — verify by image bytes.
- **`execute_blender_code` output is prefixed** with `Code executed successfully:` — strip it.
- **`get_object_info`'s MCP param is `object_name`** (not `name`).
- **PolyHaven downloads need the network** → mark INCONCLUSIVE (not BROKEN) offline.
- A freshly-spawned probe `uvx blender-mcp` **coexists** with Claude's own server on `:9876`.
