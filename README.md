<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/brand-lockup.svg">
    <img src="docs/assets/brand-lockup-light.svg" width="480" alt="Awesome Skills — Relay S" />
  </picture>
</p>

<h1 align="center">Awesome Skills</h1>

<p align="center"><strong>FROM INTENT TO ARTIFACT.</strong><br />Five focused AI skills. One shared research pipeline.</p>

<p align="center">
  <a href="https://github.com/tejasrajm46-strix/awsome_skills/releases/latest"><img src="https://img.shields.io/github/v/release/tejasrajm46-strix/awsome_skills?style=flat-square&color=176B60" alt="Latest release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-176B60?style=flat-square" alt="MIT"></a>
  <img src="https://img.shields.io/badge/main_skills-5-176B60?style=flat-square" alt="Five main skills">
  <img src="https://img.shields.io/badge/outputs-editable-176B60?style=flat-square" alt="Editable outputs">
</p>

<p align="center">
  <a href="#quick-start">Quick start</a> ·
  <a href="#skills">Skills</a> ·
  <a href="#see-the-output">Output</a> ·
  <a href="#skill-intelligence-layer">Architecture</a> ·
  <a href="#install-a-skill">Install</a> ·
  <a href="#documentation">Documentation</a> ·
  <a href="#quality-that-you-can-check">Quality</a>
</p>

<p align="center">
  <img src="design-previews/concept-a-ai-orchestration/hero.gif" width="100%"
       alt="Animated Awesome Skills hero: a teal orchestrator core lights up, six skill modules appear around it, links activate, the modules converge into a pipeline and a validated deliverable appears">
</p>

<sub align="center">Animated hero · static fallback: <a href="design-previews/concept-a-ai-orchestration/hero.svg">hero.svg</a></sub>

> **A good file is more than a good answer.** Keep content editable, preserve the
> user's source, and check the saved artifact before calling it finished.

## What this is

Awesome Skills is a collection of five production-focused document skills plus one
shared research helper, written to be read by an AI agent and verified by a human.
Each skill owns one output format, carries its own workflow and hard rules, and
ships the scripts that build and validate the artifact. Research is not duplicated
per format: one source register and one reviewed asset set feed every deliverable.

| | |
|---|---|
| **Formats** | PPTX · DOCX/DOTX · PDF · XLSX/XLSM/CSV/TSV · PNG/JPG/PDF/HTML posters |
| **Shared layer** | Bounded research, numbered source register, reviewed assets, validated handoff |
| **Entry point** | [`AGENTS.md`](AGENTS.md) for agents · [`skills.json`](skills.json) for machines |
| **License** | [MIT](LICENSE) for code and original artwork |

The design intent is narrow: **editable output, preserved sources, checked
artifacts** — and no claim that a check ran when it did not.

## Quick start

### 1 · Give your agent the entry point

```text
https://raw.githubusercontent.com/tejasrajm46-strix/awsome_skills/main/AGENTS.md
```

Paste this prompt into a browsing-enabled, tool-enabled agent:

```text
Read https://raw.githubusercontent.com/tejasrajm46-strix/awsome_skills/main/AGENTS.md
Follow the relevant SKILL.md and its references. Use the provided scripts when
available, preserve input files, validate saved outputs, and state any checks
you could not run.

My task: [format, audience, source files, constraints and output path].
```

Want only one format? Share its direct guide, for example:
`https://raw.githubusercontent.com/tejasrajm46-strix/awsome_skills/main/ppt_skill/SKILL.md`.
The [catalog](skills.json) gives machine-readable identities and routing.

**A link is not an automatic installation.** ChatGPT and other clients need
browsing to read GitHub and code/file tools to run builders and return actual
files. A text-only session can create an outline/spec, not honestly claim a
rendered Office file. Follow your client's supported skill location and permissions.

Working in ChatGPT? Read [the ChatGPT guide](docs/chatgpt-guide.md). Other clients:
[multi-model compatibility](docs/multi-model-compatibility.md). Copy-paste task
prompts: [the prompt library](docs/prompt-library.md). Measured host capabilities and
the v3.2.0 defect fixes: [the compatibility report](docs/compatibility-report.md).

### 2 · Install one skill

Download a ZIP from [GitHub Releases](https://github.com/tejasrajm46-strix/awsome_skills/releases)
or from the table below, then extract it into **your client's documented skills
directory**. Full instructions: [Install a skill](#install-a-skill).

### 3 · Build and validate

```bash
python -m pip install python-pptx
python ppt_skill/scripts/build_deck.py examples/quick-start.json -o deck.pptx
python ppt_skill/scripts/validate_deck.py deck.pptx --expect 5 --strict
```

A build that returns no error is not a validated deck. Run the validator, then
open the file; [Workflows](#workflows) has the equivalent chain for every format.

## Skills

| Skill | Built for | Read the guide | Download v3.2.0 |
|---|---|---|---|
| **PowerPoint** | Editable slides, native charts and diagrams, measured layouts and original visual references. **No slide transitions.** | [ppt_skill](ppt_skill/SKILL.md) | [PPTX ZIP](releases/skills/pptx-generator-v3.2.0.zip) |
| **Word** | Professional DOCX creation, existing DOCX/DOTX inspection and package-aware editing guidance. | [word_skill](word_skill/SKILL.md) | [Word ZIP](releases/skills/word-generator-v3.2.0.zip) |
| **PDF** | Text/table extraction, OCR, merge/split, forms, creation and redaction workflows. | [pdf_skill](pdf_skill/SKILL.md) | [PDF ZIP](releases/skills/pdf-processor-v3.2.0.zip) |
| **Excel** | XLSX and XLSM in one place: formulas, data cleanup, workbook inventory and macro-preservation safeguards; CSV/TSV too. | [xlsm_skill](xlsm_skill/SKILL.md) | [Excel ZIP](releases/skills/xlsm-processor-v3.2.0.zip) |
| **Poster** | Original posters, flyers and infographics, plus careful template-reference redesign. | [poster_skill](poster_skill/SKILL.md) | [Poster ZIP](releases/skills/smart-poster-designer-v3.2.0.zip) |
| **Shared research** | Bounded image/data/style extraction and source handoff for **all five**; optional for local-only tasks. | [ultimate-scrape-skill](ultimate-scrape-skill/SKILL.md) | [Helper ZIP](releases/skills/ultimate-scrape-skill-v3.2.0.zip) |

Each format ZIP includes a portable copy of the shared helper. Install one skill
without leaving its research guidance or scripts missing. Multiple deliverables
share one numbered source register and one selected asset set.

## See the output

Real decks, real files. Every frame below is a rendered export from a
`.pptx` built with these skills, not a mockup — click any slide to open
the full-resolution image.

**Porsche 911 — performance brief** (14 slides)

|  |  |  |
| --- | --- | --- |
| <img src="docs/assets/gallery/porsche-911/slide-01.jpg" width="260" alt="Porsche 911 — performance brief slide 1 of 14" /> | <img src="docs/assets/gallery/porsche-911/slide-02.jpg" width="260" alt="Porsche 911 — performance brief slide 2 of 14" /> | <img src="docs/assets/gallery/porsche-911/slide-03.jpg" width="260" alt="Porsche 911 — performance brief slide 3 of 14" /> |
| <img src="docs/assets/gallery/porsche-911/slide-04.jpg" width="260" alt="Porsche 911 — performance brief slide 4 of 14" /> | <img src="docs/assets/gallery/porsche-911/slide-05.jpg" width="260" alt="Porsche 911 — performance brief slide 5 of 14" /> | <img src="docs/assets/gallery/porsche-911/slide-06.jpg" width="260" alt="Porsche 911 — performance brief slide 6 of 14" /> |
| <img src="docs/assets/gallery/porsche-911/slide-07.jpg" width="260" alt="Porsche 911 — performance brief slide 7 of 14" /> | <img src="docs/assets/gallery/porsche-911/slide-08.jpg" width="260" alt="Porsche 911 — performance brief slide 8 of 14" /> | <img src="docs/assets/gallery/porsche-911/slide-09.jpg" width="260" alt="Porsche 911 — performance brief slide 9 of 14" /> |
| <img src="docs/assets/gallery/porsche-911/slide-10.jpg" width="260" alt="Porsche 911 — performance brief slide 10 of 14" /> | <img src="docs/assets/gallery/porsche-911/slide-11.jpg" width="260" alt="Porsche 911 — performance brief slide 11 of 14" /> | <img src="docs/assets/gallery/porsche-911/slide-12.jpg" width="260" alt="Porsche 911 — performance brief slide 12 of 14" /> |
| <img src="docs/assets/gallery/porsche-911/slide-13.jpg" width="260" alt="Porsche 911 — performance brief slide 13 of 14" /> | <img src="docs/assets/gallery/porsche-911/slide-14.jpg" width="260" alt="Porsche 911 — performance brief slide 14 of 14" /> |  |

**BMW M4 CS — performance brief** (9 slides)

|  |  |  |
| --- | --- | --- |
| <img src="docs/assets/gallery/bmw-m4-cs/slide-01.jpg" width="260" alt="BMW M4 CS — performance brief slide 1 of 9" /> | <img src="docs/assets/gallery/bmw-m4-cs/slide-02.jpg" width="260" alt="BMW M4 CS — performance brief slide 2 of 9" /> | <img src="docs/assets/gallery/bmw-m4-cs/slide-03.jpg" width="260" alt="BMW M4 CS — performance brief slide 3 of 9" /> |
| <img src="docs/assets/gallery/bmw-m4-cs/slide-04.jpg" width="260" alt="BMW M4 CS — performance brief slide 4 of 9" /> | <img src="docs/assets/gallery/bmw-m4-cs/slide-05.jpg" width="260" alt="BMW M4 CS — performance brief slide 5 of 9" /> | <img src="docs/assets/gallery/bmw-m4-cs/slide-06.jpg" width="260" alt="BMW M4 CS — performance brief slide 6 of 9" /> |
| <img src="docs/assets/gallery/bmw-m4-cs/slide-07.jpg" width="260" alt="BMW M4 CS — performance brief slide 7 of 9" /> | <img src="docs/assets/gallery/bmw-m4-cs/slide-08.jpg" width="260" alt="BMW M4 CS — performance brief slide 8 of 9" /> | <img src="docs/assets/gallery/bmw-m4-cs/slide-09.jpg" width="260" alt="BMW M4 CS — performance brief slide 9 of 9" /> |

> **Samples, not a license.** These renders come from decks supplied by the
> repository owner and are published to show skill output. Vehicle imagery,
> trademarks and model names belong to their respective owners and are not
> licensed for reuse through this repository. Provenance for every frame is
> recorded in [porsche-911/sources.json](docs/assets/gallery/porsche-911/sources.json)
> and [bmw-m4-cs/sources.json](docs/assets/gallery/bmw-m4-cs/sources.json).

### Other rendered examples

![Existing rendered PowerPoint example.](docs/assets/presentation-preview.png)

![Existing rendered Word example.](docs/assets/document-preview.png)

[Five-slide starter](examples/quick-start.json) · [Word starter](examples/word-quick-start.json) ·
[Shared human-evolution specification](examples/human-evolution.json)

Metrics in these examples may be illustrative. They are not performance
claims, and the frames above are new renders of the decks rather than
stock screenshots.

## Skill intelligence layer

A capable agent should not load six skill documents to answer one request, and
should not improvise a workflow it cannot later audit. `tools/orchestrator.py`
is the deterministic half of that: a registry, progressive loader, planner,
controlled executor and state machine that a reasoning LLM drives as tools.

```mermaid
flowchart LR
    T["Task request"] --> I["interpretation.json<br/>authored by the host LLM"]
    I --> R["Registry<br/>skills.json + SKILL.md metadata"]
    R --> P["Planner<br/>validated dependency DAG"]
    P --> E["Executor<br/>allowlisted python / node scripts"]
    E --> O["Deliverables"]
    E --> L[("task-state.json<br/>transitions, attempts, evidence")]
    I -. "manual steps recorded via done --evidence" .-> L
```

**Division of labor.** The host LLM reasons: it writes a task interpretation
(objective, deliverables, research needs) and performs every `manual` step -
research, spec writing, render review, the delivery note. The repository
tooling does everything checkable: discovery, metadata validation, plan
generation, command execution and the ledger.

```bash
python tools/skill_registry.py index                     # what exists, validated
python tools/skill_registry.py discover --formats pptx,pdf --json
python tools/orchestrator.py new-task  work/tasks/t1 --objective "Research X; build deck + report"
python tools/orchestrator.py interpret work/tasks/t1 --interpretation interp.json
python tools/orchestrator.py load      work/tasks/t1 --skills ppt word --references references/deck-schema.md
python tools/orchestrator.py plan      work/tasks/t1    # dependency DAG, allowlisted commands
python tools/orchestrator.py run       work/tasks/t1    # command steps; manual steps await the LLM
python tools/orchestrator.py done      work/tasks/t1 --step s2-research --note "register: 3 sources"
python tools/orchestrator.py status    work/tasks/t1
python tools/orchestrator.py report    work/tasks/t1
```

- **Progressive loading.** Stage A loads ~90-token metadata for every candidate;
  stage B loads only the selected skills' authoritative guides; stage C loads
  named references. The ledger records exactly which files entered the task and
  at what measured token cost - the e2e test proves an irrelevant skill is
  never loaded and staged context is a fraction of loading everything.
- **Planning.** The interpretation is validated against the catalog (unknown
  format → refuse; research needed → shared helper included), then expanded
  into a DAG: inputs → research → handoff validation → builds → per-deliverable
  validation → render review → consistency → manifest → delivery. Modes
  (`fast`/`balanced`/`deep`) change depth - render review, consistency,
  repair budget - never safety: every mode plans validation for every
  deliverable.
- **Controlled execution.** Commands are python/node only, inside allowlisted
  skill/tool roots (symlinks resolved before the containment check), no shell,
  no chaining; real return codes or it did not happen. A four-status protocol
  separates what the evidence supports: `command_completed` (the executor ran
  it), `manual_pending`, `manual_completed` (the host supplied an evidence
  file) and `validated` (an independent validator actually ran - never
  self-assigned). Failed steps are retried only inside a bounded REPAIR cycle.
- **Resume safety.** The ledger hashes the plan, each executed script and each
  loaded guide; a task resumed after any of them changed re-runs the affected
  steps instead of trusting stale results.
- **State.** Every transition, load, attempt and limitation lands in
  `task-state.json` - a crashed task resumes from disk.
- **Caching.** Content-hash keyed metadata cache: a modified guide is a new
  hash, so stale instructions cannot be served; hit rate is measured, not
  assumed.
- **Capability detection.** `python tools/capability_probe.py --json` reports what
  this host can actually do - document builds, rendering, shell, git, network -
  as `available`, `unavailable`, `unverified` or `permission_required`. Library
  probes build and discard a real artifact; the network is never touched without
  `--allow-network`. A capability that is not `available` is never described as
  performed.

This layer orchestrates the five skills and the shared helper; it is not a
sixth skill and executes nothing outside the repository's own scripts. The
research half of the contract (register, asset review, handoff bundle) is
described under [Reuse researched inputs](#reuse-researched-inputs).

## Workflows

**Understand → preserve → gather only what is missing → build/edit → validate → render/review.**

### Build a five-slide deck

```bash
python -m pip install python-pptx
python ppt_skill/scripts/build_deck.py examples/quick-start.json -o deck.pptx
python ppt_skill/scripts/validate_deck.py deck.pptx --expect 5 --strict
```

Inspect the [original PPT reference library](ppt_skill/assets/README.md) first.
All references are original, publication-safe layout studies. The builder removes
inherited transitions from an output copy; validation rejects any remaining.

### Build a Word brief

```bash
python -m pip install python-docx
python word_skill/scripts/build_doc.py examples/word-quick-start.json -o brief.docx
python word_skill/scripts/validate_doc.py brief.docx --strict
```

The builder creates new documents. For existing files, start with the
[OOXML preservation guide](word_skill/references/ooxml-review.md), not a blind rebuild.

### Inspect workbook/PDF structure

```bash
python xlsm_skill/scripts/inspect_workbook.py model.xlsx --json
python xlsm_skill/scripts/inspect_xlsm.py model.xlsm --json
python pdf_skill/scripts/inspect_pdf.py report.pdf --json
```

These use the standard library. They do not calculate formulas, execute VBA,
scan for malware or prove secure redaction. Their guides distinguish each check.

### Reuse researched inputs

```bash
python ultimate-scrape-skill/scripts/route.py "research for slides and Word" --json
python ultimate-scrape-skill/scripts/extract_parts.py \
  --html-file ultimate-scrape-skill/tests/fixture-product.html \
  --base-url https://example.com/product --parts images,data,template \
  --out outputs/research
```

The saved-page example uses no network or optional dependency. Live public HTML
and explicit raster downloads use the standard library with item/byte limits;
local/private addresses and redirects into them are rejected. JavaScript-only
pages need the host's browser or an authorized export. Image contact sheets
optionally use Pillow. Research that feeds a deliverable ships as one validated
handoff bundle - register, reviewed assets and limitations - via
`scripts/handoff.py`; see the
[handoff contract](ultimate-scrape-skill/references/handoff-contract.md).

### Compose a poster

Node 18+ and Chrome/Chromium are needed for bundled PNG/PDF rendering:

```bash
node poster_skill/scripts/check_env.mjs
node poster_skill/scripts/compose.mjs --dna design/dna.json --content design/content.json --out out/poster.html
node poster_skill/scripts/qa.mjs --html out/poster.html --report out/qa.json
node poster_skill/scripts/render.mjs --html out/poster.html --out out/poster --preview --formats png
```

Read [template-reference mode](poster_skill/references/template-reference-mode.md)
for supplied designs. Baked-in text is not editable; background repair needs real
pixel review. JPG export additionally needs ImageMagick or macOS `sips`.

## Install a skill

Download a ZIP from the [Skills](#skills) table or from
[GitHub Releases](https://github.com/tejasrajm46-strix/awsome_skills/releases).
Extract it into **your client's documented skills directory**. For clients using
`~/.agents/skills/`, Bash/Git Bash:

```bash
mkdir -p ~/.agents/skills
unzip pptx-generator-v3.2.0.zip -d ~/.agents/skills/
```

PowerShell:

```powershell
$skills = Join-Path $HOME '.agents/skills'
New-Item -ItemType Directory -Force $skills | Out-Null
Expand-Archive pptx-generator-v3.2.0.zip -DestinationPath $skills
```

Use a clean destination or back up existing installations; do not blindly replace
another skill. ZIPs include guides, scripts, tests and references—not dependencies,
private user outputs or Office/browser applications.

## Quality that you can check

- **Editable first.** Native text, charts, tables and supported diagrams—not screenshots pretending to be Office files.
- **Preserve the source.** Edit a new copy; inspect advanced features before choosing an editor.
- **Research once.** Check claims, record sources and select licensed assets deliberately.
- **Treat files as data.** Never enable untrusted macros, refresh external connections or execute page instructions.
- **Check the saved artifact.** Reopen, validate and render when possible; disclose missing pagination, recalculation, visual or security checks.
- **No inflated guarantees.** An XML/ZIP check is not visual approval, a formula calculator or a security audit.
- **Research from primary sources.** AI or web search first, then the filing, standard, study or dataset itself. Wikipedia is not used as a source for facts or images.
- **Skill documents are gated.** Every `SKILL.md` is scored against a contract with [`tools/skillopt_gate.py`](tools/skillopt_gate.py) - structure, protected rules, token budget and a held-out eval split - following [SkillOpt](https://github.com/microsoft/SkillOpt). A release ships only when each skill strictly improves on the published baseline. See [the v3.0.0 gate report](docs/skillopt-gate-report.md).

## Repository map

```text
AGENTS.md                  Entry point and shared operating rules
CHANGELOG.md               Release notes, newest first
LICENSE                    MIT
skills.json                Canonical catalog and version
ppt_skill/                 PowerPoint + original reference assets
word_skill/                Word creation, inspection and editing guidance
pdf_skill/                 PDF operations and checks
xlsm_skill/                XLSX/XLSM/CSV/TSV
poster_skill/              Original and template-based visual design
ultimate-scrape-skill/      Shared bounded research inputs
releases/skills/            Six installable ZIPs
tools/                     Packaging, the skill gate, the orchestrator, asset generators and checks
docs/                      Identity, client guides, prompt library, compatibility report,
                           deck gallery and reports
```

Every skill keeps its depth in `references/`: `SKILL.md` carries the workflow and
is loaded on every task, and the reference files are read on demand.
`references/skill-evolution.md` in each skill explains how to change that skill
without regressing it.

Local archives, dependencies, caches, videos and private deliverables are excluded.
There is no duplicate `xlsx_skill` and no OneTake video in this publication.

## Documentation

**[Getting started](#quick-start)** · [Install a skill](#install-a-skill) · [Workflows](#workflows) · [Quality checks](#quality-that-you-can-check)

| Category | Documents |
|---|---|
| **Skills** | [PowerPoint](ppt_skill/SKILL.md) · [Word](word_skill/SKILL.md) · [PDF](pdf_skill/SKILL.md) · [Excel](xlsm_skill/SKILL.md) · [Poster](poster_skill/SKILL.md) · [Shared research](ultimate-scrape-skill/SKILL.md) |
| **Agent integration** | [Entry point](AGENTS.md) · [ChatGPT guide](docs/chatgpt-guide.md) · [Multi-model compatibility](docs/multi-model-compatibility.md) · [Prompt library](docs/prompt-library.md) |
| **Orchestration** | [Skill intelligence layer](#skill-intelligence-layer) · [Orchestrator](tools/orchestrator.py) · [Task planner](tools/task_planner.py) · [Task state](tools/task_state.py) · [Output manifest](tools/output_manifest.py) · [Capability probe](tools/capability_probe.py) |
| **Examples** | [Five-slide starter](examples/quick-start.json) · [Word starter](examples/word-quick-start.json) · [Human-evolution specification](examples/human-evolution.json) · [Rendered output](#see-the-output) |
| **Research** | [Handoff contract](ultimate-scrape-skill/references/handoff-contract.md) · [OOXML review](word_skill/references/ooxml-review.md) · [Template-reference mode](poster_skill/references/template-reference-mode.md) |
| **Validation** | [Compatibility report](docs/compatibility-report.md) · [SkillOpt gate](tools/skillopt_gate.py) · [Gate report](docs/skillopt-gate-report.md) · [Release checks](tools/check_release.py) |
| **Releases** | [CHANGELOG](CHANGELOG.md) · [Releases](https://github.com/tejasrajm46-strix/awsome_skills/releases) · [Packages](releases/skills/) · [Release workflow](.github/workflows/release.yml) |
| **Project** | [Organization report](docs/organization-report.md) · [Brand masters](docs/brand/README.md) · [License](LICENSE) |

## Test and package

```bash
python tools/package_skill.py --skill all --version v3.2.0
python tools/verify_repository.py
python tools/check_release.py
python tools/skillopt_gate.py check
```

<details>
<summary><strong>All verification commands</strong></summary>

```bash
python tools/test_check_release.py
python tools/test_output_manifest.py
python tools/test_package_skill.py
python tools/test_skillopt_gate.py
python ppt_skill/tests/test_layout_rules.py
python ppt_skill/tests/test_extract_office_assets.py
python word_skill/tests/test_doc_rules.py
python word_skill/tests/test_inspect_docx.py
python pdf_skill/tests/test_inspect_pdf.py
python xlsm_skill/tests/test_inspect_workbook.py
python xlsm_skill/tests/test_inspect_xlsm.py
python ultimate-scrape-skill/tests/test_scraping.py
python ultimate-scrape-skill/tests/test_source_register.py
python ultimate-scrape-skill/tests/test_security.py
python ultimate-scrape-skill/tests/test_handoff.py
python tools/test_skill_registry.py
python tools/test_skill_cache.py
python tools/test_task_planner.py
python tools/test_task_state.py
python tools/test_task_executor.py
python tools/test_orchestrator_e2e.py
python tools/test_orchestration_defects.py
python tools/test_capability_probe.py
node poster_skill/tests/test_template_mode.mjs
```

</details>

Verification includes script syntax, local links, shared-file synchronization,
original asset provenance and deterministic extracted-package checks. The poster
integration test renders through Chrome. [Release automation](.github/workflows/release.yml)
checks all skills and publishes all six packages on a version-tag push;
`tools/check_release.py` is the same release-consistency gate runnable before
you tag, and `tools/output_manifest.py` records per-task proof of what was
generated, validated, rendered and visually inspected.

To see the gate the published documents had to improve on, score the current tree
against the extracted v2.0.0 baseline. It exits non-zero unless every skill is
fully compliant and strictly better than what was published before:

```bash
python tools/skillopt_gate.py check --baseline v2.0.0
```

## Identity and licensing

The approved **Relay S** is an original routed monogram: one idea carried into a
finished artifact. Graphite, electric lime and warm white make the README clear
without relying on borrowed company logos. The supplied logo-design skill was
used for research, construction, audits and export; its trademark library is not
included. [Logo masters and usage guide](docs/brand/README.md).

Original repository code and layout artwork: [MIT](LICENSE). Bundled Geist font:
[SIL Open Font License](docs/assets/fonts/OFL.txt). Unclear imported scraping code
and third-party PPT previews were replaced with original implementations/assets
before publication; originals remain private local records. See
[the organization report](docs/organization-report.md).

<p align="center"><strong>Make it clear. Keep it editable. Check what you ship.</strong></p>
