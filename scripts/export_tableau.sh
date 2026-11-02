#!/usr/bin/env bash
# Export the SQL views to CSV for Tableau authoring.
# This is the fallback path if Tableau Public Desktop refuses a live database
# connection, and it is also the artefact that documents "SQL -> Tableau".
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/data/tableau"
CONTAINER=ev-postgres
mkdir -p "$OUT"

declare -A VIEWS=(
  [ev_data]="SELECT * FROM v_ev_data"
  [yearly_growth]="SELECT * FROM v_yearly_growth"
  [manufacturer_yearly]="SELECT * FROM v_manufacturer_yearly"
  [category_summary]="SELECT * FROM v_category_summary"
  [battery_tech_summary]="SELECT * FROM v_battery_tech_summary"
  [tech_evolution]="SELECT * FROM v_tech_evolution"
  [country_manufacturing]="SELECT * FROM v_country_manufacturing"
  [satisfaction_matrix]="SELECT * FROM v_satisfaction_matrix"
  [top_rated_models]="SELECT * FROM v_top_rated_models"
  [model_detail]="SELECT * FROM v_model_detail"
)

for name in "${!VIEWS[@]}"; do
  MSYS_NO_PATHCONV=1 docker exec -i "$CONTAINER" psql -U ev -d ev_analytics \
    --no-psqlrc -v ON_ERROR_STOP=1 -q \
    -c "COPY (${VIEWS[$name]}) TO STDOUT WITH (FORMAT csv, HEADER true)" \
    > "$OUT/$name.csv"
  printf '%-26s %6s rows\n' "$name" "$(( $(wc -l < "$OUT/$name.csv") - 1 ))"
done

echo "exported to data/tableau/"
