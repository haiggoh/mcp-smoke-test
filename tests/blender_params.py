# Exact Blender-specific values that, substituted into the templates, reproduce the proven
# Blender instance files (banner stripped) — see conftest.instance_dir() for where the
# instance lives (MCP_SMOKE_INSTANCE_DIR overrides the ~/mcp-servers/blender-mcp default).
# This is the round-trip fixture AND the worked example for examples/blender.md.
import os

BLENDER_PARAMS = {
    # --- probe-capabilities.py.tmpl (Task 3) ---
    "MCP_SERVER_ARGV": '["uvx", "blender-mcp"]',
    "MCP_SERVER_ENV": '{"PATH": "/opt/homebrew/bin:/usr/local/bin:" + HOME + "/.local/bin:/usr/bin:/bin"}',
    "STDERR_LOG": "/tmp/blender-probe-mcp-stderr.log",
    "PROBE_REPO_DIR": os.path.expanduser("~/mcp-servers/blender-mcp"),
    # --- test-APP.sh.tmpl (Task 4) --- (MCP_SERVER_ARGV reused from above)
    "SMOKE_CALL": "get_scene_info",
    "SMOKE_ARGS": '{"user_prompt": "blender mcp smoke test"}',
    "SMOKE_STDERR_LOG": "/tmp/blender-mcp-smoke-stderr.log",
    "APP_CONFIG_DIR": os.path.expanduser("~/Library/Application Support/Blender"),
    # --- doc templates (Task 5) ---
    "INSTANCE_REPO": "~/mcp-servers/blender-mcp",
}
