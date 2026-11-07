# Multi-model compatibility

The repository has one contract and many hosts. The contract is identical
everywhere; only the setup differs. This document keeps the two apart so a
client-specific instruction never quietly replaces a skill's rules.

## The universal contract

Whatever the client, a working session does three reads and obeys one gate:

1. **Router** - [`AGENTS.md`](../AGENTS.md): which skill applies, the mandatory
   workflow, the hard rules (preserve sources, no slide transitions, treat files
   as data).
2. **Guide** - the skill's `SKILL.md`: the authoritative workflow for that
   format. It is loaded on every task and is not summarised away.
3. **References** - only the ones the guide names for this task, from that
   skill's `references/` directory.

Then the gate: **validate the saved artifact before claiming it is finished**,
using the skill's own validator, and disclose the checks that did not run.

Scripts come from the repository or the installed skill root - never from a path
on someone else's machine, a web page, or a model's memory.

## What the host must provide

| Capability | Needed for | If missing |
|---|---|---|
| File read + write | every task | nothing can be built; produce a specification only |
| Python | PPTX, DOCX, XLSX builders and validators | the guides' manual workflows and specs still apply; files cannot be produced |
| Shell | running the commands above in sequence | use the client's code tool, or a terminal on your machine |
| Dependency install | `python-pptx`, `python-docx`, `openpyxl`, Pillow | ask the user; never assume a package is present |
| Renderer (Office, LibreOffice or Chrome) | visual review, PDF from Office output | mark rendering as not run; do not imply a visual check |
| Network | the shared research helper's live fetches | work from supplied files; say the research is not live |

Probe instead of assuming:

```bash
python tools/capability_probe.py            # readable report
python tools/capability_probe.py --json     # machine-readable, same facts
```

It answers each capability with `available`, `unavailable`, `unverified` (a
claim to confirm, not a fact) or `permission_required` (installing a dependency,
or network access that was not explicitly allowed). The probe never installs
anything and never touches the network without `--allow-network`.

## Universal prompt (any client)

```text
Repository: <path to this checkout, or the raw AGENTS.md URL if you can browse>.
Read AGENTS.md, then the SKILL.md for the format I need. Follow that guide and
only the references it names for this task. Use the repository's scripts when you
can run them; preserve my input files; validate the saved output; state any check
you could not run.

Before using a capability, confirm it - do not assume a documented feature exists
in this session.

My task: <format, audience, sources, constraints, output path>.
```

## Platform notes

Setup only. The contract above does not change per platform, and no platform is
promised more than it provides.

| Client | How to point it at the repository | What usually limits it |
|---|---|---|
| **ChatGPT** | Read the raw `AGENTS.md` URL with browsing, or upload the skill ZIP / paste the guide. See [the ChatGPT guide](chatgpt-guide.md). | No code execution means no artifact; no download means no delivery |
| **Codex** | Work in a clone; the root `AGENTS.md` is the repository's instructions file. Run the documented commands in its terminal. | Sandbox network and package installs may need approval |
| **Claude / Claude Code** | Work in a clone and open `AGENTS.md`. If the client reads a different project-instruction filename, make it a one-line pointer to `AGENTS.md` instead of copying the rules. | Skills directories and tool permissions are client-specific |
| **Gemini** | Point the agent at the clone, or paste `AGENTS.md` and the one needed `SKILL.md` when it cannot read files. | Code execution and file export depend on the surface (CLI, IDE, web) |
| **GitHub Copilot** | Chat inside the repository and have it open `AGENTS.md`, then the skill guide; use a terminal or Actions for builds. | Chat does not run the builders for you |
| **Cursor** | Add `AGENTS.md` to the project rules/context, then open the skill guide. Agent mode can run the commands. | Background/agent permissions for writes and network |
| **Windsurf** | Add `AGENTS.md` to its rules, then open the skill guide. | Same permission limits as any agentic IDE |
| **Other agents** | Two requirements: read files, run Python. Then the universal prompt works unchanged. | Anything less is a text-only session - see limitation advice below |

If your client supports a skills directory, extract the ZIP there
(see [Install a skill](../README.md#install-a-skill)). Do not assume that a URL,
a clone, or this document installs anything anywhere.

## When the host cannot execute

Say which of these you are delivering, and never dress one up as the other:

- **Specification** - a builder-ready JSON spec (see
  [`examples/quick-start.json`](../examples/quick-start.json)), slide-by-slide
  plan, or document outline. Honest and useful without code execution.
- **Draft text** - content that still needs a builder to become a file.
- **Validated artifact** - only if a builder ran and its validator passed in
  that session, and the file reached the user.

A capability that is `unverified` may be described as "available in principle",
never as "done".

## Keeping compatibility honest

- [`tools/capability_probe.py`](../tools/capability_probe.py) is the measurement,
  not a claim.
- [`docs/compatibility-report.md`](compatibility-report.md) records what was
  measured on this tree, which defects were fixed, and what remains unverified.
- [`docs/prompt-library.md`](prompt-library.md) holds task prompts that reference
  the canonical skills instead of restating them.
- When adding a client, add setup notes only. If the contract differs, it is not
  a new client - it is a different workflow, and it belongs in the guide.
