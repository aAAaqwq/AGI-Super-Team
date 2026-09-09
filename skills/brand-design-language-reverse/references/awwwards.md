# Awwwards (awwwards.com) — Design Language Reference

> Reverse-engineering notes from 2026-09 public homepage inspection. Colors came
> from inline `:root` tokens; **interaction/motion/typography detail came from a
> 163 KB inline `<style>` block** that ships with the HTML. This reference is the
> "how it *feels*", not just "what colors".

## Brand archetype
Content/community platform for web-design awards. Monochrome discipline + one
orange brand accent + per-section category colors. Its polish comes from
**typography density and restrained motion** — not decoration.

## 1. Color system — all [observed] (inline :root)
| Role | Value | Use |
|------|-------|-----|
| text / link | `#222` (`--color-primary`, 26×) | body, links |
| light bg | `#f8f8f8` (`--bg-primary`) | page |
| alt bg / border | `#ededed` (`--bg-3rd`, `--border-gray`) | panels, hairline borders |
| inverse bg | `#222` | dark hero/footer |
| **brand orange** | `#FA5D29` (`--color-orange`= `--color-errors`=`--color-red`) | logo, primary CTA, badges, errors |
| hover dark | `#383838` | **button hover bg** (not orange) |
| muted text | `#a7a7a7`, `#7a7a7a` | secondary copy, uppercase labels |
| link blue | `#49B3FC` | links |
| per-section accents | awards `#502bd8` / inspire `#AAEEC4` / learn `#FFF083` / jobs `#74bcff` / read `#c0ab3c` | category tags, each with 2 lighter tints |

Pattern: black/white/gray carry the page; **orange is reserved for the ONE
"do this" action + logo**; category colors only appear as small tags/counts.

## 2. Typography — [observed]
| Item | Value |
|------|-------|
| family | **Inter Tight** (variable ttf preload) — `--font-1` |
| body | `font-size:14px; font-weight:300; line-height:200%` ← **the secret**: huge line-height = airy premium feel |
| headings | `font-weight:600` (bold, NOT 800) |
| hero heading | `clamp(42px, -3.07px + 9.01vw, 170px); line-height:100%` (two-term linear clamp) |
| h5 | `clamp(26px, 17.5px + 1.69vw, 50px); line-height:120%` |
| h6 (light) | `clamp(22px, 13.5px + 1.69vw, 46px); line-height:130%; font-weight:300` |
| uppercase labels | only tiny 12px `#a7a7a7` `letter-spacing` labels |
| smoothing | `-webkit-font-smoothing:antialiased; text-rendering:optimizeLegibility` |

Headings STOP at weight 600 even though 800 tokens exist. Large display type
uses negative-tracking only on the hamburger, not headings.

## 3. Interaction / motion — [observed] (the "feel")
**Global rhythm: every transition is `.3s`.** No springs, no big displacement.

- **Buttons**: default bg `#222`; **hover → bg `#383838`**, text→white; color/background/border each `.3s`. Orange (`--red`) is a variable override, not its own style. Sizes via height vars (72/60/42px). Focus uses `outline:none` — feedback is the bg swap.
- **Card figure hover**: image `transform:scale(1.05) translateY(-10px)` + `filter:drop-shadow(0 6px 3px rgba(34,34,34,.4))`; a **black bottom gradient scrim fades in** over the image (`linear-gradient(0deg, rgba(0,0,0,.5) 0%, transparent)`) to seat white text — `transition:all .3s`, starts `opacity:0`.
- **Plain image hover**: `filter:brightness(80%)` (dim, not zoom).
- **Nav link hover**: **`opacity:.7`** (fade, not underline). Active underline = full-width 1px `::after`, no grow animation.
- **Arrow / open state**: `transform:scaleY(-1)` flip.
- **Links (underlined)**: signature trick — a 220% wide two-tone gradient line (`rgb 45%` + `rgba .3 55%`), `background-size:220% 100%`, on hover shift `background-position:100%→0%`, `.3s ease-out`. Reads as an animated "chunked" underline.
- **Micro-labels**: `::after{content:attr(data-count)}` injects counts; dots default `opacity:.2`, active `1`.

## 4. Keyframes (all semantic, not decorative)
| Animation | What it does |
|-----------|--------------|
| `clippath` 2s linear inf | "load more" button: pink `#e52e86` border scans around the 4 edges via `clip-path:inset()` |
| `budgetShiny` 6s | subtle highlight sweep across a badge |
| `marquee_text` 4s linear inf | slow text ticker `translateX(0→-100%)` |
| `animloader` | 3 equalizer bars (loading grid) pulse height 48→4px, `.3s` |
| `loadingSpinner` / `btRotate` .6s | inline spinners |
| `progress` | SVG ring `stroke-dasharray` fill |
| `aniCountPulse` 1s×5 | live-count badge heartbeat `scale(1→1.4)` fade |

Motion is used for **loading + status only**; decorative loops are slow (4–6s).
Gradients appear only as image scrims and a 8px repeat hairline — no radial blobs.

## 5. Header & nav — [observed] exact values
- **Header height**: `--header-height` = `54px` (some views 71px); sticky, bg
  `--bg-primary` (`#f8f8f8`).
- **Nav text**: `--hm-text` = `--text-size-primary` **14px**; color `#222`
  (`--hm-color`). Items are **`padding-inline:10px`**, vertically centered in a
  `display:flex; height:100%` list.
- **Real top-nav order** (verified from served HTML): logo then
  **`Explore ▾`** (the ONE mega trigger) then **plain links**
  `Collections · Blog · Directory · Academy(New badge) · Jobs · Market`.
  Right side: `Log in · Sign Up · Be Pro` text links + orange **`Submit
  Website`** button. **Do NOT invent independent dropdowns** on Collections/
  Elements/Academy — only Explore drops. (`data-count` like `Nominees 48K`
  appears as a count column/link inside panels, not on every top item.)
- **Explore ▾ dropdown = a tabbed panel**: tabs **`Awards / Trending / By
  Category / By Technology`** (awwwards switches via Stimulus `doToogleTab`).
  - Awards: Honor Mentions, Nominees, Sites of the Day/Month/Year, Honors New,
    Most Awarded Profiles, Jury 2026, Annual Awards.
  - Trending: Portfolio Websites, Free fonts, Animated websites, Sites of the
    Day, Scrolling, One page design, UI design, E-commerce layouts,
    Architecture websites, Photography websites.
  - By Category: E-commerce, Architecture, Restaurant Hotel, Design Agencies,
    Business Corporate, Fashion, Mobile Apps, Interaction Design, Illustration,
    Header Design.
  - By Technology: CSS animations, Wordpress, Shopify, WebGL, React, 3D,
    Figma, Gsap, Framer, Webflow.
- **Hover**: link fades `opacity:.7` (not underline, not color shift). Arrow
  flips `scaleY(-1)` when dropdown opens.
- **Dropdown panel**: full-width below header, bg `--hm-active-bg` `#ededed`
  (or white card), rounded bottom corners, `min-height:450px`, content padded
  `0 424px 12px 60px` (right space for sub-panel/close). Left tab rail + link
  content; in-panel links ~14px/weight 300. Opens on click/keyboard (`.is-open`),
  not pure CSS hover.

## 5b. Homepage body layout — [observed]
**There is NO giant hero heading.** Below the header the page goes straight to
content:
1. **Site of the Day** block: label + date (`Sep 9, 2026`) + **Score `7.41 of
   10`** (big number) + studio name + a **PRO** tag + vote CTA, beside one
   large ~19/10 figure.
2. A section row head: **`Latest Nominees`** + `Vote for the latest websites →`.
3. A grid of nominee site cards (site name, studio, score bar).

## 6. Footer — [observed] structure
- Dark or light? Awwwards footer is a **dense multi-column layout** with small
  uppercase column headers.
- **Column types**: a brand/logo block + product columns (Sites, Elements,
  Academy, Jobs, Market, Directory) + company (About Us, Contact Us) + support
  (FAQs, Academy) + **social** (Facebook, Instagram, Twitter, LinkedIn,
  Pinterest, TikTok).
- **Bottom legal row**: `About Us · Contact Us · FAQs · Cookies Policy ·
  Privacy Policy · Legal Terms`.
- Uppercase 11px gray headers; links ~13px weight 300.

## 7. Card / navigation behavior (what "open" actually is)
- Cards link **out** to the work's own site (`<a href="…" target="_blank" rel="noopener nofollow">`), NOT to an SPA detail route. The "transition to detail" feel is the **hover scrim + float-up**, not a route animation.
- Hover overlay (`figure-rollover__hover`) is `pointer-events:none` until shown; inner buttons re-enable `pointer-events:auto`. Positioned absolutely with `1.6em` padding.

## 8. Tech stack — [inferred]
Server-rendered HTML (338 KB, `application/ld+json`, no SPA mount point / no
`__NUXT__` / no React root). Assets on `assets.awwwards.com/dist/js/*.hash.js`
with per-route chunks (`home_homepage.*.js`) → Webpack build. The strings
"Nuxt.js/Netlify" in the HTML are **page copy describing award-winning sites**,
not self-stated stack.

## When to apply this pattern
Content/community platform, awards/gallery/catalog, or any brand wanting
"calm premium" where the work itself is the star. The recipe that reproduces the
feel:
1. body `14px / line-height:200% / weight 300`
2. headings weight 600, huge `clamp()` with `line-height:100%`
3. `.3s` transitions everywhere; hover = bg swap `#222→#383838` or `opacity:.7`, not bounce
4. one saturated accent used once; everything else monochrome + muted grays
5. uppercase 12px gray labels for metadata
6. image hover: `scale(1.05)` + upward drift + bottom black scrim fade-in

## Copy-paste tokens + base styles
```css
:root {
  --text:#222; --muted:#a7a7a7; --muted-2:#7a7a7a;
  --bg:#f8f8f8; --bg-alt:#ededed; --bg-inverse:#222;
  --border:#ededed;
  --brand:#fa5d29; --hover-dark:#383838;
  --accent-awards:#502bd8; --accent-inspire:#aaeec4;
  --accent-learn:#fff083; --accent-jobs:#74bcff;
  --font:"Inter Tight",system-ui,sans-serif;
  --duration:.3s; --radius-sm:4px; --radius-md:8px;
}
body{font-family:var(--font);font-size:14px;font-weight:300;line-height:200%;
  -webkit-font-smoothing:antialiased;color:var(--text);background:var(--bg)}
h1,h2,h3{font-weight:600;line-height:1.05;letter-spacing:-.01em}
.btn{background:var(--bg-inverse);color:#fff;transition:background var(--duration);border:0}
.btn:hover{background:var(--hover-dark)}
.btn--brand{background:var(--brand)}
.btn--brand:hover{background:#e04a17}
.u-label{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
```
