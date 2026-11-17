# Changelog - arc-api-spec-review

## 1.1.2 - 2026-11-17

Prepared for public release.

- Changelog rewritten in English, without references to private documents.
- `compatibility` names the dependency on the sibling skill `arc-create-api-spec`, whose
  script does the linting.
- `LICENSE` adds a copyright line for the modifications; the upstream notice stays.

## 1.1.1 - 2026-11-13

- Renamed from `ach-api-spec-review` to `arc-api-spec-review`.
- Frontmatter now carries `license`, `compatibility` and `metadata` with `author` and
  `version`; `version` is no longer a top-level field.

## 1.1.0 - 2026-11-02

The skill runs on Windows and macOS, for any organization, under Claude Code and Codex, and
no data leaves the machine, because confidential specs go through it.

- **Offline linter instead of Rate My OpenAPI.** A new step 2 lints the spec before the
  model review with `lint_spec.py` from `arc-create-api-spec`, using `--standards`,
  `--best-practices` and `--json` with the rule sets in force. The fix step relints the
  corrected file with the same arguments and compares findings and score. `RMOA_API_KEY` is
  gone.
- **Layering.** The linter covers parsing (line of a syntax error), structure (invalid
  OpenAPI cited against the OpenAPI specification) and the mechanical rules at every place
  in the spec. The model then checks every rule of the rule sets, confirms or rejects the
  linter findings, and handles what only reading can settle: vocabulary, resources, status
  code semantics, rationale. A linter finding is a candidate, not a verdict: it is cited
  with the rule from the loaded file, a justified deviation becomes DELIBERATE, and a
  finding without a matching rule goes under the new section `Linter notes` as a
  suggestion. Where rule set and linter disagree, the rule set wins (new key principle 6).
  In testing, the linter flagged 42 places for 29 rules in the faulty spec; the model merged
  them into 20 items and found four more the linter does not check.
- The report shows the linter's score and finding count under `Linted with` and tags each
  linter-sourced finding with its rule code. Without Python or the script, the review runs
  on the model alone and says so.
- **Input without network.** New section `Data Handling`: local files and pasted text are
  the default. The skill downloads a URL or GitHub repo only when the user asks for it in
  the session; a bare address gets one follow-up question. Downloads use a plain GET or
  `git clone --depth 1` into an empty temporary folder; nothing is sent but the request, and
  nothing from the repo is run. Links in spec and rule sets and `$ref` to URLs are not
  opened.
- **YAML.** Specs in JSON or YAML, locations as JSON Pointers. If the linter's YAML reader
  hits one of its known limits, the review continues without the linter. A YAML spec gets a
  `Needs a decision` item for the bundled best practice "The OpenAPI should be in JSON".
- **Saving without overwriting.** The corrected spec goes to `[name]-reviewed.[ext]` next to
  the original, in the same format; a taken name gets `-2`, `-3`. Same for a saved report.
- `python3` on macOS, `python` on Windows, `$HOME` instead of `~` in PowerShell. Fallback
  paths next to `SKILL.md` and in the sibling folder when `~/.claude/skills/` is missing.

## 1.0.0 - 2026-11-02

Forked from `design-api-review` in https://github.com/paraskakis/skills, commit `dbe04cf`
(folder `api/design-api-review`, last changed in `62616e6`, upstream version 1.1.0). MIT
license; `LICENSE` is the upstream file.

Changes from upstream:

- Renamed, and references to the sibling skills renamed accordingly.
- Paths to `references/` are absolute under `~/.claude/skills/<skill>/references/`, so they
  resolve regardless of the working directory.
- Otherwise unchanged, including the examples under `references/examples/`.
