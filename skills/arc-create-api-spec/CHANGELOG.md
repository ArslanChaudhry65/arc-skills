# Changelog - arc-create-api-spec

## 1.3.2 - 2026-11-17

Prepared for public release. Behavior, options, rule codes and output are unchanged.

- Identifiers, comments and docstrings in `scripts/` translated to English, and
  `scripts/README.md` with them.
- Changelog rewritten in English, without references to private documents.
- `compatibility` names the preview next to the linter.
- `LICENSE` adds a copyright line for the modifications; the upstream notice stays.

## 1.3.1 - 2026-11-13

- Renamed from `ach-create-api-spec` to `arc-create-api-spec`.
- Frontmatter now carries `license`, `compatibility` and `metadata` with `author` and
  `version`; `version` is no longer a top-level field.

## 1.3.0 - 2026-11-02

Design decision "domain wins": when a domain name conflicts with a naming rule of the
standards, the same rule now applies as in `arc-new-api-stories` 1.2.0 and `arc-design-api`
1.2.0.

### Changed

- Domain names and values are not renamed in the spec, not even for the linter. Writing
  them in the casing convention of the standards (`TrackID` to `trackId`, `ID` to `id`) is
  not a rename; words, suffixes and enum values stay as the domain has them. Previously the
  standards won, and `Keynote` became `keynote`.
- Every conflict is a naming decision. The spec takes over the `## Naming Decisions`
  section of the stories and adds its own conflicts; the report in step 6 lists them under
  `Naming decisions (domain applied)`, each with its linter finding.
- Linter findings caused by such names, such as `enum-casing`, are not auto-fixed. A rule
  code goes into `--ignore` only if every finding of that rule is a naming decision. The
  linter itself is unchanged.
- Gotcha for the conference example: `TalkFormat` keeps `Keynote, Talk, Workshop, Panel`,
  the linter reports `enum-casing` once; with that code and the three codes for an open API
  the example scores 100.
- Test specs `conference-clean.json`, `conference-clean.yaml` and `conference-faulty.json`
  carry the domain's enum values; a test checks the naming decision.

## 1.2.0 - 2026-11-02

Output in English, YAML input everywhere, neutral preview.

### Added

- `scripts/yaml_reader.py`: a YAML reader using only the standard library. Linter and
  preview read `.yaml` and `.yml` with it. Values follow the YAML 1.2 core schema, keys
  stay strings as in JSON, errors name the line.
- `scripts/tests/conference-clean.yaml` and YAML tests: same report as from JSON, broken
  YAML, duplicate keys, version as a number, the reader itself.

### Changed

- Report, messages, rule texts, fix hints and JSON fields of `lint_spec.py` are in English:
  `score.overall`, `summary.errors`, `findings[].severity` with `error` or `warning`,
  `location`, `rule`, `message`, `fix`, `source`. Options are `--ignore` and `--list-rules`.
  The rule `json-valid` is now `syntax-valid`.
- Broken JSON or YAML is an error with exit code 1; exit code 2 stays for wrong usage.
- `preview_spec.py` uses a neutral design with the system font, no script and no external
  styling; options are `--output` and `--open`, labels are English.
- Gotcha for YAML: an unquoted `openapi: 3.1` is a number.

## 1.1.0 - 2026-11-02

No data leaves the machine, and no third-party code is loaded at runtime. Runs on Windows
and macOS, under Claude Code and Codex.

### Added

- `scripts/lint_spec.py`: an offline linter using only the Python standard library. It
  checks the structure of OpenAPI 3.0 and 3.1, the rules of Rate My OpenAPI, the common
  gotchas of `SKILL.md` and, with `--standards` and `--best-practices`, the rules of both
  rule files. The report has an overall score and sub-scores for Docs, Completeness, SDK
  Generation and Security; each finding has severity, JSON Pointer, rule with source, and
  fix. `--json` for machines, an ignore option for rules accepted on purpose. Exit code 1
  on errors, 2 on wrong usage. Rules and weights are rebuilt from the public source of Rate
  My OpenAPI (github.com/zuplo/rate-my-openapi, MIT); no code was copied.
- `scripts/preview_spec.py`: writes a self-contained HTML preview without external
  resources and opens it with the default program.
- `scripts/tests/`: a clean and a deliberately faulty conference spec with `unittest`
  tests.
- `scripts/README.md`: usage, options, output and exit codes of both scripts, also for
  `arc-design-api` and `arc-api-spec-review`.
- Section `Data Handling` in `SKILL.md`: no links from the input opened, nothing sent to web
  search, web fetch or online linters.

### Changed

- Step 5 lints with `lint_spec.py` instead of the Rate My OpenAPI service. `RMOA_API_KEY`,
  `curl`, reading the shell profile and `/tmp` are gone. The flow stays: score, auto-fix,
  ask the user about design questions, repeat, report.
- Step 6 shows the preview with `preview_spec.py` instead of loading Swagger UI from
  unpkg.com through `npx http-server`.
- `Optional Dependencies` is now `Requirements` and needs only Python 3.
- Step 4 never overwrites an existing file; it appends a number instead.
- From the trial run with the conference stories: a placeholder domain is asked for, not
  invented; the report in step 6 names every deviation from the domain; the commands note
  that Windows needs `python`.

## 1.0.0 - 2026-11-02

Forked from `design-api-spec` in https://github.com/paraskakis/skills, commit `dbe04cf`
(folder `api/design-api-spec`, last changed in `9acbc6b`, upstream version 1.0.0). MIT
license; `LICENSE` is the upstream file.

Changes from upstream:

- Renamed, and references to the sibling skills renamed accordingly.
- Paths to `references/` are absolute under `~/.claude/skills/<skill>/references/`, so they
  resolve regardless of the working directory.
- Otherwise unchanged, including the examples under `references/examples/`.
