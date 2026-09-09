# FlexClip (flexclip.com) — Design Language Reference

> Reverse-engineering notes from 2026-09 public homepage inspection. FlexClip is
> an online video editor SaaS — a **dark, tool-first brand** with a strong
> multi-accent color system. Color evidence is [observed] (high-frequency inline
> hexes), making this the most reliable palette of the three references.

## Brand archetype
Creative-tool SaaS (like Canva-class editors). Message: powerful but friendly,
"professional tool that anyone can use". Marketing page is a marketing shell;
the actual editor is a separate, heavier application surface.

## 1. Color — [observed] (from served HTML)
| Role | Value | Notes |
|------|-------|-------|
| ink/dark | `#1a1b1c` (19×) | near-black; page text + dark sections |
| dark-alt | `#17191d`, `#0b0c13` | secondary dark surfaces |
| muted text | `#a5a8b0`, `#aaadb9`, `#393f4f` | grays for secondary text |
| **primary green** | `#00b67a` (11×) | brand green — CTAs / positive |
| accent orange | `#fe7651` (6×) | secondary CTA / energy |
| accent blue | `#517df8` (6×) | tertiary / link-ish |
| white | `#fff` / `#ffffff` | text on dark |

Pattern: **dark canvas + one green primary CTA + orange/blue accents**. Very
different from Apple's monochrome — a tool brand uses color to telegraph
function (green = "go/do this").

## 2. Typography
| Item | Value | Grade |
|------|-------|-------|
| family | Roboto stack (`font-family: roboto, Helvetica, Arial, sans-serif`) | [observed] |
| principle | one neutral sans; hierarchy via weight/size | [inferred] |

## 3. Components & architecture
- **Hybrid stack**: a Joomla shell (`/media/system/js/core.min.js`,
  `media/fj4-*`) wrapping a **Next.js app** (`__NEXT_DATA__`, buildId
  `cnWD3YkzREUNjjE1RDKLj`, chunks under `/next_webview/_next/static/`).
- Independent feature modules each bundle their own UI:
  - login panel → `/app/login/login-panel/static/.../js/index.js` (Vite,
    `type="module" crossorigin`)
  - subscription → `/app/subscription/static/.../js/index.js`
  - share-tools, message, cookies → versioned `/media|web-res/js/*`
- Icon classes: `top-icon`, `ai-svg` (AI feature icons), `svg` with `xmlns:xlink`.

## 4. Icons & animation
- Inline `<svg>` for icons (`top-icon`, `ai-svg`); `svg` blocks with sprite/xlink
  references. [observed]
- Editor product itself (video timeline, playback) is a Canvas/web-video engine
  — a separate application surface **not inspected** here. [flagged]

## 5. Tech stack
- Marketing: **Joomla** (legacy shell) + embedded **Next.js** webviews +
  **Vite** micro-apps. Multi-framework transition architecture.
- Analytics: `ealog.js` + subscription/tracking scripts.

## When to apply this pattern
- Any **tool/creator SaaS** that wants "dark, powerful, friendly": dark ink
  canvas, one confident primary CTA color, 1–2 supportive accents, neutral
  sans, feature icons as inline SVG with `*-svg` classes.

## Copy-paste tokens (FlexClip-style dark tool)
```css
:root {
  --ink: #1a1b1c;
  --ink-alt: #17191d;
  --ink-deep: #0b0c13;
  --text: #ffffff;
  --text-muted: #a5a8b0;
  --primary: #00b67a;   /* green CTA */
  --accent-1: #fe7651;  /* orange */
  --accent-2: #517df8;  /* blue */
  --radius: 10px;
  --font-sans: "Roboto", Helvetica, Arial, sans-serif;
}
```
Recipe: dark header/sections with white text, green primary buttons (hover to a
lighter green), orange/blue used sparingly for secondary actions and highlights,
muted gray (#a5a8b0) for supporting copy so white stays meaningful.
