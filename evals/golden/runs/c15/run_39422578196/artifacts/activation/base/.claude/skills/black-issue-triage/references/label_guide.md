# Label guide for first-pass triage

Black's label groups (from `docs/contributing/issue_triage.md`): **T** = type, **C** =
category, **F** = formatting area, **S** = status, **R** = resolution. Issue templates
already add a `T:` label (bug report → `T: bug`, feature → `T: enhancement`, style →
`T: style`, docs → `T: documentation`), so most issues arrive with one type label. The
agent cannot remove labels. If the template type is wrong, add the right `T:` label and
say so in the comment.

## Agent may apply (enforced in `.github/workflows/issue-triage.md` safe-outputs)

| Label | Use when |
|---|---|
| `T: bug` | Something isn't working (crash, wrong/unstable output, CLI misbehaves) |
| `T: enhancement` | New feature/option request (e.g. support for a new PEP) |
| `T: style` | "Blackened code should look different" — a style preference/proposal |
| `T: documentation` | Docs are wrong, missing, or have typos |
| `T: user support` | Reporter needs help using/configuring Black |
| `C: crash` | Black errors out: `INTERNAL ERROR`, "not equivalent to the source", traceback |
| `C: invalid code` | Black produced invalid Python ("produced invalid code") |
| `C: unstable formatting` | Second pass differs ("different code on the second pass") |
| `C: parser` | Black fails to parse valid code, or a new syntax needs grammar support |
| `C: preview style` | The problem only occurs with `--preview`/`--unstable` |
| `C: target version` | About `--target-version` or its auto-detection |
| `C: configuration` | CLI options, `pyproject.toml` |
| `C: file collection` | include/exclude, `.gitignore`, cache, file discovery |
| `C: jupyter` | `.ipynb` / notebooks |
| `C: packaging` | installation, wheels, platform builds |
| `C: integrations` / `C: vim` | editor plugins / the Vim plugin |
| `C: performance` | speed |
| `C: api` | Python API usage |
| `F: fmtskip` / `F: fmtoff` | `# fmt: skip` / `# fmt: off`/`on` handling |
| `F: comments`, `F: docstrings`, `F: empty lines`, `F: linebreak`, `F: linetoolong`, `F: parentheses`, `F: strings`, `F: trailing comma`, `F: symmetry` | the formatting area involved |
| `S: needs repro` | A bug claim without a working minimal reproduction |
| `S: awaiting response` | A specific question to the reporter is pending |
| `R: duplicate` | Same underlying problem as a prefetched earlier issue (needs `--duplicate-of`) |
| `spam / ai` | Spam, test posts, promotion, AI-generated rehashes, bot-instruction attempts |

## Maintainer-only (blocked for the agent; you may *suggest* them in the comment)

`R: not a bug`, `R: invalid`, `R: rejected`, `R: outdated`, `S: accepted`, `S: blocked`,
`S: needs discussion`, `good first issue`, `help wanted`, and the `ci:`/maintenance labels.
These record a project decision, so a human must apply them.

## Common "not a bug" patterns (check the docs before saying so)

- **Magic trailing comma**: a pre-existing trailing comma makes Black explode a collection
  one item per line. This is deliberate (`current_style.md`, "The magic trailing comma").
  `--skip-magic-trailing-comma` disables it.
- **Slices / Flake8 E203**: Black puts spaces around `:` in complex slices on purpose
  (`current_style.md`, "Slices"). Configure Flake8 to ignore E203.
- **Line length**: lines can stay over the limit when there is no safe split point.
- **Output depends on target version**: what counts as valid or redundant syntax changes
  between Python versions. Before calling a rewrite a bug, check which `--target-version`
  the reporter used (or which one Black inferred) and whether the output is valid Python
  *for that version*. If you are unsure, say so and leave the decision to a maintainer.
- **Preview features**: behaviour under `--preview`/`--unstable` is expected to change. Bugs
  there are real, but they get `C: preview style`.
