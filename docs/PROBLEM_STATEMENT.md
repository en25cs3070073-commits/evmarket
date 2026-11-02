# Problem statement and requirements

## Objective

Build one analytical platform that turns a record-level EV dataset into decisions for three
different audiences, with every number traceable to a SQL statement. The platform is not an EV
application; it is a business-intelligence system where data flows
`dataset → Postgres → SQL → Tableau → Flask`.

## The three users and the decision each one faces

| Persona | Role | Decision to support | Dashboards |
|---|---|---|---|
| Emily Johnson | EV Market Strategy Director | Which categories and manufacturers to prioritise in the product portfolio | Market Overview, Battery Intelligence |
| David Chen | Automotive BI Manager | Where competitive advantage sits, and which markets a client should enter | Market Overview, Global EV Insights |
| Dr. Sarah Williams | Sustainable Mobility Research Analyst | Which battery innovations and grids actually deliver sustainability gains | Battery Intelligence, Global EV Insights |

These are three views on one system, not three products. The three-dashboard split maps directly
onto the pairs above: Market Overview covers Emily and David, Battery Intelligence covers Emily and
Sarah, Global EV Insights covers David and Sarah.

## KPI definitions

Each KPI is stated as a formula and the SQL object that produces it, so the Tableau layer never
re-invents a metric with different arithmetic.

| # | KPI | Definition | Source |
|---|---|---|---|
| 1 | Total Annual Sales Units | `SUM(annual_sales_units)` per year | `v_yearly_growth.units` |
| 2 | Share of Dataset Sales % | units ÷ total units for the scope, x100 | `v_manufacturer_yearly.pct_of_year_units` |
| 3 | Year-over-Year Growth % | `(units - prior units) / prior units` via `LAG` | `v_yearly_growth.yoy_growth_pct` |
| 4 | Battery Demand (GWh) | `SUM(units x capacity_kwh) / 1,000,000` | `v_ev_data.gwh_battery_demand` |
| 5 | Sales-Weighted Avg Range | `SUM(range x units) / SUM(units)` | `v_yearly_growth.avg_range_miles_weighted` |
| 6 | Sales-Weighted Avg Price | `SUM(price x units) / SUM(units)` | `v_yearly_growth.avg_price_usd_weighted` |
| 7 | Customer Satisfaction | mean `customer_rating`; report the unweighted model mean and label it | `v_satisfaction_matrix.avg_rating` |
| 8 | Manufacturing Concentration (HHI) | `SUM(pct^2)` over countries, 0-10,000 scale | `analysis_queries.sql` Q10 |
| 9 | CO2e Avoided | `SUM(units x est_annual_co2e_saved_tonnes)` | `v_ev_data.co2e_avoided_tonnes` |
| 10 | Benefit per Vehicle (t/yr) | mean saving, **holding body type constant** | Q11 |
| 11 | Manufacturing Payback (yrs) | `AVG(mfg_co2e / annual_saved_co2e)` | Q12 |
| 12 | Category Share Shift (pts) | share in last year minus share in first year | Q4 |
| 13 | Value Index | `price / driving_range_miles` | `v_ev_data.usd_per_1000_miles` |

Weighted averages are used for anything presented as a market statistic. Unweighted means are used
only where the subject is a vehicle characteristic, such as the range box plot, and the tooltip
says which.

## Questions to answering

| Question | Query | Answer in this dataset |
|---|---|---|
| Which categories contribute most to sales? | Q4 | SUVs 51.1% of dataset volume |
| Are categories gaining or losing share? | Q4 | SUV +22.9 pts of yearly share 2021-2025; hatchbacks -19.0 |
| Who leads the market, and is it stable? | Q2, Q3 | Tesla every year to 2023, BYD 2024-2025 |
| Is the field concentrating or widening? | Q3, Q10 | Top-5 share 84% to 47%; brands 9 to 51; country HHI 2,842 |
| Which chemistry dominates? | Q5, Q6 | NMC 51.0% of units, LFP 47.7%; LFP leads 2021 and 2025 |
| Does the ranking change if you measure energy instead of vehicles? | Q5 | Yes: NMC 56.4% of GWh vs LFP 41.6% |
| Does battery capacity predict range? | Q7 | Pooled r = 0.37; within a body type 0.85-0.95 |
| Which chemistry refills fastest? | Q8 | NCA 2.28C, NMC 1.91C, LFP 1.70C, sodium 0.77C |
| How has range improved? | Q9 | LFP +34.9%, NMC +34.7% over 2018-2025 |
| Is manufacturing geographically concentrated? | Q10 | Highly concentrated: HHI 2,842, China 48.6% |
| Where does an EV help the climate most? | Q11 | Sweden 2.54 t/vehicle/yr vs Vietnam 1.23 on identical bodies |
| When do manufacturing emissions get repaid? | Q12 | 2.7 years (LFP, France) to 6.5 years (NMC, Czechia) |
| Which models offer best value? | Q14 | BYD Seal, LFP sedan, $82 per mile of range |
| Where is the next growth opportunity? | Q15, Q16 | Solid-state 402 vs 302 mi on 0.62% of volume; mainstream $20-40k band holds 38% of units |

## Success criteria

1. A reviewer can pick any headline number on a dashboard and find the SQL that computes it.
2. Filters interwork across sheets on each dashboard (manufacturer, year, category, chemistry,
   country, segment).
3. The story states four conclusions, each supported by a figure rather than an opinion.
4. The site is reachable at one public URL and usable on a phone.
5. The dataset's synthetic nature and its coverage bias are disclosed, not hidden.

## Out of scope

Charging-network telemetry, battery degradation curves, forecast models, and per-country sales
census data. The brief asks for descriptive and comparative BI over a vehicle-level dataset, and
adding a forecasting layer would import assumptions the data cannot support.
