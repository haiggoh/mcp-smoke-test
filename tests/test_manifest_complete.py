import glob, os, re
from conftest import TEMPLATES
from render import placeholders

def _manifest_tokens():
    text = open(os.path.join(TEMPLATES, "placeholder-manifest.md")).read()
    # tokens documented as {{TOKEN}} or as `TOKEN` in the first table column
    return set(re.findall(r"\{\{([A-Z0-9_]+)\}\}", text)) | set(re.findall(r"^\|\s*`?([A-Z0-9_]+)`?\s*\|", text, re.M))

def _used_tokens():
    used = set()
    for f in glob.glob(os.path.join(TEMPLATES, "*.tmpl")):
        used |= placeholders(open(f).read())
    return used

def test_manifest_matches_used_tokens_exactly():
    used, documented = _used_tokens(), _manifest_tokens()
    assert used - documented == set(), f"undocumented tokens: {used - documented}"
    assert documented - used == set(), f"documented but unused tokens: {documented - used}"
