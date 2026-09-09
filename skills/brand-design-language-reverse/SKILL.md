---
name: brand-design-language-reverse
description: >-
  Reverse-engineer the design language of any live website into structured,
  immediately-usable CSS design tokens, interaction/motion rules, and a feel-
  reproducing "recipe". Feed it a URL (Apple, FlexClip, Flourish, Stripe,
  Linear, any brand or SaaS site) and it produces a full breakdown — color
  system, typography rhythm (exact body line-height/weight, heading weights,
  clamp formulas), interaction & motion (hover/focus property changes,
  transition duration, keyframes, image-hover treatment, link-underline tricks,
  page-transition behavior), components, icon/animation technique, tech stack —
  plus ready-to-copy tokens and a replication quality gate. Colors alone never
  clone a site; this digs the CSS rules that make it *feel* right.
  MAKE SURE to use this skill whenever the user wants to: study a real site's
  design, copy the look/feel/colors/fonts of a competitor or admired brand,
  extract a brand's visual language before rebuilding it in React/CSS, compare
  how different products do UI, or turn an existing brand into tokens. Also
  use when the user asks "what tech does X use", "how did they style that",
  or wants to recreate a site's component style in their own project — even if
  they don't name the skill.
---

# Brand Design Language Reverse

Turn any live site into a copy-paste design system. Reads a real URL, extracts
what is observable (colors, fonts, component patterns, icon/animation
technique, framework), and outputs a five-part report ending in usable CSS
tokens. Analysis + delivery in one pass.

## When to Use

- You admire a brand/product and want to recreate its visual feel in your own
  project (landing, dashboard, component).
- You need a competitor's palette/type/components as a reference before
  designing.
- Someone asks "what tech/framework does that site use?" or "how did they do
  that animation/icon?".
- You are starting UI work and want a grounded, real-world reference instead of
  guessing at colors and patterns.

## Core Principles

1. **Evidence over guessing.** Distinguish three confidence levels in every
   report (see grading below). Never present an industry-known value as if you
   scraped it, and never invent values.
2. **Observe, don't reverse-engineer internals.** Inspect the public HTML/CSS/JS
   the server sends. Do not decompile, do not probe authenticated product
   internals, do not harvest private endpoints. Marketing/home pages are public
   and fair game; a logged-in editor is not.
3. **Deliver working output.** End every run with a concrete `tokens.css` /
   component snippet the user can drop in, not just an analysis essay.

## Evidence Grading

Annotate each claim in the report so the user knows what to trust:

| Grade | Meaning | Example |
|-------|---------|---------|
| `[observed]` | Read directly from served HTML/CSS this run | inline `#00b67a` present in page styles |
| `[inferred]` | Reasoned from a visible pattern / public CSS variable | gradient palette derived from two observed stops |
| `[known]` | Industry-public fact (Apple brand blue #0071e3) but NOT read this run | mark it clearly as known, not scraped |

## Workflow: URL → Design Tokens

### 1. Fetch the target URL

Use `WebFetch` (or `curl` for raw inspection) on the public page.

### 2. Extract the five dimensions

Gather raw evidence into a working notes table. Extract from served HTML/CSS,
not from memory:

- **A. Colors** — scan inline styles and stylesheets for `#hex` and `rgb(...)`.
  Count frequency; repeated high-frequency hexes are the real brand tokens.
  Exclude image-data noise (long data-URI blobs, image palette).
- **B. Typography** — look for `@font-face`, `font-family`, and font-loading
  URLs (`fonts.googleapis.com`, `/wss/fonts`, etc.).
- **C. Components** — read class names and structure for nav, buttons, cards,
  hero, footer, galleries. Note naming conventions (`ac-*`, `globalnav-*`,
  `product-*`).
- **D. Icons & animation** — inline `<svg>` vs icon fonts vs icon libs; classes
  hinting at scroll/motion (`*-chevron-icon`, `-dotnav-`, `parallax`); tech
  hints (WebGL, `three`, canvas).
- **E. Tech stack** — framework fingerprints: `__NEXT_DATA__`/`/_next/`
  (Next.js), `data-reactroot`/`react` (React), generator meta (Joomla/Wix/…),
  `vite`/`webpack` chunks, `type="module" crossorigin`.

- **F. Interaction & motion — the "feel" layer.** Colors/fonts alone never
  reproduce a site. Dig the actual CSS rules shipped with the page:
  - Look for a `<style>` block in the HTML — it can be 100 KB+ of the real
    design (many sites inline it). Extract it and search it.
  - **Hover/focus/active**: what property actually changes (background color?
    `opacity`? `transform`? `filter`)? Copy the rule + value.
  - **Transitions**: the `transition:` shorthand and duration (Awwwards =
    `.3s` everywhere). Global rhythm matters.
  - **Buttons**: default bg vs hover bg hexes; `:focus` treatment
    (`outline:none` + bg swap is a common premium pattern).
  - **Motion vocabulary**: `@keyframes` names + what they animate; when motion
    is used (loading/status) vs decorative; speeds.
  - **Image hover**: `scale()` / `translateY` / `drop-shadow` on the media —
    the #1 "expensive feel" detail.
  - **Link underline tricks**: two-tone `background-size` slide, vs width-grow,
    vs simple border.
  - **Page-transition / navigation**: is there a loader overlay, route-change
    fade, or is it plain `<a target=_blank>` out-links (Awwwards cards link OUT
    to the work's own site — no SPA route)? Don't assume SPA transitions exist.
- **G. Typography rhythm** — beyond the font name: exact body `font-size /
  line-height / font-weight`, heading weights (do they stop at 600?), the
  `clamp()` formula for display type, `-webkit-font-smoothing`, uppercase-label
  styling. Dense, small-type editorial rhythm is often the real brand.

- **H. Information architecture / content layout — the "arrangement" layer.**
  A clone fails if nav/footer/content blocks aren't arranged like the source.
  Extract the real structure, not just styling:
  - **Top nav**: the actual primary items in order (Awwwards: Sites ·
    Collections · Elements · Academy · Jobs · Market · Directory), the logo,
    right-side actions (Log in / submit). Per-item typography + spacing
    (`padding-inline`, height), the `--hm-*` color tokens, and **data-count
    badges** (Nominees "48K").
  - **Dropdown/mega-menu**: does hovering/clicking open a full-width panel?
    Its bg (`#ededed`), `min-height` (~450px), rounded bottom corners, number
    of columns, in-panel link size (14px/300), whether a data count or
    sub-panel appears on the right.
  - **Footer**: the column structure (brand block + product/company/support/
    social columns), which legal links exist in the bottom row (About Us,
    Contact Us, FAQs, Cookies Policy, Privacy Policy, Legal Terms), dark vs
    light bg, small uppercase column headers.
  - **Header height token** (`--header-height:54px` vs `71px`) and whether the
    open state swaps the whole header background to the panel color.

### 3. Grade each finding (`[observed]/[inferred]/[known]`)

### 4. Before writing: check for a self-reproducing "recipe"

If you can derive ONE concrete rule that reproduces the site's feel (e.g.
"body 14px / line-height 200% / weight 300; headings 600; hover = bg swap to a
darker neutral; one accent used once"), write it as an explicit **Recipe** line.
A color list without a recipe is not enough to clone the look.

### 5. Write the report + tokens

Produce the five-part report AND a `tokens.css` block:

```css
/* tokens.css — [Site Name] */
:root {
  /* A. Color */
  --brand-primary: #00b67a;   /* [observed] */
  --brand-dark: #1a1b1c;      /* [observed] */
  --brand-accent: #fe7651;    /* [observed] */
  --surface: #fff;
  --text: #1a1b1c;
  --radius: 12px;
  /* B. Type */
  --font-sans: "Roboto", Helvetica, Arial, sans-serif; /* [observed] */
  --font-display: var(--font-sans);
}
```

Then a short component recipe (nav / primary button / card) using those tokens.

## Report Structure (ALWAYS use this template)

```
# Design Language — <Site>

## 1. Color system
primary / dark / accent / surface / text, each with hex + evidence grade

## 2. Typography (rhythm, not just names)
families + exact body font-size/line-height/weight + heading weights +
clamp() formulas + smoothing + uppercase-label styling

## 3. Interaction & motion — HOW it responds
transition duration/rhythm; hover/focus/active property changes (bg? opacity?
transform?) with hexes; @keyframes vocabulary; link-underline trick; image
hover treatment; button default→hover hexes; page-transition/navigation
behavior (loader? SPA? plain out-links?)

## 4. Components
nav, buttons, hero, cards, footer + observable class-naming patterns

## 5. Information architecture / content layout (the arrangement)
top-nav items in real order + data-count badges; dropdown/mega-menu (bg,
min-height, columns, full-width?); header height + open-state bg swap;
footer column structure (brand/product/company/support/social) + bottom legal
links (About/Contact/FAQs/Cookies/Privacy/Terms); section hierarchy (hero→tabs
→grid)

## 6. Icons & animation
inline-svg vs icon lib; motion classes; WebGL/canvas presence

## 7. Tech stack
framework, builder, SSR/CSR evidence

## 8. Recipe (one rule that reproduces the feel)
e.g. "body 14px/200%/300; headings 600; .3s transitions; hover = bg swap;
one accent; uppercase 12px gray labels"

## → Copy-paste tokens
tokens.css + a component recipe (button/card) using those tokens + the Recipe
```

## Replication Quality Gate

A report is NOT done until these are answerable from it:
- [ ] I know the exact body font-size, line-height, weight (not just the font).
- [ ] I know what happens on hover of a button AND a card image (property + hex
  / transform value), not just that "there is hover".
- [ ] I know the global transition duration.
- [ ] I can write the site's look from tokens + recipe alone.
- [ ] I know whether "detail pages" are SPA transitions, a loader overlay, or
  plain external links — I didn't assume.
- [ ] I know the top-nav items in real order + whether items carry data-count
  badges or open a full-width dropdown.
- [ ] I know the footer column structure and which legal links sit in the
  bottom row (About/Contact/FAQs/Cookies) — not just "there is a footer".
- [ ] I can reproduce the header/footer/dropdown *arrangement*, not just colors.

## Known Reference Patterns

For brand archetypes you will meet repeatedly, `references/` holds distilled
observations. Read the relevant file only when the site matches:

- `references/apple.md` — Apple: extreme minimalism, SF Pro system type,
  inline SVG, scroll-driven motion, no heavy framework.
- `references/flexclip.md` — FlexClip: dark tool brand (ink #1a1b1c) with
  multi-accent system (green/orange/blue), Joomla shell + Next.js app.
- `references/flourish.md` — Flourish: data-viz SaaS, purple/blue duo,
  self-built viz core, Next.js marketing.
- `references/awwwards.md` — Awwwards: monochrome + one orange (#fa5d29),
  body 14px/200%/300, headings 600, .3s transitions, hover = bg swap to
  #383838, full-width dropdown nav, dark multi-column footer with
  About/Contact/FAQs/Cookies/legal row.

When a site is NOT one of these, reverse it fresh per the workflow above; do
not force it into a bucket.

## Style Notes

- Be specific with evidence: cite the selector/class where you saw a value.
- If a page is a marketing shell, say so and flag that the real product editor
  is a deeper, separate surface you did not inspect.
- If you cannot reach the site or extract anything, say that plainly and
  propose a fallback (Internet Archive, or user-supplied screenshot) instead of
  fabricating.
