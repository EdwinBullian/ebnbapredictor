# EB NBA Predictor — Design Spec v2

## Vision
Bloomberg terminal meets sports betting dashboard. Data-dense, dark, sharp. Every pixel serves the data. No soft edges, no grey-blue mush.

---

## Color System

### Backgrounds (true darks, not grey-blue)
| Token | Hex | Usage |
|-------|-----|-------|
| `bg-primary` | `#0A0A0A` | Page background (near-black) |
| `bg-surface` | `#111111` | Cards, table body, sidebar |
| `bg-elevated` | `#1A1A1A` | Hover rows, expanded panels, modals |
| `bg-header` | `#0D0D0D` | Navbar, table header |

### Terminal Greens & Reds (strong, Bloomberg-style)
| Token | Hex | Usage |
|-------|-----|-------|
| `terminal-green` | `#00FF66` | OVER edges, positive values, active states |
| `terminal-red` | `#FF3B3B` | UNDER edges, negative values, losses |
| `terminal-green-dim` | `#00FF6620` | Green row backgrounds (subtle) |
| `terminal-red-dim` | `#FF3B3B20` | Red row backgrounds (subtle) |

### Accents & Data
| Token | Hex | Usage |
|-------|-----|-------|
| `accent-blue` | `#3B82F6` | Active tab indicator, links |
| `accent-amber` | `#F59E0B` | Warnings, medium confidence |
| `text-primary` | `#E8E8E8` | Primary text (not pure white — reduces glare) |
| `text-secondary` | `#888888` | Labels, secondary info |
| `text-muted` | `#555555` | Disabled, tertiary info |
| `border` | `#222222` | Subtle borders, dividers |
| `border-bright` | `#333333` | Active borders, focus rings |

---

## Typography

### Fonts
- **Data / Numbers:** `Fira Code` (monospace) — predictions, lines, edges, percentages, sidebar scores
- **UI / Labels:** `Fira Sans` (sans-serif) — player names, team names, headings, tabs, buttons

### Scale
| Element | Font | Size | Weight |
|---------|------|------|--------|
| Page title ("EB") | Fira Code | 20px | 700 |
| Nav subtitle ("NBA Predictor") | Fira Sans | 14px | 400 |
| Tab buttons | Fira Code | 12px | 600 |
| Table header | Fira Code | 11px | 500, uppercase, letter-spacing 0.05em |
| Player name | Fira Sans | 14px | 500 |
| Team/Opp abbreviation | Fira Code | 12px | 400 |
| Predicted / Line / Edge values | Fira Code | 14px | 600 |
| Confidence pill | Fira Code | 11px | 700 |
| Top Edges banner text | Fira Code | 12px | 500 |
| Sidebar game matchups | Fira Code | 13px | 500 |
| Date display | Fira Code | 12px | 400 |

---

## Layout Structure

```
+---------------------------------------------------------------+
| NAVBAR (fixed top, bg-header, h-12)                           |
| [EB] NBA Predictor   [PTS][REB][AST][PARLAYS][RECORD]   Date |
+---------------------------------------------------------------+
|                                               |               |
|  MAIN CONTENT (scrollable)                    | SIDEBAR       |
|                                               | (w-56, fixed) |
|  +-- TOP EDGES TICKER (bg-surface, border) --+|               |
|  | pill pill pill pill pill                    || TODAY'S GAMES |
|  +--------------------------------------------|| ------------- |
|                                               || ATL  @  CLE  |
|  +-- PREDICTION TABLE --------------------+  || MIN  @  ORL  |
|  | HEADER ROW (bg-header, sticky)         |  || MIL  @  DET  |
|  | ─────────────────────────────────────── |  || ...          |
|  | Player row (hover: bg-elevated)        |  ||              |
|  |   > Expanded: Last 5 chart + details   |  ||              |
|  | Player row                             |  ||              |
|  | Player row                             |  ||              |
|  | ...                                    |  ||              |
|  +-----------------------------------------+  |               |
+---------------------------------------------------------------+
```

---

## Component Designs

### 1. Navbar
- **Height:** 48px, fixed top
- **Background:** `bg-header` with 1px bottom border (`border`)
- **Left:** "EB" in `terminal-green` Fira Code bold + "NBA Predictor" in `text-secondary` Fira Sans
- **Center:** Tab buttons in a row, no rounded corners
  - Default: `text-secondary`, no background
  - Active: `text-primary` with 2px bottom border in `terminal-green`
  - Hover: `text-primary`
  - Font: Fira Code 12px uppercase, letter-spacing 0.1em
- **Right:** Date in `text-secondary` Fira Code

### 2. Top Edges Ticker
- **Container:** `bg-surface`, 1px border `terminal-green-dim`, no border-radius
- **Label:** "TOP EDGES" in `terminal-green` Fira Code 11px uppercase, left side
- **Pills:** Horizontal scroll row of edge pills
  - Each pill: player name in `text-primary` + "OVER/UNDER" in green/red + line value + edge delta
  - Background: `terminal-green-dim` or `terminal-red-dim`
  - No border-radius (square/sharp corners, 2px max)
  - Fira Code 12px
  - Separated by thin vertical divider (`border`)

### 3. Prediction Table
- **No outer border-radius** — sharp edges everywhere
- **Header row:** `bg-header`, sticky top, Fira Code 11px uppercase `text-secondary`
  - Columns: PLAYER | TEAM | OPP | PRED | LINE | EDGE | CONF
  - Sortable columns show small arrow indicator
- **Data rows:**
  - Default: `bg-surface`, 1px bottom border (`border`)
  - Hover: `bg-elevated`
  - Player name: Fira Sans 14px `text-primary`
  - Team/Opp: Fira Code 12px `text-secondary`
  - Pred: Fira Code 14px bold `text-primary`
  - Line: Fira Code 14px `text-secondary`
  - Edge: Fira Code 14px bold, colored:
    - Positive: `terminal-green` with "+" prefix
    - Negative: `terminal-red` with "-" prefix
  - Confidence: Colored pill/bar
    - 60+: `terminal-green` bg with dark text
    - 40-59: `accent-amber` bg with dark text
    - <40: `text-secondary` bg
    - Pill shape: sharp corners (2px radius max), Fira Code 11px bold
    - Also render a thin horizontal bar behind the number showing fill %

### 4. Expanded Player Row (on click)
- Slides open below the clicked row
- Background: `bg-elevated` with left border accent (3px `terminal-green` or `terminal-red`)
- **Left side:** Bar chart of last 5 games using Recharts
  - Bars colored green if above the line, red if below
  - Horizontal dashed line at the PrizePicks line value
  - X-axis: game dates (compact), Y-axis: stat values
  - Fira Code labels
  - Dark theme: grid lines `#222222`, bars have slight glow
- **Right side:** Key stats
  - Season avg, Last 5 avg, predicted, line
  - Key factors (from prediction data) as small tags
  - All in Fira Code / Fira Sans

### 5. Games Sidebar
- **Width:** 224px (w-56), fixed right
- **Header:** "TODAY'S GAMES" in Fira Code 11px uppercase `text-secondary`, with small right-arrow
- **"All Games" button:** Active state with `terminal-green` text
- **Game rows:**
  - Layout: `AWAY  @  HOME` centered
  - Team abbreviations in Fira Code 13px `text-primary`
  - "@" in `text-muted`
  - Hover: `bg-elevated`
  - Selected: left border 2px `terminal-green`
  - 1px bottom border (`border`)

### 6. Players Without Lines
- Shown in a collapsed section at the bottom
- Header: "NO LINES AVAILABLE" in `text-muted` with count
- Collapsed by default, expandable
- When expanded: simpler row (just player, team, opp, prediction — no edge/conf)

---

## Interactive Behaviors

### Row Click → Expand
- Click a player row to expand their detail panel below
- Smooth height animation (200ms ease-out)
- Only one row expanded at a time (clicking another closes the previous)
- Close by clicking the same row again

### Tab Switching
- Instant data swap (no page reload)
- Active tab has green underline that slides to new position (150ms)

### Sorting
- Click table headers to sort
- Default: confidence descending
- Visual indicator: small triangle arrow next to sorted column

### Hover Effects
- Table rows: background shifts to `bg-elevated` (100ms)
- Tabs: text brightens to `text-primary` (100ms)
- Games sidebar: background shifts (100ms)

---

## Responsive Notes
- Below 1024px: sidebar collapses to a horizontal game ticker above the table
- Below 768px: table columns compress (hide OPP column, abbreviate headers)
- Font sizes stay readable (no smaller than 11px)

---

## Tech Implementation Notes
- **Fonts:** Load via `next/font/google` (Fira Code + Fira Sans)
- **Charts:** Recharts `<BarChart>` for last-5 expansion, `<ReferenceLine>` for the PrizePicks line
- **Animations:** CSS transitions only (no JS animation libraries needed)
- **Tailwind v4:** Define color tokens as CSS custom properties in `app/globals.css`
- **No border-radius anywhere** except confidence pills (2px max)
