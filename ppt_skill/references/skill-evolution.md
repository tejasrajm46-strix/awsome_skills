# Evolving this skill

Treat `SKILL.md` as trained text rather than documentation. That is the model
[SkillOpt](https://github.com/microsoft/SkillOpt) uses: an optimizer proposes
small edits to the skill document, and an edit lands only when it strictly
improves a score that the optimizer never trained against. The model weights stay
frozen; the skill is what changes.

This file explains how to run that loop here, and what the repository will refuse.

## The contract

`tools/skillopt_gate.py` scores `SKILL.md` against the checks below. Every one of
them is a hard requirement: a document that fails any check is rejected outright,
no matter how much its numbers improve.

| Check | What it wants |
|---|---|
| `frontmatter` | A YAML block with `name` (matching `skills.json`), `description`, `license`, `compatibility` and `version`. |
| `version` | The frontmatter `version` equals the catalog version in `skills.json`. |
| `protected_regions` | Both machine-managed regions exist, in order, non-overlapping, with real content in the slow-update body. |
| `budget` | The document stays inside its token ceiling. This file is loaded on every task, so it has to stay affordable. |
| `sections` | The skill's core sections are still there. A gate on a gutted document is worthless. |
| `evolution_ref` | `SKILL.md` links this file, so the next person finds the loop. |
| `evals_split` | `evals/evals.json` declares both a `selection` and a held-out `test` eval at the catalog version. |
| `placeholders` | No `TODO`, `TBD`, `FIXME` or `XXX` left in the guide. |
| `stale_version` | No version literal other than the current one. |

```bash
python tools/skillopt_gate.py check               # every skill, failing checks named
python tools/skillopt_gate.py check --skill ppt   # just this one
python tools/skillopt_gate.py check --baseline v2.0.0
```

The last form is the release gate. It scores the current tree against a
previously published one and exits non-zero unless every skill is strictly better
and fully compliant.

## The protected regions

Two regions are machine-managed. Ordinary edits cannot touch them; only an
epoch-level slow update writes there.

```markdown
<!-- SLOW_UPDATE_START -->
... guidance distilled across revisions, not from a single task ...
<!-- SLOW_UPDATE_END -->

<!-- APPENDIX_START -->
... execution reminders applied at run time ...
<!-- APPENDIX_END -->
```

Slow-update is for rules that survived many decks: the ones that changed behavior
for good. It is the opposite of a scratchpad. If a rule came from one bad render
and you have not seen it twice more, it belongs in the body, not in the protected
region. The appendix holds short reminders about scope and safety that apply on
every run.

The distinction matters because the body is expected to churn as the skill meets
new tasks, while the protected regions are the accumulated wisdom that new edits
must not quietly delete.

## The loop

1. **Collect failures.** Run real tasks with the skill loaded and write down what
   went wrong, not what felt wrong. Keep the artifact and the exact message.
2. **Propose bounded edits.** An edit patch is JSON: `add`, `replace` or `delete`,
   a handful per step, with a character budget.

   ```json
   {
     "skill": "pptx-generator",
     "max_edits": 4,
     "lr_budget": 1200,
     "edits": [
       {"op": "replace", "find": "exact unique text", "text": "replacement text"}
     ]
   }
   ```
3. **Gate it.** The candidate is scored on the same contract as the live file and
   lands only on strict improvement.

   ```bash
   python tools/skillopt_gate.py optimize --skill ppt --patch edit.json
   # exit 0 accepted, exit 1 rejected; the candidate is still on disk either way
   ```
4. **Review rejections.** A rejected candidate is kept in
   `skill-review-workspace/skillopt/` with its edits listed. Do not delete that
   buffer to make the numbers look good.
5. **Update the split.** Move a task from `test` to `selection` only when you are
   replacing it with a genuinely new held-out task.

Nothing in this loop edits the live document. An accepted candidate is copied
over `SKILL.md` by hand, in a commit you can read.

## Where the depth lives

`SKILL.md` is the part every task pays for, so it holds the workflow, the hard
rules and the report format. Everything a single step needs goes in a reference
and is linked from that step:

| Reference | Holds |
|---|---|
| `references/deck-schema.md` | The spec JSON, every layout and its fields, the script map. |
| `references/design-rules.md` | Type scale, narrative arcs, chart conventions, anti-patterns. |
| `references/template-editing.md` | Appending to and restyling a supplied deck. |
| `references/free-assets.md` | Licence facts checked at source, and the attribution they require. |
| `references/shared-scraping.md` | The research handoff to `ultimate-scrape-skill`. |

A new rule belongs in `SKILL.md` only if it must be known before the build starts.
If it only matters while writing one spec, it goes in `deck-schema.md`.

## When the gate runs out of signal

The contract score tops out at 100, which means it can tell you a skill is broken
or over budget, but it cannot tell two compliant skills apart. Past that point the
honest move is a real evaluation: run the `test`-split tasks against the candidate
and the live skill, and compare outcomes. SkillOpt does exactly this with model
rollouts. This offline gate deliberately does not pretend to.

So use the contract score for structure and hygiene, and deck results for quality.
A change that makes real decks worse is not rescued by a higher contract score.

## Failure modes this skill has already hit

Each line is something that actually happened, and the rule it produced:

- **Called a deck finished because it built.** Shipping needs the validator's
  verdict and a rendered look, not a zero exit code from the builder.
- **Shrank type to win an overflow warning.** The slide was carrying too much
  text. Rule: split or cut, never go under 12pt.
- **Described a preview image as a reusable template.** Rule: previews show
  treatment, they are not editable layouts and they carry no reuse permission.
- **Inherited a transition from a supplied template.** Rule: strip them from the
  output copy, never from the user's only source, and let the validator prove it.
- **Reported a visual review that never ran.** No renderer means no visual
  review, and the report says so.
