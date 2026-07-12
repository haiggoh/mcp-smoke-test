# Exact Blender-specific values that, substituted into the templates, reproduce the proven
# /Users/bra0002h/mcp-servers/blender-mcp/* files verbatim (banner stripped). This is the
# round-trip fixture AND the worked example for examples/blender.md.
BLENDER_PARAMS = {
    # --- probe-capabilities.py.tmpl (Task 3) ---
    "MCP_SERVER_ARGV": '["uvx", "blender-mcp"]',
    "MCP_SERVER_ENV": '{"PATH": "/opt/homebrew/bin:/usr/local/bin:" + HOME + "/.local/bin:/usr/bin:/bin"}',
    "STDERR_LOG": "/tmp/blender-probe-mcp-stderr.log",
    # --- test-APP.sh.tmpl (Task 4) --- (MCP_SERVER_ARGV reused from above)
    "SMOKE_CALL": "get_scene_info",
    "APP_CONFIG_DIR": "/Users/bra0002h/Library/Application Support/Blender",
}
