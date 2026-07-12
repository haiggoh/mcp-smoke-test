import os
from conftest import TEMPLATES, BLENDER
from render import render, strip_banner, placeholders
from blender_params import BLENDER_PARAMS

PAIRS = [
    ("interactive-guide.md.tmpl", "interactive-guide.md"),
    ("APP-MCP-CAPABILITIES.md.tmpl", "BLENDER-MCP-CAPABILITIES.md"),
    ("PROJECT-NOTES.md.tmpl", "PROJECT-NOTES.md"),
]

def test_doc_roundtrips():
    for tmpl, proven in PAIRS:
        out = strip_banner(render(open(os.path.join(TEMPLATES, tmpl)).read(), BLENDER_PARAMS))
        assert out == open(os.path.join(BLENDER, proven)).read(), f"{tmpl} round-trip mismatch"

def test_no_stray_todo_markers():
    for tmpl, _ in PAIRS:
        body = open(os.path.join(TEMPLATES, tmpl)).read()
        for bad in ("TBD", "TODO", "FIXME"):
            assert bad not in body, f"{tmpl} contains stray {bad}"

def test_all_placeholders_known():
    for tmpl, _ in PAIRS:
        body = open(os.path.join(TEMPLATES, tmpl)).read()
        assert placeholders(body) <= set(BLENDER_PARAMS.keys()), tmpl
