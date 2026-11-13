"""Closure + offline engine tests for the probe template (no live MCP, no live app).

The probe template does `import probe_helpers as h` — the helper module must ship among the
templates, or a fresh instantiation (SKILL.md step 1, "copy the templates") dies on
ModuleNotFoundError before a single tool is probed (Workstream B created the helper only at
the external Blender instance).

Behavior rules under test, driven against a stub stdio MCP server:
  - a MUTATING tool's lost response is never blind-retried (the first execution may have
    landed; the before/after state delta decides the verdict);
  - a read-only tool's lost response retries exactly once (transport-hiccup rule);
  - a tool absent from the server's tools/list is never called (NOT-DECLARED — a validation
    error is not a capability verdict);
  - probe_helpers.unwrap_tool_result treats result.isError=true as failure, even when the
    error text does not start with "error";
  - probe_helpers.owned_new keeps cleanup ownership-aware (a pre-existing name is never ours).
"""
import ast
import importlib.util
import json
import os
import sys

import pytest

from conftest import TEMPLATES, instance_dir
from render import render, strip_banner
from blender_params import BLENDER_PARAMS

PROBE_TMPL = os.path.join(TEMPLATES, "probe-capabilities.py.tmpl")
HELPERS_TMPL = os.path.join(TEMPLATES, "probe_helpers.py.tmpl")

STUB_SERVER = r'''
"""Stub stdio MCP server for offline engine tests.

Env: PROBE_STUB_MODE in {declared, notdeclared, retry_then_ok};
     PROBE_STUB_COUNT = file the per-tool tools/call counts are written to.
"""
import json
import os
import sys

mode = os.environ.get("PROBE_STUB_MODE", "declared")
count_path = os.environ["PROBE_STUB_COUNT"]
counts = {}

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        m = json.loads(line)
    except Exception:
        continue
    mid, meth = m.get("id"), m.get("method", "")
    if meth == "initialize":
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": mid,
            "result": {"capabilities": {},
                       "serverInfo": {"name": "stub", "version": "0"}}}) + "\n")
        sys.stdout.flush()
    elif meth == "notifications/initialized":
        pass
    elif meth == "tools/list":
        names = ["read_tool", "mutating_tool", "get_scene_info"]
        if mode == "notdeclared":
            names = ["get_scene_info"]
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": mid,
            "result": {"tools": [{"name": n} for n in names]}}) + "\n")
        sys.stdout.flush()
    elif meth == "tools/call":
        name = m["params"]["name"]
        counts[name] = counts.get(name, 0) + 1
        with open(count_path, "w") as f:
            json.dump(counts, f)
        if mode == "retry_then_ok" and counts.get(name, 0) == 1:
            continue  # first attempt: silence (transport hiccup)
        if name == "mutating_tool":
            continue  # never respond
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": mid,
            "result": {"content": [{"type": "text",
                                    "text": '{"status": "SUCCESS"}'}]}}) + "\n")
        sys.stdout.flush()
'''


def _write_helpers(tmp_path):
    src = strip_banner(render(open(HELPERS_TMPL).read(), {}))
    (tmp_path / "probe_helpers.py").write_text(src)
    return tmp_path / "probe_helpers.py"


def _load_helpers(tmp_path):
    p = _write_helpers(tmp_path)
    spec = importlib.util.spec_from_file_location("probe_helpers_under_test", str(p))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _render_and_import(tmp_path, mode):
    """Render helpers + probe into tmp_path with a stub server and import the probe module.
    Module-level code spawns the stub server (mod.proc); the caller terminates it."""
    stub = tmp_path / "stub_server.py"
    stub.write_text(STUB_SERVER)
    count_file = tmp_path / "call-counts.json"
    repo_dir = tmp_path / "probed-repo"
    repo_dir.mkdir(exist_ok=True)
    params = dict(BLENDER_PARAMS)  # satisfies every template token
    params.update({
        "MCP_SERVER_ARGV": json.dumps([sys.executable, str(stub)]),
        "MCP_SERVER_ENV": json.dumps({
            "PATH": os.environ["PATH"],
            "PROBE_STUB_MODE": mode,
            "PROBE_STUB_COUNT": str(count_file),
        }),
        "STDERR_LOG": str(tmp_path / "server-stderr.log"),
        "PROBE_REPO_DIR": str(repo_dir),
    })
    _write_helpers(tmp_path)
    (tmp_path / "probe_under_test.py").write_text(render(open(PROBE_TMPL).read(), params))
    sys.path.insert(0, str(tmp_path))
    spec = importlib.util.spec_from_file_location(
        "probe_under_test_" + mode.replace("-", "_"), str(tmp_path / "probe_under_test.py"))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, count_file


@pytest.fixture()
def probe_factory(tmp_path):
    made = []

    def factory(mode):
        mod, count_file = _render_and_import(tmp_path, mode)
        made.append(mod)
        return mod, count_file

    yield factory
    for mod in made:
        try:
            mod.proc.terminate()
        except Exception:
            pass
    p = str(tmp_path)
    if p in sys.path:
        sys.path.remove(p)


@pytest.fixture()
def helpers(tmp_path):
    return _load_helpers(tmp_path)


# --- closure -------------------------------------------------------------------

def test_helper_template_shipped_and_valid():
    assert os.path.exists(HELPERS_TMPL), (
        "probe-capabilities.py.tmpl imports probe_helpers — templates/probe_helpers.py.tmpl "
        "must ship, or a fresh instantiation dies on ModuleNotFoundError")
    ast.parse(strip_banner(open(HELPERS_TMPL).read()))


def test_probe_imports_resolve_within_rendered_bundle(tmp_path):
    """Every non-stdlib import of the rendered probe must exist as a rendered .py beside it."""
    _write_helpers(tmp_path)
    params = dict(BLENDER_PARAMS)
    params.update({
        "MCP_SERVER_ARGV": json.dumps([sys.executable, "-c", "import sys; sys.exit(0)"]),
        "STDERR_LOG": str(tmp_path / "server-stderr.log"),
        "PROBE_REPO_DIR": str(tmp_path),
    })
    src = render(open(PROBE_TMPL).read(), params)
    tree = ast.parse(src)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            imported.add(node.module.split(".")[0])
    stdlib = set(sys.stdlib_module_names)
    for name in sorted(imported):
        assert (tmp_path / (name + ".py")).exists() or name in stdlib, (
            f"probe imports '{name}' but it is not part of the shipped closure")


def test_helpers_roundtrip_matches_proven_instance():
    inst = instance_dir()
    if inst is None:
        pytest.skip("proven Blender instance not present "
                    "(set MCP_SMOKE_INSTANCE_DIR to enable the lockstep check)")
    assert inst is not None  # narrows for the type checker
    rendered = strip_banner(render(open(HELPERS_TMPL).read(), {}))
    with open(os.path.join(inst, "probe_helpers.py")) as f:
        assert rendered == f.read(), "probe_helpers.py.tmpl drifted from the proven instance copy"


# --- probe_helpers behavior ----------------------------------------------------

def test_unwrap_treats_iserror_as_failure(helpers):
    msg = {"result": {"isError": True,
                      "content": [{"type": "text",
                                   "text": "Blender plugin not connected: click Connect"}]}}
    ok, payload, raw = helpers.unwrap_tool_result(msg)
    assert ok is False, "an isError=true result must never read as functional success"


def test_owned_new_ownership_rule(helpers):
    assert helpers.owned_new(existed_before=False, exists_after=True) is True   # we created it
    assert helpers.owned_new(existed_before=True, exists_after=True) is False   # pre-existing: user's
    assert helpers.owned_new(existed_before=False, exists_after=False) is False  # call made nothing
    assert helpers.owned_new(existed_before=True, exists_after=False) is False


# --- engine behavior against the stub server -----------------------------------

def test_mutating_call_is_not_retried(probe_factory):
    mod, count_file = probe_factory("declared")
    ok, _, _ = mod.call("mutating_tool", {}, timeout=1, mutating=True)
    assert ok is False, "a lost response on a mutating call is an honest not-ok"
    counts = json.load(open(count_file))
    assert counts.get("mutating_tool") == 1, (
        "a mutating call must be sent exactly once — never blind-retried")


def test_readonly_call_retries_once_then_succeeds(probe_factory):
    mod, count_file = probe_factory("retry_then_ok")
    ok, _, raw = mod.call("read_tool", {}, timeout=2)
    assert ok is True
    counts = json.load(open(count_file))
    assert counts.get("read_tool") == 2, "a read-only call retries exactly once"


def test_undeclared_tool_is_never_called(probe_factory):
    mod, count_file = probe_factory("notdeclared")
    ok, _, raw = mod.call("read_tool", {}, timeout=2)
    assert ok is False
    assert "NOT-DECLARED" in (raw or "")
    counts = json.load(open(count_file)) if count_file.exists() else {}
    assert "read_tool" not in counts, "a tool absent from tools/list must never be called"
