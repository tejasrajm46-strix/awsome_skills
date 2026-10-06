# SkillOpt gate report

Skill document contract and strict-improvement gate for `v3.0.0`.

SkillOpt treats each skill document as trainable text: a candidate edit is
accepted only when it strictly improves a held-out score, and a document that
fails any contract check is rejected regardless of its numeric score.

Baseline: v2.0.0

| Skill | Baseline | Current | Delta | Accepted | Tokens (before -> after) |
|---|---|---|---|---|---|
| `pptx-generator` | 23.81 | 100.00 | +76.19 | yes | 4748 -> 2399 |
| `word-generator` | 38.10 | 100.00 | +61.90 | yes | 1864 -> 2108 |
| `pdf-processor` | 38.10 | 100.00 | +61.90 | yes | 1629 -> 1808 |
| `xlsm-processor` | 38.10 | 100.00 | +61.90 | yes | 1308 -> 1643 |
| `smart-poster-designer` | 23.81 | 100.00 | +76.19 | yes | 2706 -> 2381 |
| `ultimate-scrape-skill` | 38.10 | 100.00 | +61.90 | yes | 1412 -> 1919 |

## Per-check evidence

### pptx-generator

- `frontmatter`: pass - name, description, license, compatibility, version
- `version`: pass - frontmatter version 'v3.0.0' vs catalog 'v3.0.0'
- `protected_regions`: pass - slow update 835 chars, appendix 2 lines
- `budget`: pass - ~2399 tokens (band 400-2400)
- `sections`: pass - 3 required sections present
- `evolution_ref`: pass - linked and present
- `evals_split`: pass - 5 evals (4 selection, 1 held-out test)
- `placeholders`: pass - none
- `stale_version`: pass - only v3.0.0

### word-generator

- `frontmatter`: pass - name, description, license, compatibility, version
- `version`: pass - frontmatter version 'v3.0.0' vs catalog 'v3.0.0'
- `protected_regions`: pass - slow update 774 chars, appendix 3 lines
- `budget`: pass - ~2108 tokens (band 400-2400)
- `sections`: pass - 3 required sections present
- `evolution_ref`: pass - linked and present
- `evals_split`: pass - 3 evals (2 selection, 1 held-out test)
- `placeholders`: pass - none
- `stale_version`: pass - only v3.0.0

### pdf-processor

- `frontmatter`: pass - name, description, license, compatibility, version
- `version`: pass - frontmatter version 'v3.0.0' vs catalog 'v3.0.0'
- `protected_regions`: pass - slow update 501 chars, appendix 3 lines
- `budget`: pass - ~1808 tokens (band 400-2400)
- `sections`: pass - 3 required sections present
- `evolution_ref`: pass - linked and present
- `evals_split`: pass - 3 evals (2 selection, 1 held-out test)
- `placeholders`: pass - none
- `stale_version`: pass - only v3.0.0

### xlsm-processor

- `frontmatter`: pass - name, description, license, compatibility, version
- `version`: pass - frontmatter version 'v3.0.0' vs catalog 'v3.0.0'
- `protected_regions`: pass - slow update 859 chars, appendix 3 lines
- `budget`: pass - ~1643 tokens (band 400-2400)
- `sections`: pass - 3 required sections present
- `evolution_ref`: pass - linked and present
- `evals_split`: pass - 4 evals (3 selection, 1 held-out test)
- `placeholders`: pass - none
- `stale_version`: pass - only v3.0.0

### smart-poster-designer

- `frontmatter`: pass - name, description, license, compatibility, version
- `version`: pass - frontmatter version 'v3.0.0' vs catalog 'v3.0.0'
- `protected_regions`: pass - slow update 831 chars, appendix 2 lines
- `budget`: pass - ~2381 tokens (band 400-2400)
- `sections`: pass - 3 required sections present
- `evolution_ref`: pass - linked and present
- `evals_split`: pass - 2 evals (1 selection, 1 held-out test)
- `placeholders`: pass - none
- `stale_version`: pass - only v3.0.0

### ultimate-scrape-skill

- `frontmatter`: pass - name, description, license, compatibility, version
- `version`: pass - frontmatter version 'v3.0.0' vs catalog 'v3.0.0'
- `protected_regions`: pass - slow update 921 chars, appendix 3 lines
- `budget`: pass - ~1919 tokens (band 400-2400)
- `sections`: pass - 3 required sections present
- `evolution_ref`: pass - linked and present
- `evals_split`: pass - 3 evals (2 selection, 1 held-out test)
- `placeholders`: pass - none
- `stale_version`: pass - only v3.0.0

