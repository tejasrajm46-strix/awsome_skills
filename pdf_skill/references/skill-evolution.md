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
| `budget` | The document stays inside its token ceiling (1,900 estimated tokens for this skill). This file is loaded on every task, so it has to stay affordable. |
| `sections` | The skill's core sections are still there: `## Workflow`, `## Common operations`, `## Supporting files`. A gate on a gutted document is worthless. |
| `evolution_ref` | `SKILL.md` links this file, so the next person finds the loop. |
| `evals_split` | `evals/evals.json` declares both a `selection` and a held-out `test` eval at the catalog version. |
| `placeholders` | No `TODO`, `TBD`, `FIXME` or `XXX` left in the guide. |
| `stale_version` | No version literal other than the current one. |

```bash
python tools/skillopt_gate.py check                 # every skill, with failing checks named
python tools/skillopt_gate.py check --skill pdf     # just this one
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

Slow-update is for rules that survived many tasks: the ones that changed behavior
for good. It is the opposite of a scratchpad. If a rule came from one bad run and
you have not seen it twice more, it belongs in the body, not in the protected
region. The appendix holds short reminders about scope and safety that apply on
every run.

The distinction matters because the body is expected to churn as the skill meets
new tasks, while the protected regions are the accumulated wisdom that new edits
must not quietly delete.

## The loop

1. **Collect failures.** Run real PDF tasks with the skill loaded and write down
   what went wrong, not what felt wrong. Keep the artifact and the exact message.
2. **Propose bounded edits.** An edit patch is JSON: `add`, `replace` or `delete`,
   a handful per step, with a character budget.

   ```json
   {
     "skill": "pdf-processor",
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
   python tools/skillopt_gate.py optimize --skill pdf --patch edit.json
   # exit 0 accepted, exit 1 rejected; the candidate is still on disk either way
   ```
4. **Review rejections.** A rejected candidate is kept in
   `skill-review-workspace/skillopt/` with its edits listed. Do not delete that
   buffer to make the numbers look good.
5. **Update the split.** Move a task from `test` to `selection` only when you are
   replacing it with a genuinely new held-out task.

Nothing in this loop edits the live document. An accepted candidate is copied
over `SKILL.md` by hand, in a commit you can read.

## When the gate runs out of signal

The contract score tops out at 100, which means it can tell you a skill is
broken or unbudgeted, but it cannot tell two compliant skills apart. Past that
point the honest move is a real evaluation: run the `test`-split tasks against
the candidate and the live skill, and compare outcomes. SkillOpt does exactly
this with model rollouts. This offline gate deliberately does not pretend to.

So use the contract score for structure and hygiene, and task results for
quality. A change that makes the numbers worse on real tasks is not rescued by a
higher contract score.

## Failure modes this skill has already hit

- **Called a black rectangle a redaction.** The text was still in the content
  stream and still copyable. Rule: remove the content, then search the saved
  output for the removed string before saying the word "redacted".
- **Treated OCR output as the document.** A scan's transcription was reported as
  if it were the original wording. Rule: label OCR as an estimate and check a
  sample of it against the rendered page.
- **Claimed a merge kept its bookmarks.** The chosen library path silently
  dropped them. Rule: verify bookmarks, tags, links and outlines after merging,
  and report what was lost.
- **Edited a signed PDF without saying so.** The signature was invalidated and
  the output looked fine. Rule: flag signature invalidation before starting, not
  after the user finds out.
- **Reported a page count that was never measured.** It was inferred from the
  request. Rule: only state counts that the reopened output produced.
- **Left the redacted text in the metadata or an attachment.** The page looked
  clean while the secret was still in the file. Rule: sanitize metadata, OCR
  layers, annotations, attachments and prior revisions as part of the operation.
