"""Serialise the analytic views into static JSON that the Flask site renders directly.

The deployed app never opens a database connection, so the aggregates are built
here and shipped as files. Same SQL, same numbers, just pre-computed.
"""

import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "static", "data")
CONTAINER = "ev-postgres"

COLUMNS = [
    "brand", "model_name", "body_type", "market_segment", "country_of_origin",
    "battery_technology", "model_year", "battery_capacity_kwh",
    "driving_range_miles", "charging_time_min_10_80", "price_usd",
    "annual_sales_units", "customer_rating", "grid_intensity_kgco2_per_kwh",
    "gwh_battery_demand", "est_annual_co2e_saved_tonnes",
]

QUERY = (
    "SELECT json_agg(row_to_json(t)) FROM ("
    "  SELECT " + ", ".join(COLUMNS) +
    "  FROM v_ev_data ORDER BY brand, model_name, model_year, variant_name"
    ") t"
)


ROUND = {
    "battery_capacity_kwh": 1, "driving_range_miles": 0,
    "charging_time_min_10_80": 1, "price_usd": 0, "annual_sales_units": 0,
    "customer_rating": 2, "grid_intensity_kgco2_per_kwh": 3,
    "gwh_battery_demand": 3, "est_annual_co2e_saved_tonnes": 2,
}
NUMERIC = set(ROUND)


def main():
    os.makedirs(OUT, exist_ok=True)
    res = subprocess.run(
        ["docker", "exec", "-i", CONTAINER, "psql", "-U", "ev", "-d", "ev_analytics",
         "--no-psqlrc", "-A", "-t", "-q", "-c", QUERY],
        capture_output=True, text=True)
    if res.returncode != 0:
        raise SystemExit("psql failed: " + res.stderr.strip())

    rows = json.loads(res.stdout)
    if len(rows) < 100:
        raise SystemExit(f"unexpectedly small result: {len(rows)} rows")

    # Columnar form: repeating 22 key names per row costs more than the values.
    out_rows = []
    for r in rows:
        line = []
        for col in COLUMNS:
            v = r[col]
            if col in NUMERIC:
                digits = ROUND[col]
                v = round(float(v), digits)
                if digits == 0:
                    v = int(v)
            line.append(v)
        out_rows.append(line)

    path = os.path.join(OUT, "facts.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"cols": COLUMNS, "rows": out_rows}, fh,
                  separators=(",", ":"), ensure_ascii=False)

    print(f"{len(out_rows)} rows x {len(COLUMNS)} cols -> "
          f"{os.path.relpath(path, ROOT)} ({os.path.getsize(path) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
