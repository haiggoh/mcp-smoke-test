# mcp-smoke-test

A Claude Code skill for onboarding and verifying any **MCP server that drives an external desktop
app** (Blender, Photoshop, Premiere, InDesign, Illustrator, …). It packages a repeatable method plus
parametrized templates for four deliverables:

1. **Smoke test** — one read-only round-trip proving the whole pipe is live, with an actionable
   failure hint.
2. **Functional capability probe** — per-tool verdicts (WORKS / PARTIAL / BROKEN / INCONCLUSIVE)
   established by assertions that can actually fail, not by "the call didn't error."
3. **Evidence-based capabilities manual** — a human-readable snapshot seeded from a probe run.
4. **Interactive setup guide** — an ordered prereq ladder (detect → guide → re-check, loop until
   all-green).

The durable value is the **method** (`skills/mcp-smoke-test/SKILL.md`); the `templates/` are a proven
starting point you instantiate per MCP. The first fully-worked instance is the Blender MCP — see
`skills/mcp-smoke-test/examples/blender.md`.

## Install

This plugin is published through the canonical `haiggoh` marketplace (the
`claude-code-desktop-sync` repo). In Claude Code:

```
/plugin marketplace add haiggoh/claude-code-desktop-sync
/plugin install mcp-smoke-test@haiggoh
```

(Or with the CLI: `claude plugin marketplace update haiggoh` then
`claude plugin install mcp-smoke-test@haiggoh`.)

## Layout

```
.claude-plugin/plugin.json          # manifest
skills/mcp-smoke-test/
  SKILL.md                          # the playbook (method)
  templates/                        # instantiate these per MCP
    test-APP.sh.tmpl
    probe-capabilities.py.tmpl
    APP-MCP-CAPABILITIES.md.tmpl
    PROJECT-NOTES.md.tmpl
    interactive-guide.md.tmpl
    placeholder-manifest.md
  examples/blender.md               # the worked Blender instance
tests/                              # round-trip + validity tests (pytest)
```

## Tests

```
pytest tests/ -q
```

The tests enforce that each template round-trips (instantiating it with the Blender parameter set
reproduces the proven Blender artifact byte-for-byte) and that the placeholder manifest documents
exactly the tokens the templates use.

## License

MIT — see [LICENSE](LICENSE).
