# Changelog - arc-design-api

## 1.2.3 - 2026-11-17

Prepared for public release.

- Changelog rewritten in English, without references to private documents.
- `compatibility` names the dependency on the sibling skill `arc-create-api-spec`, whose
  scripts do the linting and the preview.
- `LICENSE` adds a copyright line for the modifications; the upstream notice stays.

## 1.2.2 - 2026-11-13

- Renamed from `ach-design-api` to `arc-design-api`.
- Frontmatter now carries `license`, `compatibility` and `metadata` with `author` and
  `version`; `version` is no longer a top-level field.

## 1.2.1 - 2026-11-02

Domain names win over the standards for words, suffixes and enum values, but not for the
casing of field names. Text aligned with `arc-create-api-spec` 1.3.0.

### Fixed

- Writing a domain name in the casing convention of the standards is not a rename and not a
  naming decision: `ID` becomes `id`, `TrackID` becomes `trackId`, `StartTime` becomes
  `startTime`. A real conflict remains when the domain itself already writes a field name
  against the standards, such as `trackID`. Applies to phase 1 (story rules, key principles
  3 and 7) and phase 2 (schema and naming rules).
- Phase 2 takes over the `## Naming Decisions` section of the stories and adds conflicts
  found in the spec; step 10 lists all of them under `Naming decisions (domain applied)`.
  Linter findings caused by such names are neither renamed nor auto-fixed.
  `Deviations from the domain` only lists what goes beyond casing.
- Gotcha figures corrected: a spec generated from the conference example without a host
  (`example.com`) scores 92 overall, Security 80, 12 warnings; with
  `--ignore security-global,security-schemes,response-401,enum-casing,server-not-example`
  it scores 100. New gotcha for the naming decision `enum-casing` in the example.

## 1.2.0 - 2026-11-02

No data leaves the machine, and no third-party code is loaded at runtime.

### Changed

- Step 9 lints with the offline `lint_spec.py` from `arc-create-api-spec` instead of the
  Rate My OpenAPI service. `RMOA_API_KEY`, `curl`, reading the shell profile and `/tmp` are
  gone. The flow stays: score, auto-fix, ask the user about design questions, rerun with
  `--ignore`, report.
- Step 10 writes the preview with `preview_spec.py` instead of loading Swagger UI from
  unpkg.com through `npx http-server`. Afterwards the skill asks whether to keep the
  preview file.
- `Optional Dependencies` is now `Requirements` and needs only Python 3 (`python` on
  Windows, `python3` on macOS and Linux).
- If Python or the scripts are missing, the skill says so and skips linting or the preview;
  it never falls back to an online service. The report then says "Not linted".
- If `~/.claude/skills/arc-create-api-spec/scripts/` does not exist, for example when
  installed for Codex only, `arc-create-api-spec/scripts/` next to this skill's folder is
  used.
- `Data Handling`: online linters and validators are explicitly listed as forbidden
  targets.
- The report names the linter and rule files, every ignored rule with its reason, and the
  deviations from the domain.
- Unlike `arc-create-api-spec` at that time, the domain kept winning naming conflicts;
  linter findings for such names go under `Naming decisions (domain applied)`.
- Saving after linting may only overwrite the spec of the current run.

### Tested

Full run with the conference examples, `--no-pause`, offline: stories with two naming
decisions, a spec with eight operations, lint score 92 of 100 (Security 80), 100 in all
categories with the five ignored rules above. The preview contains no script and loads
nothing.

## 1.1.0 - 2026-11-02

Phase 1 and saving take over the changes of `arc-new-api-stories` 1.1.0 and 1.2.0, so both
paths produce the same stories.

- New section `Data Handling`: input only from local files or pasted text, no links from
  the input opened, nothing sent to web search, web fetch or other outside services.
- Saving stories and spec never overwrites; a taken name gets a number.
- The stories file starts with `# <API Name>: User Stories`.
- Stories are in English unless the user asks for another language.
- When a domain name conflicts with a naming rule of the standards, the domain wins in
  stories and spec, and `## Naming Decisions` lists the conflict.
- Fallback to `references/examples/` next to `SKILL.md` when the absolute path is missing.
- `--detailed` also works after the skill name or in words.

## 1.0.0 - 2026-11-02

Forked from `design-api` in https://github.com/paraskakis/skills, commit `dbe04cf` (folder
`api/design-api`, last changed in `9acbc6b`, upstream version 1.0.0). MIT license; `LICENSE`
is the upstream file.

Changes from upstream:

- Renamed, and references to the single-step skills renamed accordingly.
- Paths to `references/` are absolute under `~/.claude/skills/<skill>/references/`, so they
  resolve regardless of the working directory.
- Otherwise unchanged, including the examples under `references/examples/`.
