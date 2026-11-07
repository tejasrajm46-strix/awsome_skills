# Using Awesome Skills in ChatGPT

This guide describes what actually works in a ChatGPT session, what does not, and
the shortest prompt that gets a real file instead of a description of one.

**A GitHub link is not an installation.** Pasting a raw URL does not add a skill
to ChatGPT. It gives the model text to read - and only when that session can
fetch pages. Installation means putting a skill into a location your client
documents and supports; see [Install a skill](../README.md#install-a-skill).

## 1. What the session must provide

| Requirement | When it is present | When it is absent |
|---|---|---|
| Browsing, or the file pasted/uploaded | The model can read `AGENTS.md` and a `SKILL.md` | Nothing loads; upload the files or paste their text |
| A code-execution tool (often called Advanced Data Analysis or Code Interpreter, depending on plan) | Builders and validators run; you get a real `.pptx`/`.docx`/`.pdf`/`.xlsx` | You get a specification, a narrative, or a checklist - not a file |
| File download from the session | The generated artifact reaches your machine | The work stays in the sandbox; say so rather than implying delivery |

Feature names and plan limits change. The distinction that does not change is
this: **reading text is not executing code.** A session that can read the guide
but cannot run Python cannot honestly produce a validated Office file.

## 2. Entry point

```text
https://raw.githubusercontent.com/tejasrajm46-strix/awsome_skills/main/AGENTS.md
```

`AGENTS.md` is the router: it maps a task to one of five skills plus the shared
research helper, and states the workflow and hard rules. Every individual guide
is self-contained, so a session that can only read one file should read the
skill's `SKILL.md` instead.

If browsing is unavailable, paste this file's contents, or upload the repository
ZIP. If you upload files, prefer the ZIP for the single skill you need - it
contains the guide, references, scripts and a copy of the shared helper.

## 3. Skill discovery

| You need | Guide |
|---|---|
| Slides / PPTX | `ppt_skill/SKILL.md` |
| Word / DOCX / DOTX | `word_skill/SKILL.md` |
| PDF extraction, OCR, merge, forms | `pdf_skill/SKILL.md` |
| Excel / XLSX / XLSM / CSV / TSV | `xlsm_skill/SKILL.md` |
| Poster, flyer, infographic | `poster_skill/SKILL.md` |
| Research, sources, images for any of the above | `ultimate-scrape-skill/SKILL.md` |

Ask for the routing explicitly when the format is ambiguous:

```text
Using the Awesome Skills router, tell me which skill applies to: a 10-slide
investor deck plus a two-page Word brief, both sourced from the attached PDF.
Name the guides you would read and what you need from me before starting.
```

## 4. Activating one skill

```text
Read ppt_skill/SKILL.md from the Awesome Skills repository and follow it exactly.

Task: build a 10-slide deck on [topic] for [audience].
Source: [attached file / the facts in this message].
Constraints: editable native slides, no slide transitions, 16:9,
save as deck.pptx.

Before building, list the questions you must ask me. Then build, validate the
saved file, and report which checks you actually ran and which you could not.
```

Keep the request in the terms the guide uses: format, audience, sources,
constraints, output path. The guide's own workflow fills in the rest; do not
paraphrase its rules from memory.

## 5. Providing source files

- Upload the original and name it ("`q3-results.xlsx`, preserve it").
- For an existing document you want edited, say so explicitly; the word and
  Excel guides prescribe inspection before any edit, and editing a copy.
- Do not paste a binary as text. If upload is impossible, describe the structure
  and ask for a plan rather than an invented result.
- For research, give the question and the standard of evidence you need. The
  shared helper records one claim to one source; a chat answer without sources
  is not that register.

## 6. Multi-skill workflows

One request can produce several formats. The efficient shape is one research
pass, one source register, then independent builds:

```text
Read AGENTS.md. Produce a 12-slide deck (deck.pptx), a 2-page brief (brief.docx)
and a one-page poster (poster.png) on [topic].
Use the shared research helper once: one numbered source register, one reviewed
asset set, reused by all three outputs. Do not re-research per format.
Cite register IDs in the deck and the brief. Validate each saved file.
```

State the deliverables and their paths up front. If the session can run the
repository tooling, the orchestrator records discovery, planning, execution and
validation in one task ledger - see [the README](../README.md#skill-intelligence-layer).

## 7. Producing output when code execution exists

```bash
python -m pip install python-pptx          # ask before installing anything
python ppt_skill/scripts/build_deck.py spec.json -o deck.pptx
python ppt_skill/scripts/validate_deck.py deck.pptx --expect 10 --strict
```

Ask the model to paste the validator output verbatim. A build that returns no
error is not the same as a deck that passes validation, and neither is the same
as a deck you have looked at.

## 8. Validating what you received

| Format | Minimum check |
|---|---|
| PPTX | `python ppt_skill/scripts/validate_deck.py deck.pptx --strict` |
| DOCX | `python word_skill/scripts/validate_doc.py brief.docx --strict` |
| PDF | `python pdf_skill/scripts/inspect_pdf.py report.pdf --json` |
| XLSX/XLSM | `python xlsm_skill/scripts/inspect_workbook.py model.xlsx --json` |
| Poster | `node poster_skill/scripts/qa.mjs --html out/poster.html --report out/qa.json` |

Then open the saved file. Validation checks structure and content; it does not
prove the layout looks right, that formulas recalculated, or that redaction is
complete. Ask for the render or visual review to be reported as **not run** when
it was not run.

## 9. When code execution is unavailable

Honest outcomes in a text-only session:

- a slide-by-slide outline and a builder specification in the shape of
  [`examples/quick-start.json`](../examples/quick-start.json);
- a source list with claims mapped to sources, clearly marked unverified;
- a review checklist for a file you will build elsewhere.

Dishonest outcomes, which this repository's rules forbid claiming: a rendered
file, a validated artifact, a page count, or a formula result that was never
computed in that session.

## 10. Quick checklist

1. Does this session have browsing, code execution, and file download?
2. Did you read `AGENTS.md`, or at least the relevant `SKILL.md`?
3. Did you state format, audience, sources, constraints and output path?
4. Was the source file preserved rather than overwritten?
5. Did the validator actually run, and was its output reported?
6. Were missing renders, recalculations or reviews disclosed as missing?
