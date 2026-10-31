# Changelog

## [0.2.2] — 2026-10-31

### Changed
- The plugin description (plugin.json, and the marketplace listing it feeds) is rewritten to describe
  the plugin's full current capabilities.

## [0.2.1] — 2026-10-30 — 🔌: the credit-moment mark on the plugin's surfaces

- The repo's GitHub About emoji (🔌) now leads what the user and model read at the plugin's
  credit moments (plan 2026-10-28, §Wave 2 Task 7): the SKILL.md gains a ≤3-line Branding
  section (lead the reply after `/mcp-smoke-test` with `🔌 mcp-smoke-test:`), the
  capabilities-manual template's h1 carries the mark — and its proven Blender instance follows
  via the template↔instance round-trip test (edited in lockstep, `~/mcp-servers/blender-mcp`),
  the plugin.json description, and the README h1.
- The probe's machine-readable report stays unbranded (JSON output, consumed by tooling).
- New tests/test_branding.py pins every surface with exact strings.
- First CHANGELOG file for this repo (created with this entry; the version gate reads it).
