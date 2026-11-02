# Demonstration video script

Target length 11-12 minutes. Every number spoken here is reproducible from
`db/analysis_results.txt`. Two tabs open before you record: a terminal at the project root, and
your browser.

## Before you press record

- Docker Desktop running, `docker ps` shows `ev-postgres` healthy
- `python scripts/validate.py` prints `42/42 checks passed` — do this live if it is quick
- Tableau workbook published and all four URLs filled into `tableau_urls.json`
- Site deployed and reachable, plus the URL open in a tab
- Zoom to 150% in the terminal; close notifications
- If the Tableau embed is flaky, keep the workbook open in Tableau Public as a fallback to show

## 0:00 - 0:35 — Title

Show the deployed site home page.

> This is the EV Analytics Hub — an end-to-end business intelligence platform for the electric
> vehicle market. Data flows from a modelled dataset into PostgreSQL, through sixteen documented
> SQL queries, into three interactive Tableau dashboards and a four-scene story, and out again as
> a Flask website deployed on Vercel. Every number on screen traces back to a SQL statement.

## 0:35 - 1:35 — The problem and the three users

Home page, scroll to the persona cards.

> Three users, one system. Emily Johnson runs market strategy and needs to know which categories
> and manufacturers deserve portfolio priority. David Chen advises automotive clients and needs
> competitive and manufacturing geography. Dr. Sarah Williams researches sustainable mobility and
> needs battery innovation and emissions evidence. They are not three apps — each is served by
> exactly two of the three dashboards.

## 1:35 - 2:35 — Architecture

Home page, "How the system works" list.

> Five layers. A generated dataset, a Postgres star schema in Docker, an SQL analysis layer of ten
> views and sixteen queries, Tableau as the analytical engine working from a database extract, and
> Flask as the delivery shell. Note the deliberate design decision: Flask never touches the
> database. Tableau holds an extract, so the deployed site has no connection string, no driver and
> no secret — which is exactly why this runs on a free host.

## 2:35 - 3:50 — Data, and being honest about it

Open `data/METADATA.md` in the editor.

> The dataset is 1,263 rows across 119 vehicle lines, 2018 to 2025. Vehicle identities, segments,
> countries and battery chemistries are real. Sales, prices, ranges and ratings are modelled, and
> the documentation says so plainly. I chose to generate rather than download a Kaggle set for a
> specific reason: the closest-matching public dataset is also synthetic, has no battery-chemistry
> column at all, and computes range as capacity times a fixed constant — so its capacity-versus-
> range chart is a straight line by construction. Here, efficiency varies by body type, so pooled
> correlation between capacity and range is only 0.37, while inside a single category it is 0.85 to
> 0.95. That is a real analytical finding, not an artefact of the generator.

## 3:50 - 5:10 — Database and ETL, live

Terminal.

```bash
bash scripts/load_db.sh
```

> Three tables. `country`, `vehicle_model`, and the fact table `ev_variant_sales`. The grain is
> model, year, variant and chemistry — chemistry is on the fact because the same model can ship
> different cells; the NIO ET7 appears with both an NMC pack and a 150 kilowatt-hour
> semi-solid-state pack. Loading is a staged ETL, not a bulk insert: everything lands as text in a
> staging table, a cleaning view applies casts and range guards and rejects untypable rows, then
> three inserts build the star. This run loaded 1,263 rows with zero rejections in well under a
> second.

## 5:10 - 6:40 — SQL analysis

Terminal, run two or three and let the output scroll.

```bash
docker cp db/analysis_queries.sql ev-postgres:/tmp/aq.sql
docker exec -it ev-postgres psql -U ev -d ev_analytics -f /tmp/aq.sql
```

> Sixteen queries. Highlights. The leader-share query uses `ROW_NUMBER` and a windowed `SUM` to
> show Tesla leading every year to 2023 while the top five fall from 84 percent to 47 percent of
> volume, and active brands rise from nine to fifty-one — the market is widening, not consolidating.
> The concentration query computes a Herfindahl-Hirschman index of 2,842 across manufacturing
> countries, which is highly concentrated. And the grid query shows an equivalent passenger EV
> avoiding 2.54 tonnes of CO2 a year in Sweden against 1.23 in Vietnam.
>
> Three of these were wrong in an earlier version and I fixed them. Category growth originally read
> "SUVs up 48,000 percent", which was measuring my catalogue gaining models, not the market — so it
> now reports share-of-year movement instead. The CO2-per-vehicle ranking said the USA benefits most
> despite a coal-heavy grid, which was really just electric trucks with huge diesel baselines, so it
> now holds body type constant.

## 6:40 - 9:10 — Dashboards and interactivity

Browser, walk the three dashboard pages. Use the filters on camera.

> Market Overview: total volume, category contribution as a treemap, manufacturer ranking, the
> satisfaction heatmap, top-rated models. Filter to SUV and watch every sheet respond together.
>
> Battery Intelligence: the chemistry donut and the GWh bar are the pair I most want to draw
> attention to, because they disagree. NMC holds 51.0 percent of vehicles but 56.4 percent of
> energy demand; LFP is the reverse. Counting cars and counting kilowatt-hours give different
> answers, and only one of them tells you what the cell industry has to build.
>
> The scatter is capacity against range coloured by body type. Three distinct bands, not one line —
> that is the efficiency difference between a hatchback, a sedan and an SUV.
>
> Global EV Insights: the manufacturing map, the grid-versus-benefit bar, and the value ranking.

## 9:10 - 10:10 — Story

Story page, step through four scenes.

> Four scenes. One: a maturing market, growth falling from 284 percent to 8.6 percent while price
> falls 31 percent and range rises 13 percent. Two: leadership changed hands from Tesla to BYD and
> the field widened. Three: two chemistries in a close race and capacity does not simply buy range.
> Four: the next gains — SUVs took 22.9 points of yearly share, solid-state reaches 402 miles
> against 302 on 0.62 percent of volume at the highest cell footprint, and where you charge decides
> the climate case.

## 10:10 - 11:00 — Web integration and responsiveness

Same URL on a phone, or device-emulation in DevTools.

> The same four views embedded in Flask with an iframe, a loading skeleton, a twenty-second timeout
> and a direct Tableau Public fallback link, because I found that the public JavaScript API exposes
> no event object — a listener I originally wrote would never have fired and the dashboard would
> have sat under "loading" forever. Mobile works because the workbook has a Phone device layout;
> Flask CSS alone cannot rescue a desktop canvas.

## 11:00 - 11:40 — Testing and close

Terminal.

```bash
python scripts/validate.py
```

> Forty-two automated checks across data integrity, warehouse joins and route behaviour, all
> passing, plus a performance harness that regenerates the report from live measurements. The
> whole documented query set executes in about 30 milliseconds server-side, so the only real
> latency is fetching the Tableau view itself.
>
> What I would do next: replace the modelled sales with a real census so the share figures become
> market share rather than share of dataset, and extend the window to 2030 for the emerging
> chemistries, which currently have only eight and four rows.

## If something breaks

| Problem | Say this instead |
|---|---|
| Embed does not load | Switch to the Tableau Public tab and keep narrating; the fallback link exists precisely for this |
| Database will not start | Docker Desktop was not running — show the committed `db/analysis_results.txt` |
| A number is questioned | Open `data/METADATA.md` and point at the derivation table; it is documented as modelled |
