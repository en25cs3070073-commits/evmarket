# EV Analytics Hub

Electric Vehicle Market Analysis & Business Intelligence platform. A modelled EV dataset is
loaded into Postgres, analysed with documented SQL, visualised in Tableau, and delivered as a
Flask website embedding the published Tableau dashboards and story.

**Stack:** Python 3 · Docker + PostgreSQL 16 · SQL (star schema, 10 analytic views, 16 analysis
queries) · Tableau Public · Flask · Vercel.

## Layout

```
app.py                Flask routes: home, 3 dashboards, story
tableau_urls.json     The only file you edit after publishing to Tableau
templates/            base, home, page, 404
static/               main.css, embed.js (loading + error states)
db/                   schema.sql, load.sql, analysis_queries.sql, analysis_results.txt
data/                 ev_market_dataset.csv, METADATA.md, tableau/ (10 view exports)
scripts/              generate_dataset, load_db, export_tableau, validate, perf_test
docs/                 build spec, problem statement, docs, metrics, demo script, perf report
docker-compose.yml    Postgres 16 on localhost:5432
```

## Prerequisites

- Docker Desktop **running** (check the whale icon; the CLI works even when the engine is off)
- Python 3.11+ with `pip`
- Tableau Public Desktop (free) and a Tableau Public account
- A GitHub account and a Vercel account (free, no card) for deployment

## Quickstart

```bash
pip install -r requirements.txt
bash scripts/load_db.sh          # starts Postgres, builds schema, runs the ETL
bash scripts/export_tableau.sh   # writes data/tableau/*.csv for Tableau
python scripts/validate.py       # 42 checks over data, warehouse and site
python app.py                    # http://127.0.0.1:5000
```

The site runs before anything is published. Pages without a Tableau URL show their analytical
brief instead of a broken frame, so you can develop and demo the shell at any stage.

## Tableau step

Open [docs/TABLEAU_BUILD_SPEC.md](docs/TABLEAU_BUILD_SPEC.md). It lists the 15 calculated fields,
the 15 worksheets, dashboard layouts, filter actions, device-layout requirement and the four story
captions with their numbers already worked out.

Connect Tableau to `localhost:5432 / ev_analytics / ev / ev_local_only` and use `public.v_ev_data`,
**as an Extract** — Tableau Public does not support live external database connections. If the
connector is unavailable, open `data/tableau/ev_data.csv` instead; it is the same 1,263 rows and
31 columns.

After publishing, paste the four view URLs into `tableau_urls.json`:

```json
{ "key": "market", "url": "https://public.tableau.com/views/EVAnalyticsHub/Market", ... }
```

Restart Flask and confirm each page renders before deploying.

## Deploy to Vercel

`vercel.json` routes all traffic to `app.py` through `@vercel/python`; `.vercelignore` keeps the
dataset, SQL and scripts out of the deployed bundle.

```bash
git init && git add . && git commit -m "EV Analytics Hub"
git branch -M main
git remote add origin https://github.com/<you>/ev-analytics-hub.git
git push -u origin main
npx vercel          # import the repo, accept defaults, then:
npx vercel --prod
```

You get one `*.vercel.app` URL to submit. `requirements.txt` deliberately contains only Flask —
the deployed app never touches the database, so shipping pandas would just slow cold starts.

## Testing

```bash
python scripts/validate.py     # data integrity, warehouse joins, route behaviour
python scripts/perf_test.py    # rewrites docs/PERFORMANCE_TESTING.md with measured numbers
```

## Things to know before a demo

- **An extract is a snapshot.** Changing the database does not change the live site until you
  refresh the Tableau data source and re-publish.
- **Never rename the Tableau workbook after embedding.** The published URL contains the workbook
  name, and renaming silently breaks every iframe.
- **Docker Desktop has to be running.** `scripts/load_db.sh` fails with a pipe error if the engine
  is asleep.
- **Mobile responsiveness is a Tableau job.** Add a Phone device layout in Tableau; the Flask CSS
  cannot fix a desktop-only canvas.
- Every share figure is **share of dataset sales**, not national market share. Say so on screen.
