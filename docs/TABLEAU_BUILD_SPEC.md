# Tableau build spec

Everything below maps to real column names in the Postgres layer, so the workbook and the SQL
layer stay consistent. Numbers quoted in the story scenes are taken from
`db/analysis_results.txt` and are reproducible with seed 42.

## 1. Data source

Prefer **one** source so cross-sheet filters interwork without blend tricks.

**Option A — live Postgres** (try first; needs Tableau Public to permit a DB connector)

| Setting | Value |
|---|---|
| Connector | PostgreSQL |
| Server | `localhost` |
| Port | `5432` |
| Database | `ev_analytics` |
| Authentication | Username and password |
| Username / password | `ev` / `ev_local_only` |
| Table | `public.v_ev_data` |

Tableau Public only supports **extracts** for external databases. On connect, choose Extract
(not Live). Refresh with `bash scripts/load_db.sh` then right-click the data source → Refresh.

**Option B — CSV export** (works regardless)

Run `bash scripts/export_tableau.sh` and open `data/tableau/ev_data.csv`. It is the same 1,263
rows and 31 columns as `v_ev_data`. Add the other nine CSVs as related sources only if you want
pre-aggregated sheets.

Set **Date** properties on `model_year` to "Year" so the axis reads as years, not a count. Assign
the **Geographic role → Country** to `country_of_origin`.

## 2. Calculated fields

Create all of these on the `v_ev_data` source. Field names are shown exactly as they appear.

| Name | Definition | Used by |
|---|---|---|
| Sales Weighted Range | `SUM([driving_range_miles] * [annual_sales_units]) / SUM([annual_sales_units])` | KPI, trend, category |
| Sales Weighted Price | `SUM([price_usd] * [annual_sales_units]) / SUM([annual_sales_units])` | KPI, positioning |
| Share of Dataset Sales % | `SUM([annual_sales_units]) / TOTAL(SUM([annual_sales_units]))` | every share chart |
| Battery Demand GWh | `SUM([gwh_battery_demand])` | battery, geography |
| CO2e Avoided (kt) | `SUM([co2e_avoided_tonnes]) / 1000` | sustainability |
| YoY Growth % | `(SUM([annual_sales_units]) - LOOKUP(SUM([annual_sales_units]), -1)) / LOOKUP(SUM([annual_sales_units]), -1)` | trend (table calc, compute using `model_year`) |
| Models Count | `COUNTD([model_id])` | treemap, map |
| Brands Count | `COUNTD([brand])` | KPI |
| Avg Charging Rate C | `SUM([peak_charging_kw] * [annual_sales_units]) / SUM([annual_sales_units] * [battery_capacity_kwh])` | battery |
| Price Band | `IF [Sales Weighted Price] < 20000 THEN "A. under $20k" ELSEIF [Sales Weighted Price] < 40000 THEN "B. $20k to $40k" ELSEIF [Sales Weighted Price] < 70000 THEN "C. $40k to $70k" ELSE "D. over $70k" END` | positioning |
| Range Band | `IF [Sales Weighted Range] < 200 THEN "1. under 200 mi" ELSEIF [Sales Weighted Range] < 300 THEN "2. 200 to 300 mi" ELSE "3. over 300 mi" END` | category |
| Grid Band | `IF MIN([grid_intensity_kgco2_per_kwh]) < 0.10 THEN "1. Clean grid" ELSEIF MIN([grid_intensity_kgco2_per_kwh]) < 0.35 THEN "2. Mixed grid" ELSE "3. Coal-heavy grid" END` | sustainability |
| Technology Class | `IF [battery_technology] IN ("Semi-Solid-State","Sodium-Ion") THEN "Emerging" ELSE "Established" END` | battery, story |
| Satisfaction Tier | `IF AVG([customer_rating]) >= 4.40 THEN "Excellent" ELSEIF AVG([customer_rating]) >= 4.10 THEN "Good" ELSE "Below average" END` | heatmap |
| Brand Share Within Category % | `{FIXED [brand], [body_type]: SUM([annual_sales_units])} / {FIXED [body_type]: SUM([annual_sales_units])}` | LOD demo, heatmap tooltip |

Reference the plain-column versions (`driving_range_miles`, `customer_rating`) when a chart is
deliberately an unweighted model average, such as the box plot; use the weighted versions for
anything presented as a market statistic. Say which is which in the tooltip.

## 3. Worksheets

Build these twelve; the last three are optional extras.

| # | Sheet name | Mark | Rows / Columns | Feeds |
|---|---|---|---|---|
| W1 | KPI Strip | Measure values on Text | `annual_sales_units` (SUM), `Sales Weighted Range`, `Brands Count`, `Battery Demand GWh` | all dashboards |
| W2 | Sales by Manufacturer | Bar | Rows `brand` (sort desc, Top 10), Columns `annual_sales_units` | D1 |
| W3 | Annual Sales Trend | Line | Columns `model_year`, Rows `annual_sales_units`; label with `YoY Growth %` | D1, Story 1 |
| W4 | Share by Manufacturer | Bar (100%) | Columns `model_year`, Rows `Share of Dataset Sales %`, Colour `brand` (Top 5 + Other) | D1, Story 2 |
| W5 | Category Treemap | Square | Size `annual_sales_units`, Colour `Sales Weighted Range`, Label `body_type` | D1 |
| W6 | Chemistry Donut | Pie (dual ring) | Angle `Share of Dataset Sales %`, Colour `battery_technology` | D2, Story 3 |
| W7 | Chemistry GWh Bar | Bar | Rows `battery_technology`, Columns `Battery Demand GWh` | D2, Story 3 |
| W8 | Capacity vs Range | Circle | Columns `battery_capacity_kwh`, Rows `driving_range_miles`, Colour `body_type`, Detail `model_name` | D2, Story 3 |
| W9 | Range Box by Category | Circle + Box | Rows `body_type`, Columns `driving_range_miles` | D2 |
| W10 | Charging Profile | Bar | Rows `battery_technology`, Columns `charging_time_min_10_80`, Colour `Avg Charging Rate C` | D2 |
| W11 | Satisfaction Heatmap | Square | Rows `brand`, Columns `body_type`, Colour `customer_rating` | D1, Story 2 |
| W12 | Top Rated Models | Horizontal bar | Rows `model_name` (filter `annual_sales_units >= 50000`), Columns `customer_rating` | D1 |
| W13 | Chemistry by Manufacturer | Stacked bar | Rows `brand`, Columns `Share of Dataset Sales %`, Colour `Technology Class` | D2 |
| W14 | Manufacturing Map | Map | Rows `country_of_origin`, Size `annual_sales_units`, Colour `Battery Demand GWh` | D3, Story 4 |
| W15 | Grid vs CO2 Benefit | Bar | Rows `country_of_origin`, Columns `AVG(est_annual_co2e_saved_tonnes)`, Colour `Grid Band`, filter `body_type` to Sedan/SUV/Hatchback | D3, Story 4 |

W15 must be filtered to passenger vehicles. On the full pool the USA appears to avoid the most
CO2 per vehicle, but that is only because its rows are dominated by electric trucks, whose diesel
baseline is enormous. Holding body type constant is what exposes the grid effect.

## 4. Dashboards

| Dashboard | Sheets | Suggested layout |
|---|---|---|
| Market Overview (`Market`) | W1 across the top, W3 and W2 mid, W5 and W11 lower, W12 side | 1600 x 900 fixed |
| Battery Intelligence (`Battery`) | W1 top, W6 and W7 left, W8 large centre, W9 and W10 right, W13 bottom | 1600 x 900 fixed |
| Global EV Insights (`Global`) | W1 top, W14 large left, W15 right, W4 bottom, W12 detail | 1600 x 900 fixed |
| EV Insights Story (`Story`) | point to the sheets above | 1600 x 900 |

Sheet names in brackets are the values you will paste into `tableau_urls.json`.

**Do the responsive step properly.** Set dashboard sizing to **Fixed** and add a **Phone** size
(400 x 1000, floating layout) via Dashboard → Device → Add Device. A desktop-only canvas renders
as a shrunken, unreadable frame on mobile, and "responsive dashboard design" is a graded line in
the brief. The Flask embed uses `device: automatic`, so Tableau serves the phone layout when the
viewport is narrow.

**Filters.** Add these as "Use as Filter" / selected fields on every dashboard:
`brand`, `model_year`, `body_type`, `battery_technology`, `country_of_origin`, `market_segment`.
Six global filters comfortably covers the "utilisation of data filters" deliverable. Set
Run/Apply on selection, and add a "Clear all" via a Reset action.

## 5. Story scenes and the claims to put in each caption

Four captions, each backed by a specific number from the SQL layer.

1. **A maturing market, not a stalling one.** Modelled volume rises from 58,986 units in 2018 to
   7,146,573 in 2025, but the growth rate falls from 284% to 8.6%. Meanwhile weighted price drops
   from $48,407 to $33,376 and weighted range rises from 250 to 283 miles. Use W1 + W3.
2. **Leadership changed hands and the field widened.** Tesla leads every year to 2023; BYD takes
   over in 2024 at 18.6% and 2025 at 20.1%. Top-5 concentration falls 84% to 47% while active
   brands grow from 9 to 51. Use W2 + W4 + W11.
3. **Two chemistries, two different answers.** NMC holds 51.0% of units but 56.4% of energy
   demand; LFP holds 47.7% of units but 41.6% of GWh. LFP leads in 2021 and 2025, NMC in between,
   so describe a close race rather than a crossover. Capacity does not simply buy range: pooled
   correlation is 0.37, yet within a single body type it is 0.85 to 0.95. Use W6 + W7 + W8.
4. **Where the next gains are.** SUVs took 22.9 points of yearly share while hatchbacks lost 19.0.
   Solid-state passenger cars reach 402 miles against 302 for lithium-ion, but on 0.62% of volume
   and at the highest cell footprint (21.3 t versus 12.0 t CO2e). Charging grid decides the climate
   case: an equivalent EV avoids 2.54 t a year in Sweden and 1.23 t in Vietnam, and manufacturing
   emissions take 2.7 to 6.5 years to repay. Use W14 + W15 + W13.

## 6. Before you publish

- **Freeze the workbook name now.** The published URL contains it, and renaming later breaks every
  embed on the live Flask site with no warning.
- Publish all four sheets from one workbook so the four URLs differ only by sheet name.
- On Tableau Public, leave embedding unrestricted, or allowlist your `*.vercel.app` domain.
- Paste the four URLs into `tableau_urls.json`, restart Flask, and confirm each page loads before
  deploying.
- Re-publish after your final data change. An extract is a snapshot: the deployed site shows the
  extract, not the database.

## 7. What to state honestly on screen

Add this as a footer caption on each dashboard. The dataset is modelled, not measured, and it
covers leading models rather than the whole market, so totals are about 24.1M units against a real
global figure roughly three times larger.

> Modelled dataset, 119 vehicle lines, 2018-2025. Sales, pricing and ratings are generated.
> Share metrics are **share of dataset sales**, not national market share.
