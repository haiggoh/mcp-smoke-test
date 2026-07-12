# Reusable `mcp-smoke-test` Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Turn the proven Blender-MCP test artifacts (Workstream B) into a reusable, MCP-agnostic Claude skill — `mcp-smoke-test` — that carries the playbook (method + prereq-ladder + functional-verification + probe-reliability rules) and parametrized templates, then publish it to the canonical `haiggoh` marketplace.

**Architecture:** The skill lives in this repo (`/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/`) as a publishable Claude-Code plugin: `.claude-plugin/plugin.json` + `skills/mcp-smoke-test/SKILL.md`, with the templates and worked example bundled *inside* the skill dir so they ship with it. Each `.tmpl` is derived by **parameterizing a proven Workstream-B file** (Blender is the reference instance — we generalize from what actually worked, per spec §7), and the correctness invariant is a round-trip: instantiating a template with the Blender parameter set reproduces the original proven file. The SKILL.md encodes the durable value — the method — so the *next* MCP is faster to onboard.

**Tech Stack:** Markdown (SKILL.md, doc templates, example), a single documented `{{PLACEHOLDER}}` substitution convention, Python 3 stdlib (`pytest`, `ast`, `json`, `re` for the round-trip/validity tests), Bash (`bash -n` syntax checks), `git` + `gh` CLI (authed as `haiggoh`), and the Claude-Code `/plugin` marketplace tooling.

## Global Constraints

These rules are project-wide and apply to EVERY task below. Follow them verbatim even where a step is silent about them.

- **Generalize from the PROVEN instance, never in the abstract (core correctness invariant):** Every template under `skills/mcp-smoke-test/templates/` MUST be produced by taking the corresponding *proven* Workstream-B file from `/Users/bra0002h/mcp-servers/blender-mcp/` and replacing only the Blender-specific values with documented placeholders. Do NOT hand-author a template from memory. The invariant each template must satisfy: `instantiate(template, BLENDER_PARAMS)` reproduces the original proven file (modulo a known, stripped template-header banner). If the round-trip test cannot pass, the template lost or distorted content — fix the template, not the test.
- **Workstream B is a hard precondition:** This plan reads the proven artifacts (`test-blender.sh`, `probe-capabilities.py`, `probe_helpers.py`, `BLENDER-MCP-CAPABILITIES.md`, `PROJECT-NOTES.md`, `interactive-guide.md`) from `/Users/bra0002h/mcp-servers/blender-mcp/`. If any is missing, STOP — Workstream B has not completed; this plan cannot generalize from an instance that does not exist.
- **Plugin/skill layout convention (authoritative):** Published skills on this machine follow the sibling-plugin layout — `.claude-plugin/plugin.json` (manifest) + `skills/<skill-name>/SKILL.md` where the directory name equals the skill name. Bundled resources (templates, examples) live under `skills/mcp-smoke-test/` so they ship with the skill. Spec §5.1's flat sketch (`SKILL.md` + `templates/` at repo root) is a *content* sketch; this plan follows the real installable layout (spec §5.4 defers to `plugin-publishing-workflow`, which mandates this structure). This reconciliation is intentional and is recorded in Task 1.
- **ONE canonical marketplace:** There is a single canonical Claude-plugin marketplace — the sync repo at `/Users/bra0002h/ClaudeWorkspace/claude-code-desktop-sync/.claude-plugin/marketplace.json` (`"name": "haiggoh"`). NEVER ship a per-plugin `marketplace.json` (name-collision guard). The `mcp-smoke-test` plugin ships only `.claude-plugin/plugin.json`; the canonical marketplace references it by git URL.
- **Version-bump rule:** Bump `version` in `.claude-plugin/plugin.json` (semver) on EVERY published change. An in-place edit to a published plugin without a version bump is exactly what the `no-hidden-changes` skill flags.
- **SKILL.md frontmatter shape:** A YAML fence with exactly two keys — `name` (must equal the skill dir name `mcp-smoke-test`) and `description` (a long trigger paragraph describing WHEN to use the skill) — followed by the Markdown body.
- **Preserve file permissions on in-place edits:** When editing an existing file (the canonical `marketplace.json`, any dotfile), edit in place (Edit tool / `sed -i`) to keep the inode's mode. Never `> tmp && mv tmp file` or plain `> file` recreation on an existing file. New files created fresh in this plan have no prior mode to preserve.
- **`gh` account = `haiggoh`:** All GitHub operations (repo create, push, PR) run under the `haiggoh` login (already authed with `repo` + `workflow` scopes).
- **Single placeholder syntax:** Templates use `{{UPPER_SNAKE}}` tokens and nothing else for substitution. Every token used across all templates MUST appear in the documented placeholder manifest (Task 6). No `TBD`/`TODO`/`FIXME`/`...`-as-placeholder anywhere in a shipped template.
- **Commit frequently; commit-message trailer (verbatim, last line of every commit):**
  ```
  Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
  ```
- **This repo is already a git repo** at `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/` on branch `main` (commit `ea17a52` holds the spec). All commits in this plan go here. Work directly on `main` (solo repo) unless a step says otherwise.

---

## Task 1 — Scaffold the plugin structure + `plugin.json`, with a validity test (TDD)

**Files:**
- Create `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/.claude-plugin/plugin.json`
- Create `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/skills/mcp-smoke-test/` (directory)
- Create `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/skills/mcp-smoke-test/templates/` (directory)
- Create `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/skills/mcp-smoke-test/examples/` (directory)
- Create `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/tests/test_skill_meta.py`
- Create `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/tests/conftest.py`

**Interfaces:**
- Produces: a valid Claude-Code plugin manifest and the directory skeleton the later tasks fill.
- Consumes: the sibling-plugin layout convention (mirrors `/Users/bra0002h/ClaudeWorkspace/measure-twice/`).

Steps:
- [ ] Confirm the Workstream-B precondition (proven artifacts exist): run `for f in test-blender.sh probe-capabilities.py probe_helpers.py BLENDER-MCP-CAPABILITIES.md PROJECT-NOTES.md interactive-guide.md; do test -f "/Users/bra0002h/mcp-servers/blender-mcp/$f" && echo "OK $f" || echo "MISSING $f"; done`. Expected: six `OK` lines. If any `MISSING`, STOP — Workstream B has not completed.
- [ ] Confirm this repo is clean and on `main`: run `git -C /Users/bra0002h/ClaudeWorkspace/mcp-smoke-test status -sb`. Expected: `## main` with no unexpected staged changes.
- [ ] Create the directory skeleton: run `mkdir -p /Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/.claude-plugin /Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/skills/mcp-smoke-test/templates /Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/skills/mcp-smoke-test/examples /Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/tests`. Expected: no output, exit 0.
- [ ] Write the FAILING test `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/tests/conftest.py` with these exact contents:
```python
import os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_DIR = os.path.join(REPO, "skills", "mcp-smoke-test")
TEMPLATES = os.path.join(SKILL_DIR, "templates")
BLENDER = "/Users/bra0002h/mcp-servers/blender-mcp"
```
- [ ] Write the FAILING test `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/tests/test_skill_meta.py` with these exact contents:
```python
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
```
- [ ] Run the test and watch it FAIL (files not created yet): run `cd /Users/bra0002h/ClaudeWorkspace/mcp-smoke-test && python3 -m pytest tests/test_skill_meta.py -q`. Expected: failures/errors (`plugin.json` and `SKILL.md` do not exist yet). This proves the test is real.
- [ ] Create `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/.claude-plugin/plugin.json` with these exact contents:
```json
{
  "name": "mcp-smoke-test",
  "version": "0.1.0",
  "description": "Onboard and verify any MCP that drives an external app: a repeatable smoke test, a functional capability probe (WORKS/PARTIAL/BROKEN by assertions that can fail, not by 'no exception'), an evidence-based capabilities manual, and an interactive prereq-ladder setup guide — with parametrized templates you instantiate per MCP.",
  "author": { "name": "Heiko Brantsch" },
  "homepage": "https://github.com/haiggoh/mcp-smoke-test",
  "license": "MIT",
  "keywords": ["skill", "mcp", "testing", "probe", "onboarding", "capabilities", "blender", "photoshop"]
}
```
- [ ] Create a placeholder `SKILL.md` so the frontmatter test passes now (full body is Task 2). Write `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/skills/mcp-smoke-test/SKILL.md` with these exact contents:
```markdown
---
name: mcp-smoke-test
description: Use when onboarding, smoke-testing, or verifying an MCP server that drives an external desktop app (Blender, Photoshop, Premiere, InDesign, Illustrator, and similar) — when you need to confirm the whole pipe is live, functionally probe each tool for what actually works vs silently no-ops, produce an evidence-based capabilities manual, or walk a user from "nothing connected" to "all green" via an interactive prereq ladder. Also use when generalizing that method to a new MCP by instantiating the bundled templates.
---

# MCP Smoke-Test Playbook

(Body written in Task 2.)
```
- [ ] Run the test and watch it PASS: run `cd /Users/bra0002h/ClaudeWorkspace/mcp-smoke-test && python3 -m pytest tests/test_skill_meta.py -q`. Expected: 3 passed.
- [ ] Commit: run `cd /Users/bra0002h/ClaudeWorkspace/mcp-smoke-test && git add -A && git commit -q -m "$(printf 'Workstream C Task 1: plugin scaffold + meta validity test\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"`. Expected: commit succeeds; verify with `git log --oneline -1`.

---

## Task 2 — Write the SKILL.md playbook (the durable value = the method)

**Files:**
- Modify `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/skills/mcp-smoke-test/SKILL.md` (replace the placeholder body)
- Modify `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/tests/test_skill_meta.py` (add a content-structure test)

**Interfaces:**
- Produces: the playbook body encoding when-to-use, the prereq-ladder pattern, the functional-verification rule, the probe-reliability rules, the publish framing, and the instantiation procedure (spec §5.2).
- Consumes: the hard-won Adobe reliability lessons (unread-stderr deadlock, fail-fast on stall, terminate subprocess, clean up artifacts, no concurrent MCP calls).

Steps:
- [ ] Add a FAILING content test to `tests/test_skill_meta.py` (append these functions):
```python
def test_skill_md_has_required_sections():
    from conftest import SKILL_DIR
    body = open(os.path.join(SKILL_DIR, "SKILL.md")).read()
    for heading in (
        "## When to use",
        "## The prereq ladder",
        "## Functional verification",
        "## Probe-reliability rules",
        "## Publish framing",
        "## Instantiation procedure",
    ):
        assert heading in body, f"SKILL.md missing section: {heading}"

def test_skill_md_names_the_five_templates():
    from conftest import SKILL_DIR
    body = open(os.path.join(SKILL_DIR, "SKILL.md")).read()
    for t in ("test-APP.sh.tmpl", "probe-capabilities.py.tmpl",
              "APP-MCP-CAPABILITIES.md.tmpl", "PROJECT-NOTES.md.tmpl",
              "interactive-guide.md.tmpl"):
        assert t in body, f"SKILL.md must reference template {t}"
```
- [ ] Run just these two tests and watch them FAIL: run `cd /Users/bra0002h/ClaudeWorkspace/mcp-smoke-test && python3 -m pytest tests/test_skill_meta.py -q -k "required_sections or names_the_five"`. Expected: 2 failing (placeholder body has none of the sections).
- [ ] Replace the SKILL.md body (everything after the frontmatter fence) so it contains, as `##` sections with real prose (not placeholders):
  - `## When to use` — onboarding/verifying any MCP that drives an external app; the four deliverables (smoke test, functional probe, capabilities manual, interactive guide).
  - `## The prereq ladder` — the detect-then-guide, loop-until-green pattern generalized: rung 1 MCP-enabled-in-Claude (detect via `~/.claude.json` `disabledMcpServers`) → rung 2 app running → rung 3 plugin/add-on installed+enabled → rung 4 bridge/socket connected → rung 5 optional features. State that each instance fills in *how* to detect and *how* to guide each rung, and that after each user action you re-detect and only advance when the rung is green.
  - `## Functional verification` — classify WORKS/PARTIAL/BROKEN/INCONCLUSIVE by an assertion that can fail (snapshot observable state before, run the tool, snapshot after, require the expected delta); never trust "no exception"; reserve INCONCLUSIVE for when the *verification read itself* is unavailable.
  - `## Probe-reliability rules` — drain server stderr to a FILE (never an unread `PIPE`: ~64KB fills after ~a dozen commands → deadlock); one `tools/call` at a time, no concurrent MCP calls; retry-once then fail-fast on a second consecutive stall, writing a partial `aborted` report and flushing stdout before `os._exit`; terminate the spawned server in `finally`; clean up scene/document artifacts you created; plugins/add-ons don't hot-reload → mark reload steps user-in-loop.
  - `## Publish framing` — separate *novel additions* (probe/manual/guide) from *upstreamable bug fixes*; version-guard fixes for backward compatibility; publish the skill via the ONE canonical `haiggoh` marketplace.
  - `## Instantiation procedure` — copy the five templates from `templates/` → fill the `{{PLACEHOLDER}}` tokens (see the placeholder manifest) with the new MCP's values → run the probe once → seed the manual from that first report. Name all five templates: `test-APP.sh.tmpl`, `probe-capabilities.py.tmpl`, `APP-MCP-CAPABILITIES.md.tmpl`, `PROJECT-NOTES.md.tmpl`, `interactive-guide.md.tmpl`.
- [ ] Run the full meta test file and watch it PASS: run `cd /Users/bra0002h/ClaudeWorkspace/mcp-smoke-test && python3 -m pytest tests/test_skill_meta.py -q`. Expected: 5 passed.
- [ ] Commit: run `cd /Users/bra0002h/ClaudeWorkspace/mcp-smoke-test && git add -A && git commit -q -m "$(printf 'Workstream C Task 2: SKILL.md playbook + content-structure test\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"`. Expected: commit succeeds.

---

## Task 3 — Extract `probe-capabilities.py.tmpl` from Blender's proven probe (round-trip TDD)

**Files:**
- Create `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/skills/mcp-smoke-test/templates/probe-capabilities.py.tmpl`
- Create `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/tests/render.py` (tiny placeholder renderer used by tests)
- Create `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/tests/blender_params.py` (the Blender parameter fixture)
- Create `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/tests/test_probe_template.py`

**Interfaces:**
- Produces: `templates/probe-capabilities.py.tmpl` — the generic stdio-JSON-RPC probe engine with Blender-specifics replaced by `{{PLACEHOLDER}}` tokens.
- Produces: `render(text, params) -> str` (pure `{{KEY}}` → value substitution) and `BLENDER_PARAMS` (dict).
- Invariant: `render(template, BLENDER_PARAMS)` equals the proven `/Users/bra0002h/mcp-servers/blender-mcp/probe-capabilities.py` after stripping the template-header banner.

Steps:
- [ ] Create the pure renderer `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/tests/render.py` with these exact contents:
```python
import re

BANNER_RE = re.compile(r"^# === mcp-smoke-test template.*?===\n", re.M)

def render(text: str, params: dict) -> str:
    def sub(m):
        key = m.group(1)
        if key not in params:
            raise KeyError(f"unknown placeholder {{{{{key}}}}}")
        return params[key]
    return re.sub(r"\{\{([A-Z0-9_]+)\}\}", sub, text)

def strip_banner(text: str) -> str:
    return BANNER_RE.sub("", text, count=1)

def placeholders(text: str) -> set:
    return set(re.findall(r"\{\{([A-Z0-9_]+)\}\}", text))
```
- [ ] Create the Blender parameter fixture `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/tests/blender_params.py`. Populate `BLENDER_PARAMS` with the exact Blender-specific strings that were lifted out of the proven `probe-capabilities.py` (fill each value verbatim from that file during extraction below):
```python
# Exact values that, substituted into probe-capabilities.py.tmpl, reproduce the
# proven /Users/bra0002h/mcp-servers/blender-mcp/probe-capabilities.py verbatim.
BLENDER_PARAMS = {
    "APP": "blender",
    "MCP_SERVER_ARGV": '["uvx", "blender-mcp"]',
    "MCP_SERVER_ENV": "{}",
    "SMOKE_CALL": "get_scene_info",
    "STDERR_LOG": "/tmp/probe-blender-mcp-stderr.log",
    "REPORT_PATH_EXPR": 'os.path.join(REPO, "capability-report.json")',
    # ...any remaining tokens are filled to match the proven file exactly...
}
```
- [ ] Extract the template. Copy the proven probe as the starting point: run `cp /Users/bra0002h/mcp-servers/blender-mcp/probe-capabilities.py /Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/skills/mcp-smoke-test/templates/probe-capabilities.py.tmpl`. Expected: file copied.
- [ ] Prepend the template-header banner as the first line of the `.tmpl` (use the Edit tool to insert at top, preserving the rest): insert exactly:
```
# === mcp-smoke-test template: probe-capabilities.py — fill {{PLACEHOLDER}} tokens, see placeholder-manifest.md ===
```
- [ ] Parameterize the Blender-specifics in the `.tmpl` using in-place Edit-tool replacements (NOT redirect-and-move), replacing each concrete Blender value with its `{{TOKEN}}` and recording the original value into `tests/blender_params.py`. At minimum replace: the server argv `["uvx", "blender-mcp"]` → `{{MCP_SERVER_ARGV}}`; the spawn env → `{{MCP_SERVER_ENV}}`; the stderr log path `/tmp/probe-blender-mcp-stderr.log` → `{{STDERR_LOG}}`; the smoke/liveness call `get_scene_info` → `{{SMOKE_CALL}}`; the app tag string `blender` → `{{APP}}`. Leave the load-bearing engine (reader thread, handshake, retry-once-then-`_abort_stall`, functional before/after assertion helpers) as literal code — it is MCP-agnostic and must NOT be tokenized.
- [ ] Write the round-trip test `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/tests/test_probe_template.py` with these exact contents:
```python
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
```
- [ ] Run the test; iterate the `.tmpl` and `blender_params.py` until it PASSES: run `cd /Users/bra0002h/ClaudeWorkspace/mcp-smoke-test && python3 -m pytest tests/test_probe_template.py -q`. Expected: 4 passed. If `test_roundtrip_reproduces_proven_file` fails, the diff shows exactly which literal was over- or under-tokenized — fix the `.tmpl`/params, do not weaken the test.
- [ ] Commit: run `cd /Users/bra0002h/ClaudeWorkspace/mcp-smoke-test && git add -A && git commit -q -m "$(printf 'Workstream C Task 3: probe-capabilities.py.tmpl via round-trip from proven Blender probe\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"`. Expected: commit succeeds.

---

## Task 4 — Extract `test-APP.sh.tmpl` from `test-blender.sh` (syntax + round-trip TDD)

**Files:**
- Create `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/skills/mcp-smoke-test/templates/test-APP.sh.tmpl`
- Create `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/tests/test_launcher_template.py`
- Modify `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/tests/blender_params.py` (add launcher tokens)

**Interfaces:**
- Produces: `templates/test-APP.sh.tmpl` — the launcher skeleton (smoke vs `--capabilities`), with Blender-specifics tokenized.
- Invariant: `render(template, BLENDER_PARAMS)` reproduces the proven `test-blender.sh` (banner stripped) and passes `bash -n`.

Steps:
- [ ] Copy the proven launcher: run `cp /Users/bra0002h/mcp-servers/blender-mcp/test-blender.sh /Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/skills/mcp-smoke-test/templates/test-APP.sh.tmpl`. Expected: file copied.
- [ ] Insert the banner as line 2 (immediately after the `#!/usr/bin/env bash` shebang, using the Edit tool so the shebang stays first): `# === mcp-smoke-test template: test-APP.sh — fill {{PLACEHOLDER}} tokens ===`.
- [ ] Parameterize the Blender-specifics with in-place Edit-tool replacements and record originals into `BLENDER_PARAMS`: the socket listen-check port `9876` → `{{SOCKET_PORT}}`; the server invocation `uvx blender-mcp` → `{{MCP_SERVER_CMD}}`; the smoke `tools/call` name `get_scene_info` → `{{SMOKE_CALL}}`; the app display name `Blender` → `{{APP_DISPLAY}}`; the version-enumeration glob `/Users/bra0002h/Library/Application Support/Blender/*/` → `{{VERSION_GLOB}}`; the probe filename `probe-capabilities.py` stays literal (same name in every instance). Keep `set -euo pipefail`, the idempotent listen-check + reuse logic, and the EXIT-trap-only-if-we-started-it structure as literal.
- [ ] Add the launcher tokens to `tests/blender_params.py` with their exact original values (`SOCKET_PORT`, `MCP_SERVER_CMD`, `APP_DISPLAY`, `VERSION_GLOB`, and reuse `SMOKE_CALL`).
- [ ] Write the test `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/tests/test_launcher_template.py` with these exact contents:
```python
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
    body = open(TMPL).read()
    for needle in ("set -euo pipefail", "trap ", "lsof", "--capabilities"):
        assert needle in body, f"launcher template lost: {needle}"

def test_every_placeholder_is_known():
    assert placeholders(open(TMPL).read()) <= set(BLENDER_PARAMS.keys())
```
- [ ] Run and iterate to green: run `cd /Users/bra0002h/ClaudeWorkspace/mcp-smoke-test && python3 -m pytest tests/test_launcher_template.py -q`. Expected: 4 passed.
- [ ] Commit: run `cd /Users/bra0002h/ClaudeWorkspace/mcp-smoke-test && git add -A && git commit -q -m "$(printf 'Workstream C Task 4: test-APP.sh.tmpl via round-trip from proven launcher\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"`. Expected: commit succeeds.

---

## Task 5 — Extract the three doc templates (manual, project-notes, interactive-guide)

**Files:**
- Create `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/skills/mcp-smoke-test/templates/APP-MCP-CAPABILITIES.md.tmpl`
- Create `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/skills/mcp-smoke-test/templates/PROJECT-NOTES.md.tmpl`
- Create `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/skills/mcp-smoke-test/templates/interactive-guide.md.tmpl`
- Create `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/tests/test_doc_templates.py`
- Modify `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/tests/blender_params.py` (add doc tokens)

**Interfaces:**
- Produces: three Markdown doc templates generalized from Blender's proven docs, tokenizing the *structural* app-specifics (app name, transport description, the prereq ladder rungs, the capability rows) while keeping the reusable scaffolding literal.
- Invariant: each `render(template, BLENDER_PARAMS)` reproduces the corresponding proven Blender doc (banner stripped); no stray `TBD`/`TODO`/`FIXME`.

Steps:
- [ ] For the **interactive guide** (the deliverable spec §5.2 centers on), copy the proven doc: run `cp /Users/bra0002h/mcp-servers/blender-mcp/interactive-guide.md /Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/skills/mcp-smoke-test/templates/interactive-guide.md.tmpl`. Then tokenize the app-specifics: the app name `Blender` → `{{APP_DISPLAY}}`; each *detect* command and *guide* instruction that is Blender-specific → the ladder tokens `{{RUNG_MCP_DETECT}}`, `{{RUNG_APP_DETECT}}`, `{{RUNG_ADDON_DETECT}}`, `{{RUNG_SOCKET_DETECT}}`, `{{RUNG_OPTIONAL_DETECT}}` and their matching `{{RUNG_*_GUIDE}}` blocks. Keep the loop-until-green scaffolding and the detect-then-guide narration literal. Prepend the HTML-comment banner `<!-- mcp-smoke-test template: interactive-guide.md — fill {{PLACEHOLDER}} tokens -->` as the first line (use an HTML comment so it renders invisibly and is stripped by the banner regex — update `BANNER_RE` in `tests/render.py` to also match the `<!-- ... -->` banner form).
- [ ] For the **capabilities manual**, copy `cp /Users/bra0002h/mcp-servers/blender-mcp/BLENDER-MCP-CAPABILITIES.md /Users/…/templates/APP-MCP-CAPABILITIES.md.tmpl` and tokenize: app name → `{{APP_DISPLAY}}`; the transport sentence → `{{TRANSPORT_NOTES}}`; the per-command capability table body (the Blender verdicts) → `{{CAPABILITY_ROWS}}` (the manual is *seeded from a probe run*, so the rows are instance-specific by design). Keep the section skeleton (Works / Partial / Broken / Untested, workarounds, update-route) literal. Prepend the HTML-comment banner.
- [ ] For the **project notes**, copy `cp /Users/bra0002h/mcp-servers/blender-mcp/PROJECT-NOTES.md /Users/…/templates/PROJECT-NOTES.md.tmpl` and tokenize the app name, the repo path `/Users/bra0002h/mcp-servers/blender-mcp` → `{{INSTANCE_REPO}}`, and the novel-additions-vs-upstream-fix framing specifics. Keep the running-record structure literal. Prepend the HTML-comment banner.
- [ ] Add all new doc tokens to `tests/blender_params.py` with their exact original Blender values (for `{{CAPABILITY_ROWS}}`, `{{TRANSPORT_NOTES}}`, and the five `{{RUNG_*_DETECT}}`/`{{RUNG_*_GUIDE}}` blocks, store the verbatim multi-line originals so the round-trip is exact).
- [ ] Write the test `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/tests/test_doc_templates.py` with these exact contents:
```python
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
```
- [ ] Run and iterate to green: run `cd /Users/bra0002h/ClaudeWorkspace/mcp-smoke-test && python3 -m pytest tests/test_doc_templates.py -q`. Expected: 3 passed.
- [ ] Commit: run `cd /Users/bra0002h/ClaudeWorkspace/mcp-smoke-test && git add -A && git commit -q -m "$(printf 'Workstream C Task 5: three doc templates via round-trip from proven Blender docs\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"`. Expected: commit succeeds.

---

## Task 6 — Placeholder manifest + `examples/blender.md` + full-suite completeness gate

**Files:**
- Create `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/skills/mcp-smoke-test/templates/placeholder-manifest.md`
- Create `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/skills/mcp-smoke-test/examples/blender.md`
- Create `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/tests/test_manifest_complete.py`

**Interfaces:**
- Produces: the single source of truth for every `{{PLACEHOLDER}}` (name, meaning, Blender example), and the worked-example pointer to the Blender instance.
- Invariant: the manifest documents exactly the union of placeholders used across all five templates — no undocumented token, no documented-but-unused token.

Steps:
- [ ] Write `templates/placeholder-manifest.md` documenting each token used across the five templates: a table of `Token | Meaning | Blender example`. Include every token introduced in Tasks 3–5 (`APP`, `APP_DISPLAY`, `MCP_SERVER_ARGV`, `MCP_SERVER_CMD`, `MCP_SERVER_ENV`, `SMOKE_CALL`, `STDERR_LOG`, `SOCKET_PORT`, `VERSION_GLOB`, `TRANSPORT_NOTES`, `CAPABILITY_ROWS`, `INSTANCE_REPO`, `REPORT_PATH_EXPR`, and the `RUNG_*_DETECT`/`RUNG_*_GUIDE` set). No `TBD`.
- [ ] Write `examples/blender.md`: a short pointer that names the worked instance repo (`/Users/bra0002h/mcp-servers/blender-mcp/`), links the upstream fix PR (from Workstream A), lists the Blender values for every manifest token (so a reader sees a fully-worked instantiation), and notes the Blender-specific gotchas (add-on is a separate installed copy + not-hot-reloadable → user-in-loop reload; `uvx blender-mcp` must match the `~/.claude.json` entry; PolyHaven downloads need network → INCONCLUSIVE offline; `set_texture` fixed by Workstream A).
- [ ] Write the completeness gate `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/tests/test_manifest_complete.py` with these exact contents:
```python
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
```
- [ ] Run the FULL suite (all tests, all tasks) and confirm green: run `cd /Users/bra0002h/ClaudeWorkspace/mcp-smoke-test && python3 -m pytest tests/ -q`. Expected: all tests pass (Task 1–6 combined). This is the completeness gate for the skill's content.
- [ ] Commit: run `cd /Users/bra0002h/ClaudeWorkspace/mcp-smoke-test && git add -A && git commit -q -m "$(printf 'Workstream C Task 6: placeholder manifest + blender example + completeness gate\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"`. Expected: commit succeeds.

---

## Task 7 — Publish to the canonical `haiggoh` marketplace

**Files:**
- Modify `/Users/bra0002h/ClaudeWorkspace/claude-code-desktop-sync/.claude-plugin/marketplace.json` (add ONE entry — in place)
- Create the GitHub repo `haiggoh/mcp-smoke-test` (via `gh`)

**Interfaces:**
- Consumes: `gh` auth as `haiggoh`; the canonical marketplace.
- Produces: a published, installable `mcp-smoke-test@haiggoh` plugin.

Steps:
- [ ] Confirm `gh` identity: run `gh auth status 2>&1 | grep -i "account haiggoh"`. Expected: a line confirming `haiggoh` is logged in. If not, STOP.
- [ ] Push a README + LICENSE if absent (siblings ship both): ensure `/Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/README.md` (install instructions: `/plugin marketplace add haiggoh/claude-code-desktop-sync` then `/plugin install mcp-smoke-test@haiggoh`) and `LICENSE` (MIT) exist; create them if missing, then commit with the standard trailer.
- [ ] Create the public repo and push `main`: run `cd /Users/bra0002h/ClaudeWorkspace/mcp-smoke-test && gh repo create haiggoh/mcp-smoke-test --public --source=. --remote=origin --push`. Expected: repo created and `main` pushed; note the URL `https://github.com/haiggoh/mcp-smoke-test`.
- [ ] Confirm no per-plugin marketplace was shipped: run `test ! -f /Users/bra0002h/ClaudeWorkspace/mcp-smoke-test/.claude-plugin/marketplace.json && echo OK`. Expected: `OK`.
- [ ] Add ONE entry to the canonical marketplace **in place** (Edit tool, preserving file mode), in the `plugins[]` array of `/Users/bra0002h/ClaudeWorkspace/claude-code-desktop-sync/.claude-plugin/marketplace.json`, exactly:
```json
{
  "name": "mcp-smoke-test",
  "source": { "source": "url", "url": "https://github.com/haiggoh/mcp-smoke-test.git" },
  "description": "Onboard and verify any MCP that drives an external app: smoke test, functional capability probe, evidence-based manual, and interactive prereq-ladder guide — with parametrized templates.",
  "category": "productivity",
  "tags": ["skill", "mcp", "testing", "probe", "onboarding"]
}
```
- [ ] Validate the marketplace JSON still parses: run `python3 -c "import json; json.load(open('/Users/bra0002h/ClaudeWorkspace/claude-code-desktop-sync/.claude-plugin/marketplace.json')); print('VALID')"`. Expected: `VALID`.
- [ ] Commit + push the sync repo: run `cd /Users/bra0002h/ClaudeWorkspace/claude-code-desktop-sync && git add .claude-plugin/marketplace.json && git commit -q -m "$(printf 'Add mcp-smoke-test to canonical marketplace\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')" && git push`. Expected: pushed.
- [ ] **[USER-IN-LOOP]** Refresh + install from within Claude Code (these are `/plugin` slash commands, not bash): tell the user to run `/plugin marketplace update haiggoh` then `/plugin install mcp-smoke-test@haiggoh`. Expected: the skill appears in the skills list. Verify afterward by asking the user to confirm `mcp-smoke-test` is listed, or check the installed marketplace cache under `~/.claude/plugins/`.
- [ ] Record the published version and PR/link cross-references in `examples/blender.md` and commit (version-bump rule: this is `0.1.0`; any later change bumps `.claude-plugin/plugin.json`). Expected: final commit on `main`, working tree clean (`git status -s` empty).

---

## Done criteria

- `python3 -m pytest tests/ -q` is green: plugin.json + SKILL.md validity, SKILL.md required sections, all five templates round-trip-reproduce their proven Blender source, no stray TODO markers, and the placeholder manifest exactly matches the tokens used.
- The skill installs from the canonical `haiggoh` marketplace and appears in the skills list.
- `examples/blender.md` documents a fully-worked instantiation (every token → its Blender value) and the Blender gotchas.
- No per-plugin `marketplace.json` shipped; `.claude-plugin/plugin.json` version is set and the version-bump rule is recorded.
