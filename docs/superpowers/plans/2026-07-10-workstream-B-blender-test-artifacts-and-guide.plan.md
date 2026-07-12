# Blender MCP Test Artifacts + Interactive Setup Guide Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Build the Blender-MCP smoke test, functional capability probe, evidence-based capabilities manual, project notes, and interactive setup guide in `/Users/bra0002h/mcp-servers/blender-mcp/`, mirroring the proven Adobe Photoshop MCP artifact shape adapted to Blender's stdio-JSON-RPC → add-on-socket transport.

**Architecture:** A launcher (`test-blender.sh`) offers a read-only `smoke` mode (default) and a `--capabilities` mode. Both spawn `uvx blender-mcp` (the exact server Claude uses) and speak newline-delimited JSON-RPC over stdio; the full probe (`probe-capabilities.py`) drains server stderr to a file, runs FUNCTIONAL before/after assertions per tool, classifies WORKS/PARTIAL/BROKEN/INCONCLUSIVE, fail-fasts on a second consecutive stall, cleans up the scene artifacts it created, and writes `capability-report.json`. The manual, project notes, and interactive prereq-ladder guide are documentation seeded from the 2026-07-10 smoke-test facts and the `set_texture` finding.

**Tech Stack:** Python 3 (stdlib only: `subprocess`, `threading`, `json`, `time`, `os`, `re`, `argparse`), Bash (`set -euo pipefail`), `uvx blender-mcp` as the MCP server, the in-Blender add-on socket on `127.0.0.1:9876`, `pytest` for the pure-helper unit tests, `git`/`gh` for version control.

> **Execution refinements (added 2026-07-12 during recovery — apply when executing):**
> 1. **No Blender reload of its own — shares Workstream A's session.** This plan adds only external test scripts and does NOT modify `addon.py`, so it needs no add-on reload: its probe runs against the same live Blender + add-on session used in Workstream A (one shared reload/connection, not two).
> 2. **Be honest about the `set_texture` reload boundary in the probe.** Because the live add-on may not have been reloaded with Workstream A's fix during this session, the probe's `set_texture` check must detect whether the running add-on actually contains the fix (probe the node path via `execute_blender_code`) and classify it as WORKS (fix live) or `FIXED-PENDING-RELOAD` (fix present in `addon.py` + node-logic verified via `execute_blender_code`, awaiting an add-on reload) — never a misleading BROKEN. Seed the capabilities manual with that same distinction.

## Global Constraints

These rules are project-wide and apply to EVERY task below. Do not violate them even where a task step is silent about them.

- **Blender version-guard logic (informational — do NOT re-implement the fix here):** The `set_texture` fix (branching on `bpy.app.version >= (4, 0)` between `ShaderNodeSeparateColor` and `ShaderNodeSeparateRGB`) is Workstream A's job and is assumed ALREADY APPLIED to the clone at `/Users/bra0002h/mcp-servers/blender-mcp/addon.py` before Workstream B artifacts are exercised. Workstream B only *verifies* it (the probe's `set_texture` functional assertion) and *documents* it (the manual's pre/post-fix section). Never re-edit the fix in this plan.
- **Preserve file permissions on in-place edits:** When modifying an existing file (config, dotfile, script), edit in place (Edit tool / `sed -i`) so the inode's mode is kept. Never `> tmp && mv tmp file` or plain `> file` recreation on an existing file — that recreates it at the default umask (often 644) and can widen perms on a `600` secrets file. New files created fresh in this plan (`chmod +x` on the two scripts) are exempt because they have no prior mode to preserve.
- **`gh` account = `haiggoh`:** All GitHub operations use the `haiggoh` login (already authed with `repo`, `workflow` scopes). This plan does no PR work (that is Workstream A/C), but any incidental `gh` call must be under `haiggoh`.
- **ONE canonical marketplace:** There is a single canonical Claude-plugin marketplace — the sync repo (`haiggoh/claude-code-desktop-sync`). Never ship a per-plugin `marketplace.json`. (Not exercised in this plan; stated for consistency across the 3-plan set.)
- **No unread `stderr=PIPE`:** Any spawned subprocess whose stderr is verbose (the MCP server) MUST drain stderr to a FILE sink (or DEVNULL / a reader thread), never leave `stderr=subprocess.PIPE` unread — the OS pipe buffer (~64KB) fills after ~a dozen commands and the server blocks on its next stderr write, a real deadlock we already hit on the Adobe probe. This is load-bearing in Task 3.
- **No concurrent MCP calls:** The probe issues exactly one `tools/call` at a time and waits for its response (or stall) before the next. Never fire overlapping requests.
- **Clean up what you spawn / create:** The launcher installs an EXIT trap that kills only the process it started. The probe `try/finally`-terminates the server subprocess and deletes the scene objects/materials it created (restore to the pre-probe object set).
- **Exact Blender install path:** Only Blender 5.1 is installed; its config tree is `/Users/bra0002h/Library/Application Support/Blender/5.1/`. Version enumeration globs `/Users/bra0002h/Library/Application Support/Blender/*/`.
- **Same server Claude uses:** The probe/launcher spawn `uvx blender-mcp` with `env={}` (empty), matching the user-scope `mcpServers.blender` entry in `~/.claude.json` exactly (`command: "uvx"`, `args: ["blender-mcp"]`, `type: "stdio"`). Do not substitute a venv script or a different invocation.

---

## Task 1: Repo scaffolding + Python helper module for pure classification/parse logic (TDD)

Create the Workstream-B home directory structure and a small importable helper module `probe_helpers.py` holding the *pure* functions the probe and launcher logic depend on (JSON-RPC result unwrapping, verdict classification, Blender-version parsing, and the report summary builder). These are the only genuinely unit-testable pieces; everything else in the probe requires a live Blender and is verified live in Task 4.

**Files:**
- Create `/Users/bra0002h/mcp-servers/blender-mcp/probe_helpers.py`
- Create `/Users/bra0002h/mcp-servers/blender-mcp/test_probe_helpers.py`

**Interfaces:**
- Produces `unwrap_tool_result(msg: dict) -> tuple[bool, dict|None, str]` — returns `(ok, payload, raw_text)`.
- Produces `classify(ok: bool, changed: bool, verify_available: bool) -> str` — returns one of `"WORKS"|"PARTIAL"|"BROKEN"|"INCONCLUSIVE"`.
- Produces `parse_blender_versions(dir_names: list[str]) -> list[str]` — returns sorted numeric version dir names.
- Produces `build_summary(results: list[dict]) -> dict[str,int]` — counts by `status`.

- [ ] Verify the clone exists (Plan A precondition): run `test -f /Users/bra0002h/mcp-servers/blender-mcp/addon.py && echo CLONE_OK || echo CLONE_MISSING`. Expected output: `CLONE_OK`. If `CLONE_MISSING`, STOP — Plan A (clone + fix) has not run; this plan cannot proceed.
- [ ] Confirm you are in the clone's git repo: run `git -C /Users/bra0002h/mcp-servers/blender-mcp rev-parse --is-inside-work-tree`. Expected output: `true`.
- [ ] Write the failing test file `/Users/bra0002h/mcp-servers/blender-mcp/test_probe_helpers.py` with these exact contents:
```python
import probe_helpers as h


def test_unwrap_success_with_status_success():
    msg = {"result": {"content": [{"type": "text", "text": '{"status": "SUCCESS", "n": 3}'}]}}
    ok, payload, raw = h.unwrap_tool_result(msg)
    assert ok is True
    assert payload == {"status": "SUCCESS", "n": 3}
    assert '"status": "SUCCESS"' in raw


def test_unwrap_plain_text_no_payload_is_ok():
    msg = {"result": {"content": [{"type": "text", "text": "scene has 4 objects"}]}}
    ok, payload, raw = h.unwrap_tool_result(msg)
    assert ok is True
    assert payload is None
    assert raw == "scene has 4 objects"


def test_unwrap_transport_error():
    msg = {"error": {"code": -32000, "message": "boom"}}
    ok, payload, raw = h.unwrap_tool_result(msg)
    assert ok is False
    assert payload is None
    assert "boom" in raw


def test_unwrap_iserror_flag():
    msg = {"result": {"isError": True, "content": [{"type": "text", "text": "nope"}]}}
    ok, _, _ = h.unwrap_tool_result(msg)
    assert ok is False


def test_unwrap_text_starting_with_error():
    msg = {"result": {"content": [{"type": "text", "text": "Error: object not found"}]}}
    ok, _, _ = h.unwrap_tool_result(msg)
    assert ok is False


def test_unwrap_payload_status_error_is_failure():
    msg = {"result": {"content": [{"type": "text", "text": '{"status": "error", "message": "x"}'}]}}
    ok, payload, _ = h.unwrap_tool_result(msg)
    assert ok is False
    assert payload == {"status": "error", "message": "x"}


def test_classify_works():
    assert h.classify(ok=True, changed=True, verify_available=True) == "WORKS"


def test_classify_partial_when_ok_but_no_change():
    assert h.classify(ok=True, changed=False, verify_available=True) == "PARTIAL"


def test_classify_broken_when_not_ok():
    assert h.classify(ok=False, changed=False, verify_available=True) == "BROKEN"


def test_classify_inconclusive_when_verify_unavailable():
    assert h.classify(ok=True, changed=False, verify_available=False) == "INCONCLUSIVE"
    assert h.classify(ok=True, changed=True, verify_available=False) == "INCONCLUSIVE"


def test_parse_blender_versions_sorted_numeric_only():
    assert h.parse_blender_versions(["5.1", "4.0", "3.6", "config", ".DS_Store"]) == ["3.6", "4.0", "5.1"]


def test_parse_blender_versions_empty():
    assert h.parse_blender_versions(["config", "randomdir"]) == []


def test_build_summary_counts_by_status():
    results = [
        {"command": "a", "status": "WORKS", "detail": ""},
        {"command": "b", "status": "WORKS", "detail": ""},
        {"command": "c", "status": "BROKEN", "detail": ""},
        {"command": "d", "status": "INCONCLUSIVE", "detail": ""},
    ]
    assert h.build_summary(results) == {"WORKS": 2, "BROKEN": 1, "INCONCLUSIVE": 1}
```
- [ ] Run the test and watch it FAIL (module missing): `cd /Users/bra0002h/mcp-servers/blender-mcp && python3 -m pytest test_probe_helpers.py -q`. Expected: collection/import error (`ModuleNotFoundError: No module named 'probe_helpers'`) or all-fail.
- [ ] Create `/Users/bra0002h/mcp-servers/blender-mcp/probe_helpers.py` with these exact contents:
```python
"""Pure, unit-testable helpers for the Blender MCP capability probe.

These functions contain NO I/O and NO Blender/network dependency, so they can be
tested deterministically. Everything that needs a live Blender lives in
probe-capabilities.py and is verified live.
"""
import json
import re


def unwrap_tool_result(msg):
    """Unwrap an MCP tools/call JSON-RPC response.

    MCP wraps tool output in result.content[0].text. Returns (ok, payload, raw_text):
      - ok: functional success = no transport error, not isError, text not "error...",
            and (no JSON payload OR payload.status == "SUCCESS").
      - payload: the json.loads of the text if it parsed, else None.
      - raw_text: the first 300 chars of the text (or the error blob).
    """
    if "error" in msg:
        return (False, None, json.dumps(msg["error"])[:300])
    res = msg.get("result", {}) or {}
    content = res.get("content") or []
    text = ""
    if content and isinstance(content[0], dict):
        text = content[0].get("text") or ""
    is_err = bool(res.get("isError")) or text.lower().startswith("error")
    payload = None
    try:
        payload = json.loads(text)
    except Exception:
        payload = None
    status_ok = True
    if isinstance(payload, dict) and "status" in payload:
        status_ok = payload.get("status") == "SUCCESS"
    ok = (not is_err) and status_ok
    return (ok, payload, text[:300])


def classify(ok, changed, verify_available):
    """Functional verdict.

    - INCONCLUSIVE if the verification READ itself was unavailable (can't trust either way).
    - WORKS if ok and the observed state changed as expected.
    - PARTIAL if the call reported success but the expected change did not happen.
    - BROKEN if the call did not report success.
    """
    if not verify_available:
        return "INCONCLUSIVE"
    if not ok:
        return "BROKEN"
    return "WORKS" if changed else "PARTIAL"


def parse_blender_versions(dir_names):
    """From a list of directory names, keep only version-like ones (e.g. '5.1', '4.0')
    and return them sorted by numeric tuple ascending."""
    versions = [d for d in dir_names if re.fullmatch(r"\d+\.\d+", d)]
    versions.sort(key=lambda v: tuple(int(p) for p in v.split(".")))
    return versions


def build_summary(results):
    """Count results by their 'status' key -> {status: count}."""
    summary = {}
    for r in results:
        s = r.get("status", "UNKNOWN")
        summary[s] = summary.get(s, 0) + 1
    return summary
```
- [ ] Run the test and watch it PASS: `cd /Users/bra0002h/mcp-servers/blender-mcp && python3 -m pytest test_probe_helpers.py -q`. Expected: `13 passed`.
- [ ] Stage and commit:
```
git -C /Users/bra0002h/mcp-servers/blender-mcp add probe_helpers.py test_probe_helpers.py
git -C /Users/bra0002h/mcp-servers/blender-mcp commit -m "Add pure probe helpers (unwrap/classify/version-parse/summary) with unit tests

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: `test-blender.sh` launcher — smoke mode + version detection (TDD on version-detect, live-verify on smoke)

Create the launcher: `set -euo pipefail`, `MODE="${1:-smoke}"`, prints detected Blender version(s) from the config tree, and in smoke mode spawns `uvx blender-mcp` and does a single read-only `get_scene_info` handshake. An EXIT trap kills any spawned server. The version-detection logic is factored into a testable path (it reuses `probe_helpers.parse_blender_versions`).

**Files:**
- Create `/Users/bra0002h/mcp-servers/blender-mcp/test-blender.sh`
- Create `/Users/bra0002h/mcp-servers/blender-mcp/test_launcher_versiondetect.py`

**Interfaces:**
- Consumes `uvx blender-mcp` (stdio JSON-RPC MCP server).
- Consumes `probe_helpers.parse_blender_versions`.
- Produces console output: version list, smoke PASS/FAIL, and (in `--capabilities` mode) delegates to `python3 -u probe-capabilities.py`.

- [ ] Write the failing test `/Users/bra0002h/mcp-servers/blender-mcp/test_launcher_versiondetect.py` with these exact contents (it asserts the *shell* prints the versions the pure helper computes, guaranteeing script and helper agree):
```python
import os
import subprocess
import probe_helpers as h

REPO = "/Users/bra0002h/mcp-servers/blender-mcp"
BLENDER_CFG = "/Users/bra0002h/Library/Application Support/Blender"


def _installed_versions():
    if not os.path.isdir(BLENDER_CFG):
        return []
    return h.parse_blender_versions(os.listdir(BLENDER_CFG))


def test_launcher_reports_installed_blender_versions():
    versions = _installed_versions()
    # Run the launcher's version-print path only (BLMCP_PRINT_VERSIONS_ONLY short-circuits).
    out = subprocess.run(
        ["bash", f"{REPO}/test-blender.sh"],
        env={**os.environ, "BLMCP_PRINT_VERSIONS_ONLY": "1"},
        capture_output=True, text=True, timeout=30,
    )
    assert out.returncode == 0, out.stderr
    for v in versions:
        assert v in out.stdout, f"expected version {v} in launcher output:\n{out.stdout}"
    # 5.1 is the known-installed version per the 2026-07-10 facts.
    assert "5.1" in out.stdout
```
- [ ] Run the test and watch it FAIL (script missing): `cd /Users/bra0002h/mcp-servers/blender-mcp && python3 -m pytest test_launcher_versiondetect.py -q`. Expected: failure — `bash: .../test-blender.sh: No such file or directory` (nonzero returncode).
- [ ] Create `/Users/bra0002h/mcp-servers/blender-mcp/test-blender.sh` with these exact contents:
```bash
#!/usr/bin/env bash
# Blender MCP smoke test + capability probe launcher.
#   ./test-blender.sh                 # smoke (default): read-only get_scene_info connectivity
#   ./test-blender.sh --capabilities  # full functional probe (probe-capabilities.py)
# Spawns the SAME server Claude uses: `uvx blender-mcp` (stdio JSON-RPC), which relays to the
# in-Blender add-on socket on 127.0.0.1:9876. Blender must be running with the add-on connected.
set -euo pipefail

REPO="/Users/bra0002h/mcp-servers/blender-mcp"
BLENDER_CFG="/Users/bra0002h/Library/Application Support/Blender"
# Resolve node/python/uvx from Homebrew + user-local bins regardless of caller PATH.
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:/usr/bin:/bin"

MODE="${1:-smoke}"

# --- Blender version detection ------------------------------------------------
echo "Detecting installed Blender version(s) under: $BLENDER_CFG"
FOUND=""
if [ -d "$BLENDER_CFG" ]; then
  for d in "$BLENDER_CFG"/*/; do
    name="$(basename "$d")"
    if printf '%s' "$name" | grep -Eq '^[0-9]+\.[0-9]+$'; then
      echo "  - Blender $name"
      FOUND="$FOUND $name"
    fi
  done
fi
if [ -z "$FOUND" ]; then
  echo "  (no version-tagged Blender config dirs found)"
fi

# Test-only short-circuit: print versions and exit (used by test_launcher_versiondetect.py).
if [ "${BLMCP_PRINT_VERSIONS_ONLY:-0}" = "1" ]; then
  exit 0
fi

# --- capabilities mode: delegate to the full probe ---------------------------
case "$MODE" in
  --capabilities|capabilities)
    echo ""
    echo "Running full capability probe (probe-capabilities.py)..."
    exec python3 -u "$REPO/probe-capabilities.py"
    ;;
esac

# --- smoke mode: read-only get_scene_info connectivity ------------------------
echo ""
echo "Smoke test: spawning 'uvx blender-mcp' and calling get_scene_info (read-only)..."

STDERR_LOG="/tmp/blender-mcp-smoke-stderr.log"
: > "$STDERR_LOG"

# Spawn the server; capture its PID so the EXIT trap can kill ONLY what we started.
python3 - "$STDERR_LOG" <<'PYEOF'
import json, os, subprocess, sys, threading, time

stderr_log = sys.argv[1]
sink = open(stderr_log, "w")
proc = subprocess.Popen(
    ["uvx", "blender-mcp"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=sink,
    text=True, bufsize=1, env={"PATH": os.environ["PATH"]},
)

resp = {}
lock = threading.Lock()

def reader():
    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        try:
            m = json.loads(line)
        except Exception:
            continue
        if isinstance(m, dict) and m.get("id") is not None:
            with lock:
                resp[m["id"]] = m

threading.Thread(target=reader, daemon=True).start()

def send(o):
    proc.stdin.write(json.dumps(o) + "\n")
    proc.stdin.flush()

def wait_for(i, timeout):
    t0 = time.time()
    while time.time() - t0 < timeout:
        with lock:
            if i in resp:
                return resp.pop(i)
        time.sleep(0.08)
    return None

rc = 1
try:
    send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
          "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                     "clientInfo": {"name": "smoke", "version": "1"}}})
    if wait_for(1, 15) is None:
        print("SMOKE FAIL: no response to initialize (is `uvx blender-mcp` installed?).")
        raise SystemExit(1)
    time.sleep(0.5)
    send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    time.sleep(0.5)
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
          "params": {"name": "get_scene_info", "arguments": {}}})
    m = wait_for(2, 20)
    if m is None:
        print("SMOKE FAIL: no response to get_scene_info within 20s.")
        print("  Likely: Blender not running, add-on not enabled, or 'Connect to Claude' not clicked (no listener on 9876).")
        raise SystemExit(1)
    if "error" in m:
        print("SMOKE FAIL: get_scene_info returned an error:")
        print("  " + json.dumps(m["error"])[:400])
        print("  Likely: add-on socket (127.0.0.1:9876) not connected. Click 'Connect to Claude' in the BlenderMCP N-panel.")
        raise SystemExit(1)
    res = m.get("result", {}) or {}
    content = res.get("content") or []
    text = content[0].get("text") if content and isinstance(content[0], dict) else ""
    print("SMOKE PASS: get_scene_info responded.")
    print("  scene: " + (text or "")[:400])
    rc = 0
finally:
    try:
        proc.terminate()
    except Exception:
        pass
sys.exit(rc)
PYEOF
SMOKE_RC=$?

echo ""
echo "(server stderr log: $STDERR_LOG)"
exit "$SMOKE_RC"
```
- [ ] Make it executable: `chmod +x /Users/bra0002h/mcp-servers/blender-mcp/test-blender.sh`.
- [ ] Run the version-detect unit test and watch it PASS: `cd /Users/bra0002h/mcp-servers/blender-mcp && python3 -m pytest test_launcher_versiondetect.py -q`. Expected: `1 passed`. (This proves version enumeration prints `5.1`.)
- [ ] LIVE smoke verification (USER-IN-LOOP — requires Blender running with the add-on connected on 9876). First confirm the listener: `lsof -nP -iTCP:9876 -sTCP:LISTEN`. Expected: a `Blender` line `... TCP 127.0.0.1:9876 (LISTEN)`. If absent, ask the user to launch Blender, enable the "Interface: Blender MCP" add-on, and click "Connect to Claude" (the interactive guide in Task 6 codifies this), then re-check.
- [ ] With 9876 listening, run: `cd /Users/bra0002h/mcp-servers/blender-mcp && ./test-blender.sh`. Expected output contains `Blender 5.1`, then `SMOKE PASS: get_scene_info responded.` and a `scene:` line naming the current scene (e.g. `Scene`) with an object count. If it prints `SMOKE FAIL`, treat it as an environment/prereq problem (fix per the printed hint) and re-run — do NOT edit the script to mask it.
- [ ] Stage and commit:
```
git -C /Users/bra0002h/mcp-servers/blender-mcp add test-blender.sh test_launcher_versiondetect.py
git -C /Users/bra0002h/mcp-servers/blender-mcp commit -m "Add test-blender.sh launcher: smoke (read-only get_scene_info) + version detect

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: `probe-capabilities.py` — server harness, stderr drain, JSON-RPC, fail-fast (structure + reliability)

Build the probe's transport layer: spawn `uvx blender-mcp` with stderr drained to a FILE (the load-bearing anti-deadlock fix), a daemon reader thread filing stdout responses by id, the `initialize` handshake, a `call()` that paces, polls by id, retries once, and fail-fasts via `_abort_stall` on a second consecutive timeout, plus `try/finally` termination. Functional per-tool assertions and report-writing come in Task 4; this task ends with the harness able to complete the handshake and a single `get_scene_info` call, verified live.

**Files:**
- Create `/Users/bra0002h/mcp-servers/blender-mcp/probe-capabilities.py` (lines 1–~180: header/imports, spawn, reader, handshake, `call`, `_abort_stall`, a temporary `__main__` that does the handshake + one `get_scene_info` and prints it — replaced in Task 4).

**Interfaces:**
- Consumes `uvx blender-mcp`; `probe_helpers.unwrap_tool_result`.
- Produces module-level `call(tool: str, args: dict|None, timeout: float) -> tuple[bool, dict|None, str]`, `bl(code: str) -> str|None` (execute_blender_code round-trip helper returning captured stdout), `_abort_stall(tool: str)`, and globals `proc`, `results`, `REPORT`.
- Produces `/tmp/blender-probe-mcp-stderr.log` (stderr sink).

- [ ] Create `/Users/bra0002h/mcp-servers/blender-mcp/probe-capabilities.py` with these exact contents:
```python
#!/usr/bin/env python3
"""Blender MCP functional capability probe.

Spawns the SAME server Claude uses (`uvx blender-mcp`, stdio JSON-RPC), which relays to the
in-Blender add-on socket on 127.0.0.1:9876. For each tool it captures observable scene state
BEFORE and AFTER the call and asserts the expected change actually happened — classifying
WORKS / PARTIAL / BROKEN / INCONCLUSIVE by FUNCTIONAL checks, never by "no error" (return
status lies for broken commands). Writes capability-report.json.

Reliability rules (hard-won):
  - stderr is drained to a FILE, never an unread PIPE (see comment at _stderr_sink).
  - one call at a time; each call paces to avoid racing the per-call socket.
  - retry-once then fail-fast on a 2nd consecutive timeout (real stall != capability result).
  - try/finally terminates the subprocess; scene artifacts the probe creates are cleaned up.
"""
import json
import os
import subprocess
import threading
import time

import probe_helpers as h

HOME = os.path.expanduser("~")
REPO = f"{HOME}/mcp-servers/blender-mcp"
REPORT = f"{REPO}/capability-report.json"
STDERR_LOG = "/tmp/blender-probe-mcp-stderr.log"
PACE = 0.15  # small gap between calls; the add-on socket is per-call/relayed

results = []

# --- spawn the MCP server -----------------------------------------------------
# IMPORTANT: drain stderr to a FILE, not an unread PIPE. blender-mcp (like the Adobe
# server) logs verbosely to stderr; with stderr=PIPE that we never read, the OS pipe
# buffer (~64KB) fills after ~a dozen commands, the server blocks on its next stderr
# write, and stops responding — a classic unread-pipe deadlock that manufactured a false
# "stalls after ~13 commands". A file sink has no buffer limit, so the writer never blocks,
# and the log stays inspectable afterward.
_stderr_sink = open(STDERR_LOG, "w")
# env is the empty-relative equivalent of the Claude config ("env": {}); we only pass PATH
# so `uvx` resolves. Nothing else is inherited.
_env = {"PATH": "/opt/homebrew/bin:/usr/local/bin:" + HOME + "/.local/bin:/usr/bin:/bin"}
proc = subprocess.Popen(
    ["uvx", "blender-mcp"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=_stderr_sink,
    text=True, bufsize=1, env=_env,
)

# --- stdout reader thread: file responses by id under a lock ------------------
_resp = {}
_lock = threading.Lock()


def _reader():
    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        try:
            m = json.loads(line)
        except Exception:
            continue
        if isinstance(m, dict) and m.get("id") is not None:
            with _lock:
                _resp[m["id"]] = m


threading.Thread(target=_reader, daemon=True).start()


def _send(obj):
    proc.stdin.write(json.dumps(obj) + "\n")
    proc.stdin.flush()


# --- fail-fast stall handler --------------------------------------------------
def _abort_stall(tool):
    """A 2nd consecutive no-response is a real stall, NOT a capability verdict. Print a loud
    diagnosis, write a PARTIAL report marked aborted, terminate the server, hard-exit. Flush
    stdout first because os._exit skips buffer flush (the printed table would be lost)."""
    print(f"\n!! STALLED on '{tool}' — no response within timeout. NOT a capability result.")
    print("   Likely: Blender not running, add-on not enabled, 'Connect to Claude' not clicked")
    print("   (no listener on 127.0.0.1:9876), an open modal in Blender, or a zombie MCP server.")
    print("   Remaining commands intentionally NOT run (a stall falsifies every downstream verdict).")
    results.append({"command": tool, "status": "STALL-ABORT",
                    "detail": "aborted here (blender down / add-on disconnected / modal / zombie)"})
    with open(REPORT, "w") as f:
        json.dump({"blender_version": os.environ.get("BL_VERSION", "unknown"),
                   "aborted": True, "aborted_on": tool, "results": results}, f, indent=2)
    try:
        proc.terminate()
    except Exception:
        pass
    import sys as _sys
    _sys.stdout.flush()
    os._exit(2)


# --- one JSON-RPC tools/call, retry-once, fail-fast on 2nd stall --------------
_id = [100]


def call(tool, args=None, timeout=30):
    """Issue exactly one tools/call and return (ok, payload, raw). One call at a time."""
    time.sleep(PACE)
    for attempt in (1, 2):
        _id[0] += 1
        i = _id[0]
        _send({"jsonrpc": "2.0", "id": i, "method": "tools/call",
               "params": {"name": tool, "arguments": args or {}}})
        m = None
        t0 = time.time()
        while time.time() - t0 < timeout:
            with _lock:
                if i in _resp:
                    m = _resp.pop(i)
                    break
            time.sleep(0.08)
        if m is not None:
            break
        if attempt == 1:
            time.sleep(0.6)  # transport hiccup — one retry (the hung call never executed)
            continue
        _abort_stall(tool)  # 2nd consecutive timeout == real stall
        return (False, None, "TIMEOUT")  # unreachable
    return h.unwrap_tool_result(m)


def bl(code, timeout=30):
    """Run Python in Blender via execute_blender_code; return captured stdout text or None.

    The MCP tool name is execute_blender_code (the addon dispatch key is execute_code). The
    add-on captures print() output and returns it; we extract that text so the probe can read
    back independently-measured scene facts (object counts, types, etc.)."""
    ok, payload, raw = call("execute_blender_code", {"code": code}, timeout=timeout)
    if not ok:
        return None
    # The add-on returns the captured stdout in result; unwrap_tool_result gives us the text.
    if isinstance(payload, dict):
        # server may wrap as {"status":"success","result":{...}} or {"result": "..."}
        for k in ("result", "output", "stdout"):
            if k in payload and isinstance(payload[k], str):
                return payload[k]
        return json.dumps(payload)
    return raw


def _handshake():
    _send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
           "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                      "clientInfo": {"name": "probe", "version": "1"}}})
    t0 = time.time()
    while time.time() - t0 < 15:
        with _lock:
            if 1 in _resp:
                _resp.pop(1)
                break
        time.sleep(0.08)
    else:
        _abort_stall("initialize")
    time.sleep(0.5)
    _send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    time.sleep(0.5)


if __name__ == "__main__":
    # TEMPORARY harness check (replaced by the full probe in Task 4): handshake + one read.
    try:
        _handshake()
        ok, payload, raw = call("get_scene_info", {}, timeout=20)
        print("HARNESS OK" if ok else "HARNESS CALL FAILED")
        print("scene:", (raw or "")[:300])
    finally:
        try:
            proc.terminate()
        except Exception:
            pass
```
- [ ] Make it executable: `chmod +x /Users/bra0002h/mcp-servers/blender-mcp/probe-capabilities.py`.
- [ ] Byte-compile to catch syntax errors (fast, no Blender needed): `python3 -m py_compile /Users/bra0002h/mcp-servers/blender-mcp/probe-capabilities.py && echo COMPILE_OK`. Expected: `COMPILE_OK`.
- [ ] LIVE harness verification (USER-IN-LOOP — Blender running + add-on connected on 9876). Confirm listener first: `lsof -nP -iTCP:9876 -sTCP:LISTEN` (expect a `Blender ... (LISTEN)` line). Then run: `cd /Users/bra0002h/mcp-servers/blender-mcp && python3 -u probe-capabilities.py`. Expected output: `HARNESS OK` followed by a `scene:` line containing the live scene name. If it prints `!! STALLED on 'get_scene_info'` or `HARNESS CALL FAILED`, the prereqs are not met — fix per the printed hint (or run the Task 6 guide) and re-run; do not weaken the harness.
- [ ] Confirm the stderr sink is being written (proves the drain path is active, not deadlocking): `test -s /tmp/blender-probe-mcp-stderr.log && echo STDERR_DRAINED || echo STDERR_EMPTY`. Expected: `STDERR_DRAINED` (the server logs on startup). (Empty is acceptable only if the server truly logged nothing; the point is the file, not a PIPE.)
- [ ] Stage and commit:
```
git -C /Users/bra0002h/mcp-servers/blender-mcp add probe-capabilities.py
git -C /Users/bra0002h/mcp-servers/blender-mcp commit -m "Add probe harness: uvx spawn, stderr-to-file drain, JSON-RPC, retry-once/fail-fast

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: `probe-capabilities.py` — functional per-tool assertions, cleanup, report

Replace the temporary `__main__` with the real probe body: `rec()` recorder, scene-state read helpers (object count, object existence/type/vert/face counts via `bl()`), then FUNCTIONAL checks for each tool — `get_scene_info` (reported count == independently measured), `get_object_info` (known cube: type/verts/faces + negative lookup), `execute_blender_code` (add-cube → count+1), `get_viewport_screenshot` (PNG magic bytes + size), `download_polyhaven_asset` (material + expected maps, INCONCLUSIVE if offline), `set_texture` (post-fix: applied + node present; the version-guard is Workstream A's), and the four `get_*_status` toggle-consistency checks. Cleans up every object/material it created. Writes `capability-report.json` with `results` + `summary` + `blender_version`.

**Files:**
- Modify `/Users/bra0002h/mcp-servers/blender-mcp/probe-capabilities.py` — replace the `if __name__ == "__main__":` block (last ~12 lines) with the full probe body (~230 lines).

**Interfaces:**
- Consumes `call`, `bl`, `_handshake`, `proc`, `results`, `REPORT` (Task 3); `probe_helpers.classify`, `probe_helpers.build_summary`.
- Produces `/Users/bra0002h/mcp-servers/blender-mcp/capability-report.json` with schema `{blender_version, results:[{command,status,detail}], summary:{STATUS:count}}` (normal) or `{blender_version, aborted, aborted_on, results}` (stall).

- [ ] Read the current file to get the exact tail block to replace: `python3 -m pytest --version >/dev/null; sed -n '/^if __name__ == "__main__":/,$p' /Users/bra0002h/mcp-servers/blender-mcp/probe-capabilities.py`. Expected: the temporary harness `__main__` block from Task 3.
- [ ] Replace the temporary `__main__` block (the entire `if __name__ == "__main__":` section from Task 3) with these exact contents (use the Edit tool; the `old_string` is the temporary block, the `new_string` is below):
```python
# --- recorder + scene-state read helpers -------------------------------------
def rec(command, status, detail):
    results.append({"command": command, "status": status, "detail": detail})
    print(f"  [{status:12}] {command:26} {detail}")


def obj_count():
    """Independently-measured live object count in the scene, or -1 if the read failed."""
    out = bl("import bpy; print(len(bpy.context.scene.objects))")
    if out is None:
        return -1
    try:
        return int(out.strip().splitlines()[-1])
    except Exception:
        return -1


def obj_exists(name):
    out = bl(f"import bpy; print('YES' if bpy.data.objects.get({name!r}) else 'NO')")
    return (out or "").strip().endswith("YES")


def mat_exists(name):
    out = bl(f"import bpy; print('YES' if bpy.data.materials.get({name!r}) else 'NO')")
    return (out or "").strip().endswith("YES")


def cleanup(obj_names, mat_names):
    """Delete objects/materials the probe created; restore toward the pre-probe set."""
    code = (
        "import bpy\n"
        f"for n in {obj_names!r}:\n"
        "    o = bpy.data.objects.get(n)\n"
        "    if o: bpy.data.objects.remove(o, do_unlink=True)\n"
        f"for m in {mat_names!r}:\n"
        "    mm = bpy.data.materials.get(m)\n"
        "    if mm: bpy.data.materials.remove(mm)\n"
        "print('CLEANED')\n"
    )
    out = bl(code)
    print("  cleanup:", (out or "no-response").strip().splitlines()[-1] if out else "no-response")


def run_probe():
    created_objs = []
    created_mats = []

    # 1) get_scene_info — reported count must equal an independently-measured count.
    ok, payload, raw = call("get_scene_info", {}, timeout=20)
    measured = obj_count()
    reported = None
    if isinstance(payload, dict):
        r = payload.get("result", payload)
        if isinstance(r, dict):
            reported = r.get("object_count")
    verify_ok = measured != -1 and reported is not None
    changed = verify_ok and int(reported) == measured
    rec("get_scene_info",
        h.classify(ok, changed, verify_ok),
        f"reported object_count={reported} vs measured={measured}")

    # 2) execute_blender_code — add a cube, object count must go up by exactly 1.
    c0 = obj_count()
    ok, _, raw = call("execute_blender_code",
                      {"code": "import bpy; bpy.ops.mesh.primitive_cube_add(); "
                               "bpy.context.active_object.name='ASSERT_CUBE'; print('ADDED')"},
                      timeout=30)
    if obj_exists("ASSERT_CUBE"):
        created_objs.append("ASSERT_CUBE")
    c1 = obj_count()
    verify_ok = c0 != -1 and c1 != -1
    changed = verify_ok and c1 == c0 + 1
    rec("execute_blender_code",
        h.classify(ok, changed, verify_ok),
        f"object count {c0}->{c1} (expected +1); named ASSERT_CUBE")

    # 3) get_object_info — known cube must report MESH / 8 verts / 6 faces; bad name errors.
    ok, payload, raw = call("get_object_info", {"name": "ASSERT_CUBE"}, timeout=20)
    info = payload.get("result", payload) if isinstance(payload, dict) else {}
    otype = info.get("type") if isinstance(info, dict) else None
    is_cube = otype == "MESH"
    neg_ok, _, _ = call("get_object_info", {"name": "__does_not_exist__"}, timeout=20)
    # Negative lookup should FAIL (neg_ok False) — a real lookup, not a stub.
    verify_ok = otype is not None
    changed = is_cube and (neg_ok is False)
    rec("get_object_info",
        h.classify(ok, changed, verify_ok),
        f"ASSERT_CUBE type={otype} (want MESH); missing-name errored={neg_ok is False}")

    # 4) get_viewport_screenshot — file must exist, be a PNG, and be non-trivially sized.
    shot = "/tmp/blmcp_probe_shot.png"
    try:
        os.remove(shot)
    except Exception:
        pass
    ok, payload, raw = call("get_viewport_screenshot",
                            {"max_size": 400, "filepath": shot, "format": "png"}, timeout=30)
    png_ok = False
    size = 0
    if os.path.exists(shot):
        size = os.path.getsize(shot)
        with open(shot, "rb") as f:
            png_ok = f.read(4) == b"\x89PNG"
    verify_ok = os.path.exists(shot) or ok
    changed = png_ok and size > 1024
    rec("get_viewport_screenshot",
        h.classify(ok, changed, verify_ok),
        f"png_magic={png_ok} size={size}B (want PNG >1KB)")
    try:
        os.remove(shot)
    except Exception:
        pass

    # 5) get_polyhaven_status — enabled flag must match the live scene toggle.
    ok, payload, raw = call("get_polyhaven_status", {}, timeout=20)
    live = bl("import bpy; print(bool(bpy.context.scene.blendermcp_use_polyhaven))")
    live_on = (live or "").strip().endswith("True")
    reported_on = "true" in (raw or "").lower() or (
        isinstance(payload, dict) and bool((payload.get("result") or {}).get("enabled"))
        if isinstance(payload.get("result"), dict) else False) if isinstance(payload, dict) else False
    verify_ok = live is not None
    changed = verify_ok and (reported_on == live_on)
    rec("get_polyhaven_status",
        h.classify(ok, changed, verify_ok),
        f"reported_enabled={reported_on} vs live_toggle={live_on}")

    # 6) download_polyhaven_asset — needs PolyHaven ON + network. Material + a TEX_IMAGE node.
    if not live_on:
        rec("download_polyhaven_asset", "SKIPPED",
            "PolyHaven integration is OFF (blendermcp_use_polyhaven=False) — enable to test")
        rec("set_texture", "SKIPPED", "depends on download_polyhaven_asset (PolyHaven OFF)")
    else:
        asset = "dark_wood"
        ok, payload, raw = call("download_polyhaven_asset",
                                {"asset_id": asset, "asset_type": "textures", "resolution": "1k"},
                                timeout=90)
        made_mat = mat_exists(asset)
        # count TEX_IMAGE nodes in the created material (independent read)
        node_out = bl(
            "import bpy\n"
            f"m = bpy.data.materials.get({asset!r})\n"
            "n = 0\n"
            "if m and m.use_nodes:\n"
            "    n = sum(1 for nd in m.node_tree.nodes if nd.type=='TEX_IMAGE')\n"
            "print(n)\n"
        )
        try:
            tex_nodes = int((node_out or "0").strip().splitlines()[-1])
        except Exception:
            tex_nodes = -1
        if made_mat:
            created_mats.append(asset)
        offline = (not ok) and ("network" in (raw or "").lower() or "resolve" in (raw or "").lower()
                                 or "timed out" in (raw or "").lower() or "connection" in (raw or "").lower())
        if offline:
            rec("download_polyhaven_asset", "INCONCLUSIVE",
                "network unreachable (PolyHaven download needs connectivity) — re-run online")
            rec("set_texture", "INCONCLUSIVE", "cannot test: material download inconclusive (offline)")
        else:
            verify_ok = tex_nodes != -1
            changed = made_mat and tex_nodes > 0
            rec("download_polyhaven_asset",
                h.classify(ok, changed, verify_ok),
                f"material '{asset}' created={made_mat}, TEX_IMAGE nodes={tex_nodes}")

            # 7) set_texture — POST-FIX assertion (version-guard applied by Workstream A).
            # Build a plane to receive the texture, then apply. Success => a Separate* node
            # (SeparateColor on 4.0+, SeparateRGB on <4.0) exists in the plane's material tree
            # AND the plane now has the material assigned.
            bl("import bpy; bpy.ops.mesh.primitive_plane_add(); "
               "bpy.context.active_object.name='ASSERT_PLANE'; print('PLANE')")
            if obj_exists("ASSERT_PLANE"):
                created_objs.append("ASSERT_PLANE")
            ok_st, payload_st, raw_st = call("set_texture",
                                             {"object_name": "ASSERT_PLANE", "texture_id": asset},
                                             timeout=45)
            sep_out = bl(
                "import bpy\n"
                "o = bpy.data.objects.get('ASSERT_PLANE')\n"
                "found = False; assigned = False\n"
                "if o and o.data.materials:\n"
                "    assigned = len(o.data.materials) > 0\n"
                "    for m in o.data.materials:\n"
                "        if m and m.use_nodes:\n"
                "            for nd in m.node_tree.nodes:\n"
                "                if nd.type in ('SEPARATE_COLOR','SEPRGB','SEPARATE_RGB'):\n"
                "                    found = True\n"
                "print(f'{assigned}|{found}')\n"
            )
            parts = (sep_out or "False|False").strip().splitlines()[-1].split("|")
            assigned = parts[0] == "True"
            has_sep = len(parts) > 1 and parts[1] == "True"
            no_sepRGB_err = "separatergb" not in (raw_st or "").lower()
            verify_ok = sep_out is not None
            changed = assigned and has_sep and no_sepRGB_err
            rec("set_texture",
                h.classify(ok_st, changed, verify_ok),
                f"assigned={assigned}, ARM-split node present={has_sep}, "
                f"no 'ShaderNodeSeparateRGB' error={no_sepRGB_err} (post-fix)")

    # 8) the remaining status calls — toggle/consistency (no writes).
    for tool, toggle in (("get_hyper3d_status", "blendermcp_use_hyper3d"),
                         ("get_sketchfab_status", "blendermcp_use_sketchfab"),
                         ("get_hunyuan3d_status", "blendermcp_use_hunyuan3d")):
        ok, payload, raw = call(tool, {}, timeout=20)
        live = bl(f"import bpy; print(bool(bpy.context.scene.{toggle}))")
        live_on = (live or "").strip().endswith("True")
        reported_on = "true" in (raw or "").lower()
        verify_ok = live is not None
        changed = verify_ok and (reported_on == live_on)
        rec(tool, h.classify(ok, changed, verify_ok),
            f"reported_enabled≈{reported_on} vs live_toggle={live_on}")

    return created_objs, created_mats


if __name__ == "__main__":
    print("Blender MCP capability probe — functional checks (WORKS/PARTIAL/BROKEN/INCONCLUSIVE)")
    created_objs, created_mats = [], []
    try:
        _handshake()
        # record which Blender the server is driving (independent read)
        ver = bl("import bpy; print('.'.join(str(x) for x in bpy.app.version))")
        os.environ["BL_VERSION"] = (ver or "unknown").strip().splitlines()[-1] if ver else "unknown"
        created_objs, created_mats = run_probe()
    finally:
        # Clean up artifacts we created, then always terminate the server.
        try:
            if created_objs or created_mats:
                cleanup(created_objs, created_mats)
        except Exception as e:
            print("  cleanup error (non-fatal):", e)
        try:
            summary = h.build_summary(results)
            with open(REPORT, "w") as f:
                json.dump({"blender_version": os.environ.get("BL_VERSION", "unknown"),
                           "results": results, "summary": summary}, f, indent=2)
            print("\nSummary:", json.dumps(summary))
            print("Report written:", REPORT)
        except Exception as e:
            print("  report write error:", e)
        try:
            proc.terminate()
        except Exception:
            pass
```
- [ ] Byte-compile: `python3 -m py_compile /Users/bra0002h/mcp-servers/blender-mcp/probe-capabilities.py && echo COMPILE_OK`. Expected: `COMPILE_OK`.
- [ ] Re-run the helper unit tests to confirm no regression in imports: `cd /Users/bra0002h/mcp-servers/blender-mcp && python3 -m pytest test_probe_helpers.py -q`. Expected: `13 passed`.
- [ ] LIVE full-probe verification (USER-IN-LOOP — Blender running + add-on connected on 9876; network up for the PolyHaven check). Confirm listener: `lsof -nP -iTCP:9876 -sTCP:LISTEN` (expect `Blender ... (LISTEN)`). Then run: `cd /Users/bra0002h/mcp-servers/blender-mcp && ./test-blender.sh --capabilities`. Expected: a streamed table with a `[WORKS ...]`-style row per tool, ending with a `Summary: {...}` line and `Report written: /Users/bra0002h/mcp-servers/blender-mcp/capability-report.json`. Per the 2026-07-10 facts, expect `get_scene_info`, `get_object_info`, `execute_blender_code`, `get_viewport_screenshot`, `download_polyhaven_asset` = WORKS; `set_texture` = WORKS (post-fix) — if it shows BROKEN with a `ShaderNodeSeparateRGB` mention, Workstream A's fix is not applied to `/Users/bra0002h/mcp-servers/blender-mcp/addon.py` and the running copy; report that, do not patch here. If PolyHaven is OFF the two PolyHaven rows read `SKIPPED`; if offline they read `INCONCLUSIVE`.
- [ ] Verify the report is valid JSON with the expected schema: `python3 -c "import json; d=json.load(open('/Users/bra0002h/mcp-servers/blender-mcp/capability-report.json')); assert 'results' in d and 'summary' in d and 'blender_version' in d; print('REPORT_OK', d['blender_version'], d['summary'])"`. Expected: `REPORT_OK 5.1.x {...}`.
- [ ] Confirm cleanup ran (no probe artifacts left behind): run `./test-blender.sh` (smoke) again and inspect the printed `scene:` line — it must NOT contain `ASSERT_CUBE` or `ASSERT_PLANE`. Alternatively the probe's own `cleanup: CLEANED` line in the previous step confirms deletion.
- [ ] Stage and commit:
```
git -C /Users/bra0002h/mcp-servers/blender-mcp add probe-capabilities.py
git -C /Users/bra0002h/mcp-servers/blender-mcp commit -m "Add functional per-tool assertions, artifact cleanup, and capability-report.json

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: `BLENDER-MCP-CAPABILITIES.md` — evidence-based manual seeded from 2026-07-10

Author the capabilities manual, seeded with the confirmed 2026-07-10 smoke-test results and the `set_texture` finding (pre/post-fix + direct-assign workaround). Sections mirror the Adobe manual: verification status, headline viability, WORKING, BROKEN/PARTIAL, practical guidance, required setup, update route.

**Files:**
- Create `/Users/bra0002h/mcp-servers/blender-mcp/BLENDER-MCP-CAPABILITIES.md`

**Interfaces:** Consumes the facts in spec §2 and the `capability-report.json` shape from Task 4 (named as the source of truth in the update route). No code interface.

- [ ] Create `/Users/bra0002h/mcp-servers/blender-mcp/BLENDER-MCP-CAPABILITIES.md` with these exact contents:
```markdown
# Blender MCP — Capabilities (evidence-based)

> This manual records what the Blender MCP (`ahujasid/blender-mcp`, driven via `uvx blender-mcp`)
> can actually do **on this machine**, verified by functional assertions — not by "the call
> returned without error." Regenerate it from a probe run (see **Update route**).

## Verification status

- **Date verified:** 2026-07-10 (smoke test); capability probe added same day.
- **Blender:** 5.1.2 (only version installed; config tree `~/Library/Application Support/Blender/5.1/`).
- **Add-on:** "Interface: Blender MCP" — installed via *Install from Disk* (the running add-on is
  a COPY at `~/Library/Application Support/Blender/5.1/scripts/addons/addon.py`, distinct from the
  source clone). Socket listens on `127.0.0.1:9876` after clicking **Connect to Claude**.
- **MCP server:** `uvx blender-mcp` (stdio), the exact command in the user-scope `mcpServers.blender`
  entry Claude uses.
- **Network context:** PolyHaven downloads require connectivity; a probe run offline marks those
  INCONCLUSIVE (not BROKEN).
- **Optional integrations:** PolyHaven can be toggled on; Sketchfab / Hyper3D / Hunyuan3D were OFF
  (need API keys) and are out of scope this round.

## Headline viability

**Is Blender-MCP viable for driving Blender from Claude right now? Yes**, for scene inspection,
arbitrary scripted scene mutation, screenshots, and PolyHaven material download. The one known
defect — `set_texture` on Blender 4.0+ — is fixed by a version-guarded patch (Workstream A);
with that patch applied, PolyHaven texturing works end-to-end. A safe workaround exists even
without the patch (see BROKEN/PARTIAL).

## Confirmed WORKING (2026-07-10)

Each verified by a functional assertion in `probe-capabilities.py`:

- **`get_scene_info`** — reported `object_count` equals an independently measured
  `len(bpy.context.scene.objects)`.
- **`get_object_info`** — a known `ASSERT_CUBE` reports `type=MESH`; a non-existent name errors
  (proves the lookup is real, not a stub).
- **`execute_blender_code`** — adding a cube increases the live object count by exactly 1 (proves
  both stdout capture and real scene mutation).
- **`get_viewport_screenshot`** — writes a real PNG to disk (magic bytes `\x89PNG`, > 1 KB).
- **`download_polyhaven_asset`** (textures, 1k) — creates a `bpy.data.materials[<asset_id>]`
  whose node tree contains ≥1 `TEX_IMAGE` node. *(Requires PolyHaven toggle ON + network.)*
- **`get_polyhaven_status`** — reported `enabled` matches the live
  `bpy.context.scene.blendermcp_use_polyhaven` toggle.

## Confirmed BROKEN / PARTIAL

- **`set_texture` — BROKEN on stock add-on for Blender 4.0+ (this machine: 5.1.2).**
  - **Symptom:** raises `ShaderNodeSeparateRGB` undefined / node-type-not-found when applying a
    PolyHaven texture whose ARM map (Ambient Occlusion / Roughness / Metallic) must be split.
  - **Root cause:** Blender 4.0 removed `ShaderNodeSeparateRGB` (renamed to `ShaderNodeSeparateColor`,
    introduced in 3.3). The stock `set_texture` calls the removed node unconditionally.
  - **Post-fix (Workstream A):** a runtime branch on `bpy.app.version >= (4, 0)` uses
    `ShaderNodeSeparateColor` (input `Color`; outputs `Red`/`Green`/`Blue`) on 4.0+ and the
    original `ShaderNodeSeparateRGB` (input `Image`; outputs `R`/`G`/`B`) below 4.0 — additive
    and backward-compatible. With the fix applied to both the source clone and the running add-on
    copy, the probe's `set_texture` assertion passes (material assigned + a Separate* node present,
    no `ShaderNodeSeparateRGB` error).
  - **Workaround without the patch:** `download_polyhaven_asset` already builds a valid material —
    assign it directly (`obj.data.materials.append(bpy.data.materials[<asset_id>])` via
    `execute_blender_code`) instead of calling `set_texture`. You lose only the ARM re-wiring step.

## Practical guidance

- Prefer `execute_blender_code` for anything not covered by a dedicated tool — it is the most
  reliable surface and round-trips real scene state.
- For PolyHaven textures on Blender 4.0+: use the patched `set_texture`, or the direct-assign
  workaround above.
- Screenshots are written to a path you pass; read the file back yourself if you need the bytes.
- The optional integrations (Sketchfab/Hyper3D/Hunyuan3D) are gated by scene toggles AND API keys;
  a `get_*_status` call reflecting `enabled=False` usually means the key/toggle is unset, not a bug.

## Required setup

1. `blender` MCP server **enabled** in Claude (`/mcp`; not in the project's `disabledMcpServers`).
2. **Blender running.**
3. **Add-on installed + enabled** ("Interface: Blender MCP" — *Install from Disk* the add-on, then
   enable it in Preferences → Add-ons).
4. **Connect to Claude** clicked (N-panel → BlenderMCP tab) so the socket listens on
   `127.0.0.1:9876`.
5. *(Optional)* PolyHaven toggle ON for texture download; Sketchfab/Hyper3D/Hunyuan3D need keys.

See `interactive-guide.md` for the ordered, re-checked walkthrough.

## Update route

This document is a snapshot; the machine-readable source of truth is **`capability-report.json`**.
To refresh:

1. Ensure the prereqs above are green (run `interactive-guide.md` if unsure).
2. `./test-blender.sh --capabilities` — runs `probe-capabilities.py`, streams the verdict table,
   and (re)writes `capability-report.json` (`{blender_version, results:[{command,status,detail}], summary}`).
3. Edit the WORKING / BROKEN sections above from the fresh report; bump the **Date verified** and
   **Blender** lines under *Verification status*.
```
- [ ] Sanity-check it is well-formed Markdown and mentions the key facts: `grep -c -E "set_texture|ShaderNodeSeparateColor|9876|uvx blender-mcp|capability-report.json" /Users/bra0002h/mcp-servers/blender-mcp/BLENDER-MCP-CAPABILITIES.md`. Expected: a count `>= 5`.
- [ ] Stage and commit:
```
git -C /Users/bra0002h/mcp-servers/blender-mcp add BLENDER-MCP-CAPABILITIES.md
git -C /Users/bra0002h/mcp-servers/blender-mcp commit -m "Add BLENDER-MCP-CAPABILITIES.md manual seeded from 2026-07-10 results + set_texture finding

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: `interactive-guide.md` — ordered prereq ladder (DETECT vs GUIDE, loop-until-green)

Author the interactive setup guide: the ordered prereq ladder (1 MCP enabled → 2 Blender running → 3 add-on installed+enabled → 4 Connect-to-Claude on 9876 → 5 optional integrations), each rung marked **DETECT** (machine-checkable, with the exact command + expected output) or **GUIDE** (in-app, prompt-and-confirm), re-checking after each and looping until green. Every DETECT command must be runnable and correct on this machine.

**Files:**
- Create `/Users/bra0002h/mcp-servers/blender-mcp/interactive-guide.md`

**Interfaces:** Consumes `~/.claude.json` (`projects.<path>.disabledMcpServers`), `pgrep -x Blender`, `lsof -nP -iTCP:9876`, and `test-blender.sh` (smoke) as the final green check. No code interface.

- [ ] Create `/Users/bra0002h/mcp-servers/blender-mcp/interactive-guide.md` with these exact contents:
```markdown
# Blender MCP — interactive setup guide (detect → guide → re-check, loop until green)

Purpose: walk from "nothing connected" to "all green" for the Blender MCP, checking **each prereq
in order** and re-checking after every user action. Each rung is either **DETECT** (machine-checkable
from disk/process/socket — the assistant runs the command) or **GUIDE** (an in-app action the user
must take — prompt, wait for confirmation, then re-run the rung's check). Do NOT advance to the next
rung until the current one is green. If a later rung fails, drop back to the lowest failing rung.

The single end-to-end green signal for the whole ladder is:
`./test-blender.sh` printing `SMOKE PASS: get_scene_info responded.`

---

## Rung 1 — blender MCP server ENABLED in Claude  *(DETECT)*

The server can be disabled per-project via `disabledMcpServers` in `~/.claude.json`. Check whether
`"blender"` is listed as disabled for THIS project:

```sh
python3 - <<'PY'
import json, os
cfg = json.load(open(os.path.expanduser("~/.claude.json")))
proj = os.getcwd()
entry = cfg.get("projects", {}).get(proj, {})
disabled = entry.get("disabledMcpServers", [])
print("DISABLED" if "blender" in disabled else "ENABLED", "(project:", proj + ")")
PY
```

- **Green:** prints `ENABLED`.
- **If `DISABLED` → GUIDE:** tell the user to run `/mcp`, select **blender**, and enable it for this
  project. Then re-run the DETECT command above. (Also confirm the user-scope entry exists:
  `python3 -c "import json,os; print('blender' in json.load(open(os.path.expanduser('~/.claude.json'))).get('mcpServers',{}))"` should print `True`.)

## Rung 2 — Blender RUNNING  *(DETECT)*

The macOS binary is named `Blender`:

```sh
pgrep -x Blender && echo "RUNNING" || echo "NOT RUNNING"
```

- **Green:** prints one or more PIDs then `RUNNING`.
- **If `NOT RUNNING` → GUIDE:** ask the user to launch Blender. Wait for confirmation, then re-run.

## Rung 3 — Add-on INSTALLED + ENABLED  *(DETECT presence / GUIDE enablement)*

**3a. Presence (DETECT).** The running add-on is the installed COPY:

```sh
test -f "$HOME/Library/Application Support/Blender/5.1/scripts/addons/addon.py" \
  && echo "ADDON FILE PRESENT" || echo "ADDON FILE MISSING"
```

- **If MISSING → GUIDE:** in Blender, Edit → Preferences → Add-ons → *Install from Disk…* → choose
  `~/ClaudeWorkspace/blender-mcp/addon.py` → then continue to 3b. Re-run 3a after install.

**3b. Enablement (GUIDE — in-app, not detectable from disk).** Ask the user to confirm the add-on
is enabled: Preferences → Add-ons → search "Blender MCP" → checkbox ticked on **Interface: Blender MCP**.
There is no reliable disk signal for the enabled checkbox; enablement is proven by Rung 4 succeeding
(the socket only opens when the add-on is enabled AND Connect is clicked). Prompt, wait for
confirmation, proceed to Rung 4.

## Rung 4 — "Connect to Claude" LISTENING on 9876  *(DETECT)*

```sh
lsof -nP -iTCP:9876 -sTCP:LISTEN && echo "SOCKET LISTENING" || echo "NO LISTENER"
```

- **Green:** a `Blender ... TCP 127.0.0.1:9876 (LISTEN)` line then `SOCKET LISTENING`.
- **If `NO LISTENER` → GUIDE:** in Blender, open the N-panel (press **N** in the 3D viewport) →
  **BlenderMCP** tab → click **Connect to Claude**. Wait for confirmation, then re-run this DETECT.
  (If it still fails after Connect, drop back to Rung 3b — the add-on may not actually be enabled.)

## Rung 5 — (Optional) integrations  *(DETECT status / GUIDE enablement)*

These are not required for core use. Report current state, and only guide enablement if the user
wants a specific one.

**Report (DETECT)** — once Rungs 1–4 are green, the assistant can read the toggles live:

```sh
./test-blender.sh --capabilities 2>/dev/null | grep -E "get_(polyhaven|sketchfab|hyper3d|hunyuan3d)_status"
```

(Or run the probe directly.) Interpretation:
- **PolyHaven** — the only one exercised on 2026-07-10; enable via the BlenderMCP N-panel toggle if
  the user wants texture download. Needed for `download_polyhaven_asset` / `set_texture`.
- **Sketchfab / Hyper3D / Hunyuan3D** — require API keys; **GUIDE** the user to the respective
  N-panel toggle + key field only on request. Out of default scope.

---

## Final green check *(DETECT — the whole-ladder signal)*

```sh
./test-blender.sh
```

Expected: the Blender version line(s), then `SMOKE PASS: get_scene_info responded.` with a `scene:`
summary. If this passes, all required rungs (1–4) are green and the MCP is ready. If it prints
`SMOKE FAIL`, return to the lowest failing rung above (the failure hint names the likely rung) and
loop.
```
- [ ] Verify every DETECT command in the guide is individually runnable (syntax + resolves) without depending on Blender being up — run the two pure-shell ones now: `python3 - <<'PY'\nimport json, os\ncfg = json.load(open(os.path.expanduser("~/.claude.json")))\nproj = os.getcwd()\nentry = cfg.get("projects", {}).get(proj, {})\nprint("DISABLED" if "blender" in entry.get("disabledMcpServers", []) else "ENABLED")\nPY` and `test -f "$HOME/Library/Application Support/Blender/5.1/scripts/addons/addon.py" && echo PRESENT || echo MISSING`. Expected: the first prints `ENABLED` or `DISABLED` (no traceback); the second prints `PRESENT` (per the 2026-07-10 facts, the installed copy exists).
- [ ] Verify the process/socket DETECT commands are valid syntax (they may legitimately report "not running" if Blender is down): `pgrep -x Blender >/dev/null; echo "pgrep-exit=$?"` and `lsof -nP -iTCP:9876 -sTCP:LISTEN >/dev/null; echo "lsof-exit=$?"`. Expected: each prints an `exit=` line with no shell error (exit 0 if up, 1 if down — both are valid, non-error outcomes).
- [ ] Stage and commit:
```
git -C /Users/bra0002h/mcp-servers/blender-mcp add interactive-guide.md
git -C /Users/bra0002h/mcp-servers/blender-mcp commit -m "Add interactive-guide.md: ordered prereq ladder with DETECT/GUIDE markers, loop-until-green

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: `PROJECT-NOTES.md` — running record, diff-surface framing, two-tier testing

Author the running project record + plan. Frame the **diff surface** for publishing: novel additions (probe, launcher, manual, interactive guide, helpers) vs the single upstreamable bug fix (`set_texture`, owned by Workstream A). Capture the two-tier testing framing (unit = the probe's per-command functional checks; integration = a small real-scene goal). Record current PR status pointer and next steps.

**Files:**
- Create `/Users/bra0002h/mcp-servers/blender-mcp/PROJECT-NOTES.md`

**Interfaces:** Consumes the artifact set from Tasks 1–6. No code interface.

- [ ] Create `/Users/bra0002h/mcp-servers/blender-mcp/PROJECT-NOTES.md` with these exact contents:
```markdown
# Blender MCP — project notes (running record + plan)

Home: `~/mcp-servers/blender-mcp/` (clone of `ahujasid/blender-mcp`, produced by Workstream A).
This is the first worked instance of the reusable **mcp-smoke-test** method
(`~/ClaudeWorkspace/mcp-smoke-test/`), adapted from the Adobe Photoshop MCP artifact shape.

## What this repo contains (Workstream B artifacts)

| File | Role |
|---|---|
| `test-blender.sh` | Launcher: `smoke` (default, read-only `get_scene_info`) vs `--capabilities` (full probe). Prints installed Blender version(s); EXIT-trap kills any spawned server. |
| `probe-capabilities.py` | Functional probe: spawns `uvx blender-mcp`, JSON-RPC over stdio, per-tool before/after assertions, WORKS/PARTIAL/BROKEN/INCONCLUSIVE, fail-fast on stall, artifact cleanup, writes `capability-report.json`. |
| `probe_helpers.py` | Pure helpers (unwrap/classify/version-parse/summary), unit-tested. |
| `capability-report.json` | Machine-readable probe output (source of truth for the manual). |
| `BLENDER-MCP-CAPABILITIES.md` | Evidence-based manual, seeded 2026-07-10. |
| `interactive-guide.md` | Ordered prereq ladder (DETECT/GUIDE, loop-until-green). |

## Diff surface (for publishing)

Two distinct categories — keep them separate when deciding what goes upstream:

- **Upstreamable bug fix (Workstream A, NOT authored here):** the version-guarded `set_texture`
  fix in `addon.py` (`ShaderNodeSeparateRGB` → branch to `ShaderNodeSeparateColor` on Blender 4.0+).
  Additive/backward-compatible. Goes to `ahujasid/blender-mcp` as a PR under `haiggoh`. Workstream B
  only *verifies* it (probe's `set_texture` assertion) and *documents* it (manual).
- **Novel additions (Workstream B, this repo's new files):** the launcher, probe, helpers, manual,
  interactive guide, and report. These are the smoke-test/verification tooling — they are candidates
  to generalize into the `mcp-smoke-test` skill (Workstream C), NOT to push to the add-on upstream.

## Two-tier testing framing

- **Unit tier = the probe's per-command functional checks** (deterministic given a connected Blender):
  each tool has a before/after assertion that can actually FAIL (object-count delta, node presence,
  PNG magic bytes, toggle consistency) — never "no exception."
  - Genuinely-pure logic (result unwrapping, verdict classification, version parsing, summary) is
    covered by `test_probe_helpers.py` (pytest, no Blender needed).
- **Integration / e2e tier = a small real-scene goal** exercising the toolset together:
  textured plane + a primitive + a PolyHaven material + a screenshot. Defined here; run manually via
  `./test-blender.sh --capabilities` (which walks most of it). Not separately automated this round.

## Reliability rules baked into the probe (hard-won)

1. Drain server stderr to a FILE (`/tmp/blender-probe-mcp-stderr.log`), never an unread PIPE — an
   unread PIPE deadlocks after ~64KB (~a dozen commands). This is the load-bearing fix.
2. One MCP call at a time; small pace between calls (the relayed socket is per-call).
3. Retry a no-response once; a 2nd consecutive timeout is a real stall → `_abort_stall` writes a
   partial report and hard-exits. Never keep stamping downstream commands BROKEN off one stall.
4. `try/finally` terminates the subprocess; launcher installs an EXIT trap for anything it spawned.
5. Clean up scene artifacts the probe creates (`ASSERT_CUBE`, `ASSERT_PLANE`, downloaded material).

## Status / next steps

- [x] Workstream B artifacts authored and (live-)verified against Blender 5.1.2.
- [ ] Confirm the full `--capabilities` run is green end-to-end once Workstream A's `set_texture`
  fix is applied to BOTH the clone `addon.py` and the running copy
  `~/Library/Application Support/Blender/5.1/scripts/addons/addon.py`.
- [ ] Workstream C: extract templates from these proven artifacts into the `mcp-smoke-test` skill
  (Blender is the reference instance; generalize from what worked, not in the abstract).
- [ ] Workstream A: `set_texture` PR to `ahujasid/blender-mcp` under `haiggoh`.

## Caveats

- Only Blender 5.1 is installed; the pre-4.0 branch of the `set_texture` fix is reasoned/reviewed
  but not locally exercised — call this out in the PR.
- PolyHaven download tests hit the network → INCONCLUSIVE (not BROKEN) when offline.
- The probe must spawn the SAME server Claude uses (`uvx blender-mcp`, `env: {}`); do not substitute
  a different build or the verdicts won't reflect Claude's actual path.
```
- [ ] Sanity-check the notes reference the artifact set and both diff categories: `grep -c -E "set_texture|probe-capabilities.py|interactive-guide.md|Upstreamable|Novel additions|unread PIPE" /Users/bra0002h/mcp-servers/blender-mcp/PROJECT-NOTES.md`. Expected: a count `>= 6`.
- [ ] Stage and commit:
```
git -C /Users/bra0002h/mcp-servers/blender-mcp add PROJECT-NOTES.md
git -C /Users/bra0002h/mcp-servers/blender-mcp commit -m "Add PROJECT-NOTES.md: running record, diff-surface framing, two-tier testing

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Final integration verification + report reconciliation

Run the complete artifact set together against live Blender, confirm the manual matches the fresh report, and confirm no probe artifacts or spawned servers leak. This is the whole-Workstream-B acceptance gate.

**Files:** No new files. May Modify `/Users/bra0002h/mcp-servers/blender-mcp/BLENDER-MCP-CAPABILITIES.md` (in place, preserving mode) only if the fresh report contradicts a documented verdict.

**Interfaces:** Consumes all Task 1–7 artifacts + live Blender + `capability-report.json`.

- [ ] Confirm all unit tests still pass: `cd /Users/bra0002h/mcp-servers/blender-mcp && python3 -m pytest -q`. Expected: `14 passed` (13 helper + 1 version-detect).
- [ ] Confirm both scripts are executable and syntactically valid: `bash -n /Users/bra0002h/mcp-servers/blender-mcp/test-blender.sh && python3 -m py_compile /Users/bra0002h/mcp-servers/blender-mcp/probe-capabilities.py && echo SCRIPTS_OK`. Expected: `SCRIPTS_OK`.
- [ ] LIVE end-to-end (USER-IN-LOOP). Ensure Rungs 1–4 of `interactive-guide.md` are green (`lsof -nP -iTCP:9876 -sTCP:LISTEN` shows `Blender ... (LISTEN)`), then run in sequence: `cd /Users/bra0002h/mcp-servers/blender-mcp && ./test-blender.sh` (expect `SMOKE PASS`), then `./test-blender.sh --capabilities` (expect the verdict table + `Report written: .../capability-report.json`).
- [ ] Reconcile manual vs report: `python3 -c "import json; d=json.load(open('/Users/bra0002h/mcp-servers/blender-mcp/capability-report.json')); [print(r['command'], r['status']) for r in d['results']]"`. Compare each line against the WORKING / BROKEN sections of `BLENDER-MCP-CAPABILITIES.md`. If any verdict differs from what the manual claims, update the manual IN PLACE with the Edit tool (preserving file mode) to match the report, and bump its *Date verified* line.
- [ ] Confirm no leaked server process after the runs: `pgrep -f "blender-mcp" || echo "NO LEAKED SERVER"`. Expected: `NO LEAKED SERVER` (the launcher EXIT trap and the probe `try/finally` both terminate). If a PID is printed, investigate the trap/finally path — do not leave it running.
- [ ] Confirm no leaked scene artifacts: `./test-blender.sh` and check the `scene:` line contains neither `ASSERT_CUBE` nor `ASSERT_PLANE`. Expected: neither name present.
- [ ] Commit any reconciliation edits (skip if none were needed):
```
git -C /Users/bra0002h/mcp-servers/blender-mcp add -A
git -C /Users/bra0002h/mcp-servers/blender-mcp commit -m "Reconcile BLENDER-MCP-CAPABILITIES.md with fresh capability-report.json

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```
- [ ] Final tree check — confirm the Workstream B artifact set is present in the clone: `ls -1 /Users/bra0002h/mcp-servers/blender-mcp/ | grep -E "^(test-blender.sh|probe-capabilities.py|probe_helpers.py|test_probe_helpers.py|test_launcher_versiondetect.py|BLENDER-MCP-CAPABILITIES.md|PROJECT-NOTES.md|interactive-guide.md)$"`. Expected: all 8 filenames listed.
