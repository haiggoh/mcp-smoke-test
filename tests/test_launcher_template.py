import os, subprocess, tempfile
from conftest import TEMPLATES, BLENDER
from render import render, strip_banner, placeholders
from blender_params import BLENDER_PARAMS

TMPL = os.path.join(TEMPLATES, "test-APP.sh.tmpl")
PROVEN = os.path.join(BLENDER, "test-blender.sh")

def test_roundtrip_reproduces_proven_launcher():
    out = strip_banner(render(open(TMPL).read(), BLENDER_PARAMS))
    assert out == open(PROVEN).read()

def test_instantiated_passes_bash_syntax_check():
    out = render(open(TMPL).read(), BLENDER_PARAMS)
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as f:
        f.write(out); path = f.name
    try:
        r = subprocess.run(["bash", "-n", path], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
    finally:
        os.unlink(path)

def test_safety_and_structure_preserved():
    # markers verified present in the proven launcher (this launcher spawns uvx + does a
    # read-only smoke call; it has no lsof/EXIT-trap — that lives in the interactive guide).
    body = open(TMPL).read()
    for needle in ("set -euo pipefail", "--capabilities", "BLMCP_PRINT_VERSIONS_ONLY", "SMOKE PASS"):
        assert needle in body, f"launcher template lost: {needle}"

def test_every_placeholder_is_known():
    assert placeholders(open(TMPL).read()) <= set(BLENDER_PARAMS.keys())
