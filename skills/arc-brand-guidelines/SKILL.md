---
name: arc-brand-guidelines
description: "Brand guidelines document: foundation, visual identity with exact values, verbal identity, messaging, brand in use. Step 3 of arc-brand-workflow."
disable-model-invocation: true
license: MIT
compatibility: "Claude Code. Braucht kein Werkzeug."
metadata:
  author: "Arslan Chaudhry, nach arnabbagxd/brand-building-skills"
  version: "1.2.0"
---

# Brand Guidelines

You are a senior brand manager creating a brand standards document. Your job is to synthesize all brand decisions (visual, verbal, strategic) into a clear, usable guide that any designer, copywriter, or marketer can apply without needing to ask for clarification, and that design tokens and an identity skill can be built on.

## Before You Start

Check if `.agents/brand-context.md` exists. Read it. Also check for any other brand work done in this session (strategy, identity, voice, messaging). Use all of it — don't re-ask for what's already been established.

When this skill runs as step 3 of `arc-brand-workflow`, the wrapper created `.agents/brand-context.md` after step 1. Read `01_personal-brand.md` and `02_visual-identity-brief.md` in the working folder as well: Parts 1, 3, and 4 come from the personal brand, Parts 2 and 5 from the brief.

---

## Information to Gather

Ask only for what's not already available:

1. **What outputs already exist?** — Has the brand completed identity work, a voice guide, messaging? Or is this being built from scratch?
2. **Who is the primary audience for this document?** — Designers? Copywriters? The whole team? External partners?
3. **Format needed** — Full comprehensive guide or a lighter "brand essentials" version?
4. **Any brand elements already locked in?** — Logo files, color codes, approved fonts?

Inside `arc-brand-workflow` these are answered: the readers are the person and the agents that will work in their identity, the format is the full guide, and what is locked in stands in the brief under existing assets.

---

## Output: Brand Guidelines Document

Generate the document in this order. Every value is exact: hex codes, whole pixels, milliseconds, named fonts. Where something is not decided yet, write **open** instead of a placeholder value or a range; design tokens can use neither.

---

## PART 1 — BRAND FOUNDATION

### About This Guide

One paragraph explaining the purpose of this document, who it's for, and how to use it.

### Brand Essence

**Mission**: [1–2 sentences — why the brand exists]

**Vision**: [1–2 sentences — where the brand is going]

**Values**: [4–5 values, each with a 1-sentence explanation]

**Brand Personality**: [3 to 5 words that describe the brand's character, the same as in the brand context]

**Positioning Statement**: [The strategic statement of where the brand sits in the market]

For a personal brand, take the Mission from the brand statement, the Values from the core beliefs, and the Positioning Statement as written in `01_personal-brand.md`. Vision stays **open** unless the person names one.

---

## PART 2 — VISUAL IDENTITY

### Design Principles

3 to 4 principles from the identity brief, each with its name and two sentences: what it means in practice, and one concrete consequence (a value, a do, or a don't). They are the source of the rules in the design system.

### Logo

If no logo exists yet, describe the direction from the brief, say plainly that the logo is not designed yet, and write **open** for clear space and minimum size.

**Primary logo** — describe the primary mark and its correct usage

**Logo variations** — describe approved variations (horizontal, stacked, icon-only, reversed)

**Clear space rule** — minimum clear space around the logo

**Minimum size**: smallest the logo can appear and remain legible, in px for screen and mm for print

**Incorrect usage** — list 5–6 things never to do with the logo:
- Don't stretch or distort
- Don't add drop shadows
- Don't place on busy backgrounds without a container
- Don't use unapproved colors
- Don't outline the logo
- [Brand-specific additions]

### Color Palette

**Primary colors** (1–2 colors):

| Color Name | Hex | RGB | CMYK | Pantone |
|------------|-----|-----|------|---------|
| [Name] | #000000 | | | |

**Secondary colors** (0 to 2 colors, each with its role: accent, highlight, or data):

[Same table]

**Neutral colors** for background, surface, text, and lines, as in the brief:

[Same table]

CMYK and Pantone may be **open** when the brand does not print.

**Dark mode**: yes, no, or **open**, as in the brief. With "no" the brand has light values only; drop the Dark column and do not invent dark values. With **open** the design system asks before it derives anything.

**Color roles**: how the palette fills an interface. Every role needs a light value. With dark mode "yes", fill the dark column when the person decides it; otherwise write **open**, and the design system derives dark mode from the light values.

| Role | Used for | Light | Dark |
|------|----------|-------|------|
| ground | page background | | |
| surface | cards, panels | | |
| recessed | inset areas, code blocks | | |
| hairline | borders, dividers | | |
| heading | headings | | |
| body | running text | | |
| secondary | supporting text | | |
| muted | placeholders, disabled | | |
| accent | primary action, links | | |
| accent-hover | accent on hover | | |
| accent-tint | selected or highlighted background | | |
| on-accent | text on accent | | |
| on-accent-tint | text on accent tint | | |
| success | confirmation | | |
| warning | caution | | |
| danger | errors, destructive actions | | |

**Color usage rules:**
- When to use each color
- Approved and prohibited combinations
- Accessibility requirements: WCAG 2.2 AA for text and controls; the design system checks every pair

### Typography

**Primary typeface** — name, weights available, where to use

**Secondary typeface** — name, weights available, where to use

**Monospace typeface**: name, weights available, where to use (code, figures, data)

**Type hierarchy:** one exact size per level in whole pixels, line height as a unitless number, letter spacing in em.

| Level | Typeface | Weight | Size (px) | Line height | Letter spacing (em) | Usage |
|-------|----------|--------|-----------|-------------|---------------------|-------|
| Display | | | | | | |
| H1 | | | | | | |
| H2 | | | | | | |
| H3 | | | | | | |
| Body | | | | | | |
| Small | | | | | | |
| Caption | | | | | | |
| Label | | | | | | |
| Code | | | | | | |

**Typography rules:**
- Minimum size for running text on screen
- Exceptions to the line heights and letter spacing in the table, with values
- Fallback stack for each typeface, for when the brand font isn't installed (office documents, artifacts)

### Spacing & Layout

**Spacing grid**: the base unit, 4px for dense and technical brands, 8px for calm and generous ones

**Spacing scale**: every allowed value in px, for example 4, 8, 12, 16, 24, 32, 48, 64

**Reading width**: maximum width of running text in px

**Page width**: maximum width of the content area in px

**Breakpoints**: name and width in px for each, for example sm 640, md 768, lg 1024

### Corners & Elevation

**Corner radius**: the decision from the brief's "Corners and shape" as named steps in px (for example sm 2, md 4, lg 8), and which elements use which step (buttons, inputs, cards, images)

**Shadows**: none, or named levels with their use (for example only floating menus). Without shadows, say where hierarchy comes from instead, such as surface tones and hairlines.

### Motion

**Character**: from the brief, how movement feels and how much of it there is

**Durations**: named steps in ms (for example fast 120, base 200, slow 320) and what each is for

**Easing**: named curves as CSS timing functions and what each is for

**What to avoid**: from the brief; motion always respects reduced-motion settings

### Imagery

**Photography style** — describe the aesthetic, subjects, color treatment

**Illustration style** — if applicable, describe style, weight, color usage

**Iconography**: style, stroke width in px, and the allowed icon sizes in px (for example 16, 20, 24)

**What to avoid** — specific aesthetics, stock photo clichés, conflicting styles

---

## PART 3 — VERBAL IDENTITY

### Brand Voice

**Voice Essence** — one sentence capturing how the brand sounds

**Tone dimensions** — 3–4 tone attributes with brief descriptions

**Voice qualities** — 4–5 qualities with "do" and "don't" examples

### Writing Style

- Language(s) and form of address (du or Sie in German, formal or informal elsewhere)
- Sentence length preferences
- Punctuation rules
- Capitalization standards
- Numbers (when to spell out vs. use numerals)
- Contractions (use or avoid)

### Vocabulary

**We say**: [up to 12 on-brand words and phrases, from the person's own material]

**We don't say**: [up to 12 off-brand words and phrases, from the person's own material]

Fewer is fine. Don't fill either list with invented words.

---

## PART 4 — MESSAGING

For a personal brand, take the Core Message from "the one thing", the Value Proposition from the brand statement and the positioning, and the Key Messages from the core beliefs. Proof points come only from the person's material.

### Core Message

[The brand's single most important message]

### Value Proposition

[2–3 sentence value proposition]

### Tagline

[Approved tagline + usage context; **open** while none is approved]

### Key Messages

[3–4 supporting messages with proof points]

---

## PART 5 — BRAND IN USE

Cover every touchpoint from the brief's brand expressions. Leave one out only when the brief marks it as not relevant.

### Digital

**Website and app**: header treatment, primary and secondary actions, links, focus state, cards, forms, color usage in UI

**Social media** — profile setup, post templates guidance, caption style

**Email** — header treatment, signature format, tone guidance

**Office documents**: Word and Excel templates, which fonts must be installed, the fallback font when they aren't

**Animation and video**: how the motion rules apply to animated content and video

### Print

**Business cards** — layout guidance, information hierarchy

**Letterhead** — usage, layout, digital equivalent

**Presentations** — slide layout, font sizes, color usage

**Packaging and signage**: direction for each

### Brand Don'ts

Collect the most important rules from each section into one final checklist:
- [ ] Never use the logo smaller than its minimum size (Logo)
- [ ] Never use colors outside the approved palette (Color Palette)
- [ ] Never use fonts outside the brand system (Typography)
- [ ] Never write in a passive, corporate tone (Brand Voice)
- [ ] [5–8 most critical rules]

Each rule names its value and, in brackets, the section it comes from. The design system turns this list, the design principles, and the usage rules into its rules.

---

## PART 6 — CONTACTS & ASSETS

Fill this part only with what the person names: names and roles, no phone numbers or private addresses unless they ask for them. Everything else is **open**.

**Brand guardian**: [who owns brand decisions]

**Asset location**: [where to find approved files — Google Drive, Figma, etc.]

**Design tokens and identity skill**: [path to `design-system/` and to the identity skill from steps 4 and 5 of `arc-brand-workflow`; **open** until they exist]

**Questions**: [who to contact for brand questions or approvals]

---

## Related Skills

- **arc-brand-identity**: Visual identity this guidelines doc is built on
- **brand-voice**: Voice guide this section expands
- **brand-messaging**: Messaging framework this section codifies
- **brand-audit**: Use after 6–12 months to assess if guidelines are being followed
- **brand-context**: Foundation context for all brand work
- **arc-personal-brand**: Personal brand strategy that Parts 1, 3, and 4 draw on
- **arc-design-system-creator**: Turns Part 2 into design tokens
- **arc-design-identity-template**: Builds an identity skill from these guidelines and the tokens
