# Export the SQL views to CSV for Tableau authoring.
# Writes each file inside the container and copies it out, because PowerShell's
# > redirection re-encodes stdout as UTF-16 and would corrupt the CSV bytes.
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$out = Join-Path $Root "data\tableau"
New-Item -ItemType Directory -Force -Path $out | Out-Null

$views = [ordered]@{
    ev_data                 = "SELECT * FROM v_ev_data"
    yearly_growth           = "SELECT * FROM v_yearly_growth"
    manufacturer_yearly     = "SELECT * FROM v_manufacturer_yearly"
    category_summary        = "SELECT * FROM v_category_summary"
    battery_tech_summary    = "SELECT * FROM v_battery_tech_summary"
    tech_evolution          = "SELECT * FROM v_tech_evolution"
    country_manufacturing   = "SELECT * FROM v_country_manufacturing"
    satisfaction_matrix     = "SELECT * FROM v_satisfaction_matrix"
    top_rated_models        = "SELECT * FROM v_top_rated_models"
    model_detail            = "SELECT * FROM v_model_detail"
}

foreach ($name in $views.Keys) {
    $tmp = "/tmp/$name.csv"
    $copy = "COPY ($($views[$name])) TO '$tmp' WITH (FORMAT csv, HEADER true)"
    docker exec ev-postgres psql -U ev -d ev_analytics --no-psqlrc -q -v ON_ERROR_STOP=1 -c $copy
    if ($LASTEXITCODE -ne 0) {
        Write-Host "export failed for view: $name" -ForegroundColor Red
        exit 1
    }
    $target = Join-Path $out "$name.csv"
    docker cp "ev-postgres:$tmp" $target
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $rows = (Get-Content $target | Measure-Object -Line).Lines - 1
    Write-Host ("{0,-26} {1,6} rows" -f $name, $rows)
}

Write-Host "exported to data\tableau\" -ForegroundColor Green
