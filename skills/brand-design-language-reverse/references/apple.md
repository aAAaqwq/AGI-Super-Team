# Apple (apple.com) — Design Language Reference

> Reverse-engineering notes from 2026-09 public homepage inspection. Values are
> graded per the skill's Evidence Grading. Use this as a *pattern reference* when
> building minimal/premium brand surfaces — not as a pixel clone.

## Brand archetype
Premium-minimalist product/marketing site. The homepage is a **server-rendered
content shell** with heavy CSS layering and scroll-driven reveal modules. Apple
does NOT use a mainstream JS framework on the marketing page.

## 1. Color
| Role | Value | Grade |
|------|-------|-------|
| brand primary | black/white system (#000 / #fff) | [observed] body uses monochrome |
| brand accent | Apple blue #0071e3 | [known] industry-public; NOT read this run |
| background | #fff / #f5f5f7 (light-gray page) | [inferred] gray surfaces are Apple-signature |
| text | near-black #1d1d1f | [known] Apple system text tone |
| inline hexes seen | #000, plus per-hero image colors | [observed] mostly image-derived |

Color is used **sparingly** — monochrome base, one accent. Screenshots/heros
carry the color weight, not the chrome.

## 2. Typography
| Item | Value | Grade |
|------|-------|-------|
| family | SF Pro (loads via `/wss/fonts?families=SF+Pro,v3|SF+Pro+Icons,v3`) | [observed] |
| style | system sans; tight tracking; huge weight contrast (thin→semibold) | [observed]/[inferred] |
| principle | single family does everything via weight/size, not extra fonts | [inferred] |

Uses its own **SF Pro + SF Pro Icons** font pipeline (not Google Fonts).

## 3. Components & naming
Class prefixes reveal an internal component system:
- `ac-*` — Apple classic shared chrome (`ac-nav-overlap`, `ac-gf-content/footer`…)
- `globalnav-*` — global header (`globalnav-scrim`, chevron icon)
- `media-gallery-*` — media galleries, dot-nav pagination
- section-level modules (`section-endless-entertainment-gallery`)
- Chrome components (global-header/footer) load as **self-contained UMD/built
  bundles** (`globalheader.umd.js`, `ac-globalfooter.built.js`).

## 4. Icons & animation
- Icons = **inline `<svg>`** with explicit `viewBox` (e.g. `0 0 9 48`), classed
  like `globalnav-chevron-icon`. No icon font for chrome.
- Motion is **scroll/reveal driven**, hand-rolled in page `*.built.js` bundles
  (`bts2026.built.js`, `home.built.js`). No WebGL/three on the marketing
  homepage — motion is DOM/SVG + compositor friendly.

## 5. Tech stack
- **No mainstream framework** on marketing page (no `__NEXT_DATA__`, no React
  root markers).
- Server-side rendered HTML with `lang`, `class="no-js"` — content-first,
  strong SEO.
- Per-page + per-component JS via versioned paths `/v/home/a/scripts/*.built.js`,
  Webpack-built (`main.built.js`), cached aggressively.
- Analytics: **self-hosted** `ac-analytics` + data-relay — no Google on page.

## When to apply this pattern
- Premium/minimal brand surface, product marketing, "expensive feel" landing.
- Use when you want: one strong type system, monochrome + one accent, inline
  SVG icons, scroll-reveal motion over heavy 3D, content that renders before JS.

## Copy-paste tokens (Apple-flavored minimal)
```css
:root {
  --bg: #ffffff;
  --bg-alt: #f5f5f7;
  --text: #1d1d1f;
  --text-muted: #6e6e73;
  --accent: #0071e3;            /* known */
  --radius: 18px;
  --font-sans: -apple-system, "SF Pro Text", "Helvetica Neue", Helvetica, Arial, sans-serif;
  --tracking-tight: -0.02em;
  --ease: cubic-bezier(0.32, 0.72, 0, 1);
}
```
Recipe: generous whitespace, no border clutter, single accent for CTA, huge
display type with negative tracking, cards separated by `--bg-alt` not borders.
