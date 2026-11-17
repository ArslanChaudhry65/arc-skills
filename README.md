# arc-skills

Agent Skills by Arslan Chaudhry, Product Owner in learning software. Each skill is a folder under `skills/` with a `SKILL.md` and, where needed, scripts and references. They run in Claude Code and, where `compatibility` says so, in Codex.

## Skills

| Skill | Purpose |
| --- | --- |
| `arc-new-api-stories` | API design stories from requirements, a domain model and API standards |
| `arc-create-api-spec` | OpenAPI 3.1.0 from stories, with an offline linter and preview |
| `arc-api-spec-review` | Review an OpenAPI specification against standards and best practices |
| `arc-design-api` | The whole path from requirements to a validated specification |
| `arc-personal-brand` | Personal brand strategy for one person |
| `arc-brand-identity` | Visual identity brief |
| `arc-brand-guidelines` | Brand guidelines document |
| `arc-social-media-strategy` | Social media strategy built on a personal brand |

## API design: order and roles

The four API skills build on each other and keep product, development and QA in view.

1. `arc-new-api-stories` turns requirements, a domain model and API standards into API stories. Product owners or managers review and approve them.
2. `arc-create-api-spec` generates an OpenAPI 3.1 specification from the stories, lints it locally and shows a preview. Development usually takes over here.
3. `arc-api-spec-review` checks a new or existing specification against standards and best practices. The divergence report is written for QA and development; fixes follow only after their approval.

`arc-design-api` runs steps 1 and 2, including the review of the stories, in a single call. For an existing specification, step 3 is enough.

Inputs are Markdown files (requirements, domain model, API standards, best practices); every skill ships with examples. When names or values conflict, the domain model wins; the casing comes from the standards. Everything runs locally: the linter and preview need only the Python standard library, with no upload and no CDN.

The standards and best practices are general defaults. Some decisions may not fit every organization; pass your own rule sets instead of the examples.

## Installation

Copy the folder you want to `~/.claude/skills/`, for example:

```bash
cp -R skills/arc-new-api-stories ~/.claude/skills/
```

The four API skills build on each other. `arc-api-spec-review` and `arc-design-api` need the linter from `arc-create-api-spec`, so install them together. The brand skills refer to a workflow that is not part of this repo; they still run on their own.

## Origin and license

Everything is released under the MIT license, see [LICENSE](LICENSE).

- The four API skills are based on the method by Emmanuel Paraskakis (Level 250). His copyright notice is in the `LICENSE` of each of these skills.
- The four brand skills are adapted from [arnabbagxd/brand-building-skills](https://github.com/arnabbagxd/brand-building-skills) (MIT).
