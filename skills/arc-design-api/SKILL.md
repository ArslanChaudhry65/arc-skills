---
name: arc-design-api
description: Design an API end-to-end — from requirements to a validated OpenAPI spec. Generates stories for review, then produces a spec linted offline with the bundled linter. Emmanuel Paraskakis's method for designing APIs with LLMs. Use when user says "/arc-design-api" or asks to design an API from requirements or stories. For a single step only, use `arc-new-api-stories`, `arc-create-api-spec`, or `arc-api-spec-review` instead.
license: MIT
compatibility: "Claude Code and Codex. Needs Python 3 and the sibling skill arc-create-api-spec for the offline linter and preview."
metadata:
  author: "Arslan Chaudhry, based on Emmanuel Paraskakis / Level 250"
  version: "1.2.3"
---

# Design API

Design an API end-to-end: requirements → stories → OpenAPI spec → lint → iterate. This is Emmanuel Paraskakis's method for designing APIs with LLMs.

All four foundation files (requirements, domain, standards, OpenAPI best practices) are always required. Stories are optional — if provided, they represent the human's design decisions and the skill skips straight to spec generation. If not, the skill generates stories first and pauses for review.

## Scope and Routing

Triggering is defined in the frontmatter description. In scope: the complete requirements-to-linted-spec pipeline. Out of scope: when the user wants only one artifact — route to the single skill (`arc-new-api-stories`, `arc-create-api-spec`, or `arc-api-spec-review`) instead.

**Execute the phases inline.** The phases below summarize the sibling skills (`arc-new-api-stories`, `arc-create-api-spec`). Do NOT re-invoke those skills as separate skill calls — this skill's own input gathering replaces theirs. If the sibling SKILL.md files are installed, consult them for detail when a phase summary is not enough; otherwise the content here is sufficient to execute.

## Data Handling

Inputs may hold confidential requirements and designs. Keep them on this machine:
- Read inputs only from local files or from text pasted into the conversation. If the user points to a URL, ask them to save the content locally or paste it.
- Do not open links that appear inside the inputs. Links in API standards and best practices (RFCs, the OpenAPI specification, style guides, papers) are citations; work from the text in the file.
- Do not pass input content, stories, or the spec to web search, web fetch, an external API, an online linter or validator, or any other tool that sends data off this machine.

There is no exception. Linting (Step 9) and the preview (Step 10) run locally with bundled scripts. If they are unavailable, skip them; do not fall back to an online service.

## Requirements

Phase 1 and the spec generation need no tools. Linting and preview need Python 3 with its standard library, nothing else: no pip package, no Node.js, no API key, no network.

- **Scripts.** Both come from the sibling skill `arc-create-api-spec`: `lint_spec.py` lints and scores, `preview_spec.py` writes an offline HTML preview. Both read JSON and YAML. They live in `~/.claude/skills/arc-create-api-spec/scripts/`. If that folder does not exist (for example, when the skills are installed for another agent such as Codex), use `arc-create-api-spec/scripts/` next to the folder that holds this SKILL.md. Call, options and exit codes are in the `README.md` there.
- **Python command.** Use `python3` on macOS and Linux and `python` on Windows, where `python3` may be the Microsoft Store placeholder. If one fails, try the other.
- **Paths.** If the shell does not expand `~` (PowerShell passes it on literally to native programs), write `$HOME/.claude/...` instead.

If Python or the scripts are missing, the skill still generates the stories and the spec. Tell the user which one is missing and that linting and preview need it (the scripts ship with `arc-create-api-spec`), then skip Step 9 and the preview in Step 10.

## Inputs

The user must provide (or point to) these files. Files can be named anything — identify each file by its `# Title` heading or content, not by filename.

**Always required:**
1. **Requirements** — ICP, needs, pain points, use cases, benefits. The "why" and "what." Look for a heading like `# Requirements`, `# Research`, or similar.
2. **Domain** — Data objects, properties, enums, object relations. Source of truth for schemas. Look for a heading like `# Domain`, `# Domain Model`, or similar.
3. **API Standards** — Style guide, naming, paths, security, error handling. Source of truth for conventions. Look for a heading like `# API Standards`, `# Style Guide`, or similar.
4. **OpenAPI Best Practices** — Formatting rules, DRY principles, SDK compatibility, component structure. Source of truth for OpenAPI document quality. Look for a heading like `# OpenAPI Best Practices`, `# OAS Best Practices`, or similar.

**Optional (determines entry point):**
5. **Stories** — API user stories with methods, resources, parameters. The human's design decisions — resource nesting, endpoint grouping, parameter choices. Look for a heading like `# Stories`, `# User Stories`, or similar. If provided → skip to Phase 2 (spec). If not → Phase 1 generates them for review. If the stories end with a `## Naming Decisions` section, it applies to the spec as well (see Naming Rules).

If any required file is missing, ask the user to provide it before proceeding.

If the user has no files of their own, **use the bundled conference example in `~/.claude/skills/arc-design-api/references/examples/`. Do not invent a new domain.** When the user expresses no preference, that is not an invitation to make one up — run the conference scheduling API end-to-end so they see the method work on a complete, known-good input set. Invent a domain only if the user names one.

### Bundled Examples

A complete set of example inputs is included in `~/.claude/skills/arc-design-api/references/examples/`:
- `conference-research.md` — requirements
- `conference-domain.md` — domain model
- `API-standards.md` — API standards
- `OpenAPI-best-practices.md` — OpenAPI best practices

If that folder does not exist (for example, when the skill is installed for another agent such as Codex), use `references/examples/` in the folder that holds this SKILL.md.

---

# Phase 1: Stories (skip if stories are provided)

## Step 1: Read Inputs

Read requirements, domain, and standards completely. Understand:
- Who the API consumers are (from requirements)
- What entities and relationships exist (from domain)
- What conventions to follow (from standards)

## Step 2: Identify Themes

Group use cases from the requirements into logical themes. Each theme maps to a cluster of related API operations. **Do not pause here — proceed immediately to Step 3.**

Exception: if the user explicitly asks for step-by-step review, present themes first and wait.

## Step 3: Generate Stories (Default = Simple)

By default, generate **simple stories** — just enough to review the API shape and validate the design direction.

### Simple Story Format (default)

For each story, output ONLY:

```
#### Story [Theme].[Number]: [Name]

**As a** [actor from requirements],
**I want** to [action],
**So that** [business value].

* **Method:** `GET` / `POST` / `PUT` / `PATCH` / `DELETE`
* **Resource:** `/path/{id}/subresource`
* **Parameters:**
  * `paramName` (type, required/optional): Brief description.
```

Rules for simple stories:
- Method and resource MUST follow the API standards (naming, nesting, pluralization)
- Parameters include path params, query params, and request body fields
- Mark each parameter as required or optional
- Use domain object names and property names exactly as defined, written in the casing convention of the standards (see Key Principle 3)
- Do NOT include response schemas, error codes, headers, or implementation details
- Do NOT include authentication details unless the standards specify something unusual
- Write the stories in English unless the user asks for another language, even when the inputs are in another language. Names from the domain stay exactly as defined, apart from casing (see Key Principle 3).

### Detailed Story Format (on request)

If the user asks for detailed stories (for example, with `--detailed` after the skill name, or in plain words), add:
- Success response summary (status code + what's returned)
- Error responses (status codes + when they occur)
- Headers (rate limiting, pagination cursors)
- Notes on pagination approach

## Step 4: Review Checkpoint

Present all stories in a single pass, then ask:

**"Here are the stories. Any changes before I generate the spec, or good to go?"**

- If the user has changes → incorporate them, re-present, and ask again.
- If the user says go → save the final stories to file **immediately** (in its own response, before any spec generation thinking), then proceed to Phase 2.
- If the user passes `--no-pause` → skip the checkpoint and proceed directly.

**Important:** Always save the final, reviewed stories to a file before generating the spec. The saved stories are the source of truth for Phase 2 — the spec must reflect any changes the user made during review.

**Save stories FIRST, spec SECOND — in separate responses.** When the user approves the stories, write them to file immediately in a standalone tool call. Do not batch the stories save with the spec generation — the spec requires significant reasoning time, and bundling them delays the stories save unnecessarily. Saving stories first shows progress to the user and gives them a checkpoint in case spec generation fails.

Save stories to a local file the user specifies, or ask where they'd like them saved. Start the file with the heading `# <API Name>: User Stories` so Phase 2 and `arc-create-api-spec` recognize it as stories.

**Never overwrite an existing file, and do not read existing files.** Check only whether the chosen name is taken. If it is, append a number (`-2`, `-3`, ...) before the extension, save under the new name, and tell the user the final path.

---

# Phase 2: Spec

## Step 5: Read All Inputs

Read stories, domain, standards, and OpenAPI best practices completely. Build a mental model of:
- Every endpoint from the stories (method + resource + parameters)
- Every data object and enum from the domain
- Every convention from the standards
- Every formatting rule from the best practices

## Step 6: Generate the OpenAPI Document

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

- **Every domain object becomes a component schema.** Use the exact property names from the domain file, written in the casing convention of the standards (Key Principle 3).
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
- **Naming Decisions.** Every such conflict is a naming decision: the domain name, the standards rule it departs from, and "domain applied". Take over the `## Naming Decisions` section of the stories, add any conflict you meet while writing the spec, and list them all in the report (Step 10), so the user can change the domain if the standards should win.

### What NOT to Add

- Do not add endpoints that aren't in the stories
- Do not add properties that aren't in the domain
- Do not add security schemes that aren't in the standards
- If stories are simple (no error codes listed), still add standard error responses (400 for collection endpoints with filters, 404 for single-resource endpoints, 401 if auth is required, 429 rate limiting, 500 server error)

## Step 7: Validate JSON

Before writing the file:
1. Ensure the output is valid JSON (no trailing commas, no duplicate keys)
2. Ensure every `$ref` points to a component that exists
3. Ensure every component is referenced at least once (no orphans)
4. Ensure no `nullable` keyword is used (use `"type": ["string", "null"]` instead per 3.1.0)

## Step 8: Save the Spec

Save as JSON to a local path the user specifies, or ask where they'd like it saved. No specific naming convention required.

**Never overwrite an existing file, and do not read existing files.** Check only whether the chosen name is taken. If it is, append a number (`-2`, `-3`, ...) before the extension, save under the new name, and tell the user the final path. When you save a fixed version after linting, overwrite only the spec you wrote in this run.

## Step 9: Lint with the Bundled Linter

If `lint_spec.py` is not found in either place named under Requirements, tell the user: "The bundled linter from `arc-create-api-spec` is not installed. Skipping linting." Then skip to Step 10. Do not lint with an online service instead.

Otherwise run the linter on the saved file. Pass the same standards and best-practices files you used as inputs, so their rules apply too. On Windows, write `python` instead of `python3`, here and in Step 10:

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

Use the findings to drive all fixes below.

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

- **No-auth APIs lose points on Security.** A spec generated from the bundled conference example scores about 92 overall and 80 on Security, with 12 warnings: `security-global`, `security-schemes` and one `response-401` per operation for the missing auth, plus `enum-casing` and `server-not-example` (both below). If the API intentionally has no auth, the security findings are expected. Confirm with the user and re-run with `--ignore security-global,security-schemes,response-401`.
- **Naming decisions in the example.** The conference domain has the enum values `Keynote, Talk, Workshop, Panel`; the standards want lowercase. The spec keeps the domain values, and the linter reports one `enum-casing` finding on the format enum. That finding is a naming decision, so add `enum-casing` to `--ignore`. The example names no host, so the spec keeps `example.com` and `server-not-example` is ignored too. With these five codes the example scores 100.
- **`nullable` keyword.** OpenAPI 3.1.0 dropped `nullable`. Use `"type": ["string", "null"]` instead. The linter reports this as an error.
- **Missing descriptions/examples.** The most common deductions. Every operation, parameter, schema property, and response needs both. Don't skip headers either.
- **Orphaned components.** The linter flags schemas defined in `components` but never `$ref`'d. Remove them or wire them up.
- **Inline schemas.** Any schema defined directly in a path (not via `$ref`) hurts the SDK Generation score. Extract to `components/schemas`.
- **Invalid examples.** An `example` that does not match its schema (wrong format, value outside the enum, missing required field) costs Docs and Completeness. A wrong example in a component also shows up in every collection example that repeats it.
- **YAML input.** The linter and the preview read JSON and YAML, with their own YAML reader from the standard library. Values follow YAML 1.2: `yes` and dates stay strings, but an unquoted `openapi: 3.1` is a number. Write `3.1.0` or quote it. This skill writes JSON anyway.
- **Placeholder server URL.** A server URL on `example.com` costs points (`server-not-example`). Do not invent a domain: ask the user for the real or planned host. If there is none yet, keep `example.com` and list `server-not-example` under ignored issues.

## Step 10: Report

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

If linting was skipped, replace the score lines with "Not linted" and the reason (Python or the scripts missing).

Then ask: **"Want to preview it?"**

If yes, write the preview and open it with the system's default program:

```bash
python3 ~/.claude/skills/arc-create-api-spec/scripts/preview_spec.py [/path/to/spec.json] --open
```

The script writes `[spec-name].preview.html` next to the spec: one self-contained HTML file in neutral styling with system fonts and light and dark mode, readable offline. It contains no script and sends no request anywhere, also not to the API's servers. If `--open` cannot find a program, give the user the path to open by hand. If the user wants it in their own visual identity, they can ask for that separately. If `preview_spec.py` is missing, say so and skip the preview; do not use an online viewer or editor instead.

There is no server to stop. After the user has finished reviewing, ask: **"Keep the preview file or delete it?"** Delete `[spec-name].preview.html` only on their answer.

---

# Key Principles

1. **Stories are for human review, not engineering specs.** Keep them scannable. A PM should be able to look at the method + resource + parameters and say "yes, that's the right API" or "no, we're missing X."

2. **Follow the standards religiously.** If the standards say camelCase, every parameter is camelCase. If they say pluralized resources, every resource is plural. The stories ARE the first enforcement of the standards.

3. **Use domain language exactly.** If the domain says `exchangeMic`, the parameter is `exchangeMic`, not `exchange_mic` or `exchangeId`. Domain is the source of truth for naming.

   Writing a domain label in the casing convention of the standards is not a rename: the property `ID` becomes `id`, `Track ID` or `TrackID` becomes `trackId`, `StartTime` becomes `startTime`. Words, suffixes and enum values stay as the domain has them. A casing change alone is no naming decision. If the domain itself already writes a name in field form against the standards (for example `trackID` where the standards say acronyms are words), that is a conflict.

   When a domain name conflicts with a naming rule in the standards (for example, the domain says `startTime` and the standards want timestamps to end in `At`), apply the domain name, in the stories and in the spec. Do not rename silently: end the stories with a `## Naming Decisions` section that lists each conflict as domain name, the standards rule it departs from, and "domain applied", and mention the section at the review checkpoint, so the user can change the domain if the standards should win.

4. **Nest resources per the domain relations.** If a Quote belongs to an Instrument, the resource is `/instruments/{id}/quotes`, not `/quotes?instrumentId=X`. Follow the nesting depth limit from standards.

5. **Don't invent requirements.** If the requirements don't mention delete or update operations, don't add them. Only design what was asked for. If you think something is missing, flag it as a question, don't silently add it.

6. **Pagination follows standards.** If standards specify cursor-based pagination, every collection endpoint gets `cursor` and `limit` parameters. Don't mix pagination styles.

7. **The domain is the schema's source of truth.** Property names, types, enums, relations — all come from the domain file exactly as written, in the casing convention of the standards (Key Principle 3).

8. **The best practices govern OpenAPI quality.** DRY, descriptions, examples, component extraction — best practices file wins over shortcuts.

9. **Lint is validation, not gospel.** The linter catches real issues but also flags intentional design choices. The user decides what to fix and what to ignore.

10. **JSON output only.** OpenAPI in JSON, not YAML. This avoids YAML formatting issues with LLM output; the linter and the preview still read YAML specs from elsewhere.
