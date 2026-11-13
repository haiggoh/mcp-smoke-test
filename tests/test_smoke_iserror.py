"""The smoke launcher must fail on an MCP application error (result.isError=true) — not only
on JSON-RPC transport errors or text that happens to start with "error".

Negative control: a stub server that answers the smoke call with isError=true and text NOT
starting with "error" must NOT read SMOKE PASS (the old launcher passed it — the flag was
never checked). Planted positive: the same stub in healthy mode must SMOKE PASS.

Also pinned: a FAILING smoke still prints the stderr-log pointer (the `set -e` abort used to
swallow the single most useful debugging hint).
"""
import json
import os
import subprocess
import sys

from conftest import TEMPLATES
from render import render

LAUNCHER_TMPL = os.path.join(TEMPLATES, "test-APP.sh.tmpl")

SMOKE_STUB = r'''
"""Stub stdio MCP server for smoke-launcher tests. argv[1] = mode: ok | iserror."""
import json
import sys

mode = sys.argv[1]

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        m = json.loads(line)
    except Exception:
        continue
    if m.get("method") == "initialize":
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": m["id"],
                                     "result": {"capabilities": {}}}) + "\n")
        sys.stdout.flush()
    elif m.get("method") == "notifications/initialized":
        pass
    elif m.get("method") == "tools/call":
        if mode == "iserror":
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": m["id"], "result": {
                "isError": True,
                "content": [{"type": "text",
                             "text": "Blender plugin not connected: click Connect to Claude"}],
            }}) + "\n")
        else:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": m["id"], "result": {
                "content": [{"type": "text", "text": "scene: 3 objects"}],
            }}) + "\n")
        sys.stdout.flush()
'''


def run_launcher(tmp_path, mode):
    stub = tmp_path / "smoke_stub.py"
    stub.write_text(SMOKE_STUB)
    # the REAL documented env literal from blender_params — it references HOME, so this
    # exercises the launcher heredoc's `HOME = os.path.expanduser("~")` line (a PATH-only
    # env here would let that line rot unnoticed)
    from blender_params import BLENDER_PARAMS
    params = {
        "MCP_SERVER_ARGV": json.dumps([sys.executable, str(stub), mode]),
        "MCP_SERVER_ENV": BLENDER_PARAMS["MCP_SERVER_ENV"],
        "APP_CONFIG_DIR": str(tmp_path / "no-such-config"),
        "SMOKE_CALL": "get_scene_info",
        "SMOKE_ARGS": '{"user_prompt": "smoke test"}',
        "SMOKE_STDERR_LOG": str(tmp_path / "smoke-stderr.log"),
        "PROBE_REPO_DIR": str(tmp_path),
    }
    script = tmp_path / "test-app.sh"
    script.write_text(render(open(LAUNCHER_TMPL).read(), params))
    script.chmod(0o755)
    return subprocess.run(["bash", str(script)], capture_output=True, text=True, timeout=60)


def test_smoke_passes_on_healthy_result(tmp_path):
    r = run_launcher(tmp_path, "ok")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "SMOKE PASS" in r.stdout


def test_smoke_fails_on_iserror_result(tmp_path):
    r = run_launcher(tmp_path, "iserror")
    assert r.returncode != 0, (
        "isError=true with text not starting with 'error' must not read SMOKE PASS:\n" + r.stdout)
    assert "SMOKE FAIL" in r.stdout


def test_failed_smoke_still_points_at_stderr_log(tmp_path):
    r = run_launcher(tmp_path, "iserror")
    assert r.returncode != 0
    assert "server stderr log" in r.stdout, (
        "a failing smoke must still print the stderr-log pointer (set -e must not swallow it)")
