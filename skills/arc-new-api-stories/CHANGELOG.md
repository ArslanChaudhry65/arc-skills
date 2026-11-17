# Changelog - arc-new-api-stories

## 1.2.3 - 2026-11-17

Prepared for public release.

- Changelog rewritten in English, without references to private documents.
- `compatibility` now says what the skill really needs: no scripts, no network.
- `LICENSE` adds a copyright line for the modifications; the upstream notice stays.

## 1.2.2 - 2026-11-13

- Renamed from `ach-new-api-stories` to `arc-new-api-stories`.
- Frontmatter now carries `license`, `compatibility` and `metadata` with `author` and
  `version`; `version` is no longer a top-level field.

## 1.2.1 - 2026-11-02

Domain names win over the standards for words, suffixes and enum values, but not for the
casing of field names. Field names follow the casing convention of the standards: `ID`
becomes `id`, `TrackID` becomes `trackId`, `StartTime` becomes `startTime` (not `startAt`),
and `Keynote` stays `Keynote`.

- Rewriting only the casing is not a rename and does not go into `## Naming Decisions`.
  Real conflicts do: words, suffixes or enum values that break a rule of the standards, and
  field names the domain itself already writes in a forbidden casing, such as `trackID`.

## 1.2.0 - 2026-11-02

- Stories are written in English unless the user asks for another language, also for
  German input.
- When a domain name conflicts with a naming rule of the standards, the domain wins. The
  conflict is not dropped silently: the stories end with a `## Naming Decisions` section,
  and the handover points to it.

## 1.1.0 - 2026-11-02

The skill runs on Windows and macOS, for any organization, under Claude Code and Codex, and
no data leaves the machine, because confidential requirements go through it.

- New section `Data Handling`: input only from local files or pasted text; links in the
  input are not opened; nothing goes to web search, web fetch or other outside services.
- Saving never overwrites an existing file; if the name is taken, a number is appended.
- The saved file starts with `# <API Name>: User Stories`, so the sibling skills recognize
  it as stories.
- If `~/.claude/skills/arc-new-api-stories/references/examples/` does not exist, for
  example when installed for Codex only, `references/examples/` next to `SKILL.md` is used.
- The detailed format can be requested with `--detailed` after the skill name or in words.

## 1.0.0 - 2026-11-02

Forked from `design-api-stories` in https://github.com/paraskakis/skills, commit `dbe04cf`
(folder `api/design-api-stories`, last changed in `9acbc6b`, upstream version 1.0.0). MIT
license; `LICENSE` is the upstream file.

Changes from upstream:

- Renamed, and references to the sibling skills renamed accordingly.
- Paths to `references/` are absolute under `~/.claude/skills/<skill>/references/`, so they
  resolve regardless of the working directory.
- Otherwise unchanged, including the examples under `references/examples/`.
