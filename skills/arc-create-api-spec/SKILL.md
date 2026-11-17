---
name: arc-create-api-spec
description: Generate an OpenAPI 3.1.0 specification from API design stories, a domain model, API standards, and OpenAPI best practices. Lints it with a bundled offline linter (RateMyOpenAPI-style scores) and iterates to 100/100. Use when user says "/arc-create-api-spec" or asks to generate an OpenAPI spec from stories. Does not write the stories (that is `arc-new-api-stories`) and does not review an existing spec (that is `arc-api-spec-review`).
license: MIT
compatibility: "Claude Code and Codex. Needs Python 3 for the bundled offline linter and preview."
metadata:
  author: "Arslan Chaudhry, based on Emmanuel Paraskakis / Level 250"
  version: "1.3.2"
---

# Design API Spec

Generate an OpenAPI 3.1.0 specification from API design stories, a domain model, API standards, and an OpenAPI best practices file. Then lint it with the bundled offline linter and fix issues. This is part of Emmanuel Paraskakis's method for designing APIs with LLMs. Stories can come from the companion `arc-new-api-stories` skill or be written by hand — either way, this skill takes stories + domain + standards + OpenAPI best practices and produces a validated spec.

## Scope and Routing

Triggering is defined in the frontmatter description. In scope: turning stories + domain + standards + best practices into a linted OpenAPI document. Out of scope: writing the stories (use `arc-new-api-stories`), reviewing a spec you did not just generate (use `arc-api-spec-review`), and running the full pipeline (use `arc-design-api`).

## Data Handling

Inputs and the generated spec may hold confidential designs. Keep everything on this machine:
- Read inputs only from local files or from text pasted into the conversation. If the user points to a URL, ask them to save the content locally or paste it.
- Do not open links that appear inside the inputs. Links in API standards and best practices (RFCs, the OpenAPI specification, style guides) are citations; work from the text in the file.
- Do not pass input content or the spec to web search, web fetch, an external API, an online linter or validator, or any other tool that sends data off this machine.

## Requirements

Python 3 with its standard library, nothing else: no pip package, no Node.js, no API key, no network. Linting and preview run locally, so the spec never leaves the machine.

- **Python command.** Use `python3` on macOS and Linux and `python` on Windows, where `python3` may be the Microsoft Store placeholder. If one fails, try the other.
- **Paths.** The scripts live under `~/.claude/skills/arc-create-api-spec/scripts/`. If the shell does not expand `~` (PowerShell passes it on literally to native programs), write `$HOME/.claude/...` instead.
- **Scripts.** `lint_spec.py` lints and scores, `preview_spec.py` writes an offline HTML preview. Both read JSON and YAML. Call, options and exit codes are in `~/.claude/skills/arc-create-api-spec/scripts/README.md`.

If Python is missing, the skill still generates the spec. Tell the user that linting and preview need Python 3, then skip Step 5 and the preview in Step 6.

## Inputs

The user must provide (or point to) these files. Files can be named anything — identify each file by its `# Title` heading or content, not by filename.

1. **Stories** — Output from `/arc-new-api-stories`. Defines methods, resources, parameters, and themes. Look for a heading like `# Stories`, `# User Stories`, or similar. If the stories end with a `## Naming Decisions` section, it applies to the spec as well (see Naming Rules).
2. **Domain** — Data objects, properties, enums, object relations. Source of truth for schemas. Look for a heading like `# Domain`, `# Domain Model`, or similar.
3. **API Standards** — Style guide, naming, paths, security, error handling. Source of truth for conventions. Look for a heading like `# API Standards`, `# Style Guide`, or similar.
4. **OpenAPI Best Practices** — Formatting rules, DRY principles, SDK compatibility, component structure. Source of truth for OpenAPI document quality. Look for a heading like `# OpenAPI Best Practices`, `# OAS Best Practices`, or similar.

If any file is missing, ask the user to provide it before proceeding.

### Working Example

See `~/.claude/skills/arc-create-api-spec/references/examples/` for a complete set of inputs (conference scheduling API):
- `conference-api-stories.md` — stories (output from `/arc-new-api-stories`)
- `conference-domain.md` — domain model
- `API-standards.md` — API standards
- `OpenAPI-best-practices.md` — OpenAPI best practices

## Step 1: Read All Inputs

Read all four files completely. Build a mental model of:
- Every endpoint from the stories (method + resource + parameters)
- Every data object and enum from the domain
- Every convention from the standards
- Every formatting rule from the best practices

## Step 2: Generate the OpenAPI Document

Output a single valid JSON file. Default to OpenAPI 3.1.0 unless the user specifies a different version.

### Structure

Follow this order in the document:

1. `openapi` — "3.1.0" (or the user-specified version)
2. `info` — Title, description, version, contact, license (per best practices)
3. `servers` — At least one server with description
4. `security` — Global security scheme if standards require auth
5. `tags` — One tag per theme from the stories
6. `paths` — All endpoints from the stories
7. `components` — schemas, parameters, responses, headers, securitySchemes

### Schema Generation Rules

- **Every domain object becomes a component schema.** Use the exact property names from the domain file.
- **Every enum becomes a component schema.** Don't inline enums.
- **Collection responses get their own schema.** e.g., `InstrumentCollection` with `data` array + pagination fields.
- **Error responses use RFC 9457 (Problem Details)** unless standards specify otherwise.
- **No inline schemas.** Extract everything to `components/schemas` and `$ref` it.
- **Reusable parameters go in `components/parameters`.** Pagination params (`cursor`, `limit`), common filters — define once, reference everywhere.
- **Reusable response objects go in `components/responses`.** Error responses (400, 401, 404, 429, 500) — define once per unique shape.
- **Reusable headers go in `components/headers`.** Rate limit headers etc.

### Content Rules

- **Every** operation, parameter, schema, property, response, and header MUST have a non-empty `description`.
- **Every** schema and parameter MUST have an `example` value. Use realistic examples from the domain file.
- **Every** operation MUST have a `summary` and `operationId`.
- Error examples must match the error type (a 429 example should describe rate limiting, not "bad request").
- Use `$ref` aggressively. The document should be DRY.

### Naming Rules

- operationIds: camelCase verbs matching the story action (e.g., `searchInstruments`, `getInstrumentByFigi`)
- Tags: Match theme names from stories
- Schemas: PascalCase matching domain object names
- Parameters: camelCase matching domain property names
- **Domain versus standards: the domain wins.** When a name or value from the domain conflicts with a naming rule in the standards (for example enum values `Keynote, Talk` against lowercase enum values, or `startTime` against timestamps ending in `At`), keep the domain's version in the spec. Do not rename it, not even to satisfy the linter. Writing a domain label in the casing convention of the standards is not a rename: the property `ID` becomes `id`, `Track ID` or `TrackID` becomes `trackId`. Words, suffixes and enum values stay as the domain has them.
- **Naming Decisions.** Every such conflict is a naming decision: the domain name, the standards rule it departs from, and "domain applied". Take over the `## Naming Decisions` section of the stories, add any conflict you meet while writing the spec, and list them all in the report (Step 6), so the user can change the domain if the standards should win.

### What NOT to Add

- Do not add endpoints that aren't in the stories
- Do not add properties that aren't in the domain
- Do not add security schemes that aren't in the standards
- If stories are simple (no error codes listed), still add standard error responses (400 for collection endpoints with filters, 404 for single-resource endpoints, 401 if auth is required, 429 rate limiting, 500 server error)

## Step 3: Validate JSON

Before writing the file:
1. Ensure the output is valid JSON (no trailing commas, no duplicate keys)
2. Ensure every `$ref` points to a component that exists
3. Ensure every component is referenced at least once (no orphans)
4. Ensure no `nullable` keyword is used (use `"type": ["string", "null"]` instead per 3.1.0)

## Step 4: Save the File

Save as JSON to a location the user specifies, or ask where they'd like it saved. No specific naming convention required.

**Never overwrite an existing file, and do not read existing files.** Check only whether the chosen name is taken. If it is, append a number (`-2`, `-3`, ...) before the extension, save under the new name, and tell the user the final path. When you save a fixed version after linting, overwrite only the spec you wrote in this run.

## Step 5: Lint with the Bundled Linter

Run the linter on the saved file. Pass the same standards and best-practices files you used as inputs, so their rules apply too. On Windows, write `python` instead of `python3`, here and in Step 6:

```bash
python3 ~/.claude/skills/arc-create-api-spec/scripts/lint_spec.py [/path/to/spec.json] \
  --standards [/path/to/API-standards.md] \
  --best-practices [/path/to/OpenAPI-best-practices.md] \
  --json
```

Use `--json` when you read the result yourself; show the user the text report (the same call without `--json`) when they want to see it. Report, messages and rule codes are in English.

What it checks:

- **Structure** against OpenAPI 3.0 and 3.1: required fields, resolvable `$ref`s, path parameters, duplicate keys, `nullable` in 3.1.
- **The RateMyOpenAPI rules**, rebuilt from its public source code with the same weights, so the scores read like an RMOA report.
- **The Common Gotchas below**: missing `description` and `example`, orphaned components, inline schemas and enums, missing error responses, missing `operationId`, missing `securitySchemes`.
- **Rules from the standards and best-practices files.** Each such rule switches on only when its file is passed and mentions its topic (for example `application/problem+json` or `totalCount`). With another organization's standards, rules whose topic the file does not mention stay off; check those parts of the standards yourself.

The result has an overall score and four category scores, 0 to 100. Every finding has a severity (`error` or `warning`), a location as a JSON pointer, the rule code and its source, and a fix hint. Broken JSON or YAML syntax is an error with the line number. Exit code `0` means no errors, `1` means at least one error, `2` means a wrong call (missing file, unknown rule code).

### Interpreting Results

Scores four categories (0-100 each):
- **Docs** — Descriptions, summaries, examples
- **Completeness** — Required fields, response codes, schemas
- **SDK Generation** — operationIds, no inline schemas, proper refs
- **Security** — Auth schemes, 401/403 responses

**Target: 100/100 on all categories.**

### Handling Issues

1. **Auto-fix** anything that's clearly a formatting or completeness issue (missing description, missing example, missing error response).

2. **Ask the user** about issues that involve design decisions. Common examples:
   - **No authentication / missing 401**: If the API intentionally has no auth (e.g., a training exercise), tell the user the linter flagged it and ask if they want to ignore it or add auth.
   - **Missing error codes**: If the linter expects 401/403 but the stories don't include auth, ask.
   - **Naming conventions**: If the linter flags a naming pattern that conflicts with the standards file, the standards file wins. Tell the user.
   - **Domain versus standards**: Where a domain name conflicts with a naming rule in the standards, the domain applies (see Naming Rules). If the linter flags such a name, for example `enum-casing` on a domain enum, do not rename it and do not auto-fix it. Tell the user which finding belongs to which naming decision. Add the rule code to `--ignore` only when every finding of that rule is such a decision; otherwise leave the findings in the report and name the ones that are decisions.

3. **Re-run after fixes.** For every rule the user approved ignoring, add its code to `--ignore` (comma-separated, for example `--ignore security-global,security-schemes,response-401`). Ignored findings leave the score and the exit code and are listed separately. Keep iterating until either:
   - Score is 100/100, or
   - Remaining issues are intentional design choices the user has approved ignoring

### Common Gotchas

- **No-auth APIs lose points on Security.** The bundled conference example scores 93 overall and 80 on Security, with `security-global`, `security-schemes` and one `response-401` per operation. If the API intentionally has no auth, these are expected. Confirm with the user and re-run with `--ignore security-global,security-schemes,response-401`.
- **Naming decisions in the example.** The conference domain has the enum values `Keynote, Talk, Workshop, Panel`; the standards want lowercase. The spec keeps the domain values, and the linter reports one `enum-casing` finding on `TalkFormat`. That finding is a naming decision, so add `enum-casing` to `--ignore`; together with the three no-auth codes the example then scores 100.
- **`nullable` keyword.** OpenAPI 3.1.0 dropped `nullable`. Use `"type": ["string", "null"]` instead. The linter reports this as an error.
- **Missing descriptions/examples.** The most common deductions. Every operation, parameter, schema property, and response needs both. Don't skip headers either.
- **Orphaned components.** The linter flags schemas defined in `components` but never `$ref`'d. Remove them or wire them up.
- **Inline schemas.** Any schema defined directly in a path (not via `$ref`) hurts the SDK Generation score. Extract to `components/schemas`.
- **Invalid examples.** An `example` that does not match its schema (wrong format, value outside the enum, missing required field) costs Docs and Completeness. A wrong example in a component also shows up in every collection example that repeats it.
- **YAML input.** The linter and the preview read JSON and YAML, with their own YAML reader from the standard library. Values follow YAML 1.2: `yes` and dates stay strings, but an unquoted `openapi: 3.1` is a number. Write `3.1.0` or quote it. This skill writes JSON anyway.
- **Placeholder server URL.** A server URL on `example.com` costs points (`server-not-example`). Do not invent a domain: ask the user for the real or planned host. If there is none yet, keep `example.com` and list `server-not-example` under ignored issues.

## Step 6: Report

Show the user:

```
## OpenAPI Spec Complete

**File:** [path]
**Score:** [Overall] / 100
  - Docs: [score]
  - Completeness: [score]
  - SDK Generation: [score]
  - Security: [score]

**Linted with:** lint_spec.py, rule files [names of the standards and best-practices files]

**Issues ignored (by design):**
- [rule code and reason for each code passed to --ignore]

**Naming decisions (domain applied):**
- [each conflict between a domain name and a standards rule, from the stories' `## Naming Decisions` and from writing the spec, with the linter finding it caused, if any; "none" if there are none]

**Deviations from the domain:**
- [every name or value that differs from the domain file beyond casing, with the reason, for example a change the user asked for; "none" if there are none]
```

Then ask: **"Want to preview it?"**

If yes, write the preview and open it with the system's default program:

```bash
python3 ~/.claude/skills/arc-create-api-spec/scripts/preview_spec.py [/path/to/spec.json] --open
```

The script writes `[spec-name].preview.html` next to the spec: one self-contained HTML file in neutral styling with system fonts and light and dark mode, readable offline. It contains no script and sends no request anywhere, also not to the API's servers. If `--open` cannot find a program, give the user the path to open by hand. If the user wants it in their own visual identity, they can ask for that separately.

There is no server to stop. After the user has finished reviewing, ask: **"Keep the preview file or delete it?"** Delete `[spec-name].preview.html` only on their answer.

## Key Principles

1. **The stories are the spec's requirements.** Every story becomes one or more operations. No more, no less.

2. **The domain is the schema's source of truth.** Property names, types, enums, relations — all come from the domain file exactly as written.

3. **The standards govern conventions.** Naming, nesting, pagination, error format, auth — standards file wins over any default. Where a domain name conflicts with a naming rule, the domain wins and the conflict becomes a naming decision.

4. **The best practices govern OpenAPI quality.** DRY, descriptions, examples, component extraction — best practices file wins over shortcuts.

5. **Lint is validation, not gospel.** The linter catches real issues but also flags intentional design choices. The user decides what to fix and what to ignore.

6. **JSON output only.** OpenAPI in JSON, not YAML. This avoids YAML formatting issues with LLM output; the linter and the preview still read YAML specs from elsewhere.
