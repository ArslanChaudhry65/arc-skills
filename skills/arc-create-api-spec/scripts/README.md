# scripts/

Scripts for `arc-create-api-spec`, also called by `arc-design-api` and `arc-api-spec-review`.
They need only Python 3 with the standard library: no pip, no network, no npx. On Windows the
command is `python`, on the Mac `python3`. Both scripts read JSON and YAML. Their output is
English so that any organization can read it.

| File | Purpose |
|---|---|
| `lint_spec.py` | Linter with scores in the style of Rate My OpenAPI |
| `preview_spec.py` | Self-contained HTML preview |
| `yaml_reader.py` | YAML reader for both, standard library only |
| `tests/` | Test specs and `unittest` tests |

## lint_spec.py

Lints an OpenAPI 3.0 or 3.1 file and gives scores in the style of Rate My OpenAPI (RMOA).
The spec never leaves the machine.

```bash
python3 ~/.claude/skills/arc-create-api-spec/scripts/lint_spec.py SPEC \
  [--standards API-standards.md] [--best-practices OpenAPI-best-practices.md] \
  [--ignore CODE[,CODE...]] [--json]
python3 ~/.claude/skills/arc-create-api-spec/scripts/lint_spec.py --list-rules
```

| Option | Effect |
|---|---|
| `SPEC` | The spec as `.json`, `.yaml` or `.yml`. Without these extensions the first character decides: `{` or `[` means JSON, anything else YAML. |
| `--standards FILE` | Adds the rules from the API standards (Markdown). |
| `--best-practices FILE` | Adds the rules from the OpenAPI best practices (Markdown). |
| `--ignore CODE,...` | Excludes rules the user accepts on purpose. May be given more than once. Ignored findings count neither in the score nor in the exit code and are listed separately in the report. |
| `--json` | The same report, machine-readable. |
| `--list-rules` | Lists all rules with code, severity, weight and ruleset. |

**Exit codes:** `0` without errors (warnings allowed), `1` as soon as there is an error, also
for broken JSON or YAML, `2` on wrong usage: spec missing, rule file missing, unknown code in
`--ignore`.

### Output

The text report names the file and OpenAPI version, the active rulesets, the overall score and
the category scores Docs, Completeness, SDK Generation and Security, each from 0 to 100. Below
that comes one block per rule with severity, count, weight, rule text with its source, and fix,
then every location as a JSON Pointer with the concrete finding. An excerpt:

```text
Score: 93 / 100
  Docs:             95
  Completeness:     95
  SDK Generation:  100
  Security:         80

Findings: 0 errors, 11 warnings

3. [WARNING] response-401, 8x, weight 25
   Rule: Every operation has a 401 response with content. (Rate My OpenAPI: owasp:api3:2019-define-error-responses-401)
   Fix:  Add 401 as a $ref to a shared error response. ...
   - /paths/~1speakers/get/responses
     GET /speakers has no 401 response with content. ...
```

With `--json`:

```json
{
  "file": "...", "openapi": "3.1.0",
  "score": {"overall": 93, "docs": 95, "completeness": 95, "sdkGeneration": 100, "security": 80},
  "areas": {"paths": {"score": 94, "docs": 100, "completeness": 100, "sdkGeneration": 100, "security": 75}},
  "summary": {"errors": 0, "warnings": 11, "ignored": 0},
  "rulesets": {"standards": {"file": "API-standards.md", "active": 18, "total": 18,
                             "activeRules": ["..."], "inactiveRules": []}},
  "findings": [{"severity": "warning", "rule": "response-401",
                "location": "/paths/~1talks/get/responses", "message": "...", "fix": "...",
                "description": "...", "source": "Rate My OpenAPI: owasp:api3:2019-define-error-responses-401",
                "weight": 25, "categories": ["security"]}],
  "ignored": []
}
```

`severity` is `error` or `warning`. `location` is a JSON Pointer per RFC 6901 (`/` in a path
becomes `~1`); empty means the whole file. Findings are sorted: errors first, then by weight,
then by location. `areas` shows the areas the score is made of.

### Rules

Three rulesets; `--list-rules` lists them all:

- **base**, always active: the required fields of OpenAPI 3.x, the RMOA rules and the Common
  Gotchas of `SKILL.md`, such as missing `description` and `example`, orphaned components,
  `nullable` in 3.1, inline schemas and enums, missing error responses, missing
  `operationId`, missing `securitySchemes`.
- **standards**, only with `--standards`: rules from the bundled `API-standards.md`, such as
  camelCase, `application/problem+json`, collection wrappers with `meta.totalCount`,
  `offset`/`limit`, rate limit headers, 201 with `Location`.
- **best-practices**, only with `--best-practices`: 403 on secured operations and descriptions
  that say more than the summary (Agent-readiness).

Every rule of the two file-based rulesets has an anchor, a term from the bundled file. It
applies only if the given file contains that term. So with the bundled files the rules apply
in full, and with another organization's standards only where those cover the same topic.
Whatever else the file requires, the model checks itself.

### Score

Rebuilt from the public source code of RMOA (github.com/zuplo/rate-my-openapi, MIT), rules and
weights only, no code:

- Deduction per finding: error 75, warning 25, minor warning 10 or 5 (`info` and `hint` in
  RMOA).
- Areas with weights: `paths` 0.6, `components` 0.15, `info` 0.1, `servers`, `tags` and
  `security` 0.05 each. The overall score and each category are the weighted sum of the areas.
- Each operation is 100 minus deductions; a deduction on a parameter, a single response or a
  tag is divided by their count. A path is the mean of its operations.
- If the global `security` is missing, the `security` area gets 0 for Docs, Completeness and
  Security, as in RMOA. If `security-global` is excluded with `--ignore`, the API counts as
  open on purpose and the area is scored normally.
- If `servers` is missing, the area is 0; if `tags` is missing, Docs and Completeness are 25.

### Limits

- External `$ref`s (other files, URLs) are reported but not resolved.
- Examples are checked against a subset of JSON Schema: `type`, `enum`, `const`, `required`,
  `properties`, `additionalProperties: false`, `items`, lengths, bounds, `pattern`, `allOf`,
  `anyOf`, `oneOf` and the formats `uuid`, `date`, `date-time`, `email`, `uri`, `url`.
- The script does not know whether an operation needs permissions; it requires 403 only on
  secured operations and only with `--best-practices`.

## yaml_reader.py

Reads the YAML found in OpenAPI files: block mappings and sequences, also compact
(`- name: x`), flow collections across several lines, both kinds of quotes, block scalars `|`
and `>` with chomping, multi-line plain scalars, comments, anchors, aliases, merge keys `<<`
and `!!str`. Values follow the YAML 1.2 Core Schema: `yes`, `on` and a date stay strings,
unlike in PyYAML. Keys stay strings exactly as written, so `200:` becomes `"200"` as in JSON.
Not supported: several documents in one file, complex keys with `?`, tabs for indentation. An
error names the line.

## preview_spec.py

Writes a self-contained HTML page from the spec, with no external resources, and opens it with
the system's default program on request.

```bash
python3 ~/.claude/skills/arc-create-api-spec/scripts/preview_spec.py SPEC [--output FILE.html] [--open]
```

| Option | Effect |
|---|---|
| `--output FILE` | Target file. Default: `<spec>.preview.html` next to the spec. |
| `--open` | Opens the page with the default program through the `webbrowser` module. |

**Exit codes:** `0` written, `2` spec missing or unreadable.

The page shows the overview, servers, contact, license and security, the operations by tag
with parameters, request body, responses and examples, and all schemas with their properties.
Its design is neutral, with the system font and light or dark mode per system setting, and it
contains no script. It loads nothing: no font, no CDN, no request to the API's servers.
Descriptions are shown as text, not as Markdown, so nothing from the spec runs in the page.
Labels are English.

## tests/

```bash
python3 -m unittest discover -s ~/.claude/skills/arc-create-api-spec/scripts/tests -v
```

- `conference-clean.json`: the conference API from `references/examples/`, clean except for
  the intentionally missing authentication and one naming decision: `TalkFormat` keeps the
  domain's enum values (`Keynote`, `Talk`, ...), while the standards want lowercase. With both
  rule files and `--ignore security-global,security-schemes,response-401,enum-casing` it scores
  100 in every category.
- `conference-clean.yaml`: the same content as YAML, with comments, folded block scalars, flow
  lists and unquoted status codes. Must give the same report as the JSON file.
- `conference-faulty.json`: the clean spec with planted errors, one rule per error. Which ones
  is listed in `EXPECTED_FAULTY` in `test_lint_spec.py`.
- `test_lint_spec.py`: checks the specs, the fields of every finding, the exit codes, broken
  JSON and YAML, duplicate keys, Swagger 2.0, the YAML reader, and that the preview loads
  nothing.
