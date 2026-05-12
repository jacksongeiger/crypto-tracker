# Coinbase Design Tokens (synthesized for crypto-tracker)

Reference notes for the design language we mirror in the frontend. These
values are observed from Coinbase's public product surfaces
(coinbase.com, the advanced trading interface, the Cove design system
posts on Medium/Figma Community). Coinbase Sans is proprietary; we use
Inter as the public substitute, which matches the visual weight closely.

## Palette

### Brand

| Token | Hex | Usage |
|---|---|---|
| `brand.50`  | `#EBF1FF` | tint backgrounds (TL;DR strips, hover surfaces) |
| `brand.100` | `#D6E3FF` | secondary tints, badge backgrounds |
| `brand.200` | `#ADC6FF` | subtle borders on tinted surfaces |
| `brand.500` | `#0052FF` | primary action — Coinbase's signature blue |
| `brand.600` | `#0040C2` | hover/pressed state on primary |
| `brand.700` | `#002E8A` | active/pressed deep |

### Foreground / background

| Token | Hex | Usage |
|---|---|---|
| `bg.canvas`        | `#FFFFFF` | page background |
| `bg.surface`       | `#FAFBFC` | secondary surfaces (cards on hover, tabs background) |
| `bg.surfaceMuted`  | `#F5F7FA` | inert surfaces (footers, code blocks) |
| `fg.primary`       | `#0A0B0D` | body text, headlines |
| `fg.secondary`     | `#5B616E` | metadata, labels |
| `fg.tertiary`      | `#8A8F98` | placeholders, faded |
| `fg.disabled`      | `#B1B5BC` | disabled text |

### Borders / lines

| Token | Hex | Usage |
|---|---|---|
| `border.subtle`  | `#EAECF0` | dividers between sections, card borders at rest |
| `border.default` | `#D7DBE0` | card borders, input borders |
| `border.strong`  | `#A8AEB7` | active inputs |

### Semantic

| Token | Hex | Usage |
|---|---|---|
| `success` | `#05B169` | positive 24h change, confirmed state |
| `danger`  | `#DF5F67` | negative 24h change, errors |
| `warning` | `#F0B90B` | caution, partial states |

## Typography

- **Sans**: Inter (variable weights 400, 500, 600, 700). Enable OpenType
  features `cv02 cv03 cv04 cv11` for the more characteristic Inter look
  (single-story `a`, etc.).
- **Mono**: JetBrains Mono for numeric data (prices, conviction scores,
  IDs, timestamps). Coinbase uses a custom mono for tabular figures;
  JetBrains Mono is the closest free substitute.

### Type scale

| Token | Size / line-height | Tracking | Weight | Usage |
|---|---|---|---|---|
| `display`  | 44/48 | `-0.025em` | 600 | page hero headlines |
| `h1`       | 34/40 | `-0.02em`  | 600 | section headings |
| `h2`       | 26/32 | `-0.015em` | 600 | card titles |
| `h3`       | 20/28 | `-0.01em`  | 600 | sub-headings |
| `bodyLg`   | 19/30 | `0`        | 400 | summary prose |
| `body`     | 16/26 | `0`        | 400 | default body |
| `bodySm`   | 14/22 | `0`        | 400 | metadata |
| `caption`  | 12/18 | `0.04em`   | 500 | eyebrow / labels |
| `mono`     | 13/20 | `0`        | 500 | numeric data |

## Spacing scale

4px base; generous overall.

`0=0, 1=4, 2=8, 3=12, 4=16, 5=20, 6=24, 7=32, 8=40, 9=48, 10=64, 11=80, 12=96`

## Radius

- `radius.sm = 6px` — small chips, tags
- `radius.md = 10px` — cards, popovers, dropdown menus
- `radius.lg = 14px` — large surfaces
- `radius.full = 9999px` — pills (use sparingly; Coinbase reserves pills
  for status indicators, not buttons)

## Elevation

Coinbase rarely uses heavy shadows. We use:

- `shadow.sm` — `0 1px 2px rgba(10,11,13,0.04)` — card resting
- `shadow.md` — `0 4px 12px rgba(10,11,13,0.08)` — popovers, hover lift
- `shadow.brandRing` — `0 0 0 4px rgba(0,82,255,0.12)` — focus ring on
  primary actions

## Motion

- Default transition: `150ms cubic-bezier(0.16, 1, 0.3, 1)` (a relaxed
  exit curve)
- Hover state durations: `150ms`
- Page transitions / large layout shifts: `220ms`

## Component patterns observed

- **Buttons**: subtly rounded (8–10px), tight padding (px-4 py-2 for sm,
  px-5 py-2.5 for md), no shadow at rest, no pill shape.
- **Cards**: 10px radius, 1px border, no shadow at rest, very subtle
  shadow on hover. Padding 24–32px.
- **Tabs**: bottom-underline style with 2px brand-blue under the active
  tab. The full bar gets a subtle bottom border.
- **Badges**: tiny radius (4–6px), uppercase tracked text, soft tinted
  background (e.g. brand.50 with brand.700 text).
- **Inputs**: 1px border, 10px radius, focus state uses
  `shadow.brandRing` + brand-blue border.
- **Dropdowns / popovers**: same 10px radius as cards, light shadow,
  border.subtle ring.
