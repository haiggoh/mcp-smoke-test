# set_texture Blender 4.0+ Version-Guard Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Fix the `set_texture` `ShaderNodeSeparateRGB` crash on Blender 4.0+ with a runtime version guard that leaves pre-4.0 behavior untouched, verify it live on Blender 5.1, and publish an upstream PR to `ahujasid/blender-mcp`.

**Architecture:** The bug lives in the `blender-mcp` Blender add-on (`addon.py`), inside `set_texture`'s ARM (Ambient-Occlusion/Roughness/Metallic) channel-split block. Blender 4.0 removed `ShaderNodeSeparateRGB` (renamed to `ShaderNodeSeparateColor` in 3.3) with different socket names, so the unconditional node creation throws on 4.0+. The fix branches on `bpy.app.version`: `ShaderNodeSeparateColor` (input `Color`, outputs `Red`/`Green`/`Blue`) on 4.0+, original `ShaderNodeSeparateRGB` (input `Image`, outputs `R`/`G`/`B`) below. There are three copies of the file — a loose SOURCE copy, an UPSTREAM git clone (fork), and the RUNNING copy Blender actually loads — and the fix must reach all three, with the running copy patched in place to preserve permissions.

**Tech Stack:** Python (Blender `bpy` API), `git`, `gh` CLI (authed as `haiggoh`), Blender 5.1.2 with the "Interface: Blender MCP" add-on, `uvx blender-mcp` MCP server over stdio, the Blender MCP tools (`execute_blender_code`, `download_polyhaven_asset`, `set_texture`, `get_viewport_screenshot`, `get_scene_info`, `get_object_info`).

> **Execution refinements (added 2026-07-12 during recovery — apply when executing):**
> 1. **Decouple the upstream PR from the critical path.** Open the `ahujasid/blender-mcp` PR immediately after the fix is verified live, then proceed to Workstreams B and C without waiting on maintainer review — the PR is off the critical path. If Workstream B's probe later surfaces *unrelated* add-on bugs, file them as SEPARATE follow-up PRs; do not expand or delay this focused, backward-compatible `set_texture` PR.
> 2. **Verify by direct node-logic execution, not by hot-reloading the live add-on.** The running add-on cannot be safely hot-reloaded over its own MCP socket (disabling/re-enabling it drops the port-9876 channel we drive it through). So prove correctness on Blender 5.1 by running the fixed, version-guarded ARM-split logic directly via `execute_blender_code` against a real downloaded PBR material (assert AO/Roughness/Metallic wire through `ShaderNodeSeparateColor` and the material renders), and patch all three `addon.py` copies. The end-to-end `set_texture` *MCP-tool* call needs a natural Blender restart / add-on re-enable and is an OPTIONAL follow-up — it does not gate completion, because the fix is proven by direct execution. (Live-confirmed 2026-07-12: `bpy.app.version==(5,1,2)`, `ShaderNodeSeparateRGB` absent, `ShaderNodeSeparateColor` present.)

## Global Constraints

These rules apply project-wide to every task in this plan. Follow them verbatim.

- **Blender version-guard logic (the core correctness invariant):** The fix MUST be a runtime branch on `bpy.app.version`. If `bpy.app.version >= (4, 0)`: use `ShaderNodeSeparateColor` with input socket `'Color'` and output sockets `'Red'`/`'Green'`/`'Blue'`. Else (pre-4.0): use `ShaderNodeSeparateRGB` with input socket `'Image'` and output sockets `'R'`/`'G'`/`'B'`. **The pre-4.0 code path MUST remain byte-for-byte behaviorally identical to the original** — same node type, same socket names, same wiring. `ShaderNodeSeparateColor` defaults to `mode='RGB'` (no extra configuration needed). Never do a blind swap that drops the pre-4.0 node; it is additive and backward-compatible by construction.
- **Three file copies, do not confuse them:**
  - SOURCE (loose copy, no git): `/Users/bra0002h/ClaudeWorkspace/blender-mcp/addon.py`
  - UPSTREAM clone/fork (git, for the PR): `/Users/bra0002h/mcp-servers/blender-mcp/` → `addon.py`
  - RUNNING copy Blender loads: `/Users/bra0002h/Library/Application Support/Blender/5.1/scripts/addons/addon.py`
  - Editing SOURCE does NOT change the RUNNING copy. The RUNNING copy must be patched separately, in place, to be exercised live.
- **Preserve file permissions on in-place edits:** When patching the RUNNING copy and the SOURCE copy, use in-place edits (the Edit tool) that keep the inode's mode. Do NOT redirect-and-move (`... > tmp && mv tmp file`) or plain `> file` recreation — that recreates the file at the default umask and can widen permissions. Eyeball `ls -l` before/after any sensitive rewrite.
- **gh account = `haiggoh`:** `gh` is authenticated as `haiggoh` with `repo` + `workflow` scopes. All fork/PR operations run under this account. The PR targets `ahujasid/blender-mcp`.
- **Branch name (exact):** `fix/set-texture-bl4-separate-color`.
- **Only Blender 5.1 is installed:** The 4.0+ branch is exercised live; the pre-4.0 branch is code-reviewed only, not locally run. This limitation MUST be stated explicitly in the PR body.
- **Add-on reload is user-in-loop:** Blender has no hot-reload for add-ons. After patching the RUNNING copy, a human must disable/re-enable the "Interface: Blender MCP" add-on (or restart Blender) and re-click "Connect to Claude" before the fix is live on socket 9876. Steps requiring this are marked **[USER-IN-LOOP]**.
- **PolyHaven downloads hit the network:** The `download_polyhaven_asset` verification step needs connectivity. If the download fails due to network (not the fix), treat it as INCONCLUSIVE and retry, not as a failed verification.
- **Commit message trailer (verbatim, last line of every commit):**
  ```
  Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
  ```
- **Commit frequently:** every task ends with a commit (where a git repo exists). The SOURCE and RUNNING copies are not git repos; their changes are committed via the UPSTREAM clone, which is the canonical versioned artifact for this fix.

---

## Task 1 — Clone `ahujasid/blender-mcp` into `~/mcp-servers/`, fork under `haiggoh`, create the fix branch

**Files:**
- Create (directory): `/Users/bra0002h/mcp-servers/blender-mcp/` (git clone of the fork)

**Interfaces:**
- Consumes: `gh` auth as `haiggoh` (repo + workflow scopes); upstream repo `ahujasid/blender-mcp`.
- Produces: local git repo at `/Users/bra0002h/mcp-servers/blender-mcp/` with remote `origin` = `haiggoh/blender-mcp` fork and remote `upstream` = `ahujasid/blender-mcp`; branch `fix/set-texture-bl4-separate-color` checked out.

Steps:
- [ ] Confirm `gh` identity is `haiggoh`: run `gh auth status` and verify the output contains `Logged in to github.com account haiggoh` and the token has scopes including `repo` and `workflow`. Expected: a line naming `haiggoh` as the active account.
- [ ] Ensure the parent directory exists: run `mkdir -p /Users/bra0002h/mcp-servers`. Expected: no output, exit 0.
- [ ] Verify the target clone path does not already exist: run `ls -la /Users/bra0002h/mcp-servers/blender-mcp 2>/dev/null || echo NOT_PRESENT`. Expected: `NOT_PRESENT` (if it already exists, stop and inspect before proceeding — do not clobber).
- [ ] Fork and clone in one step under `haiggoh`, cloning into the exact target path: run `gh repo fork ahujasid/blender-mcp --clone=false`. Expected: output confirms a fork exists at `haiggoh/blender-mcp` (either "Created fork haiggoh/blender-mcp" or "haiggoh/blender-mcp already exists").
- [ ] Clone the fork to the canonical path: run `git clone https://github.com/haiggoh/blender-mcp.git /Users/bra0002h/mcp-servers/blender-mcp`. Expected: `Cloning into '/Users/bra0002h/mcp-servers/blender-mcp'...` and a completed clone.
- [ ] Add the upstream remote: run `git -C /Users/bra0002h/mcp-servers/blender-mcp remote add upstream https://github.com/ahujasid/blender-mcp.git`. Expected: no output, exit 0.
- [ ] Confirm both remotes: run `git -C /Users/bra0002h/mcp-servers/blender-mcp remote -v`. Expected: `origin` pointing at `haiggoh/blender-mcp` and `upstream` pointing at `ahujasid/blender-mcp`.
- [ ] Fetch upstream to ensure the branch base is current: run `git -C /Users/bra0002h/mcp-servers/blender-mcp fetch upstream`. Expected: fetch completes; note the default branch name in the output (typically `main`).
- [ ] Determine the default branch name: run `git -C /Users/bra0002h/mcp-servers/blender-mcp symbolic-ref refs/remotes/origin/HEAD --short`. Expected: something like `origin/main` — the trailing segment is the default branch.
- [ ] Create and check out the fix branch off the up-to-date default branch (replace `main` if the previous step reported a different default): run `git -C /Users/bra0002h/mcp-servers/blender-mcp checkout -b fix/set-texture-bl4-separate-color upstream/main`. Expected: `Switched to a new branch 'fix/set-texture-bl4-separate-color'`.
- [ ] Confirm the cloned repo contains `addon.py`: run `ls -l /Users/bra0002h/mcp-servers/blender-mcp/addon.py`. Expected: the file exists and is listed with its size and mode.
- [ ] Confirm the ARM block in the clone matches the known source (line numbers may differ slightly if upstream drifted): run `grep -n "ShaderNodeSeparateRGB" /Users/bra0002h/mcp-servers/blender-mcp/addon.py`. Expected: exactly one match, the `separate_rgb = nodes.new(type='ShaderNodeSeparateRGB')` line. If zero or more than one match, STOP — upstream has changed and the enumerated line numbers below must be re-derived from this file before editing.

---

## Task 2 — Apply the version-guarded fix to the UPSTREAM clone (the PR artifact) with a failing→passing static check

This is the one file where we can run an automated, deterministic check without Blender: a small Python AST/string assertion that the guard exists and that both branches wire the correct sockets. We write that check first (it fails against the unfixed file), then apply the fix, then the check passes.

**Files:**
- Create: `/Users/bra0002h/mcp-servers/blender-mcp/test_set_texture_version_guard.py` (static structural test; committed alongside the fix)
- Modify: `/Users/bra0002h/mcp-servers/blender-mcp/addon.py` — the ARM block. In the known-good source this is lines **1065–1103**; the `ShaderNodeSeparateRGB` creation is line **1067**, and the six `separate_rgb` references are lines **1067, 1068, 1069, 1073, 1078, 1101**. Confirm these against the clone (Task 1's grep) before editing; if upstream drifted, locate the identical block by content.

**Interfaces:**
- Consumes: `bpy.app.version` (tuple, e.g. `(5, 1, 2)`) at Blender runtime; `texture_nodes['arm']` image-texture node; `principled` (Principled BSDF); `nodes`, `links` (node tree collections); `ShaderNodeMixRGB` mix node.
- Produces: a `sep` node (either `ShaderNodeSeparateColor` on 4.0+ or `ShaderNodeSeparateRGB` below) with channel-name locals `in_socket`, `ch_r`, `ch_g`, `ch_b` used for all downstream wiring; identical rendered material to the pre-fix behavior on both version paths.

Steps:
- [ ] Write the failing static test. Create `/Users/bra0002h/mcp-servers/blender-mcp/test_set_texture_version_guard.py` with EXACTLY this content:

  ```python
  """Static structural check for the set_texture ARM version guard.

  Blender 4.0 removed ShaderNodeSeparateRGB (renamed to ShaderNodeSeparateColor,
  added in 3.3). This test asserts addon.py branches on bpy.app.version and wires
  the correct socket names on each branch, without running Blender.
  """
  import ast
  import pathlib

  ADDON = pathlib.Path(__file__).with_name("addon.py")


  def _source():
      return ADDON.read_text()


  def test_addon_parses():
      # The file must remain syntactically valid Python after the edit.
      ast.parse(_source())


  def test_has_version_guard():
      src = _source()
      assert "bpy.app.version >= (4, 0)" in src, \
          "expected a runtime guard `bpy.app.version >= (4, 0)`"


  def test_uses_separate_color_on_4x():
      src = _source()
      assert "ShaderNodeSeparateColor" in src, \
          "expected ShaderNodeSeparateColor node for Blender 4.0+"


  def test_keeps_separate_rgb_for_legacy():
      src = _source()
      assert "ShaderNodeSeparateRGB" in src, \
          "pre-4.0 path must keep the original ShaderNodeSeparateRGB node"


  def test_socket_name_locals_present():
      # Both branches must bind the channel-name locals used downstream.
      src = _source()
      for token in ("in_socket", "ch_r", "ch_g", "ch_b"):
          assert token in src, f"expected downstream channel local `{token}`"
      # 4.0+ socket names
      for token in ("'Color'", "'Red'", "'Green'", "'Blue'"):
          assert token in src, f"expected 4.0+ socket name {token}"
      # legacy socket names
      for token in ("'Image'", "'R'", "'G'", "'B'"):
          assert token in src, f"expected legacy socket name {token}"


  def test_no_literal_separate_rgb_output_indexing():
      # After the fix, downstream wiring must go through ch_* locals,
      # not `separate_rgb.outputs['G'|'B'|'R']` literals.
      src = _source()
      for bad in ("separate_rgb.outputs['G']",
                  "separate_rgb.outputs['B']",
                  "separate_rgb.outputs['R']"):
          assert bad not in src, \
              f"downstream wiring still uses literal {bad}; convert to ch_* local"
  ```
- [ ] Run the test and confirm it FAILS against the unfixed file: run `cd /Users/bra0002h/mcp-servers/blender-mcp && python3 -m pytest test_set_texture_version_guard.py -q` (if `pytest` is unavailable, run `python3 -c "import test_set_texture_version_guard as t; t.test_no_literal_separate_rgb_output_indexing()"` which will raise). Expected: failures on `test_has_version_guard`, `test_uses_separate_color_on_4x`, `test_socket_name_locals_present`, and `test_no_literal_separate_rgb_output_indexing` (the literal `separate_rgb.outputs['G']` etc. still present). This proves the check can fail.
- [ ] Read the exact ARM block from the clone to anchor the edit: run `sed -n '1065,1103p' /Users/bra0002h/mcp-servers/blender-mcp/addon.py` and confirm it matches the block below before editing. (Reading via `sed` here is acceptable — we are anchoring an exact-match Edit, not modifying.)
- [ ] Apply the fix with an in-place Edit on `/Users/bra0002h/mcp-servers/blender-mcp/addon.py`. Replace this EXACT original block:

  ```python
              # Handle ARM texture (Ambient Occlusion, Roughness, Metallic)
              if 'arm' in texture_nodes:
                  separate_rgb = nodes.new(type='ShaderNodeSeparateRGB')
                  separate_rgb.location = (-200, -100)
                  links.new(texture_nodes['arm'].outputs['Color'], separate_rgb.inputs['Image'])

                  # Connect Roughness (G) if no dedicated roughness map
                  if not any(map_name in texture_nodes for map_name in ['roughness', 'rough']):
                      links.new(separate_rgb.outputs['G'], principled.inputs['Roughness'])
                      print("Connected ARM.G to Roughness")

                  # Connect Metallic (B) if no dedicated metallic map
                  if not any(map_name in texture_nodes for map_name in ['metallic', 'metalness', 'metal']):
                      links.new(separate_rgb.outputs['B'], principled.inputs['Metallic'])
                      print("Connected ARM.B to Metallic")

                  # For AO (R channel), multiply with base color if we have one
                  base_color_node = None
                  for map_name in ['color', 'diffuse', 'albedo']:
                      if map_name in texture_nodes:
                          base_color_node = texture_nodes[map_name]
                          break

                  if base_color_node:
                      mix_node = nodes.new(type='ShaderNodeMixRGB')
                      mix_node.location = (100, 200)
                      mix_node.blend_type = 'MULTIPLY'
                      mix_node.inputs['Fac'].default_value = 0.8  # 80% influence

                      # Disconnect direct connection to base color
                      for link in base_color_node.outputs['Color'].links:
                          if link.to_socket == principled.inputs['Base Color']:
                              links.remove(link)

                      # Connect through the mix node
                      links.new(base_color_node.outputs['Color'], mix_node.inputs[1])
                      links.new(separate_rgb.outputs['R'], mix_node.inputs[2])
                      links.new(mix_node.outputs['Color'], principled.inputs['Base Color'])
                      print("Connected ARM.R to AO mix with Base Color")
  ```

  with this EXACT version-guarded block (note: every `separate_rgb.outputs['G'|'B'|'R']` reference is converted to `sep.outputs[ch_g|ch_b|ch_r]`, and the input socket goes through `in_socket`; the pre-4.0 branch reproduces the original node and socket names exactly):

  ```python
              # Handle ARM texture (Ambient Occlusion, Roughness, Metallic)
              if 'arm' in texture_nodes:
                  # Blender 4.0 removed ShaderNodeSeparateRGB (renamed to
                  # ShaderNodeSeparateColor, added in 3.3). Branch on the running
                  # Blender version so pre-4.0 behavior is untouched.
                  if bpy.app.version >= (4, 0):
                      sep = nodes.new(type='ShaderNodeSeparateColor')  # defaults to mode='RGB'
                      in_socket, ch_r, ch_g, ch_b = 'Color', 'Red', 'Green', 'Blue'
                  else:
                      sep = nodes.new(type='ShaderNodeSeparateRGB')
                      in_socket, ch_r, ch_g, ch_b = 'Image', 'R', 'G', 'B'
                  sep.location = (-200, -100)
                  links.new(texture_nodes['arm'].outputs['Color'], sep.inputs[in_socket])

                  # Connect Roughness (G) if no dedicated roughness map
                  if not any(map_name in texture_nodes for map_name in ['roughness', 'rough']):
                      links.new(sep.outputs[ch_g], principled.inputs['Roughness'])
                      print("Connected ARM.G to Roughness")

                  # Connect Metallic (B) if no dedicated metallic map
                  if not any(map_name in texture_nodes for map_name in ['metallic', 'metalness', 'metal']):
                      links.new(sep.outputs[ch_b], principled.inputs['Metallic'])
                      print("Connected ARM.B to Metallic")

                  # For AO (R channel), multiply with base color if we have one
                  base_color_node = None
                  for map_name in ['color', 'diffuse', 'albedo']:
                      if map_name in texture_nodes:
                          base_color_node = texture_nodes[map_name]
                          break

                  if base_color_node:
                      mix_node = nodes.new(type='ShaderNodeMixRGB')
                      mix_node.location = (100, 200)
                      mix_node.blend_type = 'MULTIPLY'
                      mix_node.inputs['Fac'].default_value = 0.8  # 80% influence

                      # Disconnect direct connection to base color
                      for link in base_color_node.outputs['Color'].links:
                          if link.to_socket == principled.inputs['Base Color']:
                              links.remove(link)

                      # Connect through the mix node
                      links.new(base_color_node.outputs['Color'], mix_node.inputs[1])
                      links.new(sep.outputs[ch_r], mix_node.inputs[2])
                      links.new(mix_node.outputs['Color'], principled.inputs['Base Color'])
                      print("Connected ARM.R to AO mix with Base Color")
  ```
- [ ] Confirm no stray `separate_rgb` references remain anywhere in the file: run `grep -n "separate_rgb" /Users/bra0002h/mcp-servers/blender-mcp/addon.py`. Expected: NO output (zero matches). If any line is returned, convert it to the `sep`/`ch_*` form before proceeding.
- [ ] Confirm the guard and both node types are present: run `grep -n "bpy.app.version >= (4, 0)\|ShaderNodeSeparateColor\|ShaderNodeSeparateRGB" /Users/bra0002h/mcp-servers/blender-mcp/addon.py`. Expected: three lines — the version guard, the `ShaderNodeSeparateColor` creation, and the `ShaderNodeSeparateRGB` creation.
- [ ] Run the static test and confirm it now PASSES: run `cd /Users/bra0002h/mcp-servers/blender-mcp && python3 -m pytest test_set_texture_version_guard.py -q`. Expected: all tests pass (e.g. `6 passed`). This confirms the guard, both branches, the channel locals, and the absence of literal `separate_rgb.outputs[...]` indexing.
- [ ] Commit the fix and its test on the fix branch:
  ```
  git -C /Users/bra0002h/mcp-servers/blender-mcp add addon.py test_set_texture_version_guard.py
  git -C /Users/bra0002h/mcp-servers/blender-mcp commit -m "Fix set_texture on Blender 4.0+: version-guard ARM channel split

Blender 4.0 removed ShaderNodeSeparateRGB (renamed to ShaderNodeSeparateColor,
which was added in 3.3). set_texture unconditionally created ShaderNodeSeparateRGB
to split the packed ARM (AO/Roughness/Metallic) map, so on Blender 4.0+ it raised
'ShaderNodeSeparateRGB undefined' and texture application failed.

Branch on bpy.app.version: use ShaderNodeSeparateColor (input 'Color', outputs
'Red'/'Green'/'Blue', default mode 'RGB') on 4.0+, and keep the original
ShaderNodeSeparateRGB (input 'Image', outputs 'R'/'G'/'B') below 4.0. The pre-4.0
path is unchanged; the fix is additive and backward compatible. All downstream
channel wiring now goes through in_socket/ch_r/ch_g/ch_b locals.

Adds a static structural test (test_set_texture_version_guard.py) asserting the
guard, both branches, and the socket-name locals without requiring Blender.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
  ```
  Expected: one commit created on `fix/set-texture-bl4-separate-color`.

---

## Task 3 — Mirror the fix into the SOURCE loose copy (in place, preserving permissions)

The SOURCE copy at `~/ClaudeWorkspace/blender-mcp/addon.py` is the loose reference (not a git repo). Keep it in sync with the fix so it does not drift. Edit in place to preserve its mode.

**Files:**
- Modify: `/Users/bra0002h/ClaudeWorkspace/blender-mcp/addon.py` — same ARM block (known-good lines **1065–1103**; `ShaderNodeSeparateRGB` at **1067**).

**Interfaces:**
- Consumes: same runtime interfaces as Task 2.
- Produces: SOURCE copy carrying the identical version-guarded ARM block.

Steps:
- [ ] Record the current mode of the SOURCE file so any accidental change is caught: run `ls -l /Users/bra0002h/ClaudeWorkspace/blender-mcp/addon.py`. Note the permission string (e.g. `-rw-r--r--`).
- [ ] Confirm the SOURCE still contains exactly the original single `ShaderNodeSeparateRGB` occurrence (i.e. it has not already been patched): run `grep -c "ShaderNodeSeparateRGB" /Users/bra0002h/ClaudeWorkspace/blender-mcp/addon.py`. Expected: `1`. If `0`, it was already patched — skip the edit and verify with the grep checks below.
- [ ] Confirm the exact ARM block matches before editing: run `sed -n '1065,1103p' /Users/bra0002h/ClaudeWorkspace/blender-mcp/addon.py`. Expected: identical to the original block quoted in Task 2.
- [ ] Apply the fix with an in-place Edit on `/Users/bra0002h/ClaudeWorkspace/blender-mcp/addon.py`, replacing the SAME original ARM block quoted in Task 2 with the SAME version-guarded block quoted in Task 2. (Use the Edit tool — do NOT redirect-and-move; this preserves the inode mode.)
- [ ] Confirm no stray `separate_rgb` references remain: run `grep -n "separate_rgb" /Users/bra0002h/ClaudeWorkspace/blender-mcp/addon.py`. Expected: NO output.
- [ ] Confirm the guard and both node types are present: run `grep -n "bpy.app.version >= (4, 0)\|ShaderNodeSeparateColor\|ShaderNodeSeparateRGB" /Users/bra0002h/ClaudeWorkspace/blender-mcp/addon.py`. Expected: three matching lines.
- [ ] Confirm the file still parses as valid Python: run `python3 -c "import ast,pathlib; ast.parse(pathlib.Path('/Users/bra0002h/ClaudeWorkspace/blender-mcp/addon.py').read_text()); print('OK')"`. Expected: `OK`.
- [ ] Confirm the mode is UNCHANGED: run `ls -l /Users/bra0002h/ClaudeWorkspace/blender-mcp/addon.py` and compare to the recorded permission string. Expected: identical mode (e.g. still `-rw-r--r--`). If it changed, restore it with `chmod` to the recorded mode.
- [ ] There is no git repo here to commit to; the versioned commit lives in the UPSTREAM clone (Task 2). No commit step for this task — the SOURCE sync is verified by the greps above.

---

## Task 4 — Patch the RUNNING copy Blender loads (in place, preserving permissions)

This is the copy Blender actually executes. Editing SOURCE or the clone does NOT affect it. Patch it in place so the mode is preserved, then it is ready for the user-in-loop reload in Task 5.

**Files:**
- Modify: `/Users/bra0002h/Library/Application Support/Blender/5.1/scripts/addons/addon.py` — same ARM block (`ShaderNodeSeparateRGB` creation line; confirm exact line numbers in this copy, which should match the known-good **1065–1103** unless the installed copy differs from source).

**Interfaces:**
- Consumes: same runtime interfaces as Task 2.
- Produces: the RUNNING add-on file carrying the version-guarded ARM block, ready to be reloaded by the user.

Steps:
- [ ] Confirm the running-copy path exists: run `ls -l "/Users/bra0002h/Library/Application Support/Blender/5.1/scripts/addons/addon.py"`. Expected: the file exists; record its permission string.
- [ ] Confirm it currently contains exactly one `ShaderNodeSeparateRGB` (unpatched): run `grep -c "ShaderNodeSeparateRGB" "/Users/bra0002h/Library/Application Support/Blender/5.1/scripts/addons/addon.py"`. Expected: `1`. If `0`, it is already patched — skip the edit and verify with the grep checks below.
- [ ] Confirm the exact ARM block matches before editing: run `sed -n '1065,1103p' "/Users/bra0002h/Library/Application Support/Blender/5.1/scripts/addons/addon.py"`. Expected: identical to the original block quoted in Task 2. (If line numbers differ, locate the block by content — the `# Handle ARM texture` comment through the `print("Connected ARM.R to AO mix with Base Color")` line.)
- [ ] Apply the fix with an in-place Edit on `/Users/bra0002h/Library/Application Support/Blender/5.1/scripts/addons/addon.py`, replacing the SAME original ARM block quoted in Task 2 with the SAME version-guarded block quoted in Task 2. Use the Edit tool (in-place) — do NOT redirect-and-move.
- [ ] Confirm no stray `separate_rgb` references remain: run `grep -n "separate_rgb" "/Users/bra0002h/Library/Application Support/Blender/5.1/scripts/addons/addon.py"`. Expected: NO output.
- [ ] Confirm the guard and both node types are present: run `grep -n "bpy.app.version >= (4, 0)\|ShaderNodeSeparateColor\|ShaderNodeSeparateRGB" "/Users/bra0002h/Library/Application Support/Blender/5.1/scripts/addons/addon.py"`. Expected: three matching lines.
- [ ] Confirm the file still parses as valid Python: run `python3 -c "import ast,pathlib; ast.parse(pathlib.Path('/Users/bra0002h/Library/Application Support/Blender/5.1/scripts/addons/addon.py').read_text()); print('OK')"`. Expected: `OK`.
- [ ] Confirm the mode is UNCHANGED vs the recorded permission string: run `ls -l "/Users/bra0002h/Library/Application Support/Blender/5.1/scripts/addons/addon.py"`. Expected: identical mode. If changed, restore with `chmod`.
- [ ] No git commit for this task (not a repo). The canonical commit is in the UPSTREAM clone (Task 2).

---

## Task 5 — [USER-IN-LOOP] Reload the add-on and re-establish the socket connection

Blender has no hot-reload. The patched RUNNING copy is not live until the user reloads the add-on and reconnects. Detect readiness before and after.

**Files:** none modified.

**Interfaces:**
- Consumes: Blender process; add-on socket on `127.0.0.1:9876`.
- Produces: a live, reloaded add-on listening on 9876 that includes the fix.

Steps:
- [ ] Detect whether Blender is currently running: run `pgrep -x Blender || echo NOT_RUNNING`. Expected: a PID (Blender running) or `NOT_RUNNING`.
- [ ] Detect whether the add-on socket is currently listening: run `lsof -nP -iTCP:9876 -sTCP:LISTEN || echo NO_SOCKET`. Expected: a `Blender ... TCP 127.0.0.1:9876 (LISTEN)` line, or `NO_SOCKET`.
- [ ] **[USER-IN-LOOP]** Ask the user to reload the add-on so the patched code takes effect, giving these exact instructions: "In Blender: open Edit → Preferences → Add-ons, find 'Interface: Blender MCP', uncheck it, then re-check it (or simply restart Blender). Then open the N-panel (press N in the 3D viewport) → BlenderMCP tab → click 'Connect to Claude'. Tell me when the panel shows it is connected." Wait for the user's confirmation before continuing.
- [ ] After the user confirms, verify the socket is listening again: run `lsof -nP -iTCP:9876 -sTCP:LISTEN`. Expected: a `Blender ... TCP 127.0.0.1:9876 (LISTEN)` line. If absent, re-prompt the user to click "Connect to Claude" and re-check.
- [ ] Verify end-to-end MCP connectivity through the reloaded add-on by calling the read-only `mcp__blender__get_scene_info` tool (with `user_prompt` set to a short description like "verify blender connection after set_texture reload"). Expected: a scene-info result (object list / scene name), NOT a connection error. If it errors with connection refused, the socket is not connected — return to the reload instruction.

---

## Task 6 — [USER-IN-LOOP] Live verification: reproduce the 4.0+ path succeeds on the reproduction scene

This is the real proof the fix works on Blender 5.1 (the 4.0+ branch). It cannot be a unit test — it requires the running Blender, a network PolyHaven download, and visual confirmation. Every step below is a concrete MCP tool call with an explicit expected observation.

**Files:** none modified (scene artifacts are created then cleaned up).

**Interfaces:**
- Consumes: live Blender MCP tools `mcp__blender__execute_blender_code`, `mcp__blender__download_polyhaven_asset`, `mcp__blender__set_texture`, `mcp__blender__get_viewport_screenshot`, `mcp__blender__get_object_info`.
- Produces: a textured plane whose material contains the version-guarded ARM split (a `Separate Color` node on 5.1) wired into the Principled BSDF; then a cleaned-up scene.

Steps:
- [ ] Record the pre-test object set so cleanup is verifiable: call `mcp__blender__get_scene_info` (user_prompt: "record scene before set_texture verification") and note the list of object names present. Expected: a scene-info result; save the current object names.
- [ ] Create the reproduction plane named `SetTextureFixTest`: call `mcp__blender__execute_blender_code` with `code`:
  ```python
  import bpy
  bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
  plane = bpy.context.active_object
  plane.name = "SetTextureFixTest"
  print("CREATED", plane.name)
  ```
  Expected: output contains `CREATED SetTextureFixTest`.
- [ ] Confirm PolyHaven integration is enabled before downloading: call `mcp__blender__get_polyhaven_status` (user_prompt: "check polyhaven before dark_wood download"). Expected: a message indicating PolyHaven is enabled. If disabled, STOP and note this is a prerequisite (out of scope of the fix).
- [ ] Download the `dark_wood` texture at 1k (this hits the network — if it fails on connectivity, retry; treat a network failure as INCONCLUSIVE, not a fix failure): call `mcp__blender__download_polyhaven_asset` with `asset_id="dark_wood"`, `asset_type="textures"`, `resolution="1k"`, `user_prompt="verify set_texture fix with dark_wood ARM map"`. Expected: a success message indicating the texture downloaded and a material was created; note the created material name (typically `dark_wood`).
- [ ] Apply the texture to the plane via the FIXED code path: call `mcp__blender__set_texture` with `object_name="SetTextureFixTest"`, `texture_id="dark_wood"`, `user_prompt="verify set_texture fix"`. Expected: a SUCCESS result. Specifically, it MUST NOT return an error mentioning `ShaderNodeSeparateRGB` or "undefined" — that was the pre-fix crash. This is the primary pass/fail signal for the fix.
- [ ] Verify the ARM split node was created as the 4.0+ `Separate Color` node (proves the guard took the correct branch on 5.1) and is wired into the shader: call `mcp__blender__execute_blender_code` with `code`:
  ```python
  import bpy
  obj = bpy.data.objects["SetTextureFixTest"]
  mat = obj.active_material
  nodes = mat.node_tree.nodes
  sep = [n for n in nodes if n.bl_idname == "ShaderNodeSeparateColor"]
  rgb_legacy = [n for n in nodes if n.bl_idname == "ShaderNodeSeparateRGB"]
  print("SEPARATE_COLOR_COUNT", len(sep))
  print("SEPARATE_RGB_COUNT", len(rgb_legacy))
  if sep:
      print("SEP_OUTPUTS", [o.name for o in sep[0].outputs])
      print("SEP_INPUTS", [i.name for i in sep[0].inputs])
  ```
  Expected: `SEPARATE_COLOR_COUNT 1`, `SEPARATE_RGB_COUNT 0`, `SEP_OUTPUTS ['Red', 'Green', 'Blue']`, `SEP_INPUTS ['Color']`. This confirms the 4.0+ branch ran and used the correct sockets.
- [ ] Capture a viewport screenshot to visually confirm the wood material rendered with ARM-driven roughness/AO: call `mcp__blender__get_viewport_screenshot` (max_size 1000, user_prompt: "confirm dark_wood material on plane after set_texture fix"). Expected: a non-empty image showing the plane with a dark wood texture (not a flat/pink/error material).
- [ ] Clean up the test artifacts — delete the test plane and its material: call `mcp__blender__execute_blender_code` with `code`:
  ```python
  import bpy
  name = "SetTextureFixTest"
  if name in bpy.data.objects:
      obj = bpy.data.objects[name]
      bpy.data.objects.remove(obj, do_unlink=True)
      print("REMOVED_OBJECT", name)
  # Remove orphaned dark_wood material if now unused
  for mat in list(bpy.data.materials):
      if mat.name.startswith("dark_wood") and mat.users == 0:
          bpy.data.materials.remove(mat)
          print("REMOVED_MATERIAL", mat.name)
  ```
  Expected: `REMOVED_OBJECT SetTextureFixTest` (and possibly `REMOVED_MATERIAL dark_wood`).
- [ ] Confirm the scene is restored to the pre-test object set: call `mcp__blender__get_scene_info` (user_prompt: "confirm scene restored after set_texture verification") and compare the object names to those recorded at the start of this task. Expected: the object set matches the pre-test set (no leftover `SetTextureFixTest`).
- [ ] Record the verification outcome in the UPSTREAM clone's commit history as an empty marker commit documenting the live result (so the PR branch carries evidence the 4.0+ path was exercised):
  ```
  git -C /Users/bra0002h/mcp-servers/blender-mcp commit --allow-empty -m "Verify set_texture fix live on Blender 5.1.2

Reproduction: create plane -> download_polyhaven_asset(dark_wood, 1k) ->
set_texture -> SUCCESS (no ShaderNodeSeparateRGB error). Confirmed the material
contains one ShaderNodeSeparateColor node with inputs ['Color'] and outputs
['Red','Green','Blue'], wired into the Principled BSDF; viewport screenshot shows
the dark wood material with ARM-driven roughness/AO. Scene cleaned up afterward.

Only Blender 5.1 is installed, so the 4.0+ branch is exercised live; the pre-4.0
branch is code-reviewed, not locally run.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
  ```
  Expected: an empty commit recording the verification.

---

## Task 7 — Push the fix branch and open the upstream PR to `ahujasid/blender-mcp`

**Files:** none modified (PR body authored inline).

**Interfaces:**
- Consumes: the committed fix branch `fix/set-texture-bl4-separate-color` in `/Users/bra0002h/mcp-servers/blender-mcp/`; `gh` auth as `haiggoh`; upstream `ahujasid/blender-mcp`.
- Produces: `origin` branch `haiggoh:fix/set-texture-bl4-separate-color` pushed; an open PR against `ahujasid/blender-mcp`.

Steps:
- [ ] Confirm the working tree is clean and the branch has the fix commit(s): run `git -C /Users/bra0002h/mcp-servers/blender-mcp status` and `git -C /Users/bra0002h/mcp-servers/blender-mcp log --oneline upstream/main..HEAD`. Expected: clean tree; the log shows the fix commit and the verification marker commit.
- [ ] Push the branch to the fork: run `git -C /Users/bra0002h/mcp-servers/blender-mcp push -u origin fix/set-texture-bl4-separate-color`. Expected: the branch is pushed to `haiggoh/blender-mcp` and `gh` may print a create-PR hint URL.
- [ ] Create the PR against upstream with a full reproduction and rationale. Run this exact command (the `--repo` targets upstream; `--head haiggoh:...` names the fork branch):
  ```
  git -C /Users/bra0002h/mcp-servers/blender-mcp status >/dev/null && \
  gh pr create \
    --repo ahujasid/blender-mcp \
    --head haiggoh:fix/set-texture-bl4-separate-color \
    --title "Fix set_texture on Blender 4.0+: version-guard ARM channel split (SeparateRGB removed in 4.0)" \
    --body "$(cat <<'EOF'
## Problem

`set_texture` fails on Blender 4.0+ whenever the applied PolyHaven texture set
includes a packed **ARM** map (Ambient Occlusion / Roughness / Metallic). The
ARM-handling code unconditionally creates a `ShaderNodeSeparateRGB` node to split
the packed channels:

```python
separate_rgb = nodes.new(type='ShaderNodeSeparateRGB')
```

Blender **4.0 removed** `ShaderNodeSeparateRGB` — it was renamed to
`ShaderNodeSeparateColor` (introduced in Blender **3.3**). On 4.0+ the call raises
and texture application fails.

## Reproduction

1. Blender 4.0+ (reproduced on 5.1.2), add-on installed and "Connect to Claude" active.
2. Create a mesh (e.g. a plane).
3. `download_polyhaven_asset` a texture that ships an ARM map (e.g. `dark_wood`, 1k).
4. `set_texture` that texture onto the mesh.
5. Result: error creating `ShaderNodeSeparateRGB` (undefined node type on 4.0+);
   the texture is not applied.

## Fix

Branch on `bpy.app.version` and use the version-appropriate node + socket names:

- **Blender 4.0+**: `ShaderNodeSeparateColor` (defaults to `mode='RGB'`), input
  `Color`, outputs `Red`/`Green`/`Blue`.
- **Below 4.0**: the original `ShaderNodeSeparateRGB`, input `Image`, outputs
  `R`/`G`/`B` — **unchanged**.

All downstream channel wiring goes through `in_socket` / `ch_r` / `ch_g` / `ch_b`
locals, so both branches share one code path. The fix is **additive and backward
compatible**: the pre-4.0 behavior is byte-for-byte the same node and sockets as
before. `SeparateColor` was added in 3.3 and `SeparateRGB` removed in 4.0, so the
`>= (4, 0)` boundary is the correct cutover.

## Verification

- Exercised live on **Blender 5.1.2**: create plane → `download_polyhaven_asset(dark_wood, 1k)`
  → `set_texture` → success (no error). The resulting material contains one
  `ShaderNodeSeparateColor` node (inputs `['Color']`, outputs `['Red','Green','Blue']`)
  wired into the Principled BSDF; the viewport shows the wood material with ARM-driven
  roughness/AO.
- **Only Blender 5.1 was available for testing**, so the pre-4.0 branch is
  code-reviewed (it reproduces the original node/socket names exactly) rather than
  run locally.
EOF
)"
  ```
  Expected: `gh` prints the new PR URL on `ahujasid/blender-mcp`.
- [ ] Capture the PR URL and confirm it is open against upstream: run `gh pr view --repo ahujasid/blender-mcp --head haiggoh:fix/set-texture-bl4-separate-color --json url,state,title`. Expected: JSON showing `"state": "OPEN"`, the PR title, and the URL.
- [ ] There is nothing further to commit for this task; the PR is the deliverable. Record the PR URL in the final task output so downstream workstreams (B PROJECT-NOTES, C skill examples) can reference it.
