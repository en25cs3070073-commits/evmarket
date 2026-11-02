"""Validate the dataset, the warehouse and the web layer.

Exit code is non-zero if any check fails, so this can gate a release.
"""

import csv
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILURES = []
CHECKS = 0


def check(name, ok, detail=""):
    global CHECKS
    CHECKS += 1
    if ok:
        print(f"  pass  {name}")
    else:
        print(f"  FAIL  {name}  {detail}")
        FAILURES.append(name)


def psql(sql):
    res = subprocess.run(
        ["docker", "exec", "-i", "ev-postgres", "psql", "-U", "ev",
         "-d", "ev_analytics", "--no-psqlrc", "-A", "-F", "|", "-t", "-c", sql],
        capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip())
    return res.stdout.strip()


def load_csv():
    with open(os.path.join(ROOT, "data", "ev_market_dataset.csv"), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def csv_checks(rows):
    print("\n[dataset]")
    check("row count is substantial", len(rows) >= 1000, f"{len(rows)}")
    check("no blank required fields",
          all(r[c].strip() for r in rows
              for c in ("brand", "model", "year", "country_of_origin", "battery_technology")))

    numeric = [c for c in rows[0] if c not in
               ("brand", "model", "variant", "powertrain_type", "battery_technology",
                "body_type", "market_segment", "country_of_origin")]
    bad = [(r["model"], c, r[c]) for r in rows for c in numeric if not re.match(r"^-?\d+(\.\d+)?$", r[c])]
    check("every numeric column parses", not bad, str(bad[:3]))

    km = [float(r["driving_range_km"]) for r in rows]
    mi = [float(r["driving_range_miles"]) for r in rows]
    check("km matches miles", all(abs(a - b * 1.60934) < 1.5 for a, b in zip(km, mi)))

    ratings = [float(r["customer_rating"]) for r in rows]
    check("ratings vary enough for a heatmap", max(ratings) - min(ratings) > 1.0,
          f"range {min(ratings)}-{max(ratings)}")
    check("ratings in 3.0-4.9", all(3.0 <= x <= 4.9 for x in ratings))

    cap = [float(r["battery_capacity_kwh"]) for r in rows]
    check("capacity within physical bounds", all(1 <= x <= 600 for x in cap), f"{min(cap)}-{max(cap)}")

    sales = [float(r["annual_sales_units"]) for r in rows]
    check("all sales positive", all(x > 0 for x in sales))

    chems = {r["battery_technology"] for r in rows}
    check("five chemistries incl. emerging", len(chems) >= 5 and "Sodium-Ion" in chems, str(chems))

    countries = {r["country_of_origin"] for r in rows}
    check("at least 8 manufacturing countries", len(countries) >= 8, str(len(countries)))

    # Range must not be a global constant times capacity, or the scatter is meaningless.
    cars = [r for r in rows if r["body_type"] in ("Sedan", "SUV", "Hatchback")]
    ratio = {round(float(r["driving_range_miles"]) / float(r["battery_capacity_kwh"]), 2)
             for r in cars}
    check("capacity-to-range ratio is not constant", len(ratio) > 40, f"{len(ratio)} distinct")

    combos = {(r["brand"], r["model"], r["variant"], r["year"], r["battery_technology"])
              for r in rows}
    check("grain is unique", len(combos) == len(rows), f"{len(combos)} vs {len(rows)}")


def db_checks(rows):
    print("\n[warehouse]")
    fact = int(psql("SELECT COUNT(*) FROM ev_variant_sales"))
    check("fact rows match CSV", fact == len(rows), f"{fact} vs {len(rows)}")
    check("no orphan facts",
          psql("SELECT COUNT(*) FROM ev_variant_sales f LEFT JOIN vehicle_model m USING(model_id) WHERE m.model_id IS NULL") == "0")
    check("all countries resolve",
          psql("SELECT COUNT(*) FROM vehicle_model m LEFT JOIN country c "
               "ON c.country_name = m.country_of_origin WHERE c.country_name IS NULL") == "0")

    views = ["v_ev_data", "v_yearly_growth", "v_manufacturer_yearly", "v_category_summary",
            "v_battery_tech_summary", "v_tech_evolution", "v_country_manufacturing",
            "v_satisfaction_matrix", "v_top_rated_models", "v_model_detail"]
    for v in views:
        n = int(psql(f"SELECT COUNT(*) FROM {v}"))
        check(f"{v} returns rows", n > 0, str(n))

    # Category view: share percentages must total 100.
    total = float(psql("SELECT SUM(pct_of_dataset_units) FROM v_category_summary"))
    check("category shares total 100", abs(total - 100.0) < 0.1, f"{total}")

    total_units = float(psql("SELECT SUM(annual_sales_units) FROM ev_variant_sales"))
    csv_units = sum(float(r["annual_sales_units"]) for r in rows)
    check("no volume lost in ETL", abs(total_units - csv_units) < 1, f"{total_units} vs {csv_units}")

    gwh = float(psql("SELECT SUM(gwh_battery_demand) FROM v_ev_data"))
    expect = sum(float(r["annual_sales_units"]) * float(r["battery_capacity_kwh"]) for r in rows) / 1e6
    check("GWh units are correct", abs(gwh - expect) < 2, f"{gwh} vs {expect}")


def app_checks():
    print("\n[web]")
    cfg = json.load(open(os.path.join(ROOT, "tableau_urls.json"), encoding="utf-8"))
    keys = [p["key"] for p in cfg["pages"]]
    check("four pages configured", len(keys) == 4, str(keys))
    check("every page has a title and summary",
          all(p.get("title") and p.get("summary") for p in cfg["pages"]))

    base = "http://127.0.0.1:5099"
    import threading
    import time
    sys.path.insert(0, ROOT)
    from app import app

    srv = threading.Thread(target=lambda: app.run(host="127.0.0.1", port=5099,
                                                  threaded=True, use_reloader=False),
                           daemon=True)
    srv.start()
    for _ in range(60):
        try:
            urllib.request.urlopen(base, timeout=1)
            break
        except Exception:
            time.sleep(0.4)

    def get(path):
        try:
            r = urllib.request.urlopen(base + path, timeout=10)
            return r.status, r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8")

    status, home = get("/")
    check("home renders", status == 200 and "EV Analytics Hub" in home)
    check("home lists all personas",
          all(n in home for n in ("Emily Johnson", "David Chen", "Sarah Williams")))

    for key in keys:
        s, body = get("/" + key)
        check(f"/{key} renders", s == 200)

    s404, body404 = get("/does-not-exist")
    check("unknown route is 404", s404 == 404)
    check("404 page is friendly", "no such page" in body404)

    for path, needle in (("/static/css/main.css", ":root"), ("/static/js/embed.js", "viz-iframe")):
        s, _ = get(path)
        check(f"{path} served", s == 200)

    # An unconfigured page must show guidance, never a broken frame.
    _, unconfigured = get("/" + next(k for k in keys
                                    if not next(p for p in cfg["pages"] if p["key"] == k)["url"]))
    check("unconfigured page shows placeholder", "Not published yet" in unconfigured)
    check("unconfigured page has no iframe", "<iframe" not in unconfigured)


def main():
    rows = load_csv()
    csv_checks(rows)
    db_checks(rows)
    app_checks()
    print(f"\n{CHECKS - len(FAILURES)}/{CHECKS} checks passed")
    if FAILURES:
        print("failed: " + ", ".join(FAILURES))
        sys.exit(1)


if __name__ == "__main__":
    main()
