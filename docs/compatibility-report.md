# Compatibility and validation report - v3.2.0

What was measured on this tree, what it fixed, and what remains unverified. Every
number here came from a command run against this working tree; nothing is carried
over from a report without being re-checked.

## 1. Starting state

| Item | Value |
|---|---|
| Branch | `main` |
| HEAD at baseline | `8e17227` "Release v3.1.0: version bump, docs and rebuilt packages" (2026-10-31) |
| Working tree at baseline | clean - no uncommitted or staged changes |
| Local vs remote | `origin/main` at `db08706` (2026-10-06); local `main` 9 commits ahead, so the v3.1.0 work was never pushed |
| Tags | `v3.1.0` exists locally (and `v2.0.0`, `v3.0.0`, `ASSETS`, `prompt_for_perfect_ppt`) |
| Packages at baseline | six `*-v3.1.0.zip` files, byte-identical to a fresh build of the tree |
| Suites at baseline | 21 Python suites plus one Node poster test, all passing |
| Environment | Windows 11 (10.0.26200), Python 3.14.7 |

Baseline gates: `verify_repository.py` passed with 91 local links,
`skillopt_gate.py check` scored six documents at 100.00 (~2399 / 2108 / 1808 /
1643 / 2381 / 2207 tokens), and `check_release.py` byte-matched the six packages.

## 2. Defects reproduced

Each defect was reproduced before fixing - five by running the new regression
suite against an untouched export of `HEAD`, and E.5 by inspection (it was a
documentation and consistency gap, not a crash).

| Defect | Observed on the pre-fix tree | Root cause |
|---|---|---|
| E.1 `load --references` | `ValueError: ppt has no reference 'deck-schema.md'; available: references/deck-schema.md, ...` raised out of the CLI | References are per-skill but the flag is task-level; `reference()` was called for every name on every requested skill, with no resolution and no pre-validation |
| E.2 REPAIR from EXECUTION | `run` returned 0 and printed `not yet ready (dependencies unmet): b1-build`; the task sat in EXECUTION with a failed step and no transition available | `TRANSITIONS["EXECUTION"]` omitted REPAIR, and `cmd_run` never examined failures |
| E.3 input freshness | `KeyError: 'inputs'` - the ledger had no record of the files a command read | `freshen()` hashed the plan, the script and the loaded guide, but nothing hashed the step's input arguments |
| E.4 `validate` at delivery | `IllegalTransition: illegal transition DELIVERY -> REPAIR` propagated as a traceback | `cmd_validate` called `state.transition("REPAIR")` unguarded after finding a failed step |
| E.5 manifest paths | Suite passed pre-fix: resolution already followed the manifest directory in `validate`, but `mark` used an `isfile`-only check (a directory output read as `missing`) and no rule was documented | Two implementations of the same rule, neither documented |
| E.6 counter and placeholders | `failed steps recorded; repair cycle 2/2` printed for the first cycle; planner's `<spec>` was refused as "shell metacharacters" | The counter was printed before the transition; the planner and executor disagreed on placeholder syntax |

## 3. Fixes and their regression tests

All six are pinned in `tools/test_orchestration_defects.py`, which runs in the
release workflow. The fixes are described in the [changelog](../CHANGELOG.md).

- **E.1** - `SkillLoader.resolve_reference()` resolves exact paths, `./path` and
  unambiguous basenames, and lists what a skill ships when it cannot. `cmd_load`
  validates every name against every requested skill before recording anything,
  loads a shared reference from each skill that ships it, and reports unknown
  skills with the catalog keys.
- **E.2** - `EXECUTION -> REPAIR` is legal; `run` opens a cycle directly (exit
  code 2) or records FAILED when the budget is spent; a retry that still fails
  reports the spent cycle; `validate` closes a REPAIR cycle before opening the
  next, so the budget is counted once per cycle. Terminal states refuse all moves.
- **E.3** - `task_executor.input_hashes()` hashes only arguments that resolve to
  an existing file inside the repository; the ledger stores them per step, and
  `freshen()` demotes a step whose input changed or disappeared. Flags, output
  paths and unrelated files are never hashed.
- **E.4** - every CLI transition goes through `_transition()`, which reports
  `illegal transition <from> -> <to>` and leaves the ledger unchanged; the stale
  plan refusal is caught and reported instead of raised.
- **E.5** - one `resolve_path(base, path)` rule (absolute stays absolute,
  otherwise relative to the manifest) is used by `new`, `mark` and `validate` for
  outputs, evidence and `sources_register`, and documented in the module.
- **E.6** - the cycle number is read after the transition; plans use `{{name}}`
  placeholders declared per step; the planner rejects angle-bracket, undeclared
  and unused placeholders; the executor refuses an unfilled placeholder by name.

## 4. Capability measurement

`python tools/capability_probe.py --json` on the development host:

| Status | Capabilities |
|---|---|
| `available` (9) | `repo_read`, `file_write`, `python_exec`, `shell_exec`, `document_generation` (built a DOCX), `spreadsheet_generation` (built an XLSX), `presentation_generation` (built a PPTX), `image_inspection` (encoded and reopened a PNG), `git_ops` |
| `unavailable` (1) | `pdf_generation` - no `soffice`/LibreOffice/Chrome on PATH and no reportlab |
| `unverified` (1) | `rendering` - no renderer on PATH; an Office COM renderer may still exist, so this is a claim to confirm, not a fact |
| `permission_required` (2) | `dependency_install` (never attempted), `network_access` (no request without `--allow-network`) |

This is a statement about one host, not about any client. The probe builds and
discards a real artifact for the library capabilities; it does not prove a full
deliverable or a visual review, and it never reports `available` for something it
did not observe.

One caveat the verification run exposed: the Node poster suite rendered through
Chrome on this host, so a renderer does exist behind a path the probe does not
inspect. `rendering` therefore stays `unverified` as the probe's PATH-only answer,
while poster rendering is separately verified in section 5. Neither says anything
about PowerPoint or Word rendering.

## 5. Verification run

| Command | Result |
|---|---|
| `python tools/check_release.py` | PASS - v3.2.0 consistent across `skills.json`, 6 frontmatters, 6 eval manifests, README links, CHANGELOG, workflow; 6 packages byte-matched against fresh builds |
| `python tools/skillopt_gate.py check` | PASS - six documents at 100.00, token counts unchanged from baseline |
| 23 Python suites (tools + all skills) | all exit 0, including the two new suites |
| `python tools/capability_probe.py` | 9 available, 1 unavailable, 1 unverified, 2 permission_required |
| `python tools/verify_repository.py` | PASS - six catalog entries, synchronized helpers, PPT references, script syntax and 116 local links |
| `node poster_skill/tests/test_template_mode.mjs` | PASS - Chrome rendered a correctly scaled 300x450 preview; dimensions, replacement regions, patch markers, static QA and aspect-ratio refusal checked |
| `build_deck.py` then `validate_deck.py --expect 5 --strict` | PASS - 5 slides, 13.33 x 7.50 in, 0 embedded transitions, 0 errors, 0 warnings |
| `build_doc.py` then `validate_doc.py --strict` | PASS - 0 errors, 0 warnings |

## 6. Remaining limitations

These are not worked around silently; each is either a host gap or a disclosed
scope limit.

- **PDF generation is unavailable and Office rendering is unverified on this
  host.** The probe found no renderer on PATH. The poster suite did render through
  Chrome, so Chrome exists behind a path the probe does not inspect - that verifies
  the poster pipeline only, not PowerPoint or Word rendering.
- **Network access was not tested.** It stays `permission_required` by design, so
  live research behaviour is unverified in this report.
- **Symlink containment is untested on this host.** The executor suite reports that
  symlinks are unavailable without additional privilege; the check itself is
  unchanged and still runs where symlinks can be created.
- **E.5 was a documentation gap, not a crash.** The pre-fix tree already resolved
  paths correctly in `validate`; the measurable defect was `mark` disagreeing about
  a directory output, plus the missing rule. It is fixed and tested, but it should
  not be described as a reproduced crash.
- **First-run cost.** The 23 suites spawn subprocesses (Python, git, shell); on a
  cold Windows filesystem the full set takes tens of seconds.
- **Nothing was pushed and no tag was created.** `main` remains 9 commits plus the
  v3.2.0 work ahead of `origin/main`; publication is an explicit, separate step.
- **Client documentation is setup guidance, not a compatibility guarantee.** The
  guides describe what a session needs and how to check for it; they do not claim
  that any client auto-installs a skill from a link.
