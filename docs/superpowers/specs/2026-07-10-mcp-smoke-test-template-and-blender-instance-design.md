# MCP Smoke-Test Template + Blender-MCP Instance — Design

**Date:** 2026-07-10
**Status:** Approved (design); pending implementation plan
**Author:** Claude (with user)

---

## 1. Overview

We are turning the ad-hoc "manual + capability probe + interactive setup walk" approach we
built for the **Adobe Photoshop MCP** into a **reusable, MCP-agnostic template delivered as a
Claude skill**, and simultaneously producing its **first worked instance for the Blender MCP**
(`ahujasid/blender-mcp`). Along the way we fix a real Blender-MCP bug (`set_texture` on
Blender 4.0+) and publish it upstream.

This is three workstreams:

- **A. Fix + upstream PR** — version-safe fix for the `set_texture` `ShaderNodeSeparateRGB` bug.
- **B. Blender test artifacts** — the concrete instance: launcher, probe, capabilities manual,
  project notes, and the **interactive setup guide** (built here first).
- **C. Reusable template as a skill** — `mcp-smoke-test`, carrying the playbook + parametrized
  templates that future MCPs instantiate. (Approach #1: skill-embedded templates, no shared
  runtime library yet.)

### Goals
- A merged-or-mergeable upstream PR that fixes `set_texture` on Blender 4.0+ **without breaking
  pre-4.0 users**.
- A repeatable, functionally-verified smoke test + capability probe for the Blender MCP.
- An **interactive guide** that walks a user from "nothing connected" to "all green," re-checking
  after each step — the repeatable form of what we did live on 2026-07-10.
- A skill that makes the *next* MCP faster by encoding the method + templates.

### Non-goals (YAGNI)
- No shared `mcp_probe` Python library yet (revisit after 2–3 instances — see §6).
- No cookiecutter/standalone template repo.
- No changes to Blender-MCP behavior beyond the `set_texture` fix.
- Not enabling/keying the optional integrations (Sketchfab/Hyper3D/Hunyuan) — out of scope.

---

## 2. Background & confirmed facts (2026-07-10)

- **Blender present:** 5.1.2 only (`~/Library/Application Support/Blender/5.1/`).
- **Running add-on is a COPY:** `~/Library/Application Support/Blender/5.1/scripts/addons/addon.py`
  — installed via "Install from Disk", *distinct* from the source at
  `~/ClaudeWorkspace/blender-mcp/addon.py`. Editing the source does NOT change the running add-on.
- **Not a git clone:** `~/ClaudeWorkspace/blender-mcp/` holds only the loose `addon.py`. The MCP
  *server* runs via `uvx blender-mcp`.
- **The bug:** `addon.py:1067` `nodes.new(type='ShaderNodeSeparateRGB')` inside `set_texture`
  (def at :878), used to split the packed ARM map (AO/Roughness/Metallic).
- **Root cause (verified):** Blender 4.0 removed `ShaderNodeSeparateRGB` (renamed to
  `ShaderNodeSeparateColor`, added in 3.3). Probe on 5.1.2: `SeparateRGB` unavailable,
  `SeparateColor` available. Socket sockets differ: RGB input `Image`, outputs `R/G/B`;
  Color input `Color`, outputs `Red/Green/Blue`.
- **`download_polyhaven_asset` works** and already builds a valid material; only the separate
  `set_texture` re-wiring step breaks. Direct material assignment is the current workaround.
- **`gh` authed as `haiggoh`** (`repo`, `workflow` scopes) → can fork + PR.
- **Smoke test 2026-07-10 (PASS):** connection, `get_scene_info`, `get_object_info`,
  `execute_blender_code` (create mesh/material/modifier), `get_viewport_screenshot`,
  PolyHaven search + download. Optional integrations off (need keys).

### Adobe template shape we are generalizing (`~/mcp-servers/adobe-mcp/`)
- `probe-capabilities.py` — functional probe, WORKS/PARTIAL/BROKEN/INCONCLUSIVE, real assertions
  (bounds deltas), stderr drained, fail-fast on stall.
- `test-photoshop.sh` — smoke (read-only connectivity) vs `--capabilities` (full probe); prints
  app version; reuses/starts proxy with EXIT-trap cleanup.
- `PHOTOSHOP-MCP-CAPABILITIES.md` — evidence-based manual (verification status, working, broken,
  practical guidance, required setup, update route).
- `PROJECT-NOTES.md` — running record + plan; frames the diff surface (novel additions vs
  upstreamable bug fixes) for publishing.
- **Interactive guide** — *planned in Adobe PROJECT-NOTES §5.2, not yet built.* We build it first
  for Blender.

---

## 3. Workstream A — Fix + upstream PR

### 3.1 The fix (version-guarded)
Replace the unconditional `SeparateRGB` node creation with a runtime branch on `bpy.app.version`
so pre-4.0 behavior is untouched:

```python
# Handle ARM texture (Ambient Occlusion, Roughness, Metallic)
if 'arm' in texture_nodes:
    if bpy.app.version >= (4, 0):
        sep = nodes.new(type='ShaderNodeSeparateColor')  # 4.0+ : SeparateRGB removed
        in_socket, ch_r, ch_g, ch_b = 'Color', 'Red', 'Green', 'Blue'
    else:
        sep = nodes.new(type='ShaderNodeSeparateRGB')     # <4.0 : original node, untouched
        in_socket, ch_r, ch_g, ch_b = 'Image', 'R', 'G', 'B'
    sep.location = (-200, -100)
    links.new(texture_nodes['arm'].outputs['Color'], sep.inputs[in_socket])
    # ...use ch_g (Roughness), ch_b (Metallic), ch_r (AO) below instead of literal 'G'/'B'/'R'
```

All downstream references to `separate_rgb.outputs['G'|'B'|'R']` become the `ch_*` variables.
`ShaderNodeSeparateColor` defaults to `mode='RGB'`, which is what we need (no extra config).

**Audit note:** grep the whole `set_texture` body for every `separate_rgb`/`outputs['R'|'G'|'B']`
reference (the read showed uses through ~:1094; there is an AO `R` use further down) and convert
each. The implementation plan must enumerate them from the actual file, not from this excerpt.

### 3.2 Local application + verification
1. Apply the fix to the **source** clone (§3.3) AND the **running copy**
   `~/Library/Application Support/Blender/5.1/scripts/addons/addon.py` (in-place edit to preserve
   the file; per the preserve-permissions rule).
2. Reload in Blender: disable/re-enable the "Interface: Blender MCP" add-on (or restart Blender),
   then re-click "Connect to Claude" (socket re-opens on 9876).
3. Re-run the 2026-07-10 texture test: create plane → `download_polyhaven_asset(dark_wood, 1k)`
   → `set_texture` → expect success (no `ShaderNodeSeparateRGB undefined`) → screenshot shows
   wood with ARM-driven roughness/AO → clean up.

*Blender add-on reload is the analog of Adobe's §6 edit↔reload loop: no hot-reload; the user (or a
scripted disable/enable) must reload before re-testing.*

### 3.3 Upstream PR
1. Clone `ahujasid/blender-mcp` → `~/mcp-servers/blender-mcp/` (matches Adobe home).
2. `gh repo fork` under `haiggoh` (already authed).
3. Branch `fix/set-texture-bl4-separate-color`.
4. Apply the version-guarded fix; commit with a message explaining the 3.3/4.0 node history and
   why the guard (not a blind swap) is correct for all versions.
5. `gh pr create` to `ahujasid/blender-mcp` with a clear reproduction (Blender 5.x, any PolyHaven
   texture with an ARM map → `set_texture` → `ShaderNodeSeparateRGB undefined`) and the fix
   rationale. Note it is additive/backward-compatible.

---

## 4. Workstream B — Blender test artifacts (first instance)

Home: `~/mcp-servers/blender-mcp/` (the clone from §3.3). Each artifact mirrors an Adobe one,
adapted to Blender's transport.

### 4.1 Transport model
The Blender probe spawns the **MCP server** (`uvx blender-mcp`) and speaks **stdio JSON-RPC** to
it (same pattern as the Adobe probe spawning `adobe-photoshop`), rather than opening the raw
`localhost:9876` socket directly. Rationale: it tests the *same path Claude uses* (MCP server →
add-on socket), and keeps the probe transport-consistent with Adobe so the template generalizes.
The server in turn requires Blender running with the add-on's socket server listening on 9876.

### 4.2 `test-blender.sh`
- **smoke (default):** read-only connectivity — call `get_scene_info`; a healthy result returns
  the scene. Absence of a listening 9876 / "connection refused" = add-on not connected.
- **`--capabilities`:** runs the full probe (§4.3).
- Prints detected Blender version(s) from `~/Library/Application Support/Blender/*/`.
- EXIT-trap cleanup of any process it spawns (Adobe §10 lesson: never leak spawned MCP servers;
  kill the process group).

### 4.3 `probe-capabilities.py` (Blender)
- Spawns `uvx blender-mcp`, JSON-RPC `initialize` → `tools/call` per capability.
- **Functional classification** (not "no error"): e.g.
  - `execute_blender_code` add-cube → assert object count increased.
  - material/modifier build → assert node count / modifier present.
  - `download_polyhaven_asset` (1k) → assert material created with expected maps.
  - `set_texture` → assert applied without exception AND ARM split node present (post-fix).
  - `get_viewport_screenshot` → assert non-empty image bytes.
- **Reliability rules baked in (Adobe §10 + [[unread-stderr-pipe-deadlock]]):**
  1. Drain server stderr to a file (`_stderr_sink`) — never leave `stderr=PIPE` unread.
  2. Fail-fast: abort on 2nd consecutive call timeout with a clear "stalled — check
     Blender/add-on/connection" message; never keep stamping BROKEN.
  3. Wall-clock stall guard per op.
  4. `try/finally` terminate the subprocess; EXIT-trap in the launcher.
  5. Clean up scene artifacts it creates (restore to prior object set).
- Writes `capability-report.json` (machine-readable: name → verdict + evidence).

### 4.4 `BLENDER-MCP-CAPABILITIES.md`
Manual seeded with the 2026-07-10 results and the `set_texture` finding. Sections mirror Adobe:
verification status (date, Blender/add-on versions, network context), headline ("is X viable
now?"), confirmed WORKING, confirmed BROKEN/PARTIAL (with `set_texture` pre/post-fix + workaround),
practical guidance, required setup, and an **update route** (re-run `--capabilities`; the report
is the source of truth; edit this doc from it).

### 4.5 `PROJECT-NOTES.md`
Running record + plan. Frames the diff surface for publishing: **novel additions** (probe,
launcher, manual, interactive guide) vs **upstreamable bug fix** (`set_texture`). Tracks PR status
and the two-tier testing framing (§4.6).

### 4.6 Two-tier testing (framing, from Adobe §7)
- **Unit** = the probe (per-command, functional, deterministic).
- **Integration/e2e** = a small real scene goal (e.g. textured plane + primitive + PolyHaven
  material + screenshot) that exercises the toolset together. Defined here, not necessarily
  automated this round.

### 4.7 Interactive setup guide (**built first here**)
When a prereq is not ready, drop into an interactive walk that guards **each prereq in order**,
re-checking after each user confirmation, looping until all green:

1. **blender MCP server enabled in Claude?** Detect via `~/.claude.json` `disabledMcpServers`
   (project scope). If disabled → tell the user to run `/mcp` and enable it. (Machine-detectable.)
2. **Blender running?** Detect the process. If not → ask the user to launch Blender.
3. **Add-on installed + enabled?** ("Interface: Blender MCP".) If a connection attempt fails and
   the add-on file is present but not enabled → guide: Preferences → Add-ons → enable. (Enablement
   is in-app; guide + confirm.)
4. **"Connect to Claude" listening on 9876?** Detect the listening socket. If not → guide: N-panel
   → BlenderMCP tab → "Connect to Claude"; then re-check.
5. **(Optional) integrations** — report PolyHaven on / Sketchfab/Hyper3D/Hunyuan off; offer the
   enable steps only if the user wants them.

**Detection vs guidance boundary:** steps machine-detectable from disk/process/socket
(1, 2, 4, and the presence half of 3) are auto-checked; purely in-app actions (add-on *enable*,
clicking Connect, entering keys) are guided with a prompt-and-confirm, then re-tested. Loop until
green. This lives as a documented flow the skill (Workstream C) drives — initial form can be a
guided runbook the assistant executes; a scripted `--setup` mode is a possible enhancement.

---

## 5. Workstream C — Reusable template as a skill (`mcp-smoke-test`)

Home: `~/ClaudeWorkspace/mcp-smoke-test/` (this repo).

### 5.1 Structure (Approach #1 — skill-embedded templates)
```
mcp-smoke-test/
  SKILL.md                     # the playbook (method + when-to-use)
  templates/
    test-APP.sh.tmpl           # launcher skeleton (smoke vs --capabilities)
    probe-capabilities.py.tmpl # generic stdio-JSON-RPC probe engine + reliability rules
    APP-MCP-CAPABILITIES.md.tmpl
    PROJECT-NOTES.md.tmpl
    interactive-guide.md.tmpl  # ordered prereq checklist w/ detect-vs-guide markers
  docs/superpowers/specs/…     # this spec
  examples/
    blender.md                 # pointer to ~/mcp-servers/blender-mcp as the worked instance
```

### 5.2 What the SKILL.md encodes (the durable value = method)
- **When to use:** onboarding/verifying any MCP that drives an external app.
- **The prereq-ladder pattern** (detect-then-guide, loop-until-green) generalized: MCP-enabled-in-
  Claude → app-running → plugin/add-on installed+enabled → bridge/socket connected → optional
  features. Each instance fills in *how* to detect/guide each rung.
- **Functional-verification rule:** classify WORKS/PARTIAL/BROKEN by an assertion that can fail,
  never by "no exception."
- **Probe-reliability rules** (drain stderr; fail-fast on stall; terminate subprocess; clean up
  artifacts; no concurrent MCP calls during a probe) — the hard-won Adobe §10 lessons as rules.
- **Publish framing:** separate *novel additions* (probe/manual/guide) from *upstreamable bug
  fixes*; version-guard fixes for backward compatibility.
- **Instantiation procedure:** copy templates → fill placeholders (APP name, MCP server binary,
  prereq specifics, functional assertions) → seed the manual from a first probe run.

### 5.3 Placeholders the templates expose
`APP` (photoshop/blender/…), MCP server launch command, transport notes, the ordered prereq list
with per-rung detect/guide, and the per-command functional assertions.

### 5.4 Publishing the skill
Follow [[plugin-publishing-workflow]]: ONE canonical marketplace (the sync repo); add an entry,
bump version, `marketplace update`. Blender instance references the skill as `examples/blender.md`.

---

## 6. Future work (explicitly deferred)
- Promote the generic probe engine into a shared `mcp_probe` library (Approach #2) once 2–3
  instances reveal the truly-common core. Skill's `probe-capabilities.py.tmpl` is the staging
  ground.
- Scripted `--setup` interactive mode (vs assistant-driven runbook).
- Back-port the interactive guide into the Adobe repo (closes Adobe PROJECT-NOTES §5.2).

---

## 7. Sequencing & dependencies
1. **A.3 clone + A.1 fix** (unblocks everything Blender-side).
2. **A.2 local verify** (proves the fix; needs Blender reload — user-in-loop).
3. **B** artifacts in the clone (probe reuses the transport; manual seeded from a probe run).
4. **C** skill: extract templates from the Blender artifacts once they're proven (Blender is the
   reference; generalize from a working instance, not in the abstract).
5. **A.3 PR** can go out as soon as the fix is verified (step 2), in parallel with B/C.

Order rationale: build the concrete instance first, then generalize from what actually worked —
mirrors the YAGNI stance and avoids freezing a template before it's validated.

---

## 8. Risks & open questions
- **Add-on reload requires the user** (in-app enable/connect). The local verify (A.2) and any
  interactive-guide testing need user-in-loop confirmations.
- **`uvx blender-mcp` in the probe** must use the same server the Claude MCP config uses; confirm
  the invocation/version to avoid testing a different build than Claude drives.
- **`set_texture` downstream references:** enumerate ALL `separate_rgb.outputs[...]` uses from the
  real file during implementation (excerpt in §3.1 is partial).
- **PolyHaven downloads hit the network** — the probe's `download_polyhaven_asset` test needs
  connectivity; mark INCONCLUSIVE (not BROKEN) if offline.
- **Only Blender 5.1 is installed** — the pre-4.0 branch of the fix can be reasoned about and
  code-reviewed but not locally exercised; call this out in the PR.
