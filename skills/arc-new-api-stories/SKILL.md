---
name: arc-new-api-stories
description: Generate API design stories from requirements, a domain model, and API standards. Stories bridge product requirements and OpenAPI specs — Emmanuel Paraskakis's method for designing APIs with LLMs. Use when user says "/arc-new-api-stories" or asks to generate API user stories from requirements. Does not generate an OpenAPI spec (that is `arc-create-api-spec`).
license: MIT
compatibility: "Claude Code and Codex. Needs no scripts and no network."
metadata:
  author: "Arslan Chaudhry, based on Emmanuel Paraskakis / Level 250"
  version: "1.2.3"
---

# Design API Stories

Generate API design stories from requirements, a domain model, and API standards. This is Emmanuel Paraskakis's method for designing APIs with LLMs — the stories become the bridge between product requirements and an OpenAPI specification.

## Scope and Routing

Triggering is defined in the frontmatter description. In scope: turning requirements + domain + standards into reviewable API stories. Out of scope: generating an OpenAPI spec (use `arc-create-api-spec`) and running the full pipeline (use `arc-design-api`).

## Data Handling

Inputs may hold confidential requirements and designs. Keep everything on this machine:
- Read inputs only from local files or from text pasted into the conversation. If the user points to a URL, ask them to save the content locally or paste it.
- Do not open links that appear inside the inputs. Links in API standards (RFCs, style guides, papers) are citations; work from the text in the file.
- Do not pass input content or generated stories to web search, web fetch, an external API, or any other tool that sends data off this machine.

The skill needs no network access and runs no scripts: it reads local files, reasons, and writes one local file.

## Inputs

The user must provide three files (or paste their content). Files can be named anything — identify each file by its `# Title` heading or content, not by filename.

1. **Requirements** — ICP, needs, pain points, use cases, benefits. The "why" and "what." Look for a heading like `# Requirements`, `# Research`, or similar.
2. **Domain** — Data objects, properties, enums, object relations. The "nouns." Look for a heading like `# Domain`, `# Domain Model`, or similar.
3. **API Standards** — Style guide, naming conventions, path rules, security, error handling. The "how." Look for a heading like `# API Standards`, `# Style Guide`, or similar.

If any file is missing, ask the user to provide it before proceeding.

### Working Example

See `~/.claude/skills/arc-new-api-stories/references/examples/` for a complete set of inputs (conference scheduling API):
- `conference-research.md` — requirements
- `conference-domain.md` — domain model
- `API-standards.md` — API standards

If that folder does not exist (for example, when the skill is installed for another agent such as Codex), use `references/examples/` in the folder that holds this SKILL.md.

## Step 1: Read All Inputs

Read all three files completely. Understand:
- Who the API consumers are (from requirements)
- What entities and relationships exist (from domain)
- What conventions to follow (from standards)

## Step 2: Identify Themes and Use Cases

Group the use cases from the requirements into logical themes. Each theme maps to a cluster of related API operations. **Do not pause here — proceed immediately to Step 3 and generate all stories.**

Exception: if the user explicitly asks for step-by-step review, present the themes first and wait for confirmation.

## Step 3: Generate Stories (Default = Simple)

By default, generate **simple stories** — just enough for a product manager to review the API shape and validate the design direction.

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
- Use domain object names and property names as defined, written in the casing convention of the standards (see Key Principle 3)
- Do NOT include response schemas, error codes, headers, or implementation details
- Do NOT include authentication details unless the standards specify something unusual
- Write the stories in English unless the user asks for another language, even when the inputs are in another language. Names from the domain keep their words; only their casing follows the standards (see Key Principle 3).

### Detailed Story Format (on request)

If the user asks for detailed stories (for example, with `--detailed` after the skill name, or in plain words), add:
- Success response summary (status code + what's returned)
- Error responses (status codes + when they occur)
- Headers (rate limiting, pagination cursors)
- Notes on pagination approach

## Step 4: Present for Review

Present all themes and stories in a single pass. Do not pause between themes or ask for confirmation after each one — deliver the complete output, then ask once at the end if anything needs to change.

Exception: if the user explicitly asks for step-by-step review, pause after each theme.

## Step 5: Save

Save the completed stories to a local file the user specifies, or ask where they'd like it saved. No specific naming convention required. Start the file with the heading `# <API Name>: User Stories`, as in the example output below, so `arc-create-api-spec` and `arc-design-api` recognize it as stories.

**Never overwrite an existing file, and do not read existing files.** Check only whether the chosen name is taken. If it is, append a number (`-2`, `-3`, ...) before the extension, save under the new name, and tell the user the final path.

## Key Principles

1. **Stories are for PM review, not engineering specs.** Keep them scannable. A PM should be able to look at the method + resource + parameters and say "yes, that's the right API" or "no, we're missing X."

2. **Follow the standards religiously.** If the standards say camelCase, every parameter is camelCase. If they say pluralized resources, every resource is plural. If they say no /api prefix, don't add one. The stories ARE the first enforcement of the standards.

3. **Use domain language; casing follows the standards.** If the domain says `exchangeMic`, the parameter is `exchangeMic`, not `exchange_mic` or `exchangeId`. Domain is the source of truth for naming.

   Writing a domain label in the casing convention of the standards is not a rename: the property `ID` becomes `id`, `Track ID` or `TrackID` becomes `trackId`, `SpeakerIDs` becomes `speakerIds`, `StartTime` becomes `startTime`. Words, suffixes and enum values stay as the domain has them: `StartTime` does not become `startAt`, and the enum value `Keynote` stays `Keynote`. A casing change alone is not a conflict and does not go into Naming Decisions.

   When a domain name conflicts with a naming rule in the standards, apply the domain name. Conflicts are words, suffixes or enum values that break a standards rule (for example, the domain says `StartTime` and the standards want timestamps to end in `At`, or the domain has the enum value `Keynote` and the standards want lowercase enum values), and field names the domain already writes in a casing the standards forbid (for example, `trackID`). Do not rename silently: end the stories with a `## Naming Decisions` section that lists each conflict as domain name, the standards rule it departs from, and "domain applied", and mention the section when presenting the stories, so the user can change the domain if the standards should win.

4. **Nest resources per the domain relations.** If a Quote belongs to an Instrument, the resource is `/instruments/{id}/quotes`, not `/quotes?instrumentId=X`. Follow the nesting depth limit from standards.

5. **Don't invent requirements.** If the requirements don't mention delete or update operations, don't add them. Only design what was asked for. If you think something is missing, flag it as a question, don't silently add it.

6. **Pagination follows standards.** If standards specify cursor-based pagination, every collection endpoint gets `cursor` and `limit` parameters. Don't mix pagination styles.

## Example Output (Simple)

```markdown
# Pet Store API: User Stories

## Theme 1: Pet Management

#### Story 1.1: List Pets

**As a** store employee,
**I want** to browse all pets with optional filters,
**So that** I can find pets matching a customer's preferences.

* **Method:** `GET`
* **Resource:** `/pets`
* **Parameters:**
  * `cursor` (string, optional): Pagination cursor.
  * `limit` (integer, optional): Max results. Default 20.
  * `species` (enum, optional): Filter by species (Dog, Cat, Bird, Fish).
  * `status` (enum, optional): Filter by availability (Available, Sold, Pending).

#### Story 1.2: Get Pet Details

**As a** store employee,
**I want** to view full details of a specific pet,
**So that** I can answer customer questions about the pet.

* **Method:** `GET`
* **Resource:** `/pets/{petId}`
* **Parameters:**
  * `petId` (string, required): Unique pet identifier.
```
