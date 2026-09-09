# Flourish (flourish.studio) — Design Language Reference

> Reverse-engineering notes from 2026-09 public homepage inspection. Flourish is
> a **data-visualization SaaS** (users build charts/stories). Brand = calm,
> analytical, colorful-but-controlled. Marketing page is Next.js; the real
> product is a self-built visualization engine (embed scripts, not a generic
> chart library).

## Brand archetype
Data-viz / content-tool SaaS. Audience: journalists, studios, analysts — needs
to feel trustworthy and creative simultaneously. Colors are soft, friendly,
with one strong primary.

## 1. Color — [observed] (from served HTML)
| Role | Value | Notes |
|------|-------|-------|
| **brand purple** | `#9852d9` | signature primary |
| **link/action blue** | `#135ae1` | secondary action |
| light purple tint | `#e7d9f6` (2×) | backgrounds / soft accents |
| light blue tint | `#d0dbf3` (2×) | backgrounds / soft accents |

Pattern: a **duo of purple + blue** plus their light tints used as soft
background fills — friendlier than FlexClip's dark tool and less austere than
Apple. Color feels "data-viz-native": tints for fills, saturated pair for
actions.

## 2. Typography
| Item | Value | Grade |
|------|-------|-------|
| family | (no Google Fonts on marketing page; local/system) | [observed: none found] |
| principle | editorial-ish clarity befitting a data product | [inferred] |

## 3. Components
- Product-card grid for their viz tools; class hints `product-icon-container`,
  `product-icon product-viz-icon` — each data-viz type (viz/chart) has its own
  icon. [observed]
- Marketing pages: standard SaaS header + card sections.

## 4. Icons & animation
- Data-viz types represented as **inline-SVG product icons** (`product-viz-icon`).
- Visualization embedding via `https://public.flourish.studio/resources/embed.js`
  — iframes to self-hosted viz. The chart engine itself is **self-built** (not
  D3/ECharts-branded marketing). [observed]

## 5. Tech stack
- Marketing: **Next.js** (`next` markers). [observed]
- Analytics: OneTrust (consent) + GA + **Snowplow** (event pipeline) +
  **FullStory** (session replay). Notably heavy, data-driven analytics stack —
  fitting for a data company.
- Product: self-hosted viz core + public embed host (`public.flourish.studio`).

## When to apply this pattern
- A **data/analytics/insight product**, or any brand wanting "friendly +
  credible". Use a saturated primary + secondary action color, with light tints
  of the same hues as soft surface fills. Give each product category/feature a
  bespoke inline-SVG icon. Invest in real analytics instrumentation.

## Copy-paste tokens (Flourish-style data-viz SaaS)
```css
:root {
  --primary: #9852d9;     /* purple */
  --action: #135ae1;      /* blue */
  --primary-tint: #e7d9f6;/* soft purple fill */
  --action-tint: #d0dbf3; /* soft blue fill */
  --text: #10151f;
  --text-muted: #5a6472;
  --bg: #ffffff;
  --radius: 12px;
  --font-sans: system-ui, "SF Pro Text", Roboto, Helvetica, Arial, sans-serif;
}
```
Recipe: white canvas, purple for primary identity/brand moments, blue for
links/actions, the two tints for section backgrounds and card fills; mute body
copy to keep the saturated pair meaningful.
