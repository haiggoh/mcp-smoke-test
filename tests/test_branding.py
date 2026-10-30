"""tests/test_branding.py — the 🔌 identity mark on the plugin's credit-moment surfaces.

Plan 2026-10-28, §Wave 2 Task 7. The mark is the repo's GitHub About emoji, verbatim, on the
static identity surfaces and the report template. The capabilities MANUAL's rendered instance
is pinned by test_doc_templates.test_doc_roundtrips (template↔instance lockstep), so the
instance follows the template automatically.
"""
import json
import os

from conftest import REPO, SKILL_DIR, TEMPLATES


def test_plugin_json_description_leads_with_mark():
    d = json.load(open(os.path.join(REPO, ".claude-plugin", "plugin.json")))
    assert d["description"].startswith("🔌 ")


def test_readme_h1():
    with open(os.path.join(REPO, "README.md")) as fh:
        h1 = fh.readline().rstrip("\n")
    assert h1 == "# 🔌 mcp-smoke-test"


def test_skill_md_branding_section():
    body = open(os.path.join(SKILL_DIR, "SKILL.md")).read()
    assert "## Branding (🔌)" in body
    assert "🔌 mcp-smoke-test:" in body


def test_capabilities_template_leads_with_mark():
    lines = open(os.path.join(TEMPLATES, "APP-MCP-CAPABILITIES.md.tmpl")).read().splitlines()
    # line 0 is the template banner comment; the h1 follows it
    assert lines[1].startswith("# 🔌 "), lines[1]
