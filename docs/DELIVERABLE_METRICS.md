# Deliverable metrics and build status

Answers the countable lines in the project checklist directly. "Specified" means the definition
exists and is unambiguous but the artefact is built by hand in Tableau.

## Counts

| Checklist item | Value | Evidence | Status |
|---|---|---|---|
| Problem understanding | 3 personas, 13 KPIs, 14 questions with answers | `docs/PROBLEM_STATEMENT.md` | Done |
| Dataset | 1,263 rows x 26 columns, 119 model lines, 52 brands, 11 countries, 5 chemistries, 2018-2025 | `data/ev_market_dataset.csv`, `data/METADATA.md` | Done |
| Stored in DB | PostgreSQL 16 in Docker, 3 tables, 448 kB fact + indexes | `docker-compose.yml`, `db/schema.sql` | Done |
| SQL operations | 16 labelled analysis queries + staged ETL, `SUM`/`AVG`/`COUNT`/`COUNTD`/`GROUP BY`/`HAVING`, `ROW_NUMBER`/`RANK`/`LAG`/`SUM() OVER`, CTEs, joins, CASE bucketing, HHI index | `db/analysis_queries.sql`, `db/load.sql` | Done |
| DB connected to Tableau | Two supported paths: live Postgres extract (`public.v_ev_data`) or `data/tableau/ev_data.csv` | `docs/TABLEAU_BUILD_SPEC.md` §1 | Specified, needs install |
| Data preparation | Text staging -> typed cleansing view -> star schema; 5 measures derived in SQL | `db/load.sql`, `v_ev_data` | Done |
| Unique visualisations | 15 worksheets W1-W15 (brief recommends 10-12) | `docs/TABLEAU_BUILD_SPEC.md` §3 | Specified |
| Calculation fields | 15, including two `FIXED` LOD expressions in one field | `docs/TABLEAU_BUILD_SPEC.md` §2 | Specified |
| Dashboards | 3, at 1600x900 fixed with a Phone device layout each | `docs/TABLEAU_BUILD_SPEC.md` §4 | Specified |
| Responsive design | Device layouts in Tableau; fluid CSS, breakpoint at 640px, horizontally scrollable nav in Flask | `static/css/main.css` | Flask done |
| Story scenes | 4, each with a pre-written caption and its figures | `docs/TABLEAU_BUILD_SPEC.md` §5 | Specified |
| Data filters | 6 per dashboard: brand, model_year, body_type, battery_technology, country_of_origin, market_segment | `docs/TABLEAU_BUILD_SPEC.md` §4 | Specified |
| Web pages | 5 routes: `/`, `/market`, `/battery`, `/global`, `/story` | `app.py` | Done |
| Embedded Tableau | 4 embeds (3 dashboards + story) with loading skeleton, 20 s timeout and fallback link | `templates/page.html`, `static/js/embed.js` | Done |
| Error / loading states | Placeholder when unpublished, skeleton while loading, fallback when slow, styled 404 | verified by `scripts/validate.py` | Done |
| Performance testing | Server-side query latency, ETL timing and page latency, all regenerated from live measurement | `docs/PERFORMANCE_TESTING.md` | Done |
| Data rendered to DB | 1,263 fact rows, 24,054,926 modelled vehicle-years of sales, zero ETL rejections | load report in `db/load.sql` | Done |
| Validation | 42 automated checks, all passing | `scripts/validate.py` | Done |
| Documentation | 6 documents covering problem, procedure, data, metrics, performance, build spec | `docs/`, `data/METADATA.md`, `README.md` | Done |
| Demo video | Shot-by-shot script with timings written; recording needs the published workbook | `docs/DEMO_VIDEO_SCRIPT.md` | Script done |
| Deployment | `vercel.json`, `requirements.txt`, `.vercelignore` prepared | repo root | Config done, needs account |

## Epic status

| Epic | State | What is left |
|---|---|---|
| 1 Problem understanding | Complete | — |
| 2 Data collection and database | Complete | — |
| 3 SQL analysis | Complete | — |
| 4 Data preparation | Complete | — |
| 5 Tableau visualisations | Specified | Build W1-W15 in Tableau Public Desktop |
| 6 Dashboard and story | Specified | Assemble 3 dashboards, phone layouts, story, publish |
| 7 Flask integration and testing | Complete except live embed | Paste the 4 published URLs, re-run `validate.py` |
| 8 Demonstration and documentation | Docs complete | Record the video, deploy to Vercel |

Two epics cannot be finished by automation: **Epic 5-6 are manual GUI work inside Tableau**, and
**deployment needs accounts you must create**. Everything feeding them is built, tested and
measured, so the remaining work is execution against a written spec rather than design.

## Figures to quote in the presentation

| Claim | Number |
|---|---|
| Dataset volume loaded | 1,263 rows, 24.1M modelled units, 2018-2025 |
| Growth deceleration | 284% YoY in 2019 to 8.6% in 2025 |
| Battery demand | 4.1 GWh in 2018 to 490 GWh in 2025 |
| Price and range move | $48,407 to $33,376 while range rises 250 to 283 miles |
| Leadership change | Tesla leads 2018-2023; BYD 18.6% in 2024, 20.1% in 2025 |
| Competitive widening | Top-5 share 84% to 47%; brands 9 to 51 |
| Chemistry split | NMC 51.0% of units but 56.4% of GWh; LFP 47.7% and 41.6% |
| Capacity is not range | Pooled r = 0.37, but 0.85-0.95 within one body type |
| Manufacturing concentration | HHI 2,842; China 48.6% of dataset volume |
| Grid decides the climate case | 2.54 t/vehicle/yr in Sweden vs 1.23 in Vietnam |
| Emissions payback | 2.7 years (LFP, France) to 6.5 years (NMC, Czechia) |
| Emerging technology | Solid-state passenger range 402 mi vs 302 mi, on 0.62% of volume |
