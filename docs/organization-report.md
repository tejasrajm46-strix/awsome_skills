# Organization and publication report

## Final distribution

Five main folders: `ppt_skill`, `word_skill`, `pdf_skill`, `xlsm_skill`,
`poster_skill`. One shared helper: `ultimate-scrape-skill`.
Ordinary XLSX/CSV/TSV tools and macro-enabled XLSM safeguards are consolidated
under `xlsm_skill`; no separate duplicate XLSX folder is published.

[Agent entry point](../AGENTS.md) · [catalog](../skills.json) · [README](../README.md)

## ZIP selection and preservation

All 13 original/local ZIPs were inspected. Older PPT/Word releases and test ZIPs
were not blindly extracted over live sources: live code contained newer inspectors,
asset extractors and fixes. Matching PDF/Excel releases were consolidated from
source. Poster kept the newer QA script. Background-demo and assignment ZIPs were
identified as deliverables, not installable skills.

Original ZIPs, duplicate Excel source, native template library and full-resolution
previews remain preserved in ignored `local-archive/`; user deliverables remain
in ignored `outputs/`. Nothing from those private folders is pushed or packaged.
Generated caches, dependencies, editor metadata and obsolete transition tooling
are excluded from the public distribution.

## Publication rights resolved by replacement

The scraping ZIP lacked a license file and PPT preview redistribution rights were
unclear. The user chose **only cleared/original material** for publication.

- Imported scraper/harvest/downloader code and fixture were replaced with original
  standard-library implementations and tests. Retired sources remain private.
- Third-party PPT previews were replaced with six original editorial layout
  studies, a source/license register and contact sheets. Reference assets remain
  central to the PPT workflow, not discarded.
- The supplied logo-design skill guided original geometry, comparison, audits and
  export; its trademark logo library is not shipped.
- Original code, Relay S artwork and layout studies are under root MIT. Bundled
  Geist font retains its [SIL OFL](assets/fonts/OFL.txt).
- The user canceled video publication. No OneTake runtime, composition, audio,
  MP4 or GIF is included in the repository/release.

## Portable skills and policy

Each format ZIP includes one top-level discoverable skill folder and a generated
canonical helper copy under `shared/ultimate-scrape-skill/`. Word includes the
canonical local Office image extractor owned by PPT. All shared references are
synchronized. Installation is tested from outside the repository.

Generated PPTs contain **zero slide transitions**; inherited transitions are
removed from output copies and the validator rejects remaining transition markup.
Macro inspection never executes VBA. Spreadsheet inventory never claims formula
recalculation. PDF inventory never claims secure redaction. Rendering and saved-file
structure are separate checks.

## Verification and remaining limits

The documented suites cover catalog/frontmatter, local links, script syntax,
shared synchronization, original asset provenance, deterministic archives,
extracted helper execution, PPT layout/policy, Word structure, PDF inventory,
ordinary/macro Excel inventory and actual Chrome poster rendering.

The original replacement helper is tested offline with synthetic HTML and in-memory
responses: item/byte limits, URL validation, correct raster extensions, deduplication,
partial cleanup and manifest failure reporting. Live source compatibility is not
promised; JavaScript pages need the host browser or an authorized export.

The logo has original filled geometry and outlined typography; legal trademark
clearance and print proofing are not performed. A GitHub link still needs browsing
and code/file tools—no automatic universal-agent installation is claimed.

## Release target

Publication target: `https://github.com/tejasrajm46-strix/awsome_skills`.
Release: `v2.0.0`, six installable skill ZIPs, no video.
Final remote verification is recorded after push/release; local completion alone
is not claimed to prove a GitHub-hosted result.
