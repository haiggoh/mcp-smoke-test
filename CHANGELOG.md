# Changelog

## [0.2.3] — 2026-11-13

### Fixed (desktop-migration FLEET Phase 1 P0)

- **The probe's helper closure now ships.** New `templates/probe_helpers.py.tmpl`
  (unwrap/classify/`owned_new`/summary): a fresh instantiation no longer dies on
  `ModuleNotFoundError: probe_helpers` — the helper existed only at the proven Blender instance.
- **The smoke launcher checks `result.isError`.** An MCP application error whose text does not
  start with "error" no longer reads SMOKE PASS (negative control: a stub server answering
  `isError=true` with "Blender plugin not connected: …" previously printed SMOKE PASS; it now
  fails with exit 1). A failing smoke still prints the stderr-log pointer — the `set -e` abort
  used to swallow exactly that hint.
- **Mutating tools are never blind-retried on a lost response** (`call(..., mutating=True)`): the
  first execution may have landed; a retry double-applies the mutation and the app's auto-rename
  (`ASSERT_CUBE.001`) leaks the duplicate past name-based cleanup. The state delta decides the
  verdict instead; read-only calls keep the retry-once/fail-fast rule.
- **Cleanup is ownership-aware** (`owned_new`): artifacts are tracked only when absent before and
  present after the call — a pre-existing user material (e.g. `dark_wood`) is never deleted by
  the probe's cleanup.
- **Every probe call is gated on the server's `tools/list`** (NOT-DECLARED): an undeclared tool is
  skipped with a reason instead of a validation error masquerading as a capability verdict.
- **Templates carry no personal paths**: `REPO`/`PROBE_REPO_DIR`, `SMOKE_ARGS` and
  `SMOKE_STDERR_LOG` are tokens now; the launcher spawns the server with the documented
  `MCP_SERVER_ENV` dict (it previously hardcoded a PATH-only env).
- **The suite is self-contained**: the round-trip checks skip with a reason when the proven
  Blender instance is absent (`MCP_SMOKE_INSTANCE_DIR` overrides; an explicit override that does
  not exist fails loudly), and the probe engine and launcher are additionally exercised offline
  against stub stdio MCP servers (10 new tests, watched red against the unfixed code first).
- The proven Blender instance files were updated in lockstep (template↔instance round-trip
  holds): instance helper tests 15/15, repo suite 32/32.

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
