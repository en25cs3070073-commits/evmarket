# Recreate the EV Analytics database and reload it from the generated CSV.
# PowerShell equivalent of scripts/load_db.sh, for running straight from a PS prompt.
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

docker info | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker engine is not running." -ForegroundColor Red
    Write-Host "Start Docker Desktop and wait until the status is steady, then re-run this."
    exit 1
}

docker compose up -d
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    docker exec ev-postgres pg_isready -U ev -d ev_analytics | Out-Null
    if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    Start-Sleep -Seconds 2
}
if (-not $ready) {
    Write-Host "Postgres did not become ready within 120 seconds." -ForegroundColor Red
    exit 1
}

docker cp "db\schema.sql" "ev-postgres:/tmp/schema.sql"
docker cp "db\load.sql" "ev-postgres:/tmp/load.sql"
docker cp "data\ev_market_dataset.csv" "ev-postgres:/tmp/ev_market_dataset.csv"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "applying schema..."
docker exec ev-postgres psql -U ev -d ev_analytics -v ON_ERROR_STOP=1 -q -f /tmp/schema.sql
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "loading data..."
docker exec ev-postgres psql -U ev -d ev_analytics -v ON_ERROR_STOP=1 -f /tmp/load.sql
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "database ready: localhost:5432 / ev_analytics / user ev" -ForegroundColor Green
