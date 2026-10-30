# Changelog

Notable changes to Awesome Skills. Newest first, and the release workflow uses the
section for a version tag as the body of the GitHub release.

## [v3.1.0] - 2026-10-30

Release metadata, research provenance and output verification become checkable
artifacts instead of prose promises. No format builder changed; the shared
research pipeline gained the tooling that enforces its own rules, and the
collection gained the checks that prove it followed them.

### Added

- **Skill intelligence layer** (`tools/orchestrator.py` with
  `skill_registry.py`, `skill_loader.py`, `skill_cache.py`, `task_planner.py`,
  `task_executor.py`, `task_state.py`, and three test suites). The
  deterministic half of LLM orchestration: a catalog-driven registry (no skill
  hardcoded - a new compatible skill is discoverable by catalog entry alone),
  progressive three-stage loading with measured token cost and a
  content-hash cache that cannot serve stale instructions, interpretation
  validation and dependency-ordered plan generation whose commands are
  allowlisted repository scripts, a controlled executor with timeouts and
  bounded repair that never reports an unobserved success, and a persisted
  task state machine (CREATED through DELIVERY with recorded transitions).
  Modes (`fast`/`balanced`/`deep`) change depth - render review,
  cross-format consistency, repair budget - never safety: every mode plans
  validation for every deliverable. The host LLM authors interpretations and
  performs the manual steps; the layer makes the rest checkable.
- **Manual-step completion protocol.** Step statuses are distinct and not
  interchangeable: `command_completed` (a controlled command actually ran -
  only the executor records it), `manual_pending`, `manual_completed` (the
  host supplied an evidence file through `done --evidence`; work finished,
  verification not implied) and `validated` (set only by the validation pass
  over a validator that ran as a command; a manual completion can never
  self-assign it). Deliveries report per-deliverable checks, and a task with
  manual-only validation ships marked `fully_validated: false`.
- **Resume freshness.** The ledger stores the plan's hash, each command step's
  script hash and each loaded guide's hash. On resume, a changed plan refuses
  to continue, and any step whose script or skill guide changed on disk is
  demoted to `stale` and re-runs - persisted state cannot silently skip work
  whose instructions moved. Failed steps are retried only inside a REPAIR
  cycle, never blindly. The executor additionally resolves symlinks before
  its containment check, so a link inside a skill root cannot smuggle a
  script in from outside the repository.
- **Research handoff contract.** `ultimate-scrape-skill/scripts/handoff.py`
  assembles and validates one `handoff.json` per research workspace - register,
  reviewed assets, page data, theme tokens and limitations - so a format skill
  consumes one predictable structure instead of re-deciding from prose.
  `references/handoff-contract.md` documents the layout;
  `references/shared-scraping.md` wires it into all five format skills.
- **Asset selection workflow.** `ultimate-scrape-skill/scripts/select_assets.py`
  is the review gate between downloaded candidates and the builders: every
  candidate is approved (with intended use and license recorded) or rejected
  (with a reason), `validate` refuses an incomplete review, and approvals
  re-hash the file so a swapped candidate cannot pass on an old decision.
- **Register/spec cross-reference.** `source_register.py check-spec` compares a
  builder spec's citations against the register, so slides and documents cite
  register IDs exactly - unknown IDs fail, contradicted sources cannot be
  cited, unverified ones warn (or fail under `--strict`), and both output
  manifests can point at the same register (`tools/output_manifest.py new
  --register`).
- **Security regression suite** (`ultimate-scrape-skill/tests/test_security.py`):
  redirect chains (every hop validated, private hops refused before urllib),
  private/mixed DNS destinations, malformed URLs (with a fail-closed
  `ValueError` contract for unresolvable hosts), MIME mismatches judged by
  magic bytes, oversized HTML and saved pages, mid-stream download cleanup, and
  hostile page instructions preserved verbatim as inert data with a static
  no-dynamic-execution guard.
- **Cross-format reuse proof** (`ultimate-scrape-skill/tests/test_handoff.py`):
  one brief, one register, one reviewed asset set, two deliverables - both
  specs cross-referenced against the shared register, both output manifests
  pointing at it.
- **Release-consistency checker** (`tools/check_release.py`, with
  `tools/test_check_release.py`). It compares every place a version lives -
  `skills.json`, each `SKILL.md` frontmatter, each `evals/evals.json`, the README
  download links, the CHANGELOG section, the committed packages and the release
  workflow - and fails with the exact file when they disagree. Committed ZIPs are
  byte-compared against fresh deterministic rebuilds, and each package's inner
  SKILL.md must carry the catalog version, so a package that no longer
  matches its sources cannot be tagged. It reports drift; it never repairs it.
- **Source register** (`ultimate-scrape-skill/scripts/source_register.py`, with
  tests and `references/source-register.md`). The "no fact without a source ID"
  rule becomes a validated JSON artifact: stable IDs, one claim mapped to exactly
  one source, `accessed` dates, and a `verified` status that is refused without
  recorded evidence. Unknown fields are rejected so metadata cannot be invented
  into the schema.
- **Output manifest** (`tools/output_manifest.py`, with
  `tools/test_output_manifest.py`). One machine-readable manifest per task
  records which checks ran for each output and derives the state ladder -
  `generated` -> `validated` -> `rendered` -> `visually_inspected` - from checks
  that have evidence on disk. A hand-written state is refused; a deck that merely
  built reads as `generated`.

### Changed

- **The release workflow derives its version from `skills.json`** instead of
  hardcoding one in three places - the mechanism behind earlier version drift.
  The publish job now also refuses a tag that disagrees with the catalog.
- **Router awareness** (`ultimate-scrape-skill/scripts/route.py`): the checklist
  now distinguishes creating from editing, detects input files by extension, and
  adds an "inspect the existing file first" step for edit requests.
- **Version is `v3.1.0` everywhere**; packages rebuilt from this tree.

## [v3.0.0] - 2026-10-06

Skill documents are now gated, so a release cannot quietly make them worse.
Every `SKILL.md` is scored against a contract and a version ships only when each
skill strictly improves on the published baseline.

**Measured result of the upgrade** - `python tools/skillopt_gate.py check --baseline v2.0.0`.
The full per-check evidence is committed at
[docs/skillopt-gate-report.md](docs/skillopt-gate-report.md):

| Skill | v2.0.0 | v3.0.0 |
|---|---|---|
| `pptx-generator` | 23.81 | 100.00 |
| `word-generator` | 38.10 | 100.00 |
| `pdf-processor` | 38.10 | 100.00 |
| `xlsm-processor` | 38.10 | 100.00 |
| `smart-poster-designer` | 23.81 | 100.00 |
| `ultimate-scrape-skill` | 38.10 | 100.00 |

### Added

- **Skill-document gate** (`tools/skillopt_gate.py`) with its own regression suite
  (`tools/test_skillopt_gate.py`). It adapts the training loop from
  [Microsoft SkillOpt](https://github.com/microsoft/SkillOpt): a skill document is
  trainable text, an optimizer proposes bounded `add`/`replace`/`delete` edits with
  a character budget, and a candidate is accepted only when it strictly improves
  the score with no hard failure. It implements `check`, `optimize` and `report`,
  and refuses to write inside a protected region.
- **Protected regions in every skill document.** A `SLOW_UPDATE` block holds the
  rules distilled across revisions, and an `APPENDIX` holds the run-time
  reminders. Ordinary edits cannot touch either, which is what keeps a rewrite
  from deleting hard-won guidance.
- **A held-out eval split per skill.** `evals/evals.json` now declares a
  `selection` split that an edit is optimized against and a `test` split that is
  only ever used to check a finished candidate. `ultimate-scrape-skill` gained an
  eval suite, having had none.
- **`references/skill-evolution.md` in every skill**, explaining the contract, the
  loop, where the depth is meant to live, and the failure modes that skill has
  already hit.
- **`references/deck-schema.md`** for the PPT skill: the deck spec JSON, all 24
  layouts and the script map, moved out of the always-loaded guide.
- **`references/fallback.md`** for the PPT skill: what to do when `python-pptx`
  cannot be installed.
- **`CHANGELOG.md`**, and release notes sourced from it.

### Changed

- **Version is `v3.0.0` everywhere**: every `SKILL.md` frontmatter, `skills.json`,
  the eval manifests, the README download links and the release workflow.
- **Guides were compacted under a token budget.** `SKILL.md` is the artifact loaded
  on every task, so it now holds the workflow, the hard rules and the report
  format, with depth in `references/`. The PPT guide dropped from about 4,750 to
  about 2,400 estimated tokens and the poster guide from about 2,700 to about
  2,380, with no rule removed. The other four grew by roughly 150 to 500 tokens
  each, which is the cost of the protected regions and the new gate link - the
  collection as a whole is smaller than v2.0.0.
- **Plainer language throughout.** The legalistic hedging is gone; the rules are
  stated as consequences rather than as warnings. Every safety rule survived, and
  the ones that matter are stated plainly: no fabricated sources, no bypassing a
  paywall or a login, no executing macros, no uploading a confidential file to a
  third party.
- **Research policy.** AI search or a Google/web search first, then the primary
  source. **Wikipedia is no longer used as a source for facts or images** - the
  guides say what to do instead, and how to treat a Wikipedia link a user supplies.
- **The poster skill** now points at its existing template-mode reference instead
  of repeating the same method in two places.

### Notes

- The contract score saturates at full compliance, so it measures structure,
  budget and hygiene well and cannot separate two compliant documents. Beyond
  that, quality has to come from real task results - the gate's own documentation
  says so rather than pretending otherwise.
- The v2.0.0 archives stay exactly as they were; `releases/skills/` contains only
  freshly built, gated v3.0.0 packages.

## [v2.0.0]

Five format skills and one shared research helper, with synchronized helpers,
original replacement assets, deterministic packaging and no PPT slide transitions.
See the [v2.0.0 release](https://github.com/tejasrajm46-strix/awsome_skills/releases/tag/v2.0.0).
