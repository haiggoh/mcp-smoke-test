---
name: mcp-smoke-test
description: Use when onboarding, smoke-testing, or verifying an MCP server that drives an external desktop app (Blender, Photoshop, Premiere, InDesign, Illustrator, and similar) — when you need to confirm the whole pipe is live, functionally probe each tool for what actually works vs silently no-ops, produce an evidence-based capabilities manual, or walk a user from "nothing connected" to "all green" via an interactive prereq ladder. Also use when generalizing that method to a new MCP by instantiating the bundled templates.
---

# MCP Smoke-Test Playbook

A repeatable method for taking any MCP server that drives an **external desktop app** from
"is this even connected?" to a trustworthy, evidence-based map of what it can and cannot do.
Born from the Adobe Photoshop MCP work and first generalized against the Blender MCP
(`ahujasid/blender-mcp`) — see `examples/blender.md` for the fully-worked instance.

The durable value here is the **method**, not any one script. The `templates/` are a proven
starting point you instantiate per MCP; the deep, per-tool logic is inherently rewritten for each
app, but the engine, the reliability rules, and the ladder pattern carry over unchanged.

## When to use

Reach for this skill when you are onboarding or auditing an MCP that relays to an external app and
you need any of these four deliverables:

1. **A repeatable smoke test** — one read-only round-trip that proves the whole pipe is alive
   (Claude → MCP server → app bridge → app), fast, with an actionable failure hint.
2. **A functional capability probe** — per-tool verdicts (WORKS / PARTIAL / BROKEN / INCONCLUSIVE)
   established by assertions that can actually fail, written to a machine-readable report.
3. **An evidence-based capabilities manual** — a human-readable snapshot seeded from a probe run:
   what works, what's broken, workarounds, required setup, and how to refresh it.
4. **An interactive setup guide** — an ordered prereq ladder that walks a user from nothing
   connected to all-green, re-checking after each step.

## When NOT to use

Not for MCPs that are pure HTTP/API wrappers with no external app and no local bridge — there is
no "is the app running / is the panel connected" ladder to climb, and a normal integration test
suffices. This skill earns its keep when a **stateful external app + a local socket/panel/add-on**
sits between Claude and the result.

## The prereq ladder

Every app-driving MCP has the same shape of prerequisites; only the *how* differs. Climb them in
order, and after any user action **re-detect** before advancing. Each rung is either **DETECT**
(machine-checkable — you run a command) or **GUIDE** (an in-app action the user must take — prompt,
wait for confirmation, re-check). Never advance past a red rung; if a later rung fails, drop back
to the lowest failing one.

1. **MCP enabled in Claude** *(DETECT)* — the server isn't disabled for this project. Detect via
   `~/.claude.json` (`projects.<cwd>.disabledMcpServers`); confirm the user-scope `mcpServers`
   entry exists.
2. **App running** *(DETECT)* — the desktop app process is up (`pgrep`).
3. **Plugin / add-on installed + enabled** *(DETECT presence / GUIDE enablement)* — the bridge
   plugin file is present on disk (detectable); the *enabled* checkbox usually is not (proven only
   by rung 4 succeeding).
4. **Bridge / socket connected** *(DETECT)* — the app is listening on its bridge port (`lsof`), i.e.
   the user clicked the app's "Connect" affordance.
5. **Optional features** *(DETECT status / GUIDE enablement)* — integrations gated by toggles and/or
   API keys; report state, guide enablement only on request.

The single end-to-end green signal is the smoke test passing. Each instance fills in the exact
detect command and guide text per rung — the interactive-guide template is where that lives.

## Functional verification

The core rule: **classify by an assertion that can fail, never by "the call returned without an
error."** Return status lies for exactly the broken commands you care about. For each tool:

- Snapshot an observable piece of state **before**, run the tool, snapshot **after**, and require
  the expected delta. Examples: object count +1 after an add; opaque-area shrink after a cutout;
  PNG/image bytes present after a screenshot; a node of the expected type present after a material
  op; a reported flag matching the live toggle.
- **WORKS** = call ok AND the state changed as expected. **PARTIAL** = call ok but the change did
  not happen. **BROKEN** = the call did not report success.
- Reserve **INCONCLUSIVE** for when the *verification read itself* was unavailable (you can't trust
  the verdict either way) — e.g. the state-reading call failed, or a network dependency was offline.
- Prefer an independent measurement path for the "after" read (e.g. run code in the app to count
  objects) rather than trusting the same tool's self-report.

Add instance-specific statuses only when they carry real meaning — e.g. Blender needed
`FIXED-PENDING-RELOAD` (the fix is on disk but the running add-on hasn't been reloaded).

## Probe-reliability rules

These are hard-won; ignore them and the probe lies or hangs:

- **Drain the server's stderr to a FILE, never an unread `PIPE`.** A verbose MCP server fills the
  ~64KB OS pipe buffer after ~a dozen commands and then blocks on its next stderr write — a classic
  unread-pipe deadlock that masquerades as "stalls after ~13 commands." A file sink never blocks
  and stays inspectable. (`DEVNULL` or a reader thread also work; a file is the most debuggable.)
- **One `tools/call` at a time.** Never fire overlapping requests; the relayed app socket is
  typically per-call. Pace calls slightly if the transport connects/disconnects per call.
- **Retry a no-response once, then fail-fast.** A single missed response is usually a transient
  transport hiccup (the hung call never executed). A *second consecutive* timeout is a real stall —
  write a partial report marked `aborted`, `stdout.flush()` (because `os._exit` skips buffer flush),
  and hard-exit. Never let one stall stamp every downstream command BROKEN (that manufactures false
  cascades).
- **Terminate the spawned server in `finally`,** and clean up every artifact the probe created in
  the app (objects, materials, documents, temp files) — restore the pre-probe state.
- **Plugins/add-ons don't hot-reload.** After a bridge-plugin code change, the user must reload it
  in-app; mark those steps user-in-loop, and don't reload over the very socket you're driving.
- **Spawn the SAME server Claude uses** (same command + env as the `~/.claude.json` entry), or the
  verdicts won't reflect Claude's real path.
- **Pass whatever arguments the server requires on every call** (e.g. some servers require a
  `user_prompt` field) — a validation error is not a capability verdict.

## Publish framing

Keep two categories strictly separate when deciding what to ship:

- **Upstreamable bug fixes** — defects in the MCP/add-on itself. Fix them **backward-compatibly**
  (e.g. version-guard an API change rather than a blind swap) and PR them upstream, scoped tight.
- **Novel additions** — the smoke test, probe, manual, and interactive guide. These are *your*
  tooling; they generalize into this skill, they do **not** belong in the upstream add-on PR.

Publish the skill itself through the ONE canonical `haiggoh` marketplace (never ship a per-plugin
`marketplace.json`), and bump `.claude-plugin/plugin.json`'s version on every published change.

## Instantiation procedure

To onboard a new MCP (call it `APP`):

1. Copy the five templates from `templates/` into the new instance repo, renaming `APP`/`test-APP`
   to the app:
   - `test-APP.sh.tmpl` — the launcher (smoke vs `--capabilities`).
   - `probe-capabilities.py.tmpl` — the stdio-JSON-RPC probe engine + a worked `run_probe` example.
   - `APP-MCP-CAPABILITIES.md.tmpl` — the evidence-based manual skeleton.
   - `PROJECT-NOTES.md.tmpl` — the running record / diff-surface / two-tier-testing skeleton.
   - `interactive-guide.md.tmpl` — the prereq-ladder walkthrough.
2. Fill the `{{PLACEHOLDER}}` tokens with the new MCP's values (see
   `templates/placeholder-manifest.md` for the full list, meanings, and the Blender example values).
3. Rewrite `run_probe`'s per-tool assertions for the new app's tools (the engine stays as-is).
4. Run the probe once and **seed the manual from that first report** — do not hand-write verdicts.
5. Climb the interactive guide's ladder to get to all-green, filling each rung's detect/guide.

See `examples/blender.md` for a complete worked instantiation with every token's Blender value.
