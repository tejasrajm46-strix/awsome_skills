# Changelog

Notable changes to Awesome Skills. Newest first, and the release workflow uses the
section for a version tag as the body of the GitHub release.

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
