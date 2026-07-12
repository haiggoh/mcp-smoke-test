import json, os, re
from conftest import REPO, SKILL_DIR

def test_plugin_json_valid_and_semver():
    p = os.path.join(REPO, ".claude-plugin", "plugin.json")
    d = json.load(open(p))
    for k in ("name", "version", "description", "author", "license", "keywords"):
        assert k in d, f"plugin.json missing {k}"
    assert d["name"] == "mcp-smoke-test"
    assert re.fullmatch(r"\d+\.\d+\.\d+", d["version"]), d["version"]
    assert isinstance(d["keywords"], list) and d["keywords"]
    assert d["author"].get("name")

def test_no_per_plugin_marketplace():
    # the one-canonical-marketplace rule: this repo must NOT ship its own marketplace.json
    assert not os.path.exists(os.path.join(REPO, ".claude-plugin", "marketplace.json"))

def test_skill_md_frontmatter():
    p = os.path.join(SKILL_DIR, "SKILL.md")
    text = open(p).read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, "SKILL.md must start with a YAML frontmatter fence"
    fm = m.group(1)
    assert re.search(r"^name:\s*mcp-smoke-test\s*$", fm, re.M), "name must equal dir name"
    assert re.search(r"^description:\s*\S", fm, re.M), "description required"
