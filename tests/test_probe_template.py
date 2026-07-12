import ast, os
from conftest import TEMPLATES, BLENDER
from render import render, strip_banner, placeholders
from blender_params import BLENDER_PARAMS

TMPL = os.path.join(TEMPLATES, "probe-capabilities.py.tmpl")
PROVEN = os.path.join(BLENDER, "probe-capabilities.py")

def test_instantiated_is_valid_python():
    out = render(open(TMPL).read(), BLENDER_PARAMS)
    ast.parse(out)  # raises SyntaxError if the template produces invalid Python

def test_roundtrip_reproduces_proven_file():
    out = strip_banner(render(open(TMPL).read(), BLENDER_PARAMS))
    proven = open(PROVEN).read()
    assert out == proven, "instantiated template must byte-match the proven Blender probe"

def test_loadbearing_engine_lines_present():
    body = open(TMPL).read()
    for needle in ("threading.Thread(target=", "notifications/initialized",
                   "os._exit", "_abort_stall", "stderr="):
        assert needle in body, f"probe template lost load-bearing line: {needle}"

def test_every_placeholder_is_known():
    body = open(TMPL).read()
    assert placeholders(body) <= set(BLENDER_PARAMS.keys())
