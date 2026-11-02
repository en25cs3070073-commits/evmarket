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

**Windows — run these from a PowerShell prompt.**

```powershell
pip install -r requirements.txt
.\scripts\load_db.ps1             # starts Postgres, builds schema, runs the ETL
python scripts\build_site_data.py # serialises v_ev_data to static/data/facts.json
.\scripts\export_tableau.ps1      # writes data\tableau\*.csv for Tableau
python scripts\validate.py        # 49 checks over data, warehouse and site
python app.py                     # http://localhost:5000
```

**macOS / Linux:**

```bash
pip install -r requirements.txt
bash scripts/load_db.sh
python scripts/build_site_data.py
bash scripts/export_tableau.sh
python scripts/validate.py
python app.py
```

## Two layers of visualisation

Each dashboard page renders **built-in interactive charts** computed in the browser from
`static/data/facts.json`, which is serialised straight from the `v_ev_data` SQL view. Six filters
(brand, year, category, chemistry, country, segment) re-aggregate every chart on the page. This
layer works with no Tableau and no database connection, so the site is presentable at any time.

When you publish the workbook and paste its URL into `tableau_urls.json`, a second section titled
**Tableau version** appears beneath the charts. That Tableau layer is what satisfies the brief's
"Connect DB with Tableau" requirement; the built-in charts are the delivery shell's own view of
the same numbers. Re-run `build_site_data.py` whenever the database changes so the two never drift.

Do not run the `.sh` scripts from PowerShell via `bash` on Windows. Git Bash resolves `docker` to
a Linux client that looks for `unix:///var/run/docker.sock`, which Docker Desktop does not expose,
and its path translation mangles the compose arguments. The `.ps1` scripts do the same work with
Windows-native paths and are byte-checked: they write CSVs inside the container and copy them out,
because PowerShell's `>` redirection would re-encode stdout as UTF-16.

The site is fully functional before anything is published: every page renders interactive charts
from the SQL-derived JSON, and the Tableau embed section appears only once a URL is configured.

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
