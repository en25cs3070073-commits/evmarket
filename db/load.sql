-- EV Analytics Hub — ETL: raw CSV -> staging -> star schema.
-- Run with:  psql -v ON_ERROR_STOP=1 -f db/load.sql
-- The \copy path assumes the CSV was docker-cp'd to /tmp inside the container.

\set ON_ERROR_STOP on

BEGIN;

DROP TABLE IF EXISTS stg_ev_raw CASCADE;
CREATE TABLE stg_ev_raw (
    brand                              TEXT,
    model                              TEXT,
    variant                            TEXT,
    year                               TEXT,
    powertrain_type                    TEXT,
    battery_technology                 TEXT,
    body_type                          TEXT,
    market_segment                     TEXT,
    country_of_origin                  TEXT,
    battery_capacity_kwh               TEXT,
    driving_range_miles                TEXT,
    driving_range_km                   TEXT,
    energy_consumption_wh_per_mi       TEXT,
    peak_charging_kw                   TEXT,
    charging_time_min_10_80            TEXT,
    acceleration_0_60_mph              TEXT,
    top_speed_mph                      TEXT,
    horsepower                         TEXT,
    seating_capacity                   TEXT,
    price_usd                          TEXT,
    annual_sales_units                 TEXT,
    customer_rating                    TEXT,
    safety_rating                      TEXT,
    grid_intensity_kgco2_per_kwh       TEXT,
    estimated_manufacturing_co2e_tonnes TEXT,
    estimated_annual_co2e_saved_tonnes TEXT
);

\copy stg_ev_raw FROM '/tmp/ev_market_dataset.csv' WITH (FORMAT csv, HEADER true)

-- Normalise text keys and discard rows that cannot be typed.
CREATE OR REPLACE FUNCTION is_numeric(v TEXT) RETURNS BOOLEAN LANGUAGE sql AS $$
    SELECT v ~ '^-?([0-9]+(\.[0-9]*)?|\.[0-9]+)$'
$$;

CREATE OR REPLACE VIEW v_stg_clean AS
SELECT
    btrim(brand)                                    AS brand,
    btrim(model)                                    AS model_name,
    btrim(variant)                                  AS variant_name,
    year::SMALLINT                                  AS model_year,
    btrim(powertrain_type)                          AS powertrain_type,
    btrim(battery_technology)                       AS battery_technology,
    btrim(body_type)                                AS body_type,
    btrim(market_segment)                           AS market_segment,
    btrim(country_of_origin)                        AS country_of_origin,
    battery_capacity_kwh::NUMERIC                   AS battery_capacity_kwh,
    driving_range_miles::NUMERIC                    AS driving_range_miles,
    driving_range_km::NUMERIC                       AS driving_range_km,
    energy_consumption_wh_per_mi::NUMERIC           AS energy_consumption_wh_per_mi,
    peak_charging_kw::NUMERIC                       AS peak_charging_kw,
    charging_time_min_10_80::NUMERIC                AS charging_time_min_10_80,
    acceleration_0_60_mph::NUMERIC                  AS acceleration_0_60_mph,
    top_speed_mph::NUMERIC                          AS top_speed_mph,
    horsepower::NUMERIC                             AS horsepower,
    seating_capacity::SMALLINT                      AS seating_capacity,
    price_usd::NUMERIC                              AS price_usd,
    annual_sales_units::NUMERIC                     AS annual_sales_units,
    customer_rating::NUMERIC                        AS customer_rating,
    safety_rating::NUMERIC                          AS safety_rating,
    grid_intensity_kgco2_per_kwh::NUMERIC           AS grid_intensity_kgco2_per_kwh,
    estimated_manufacturing_co2e_tonnes::NUMERIC    AS est_manufacturing_co2e_tonnes,
    estimated_annual_co2e_saved_tonnes::NUMERIC     AS est_annual_co2e_saved_tonnes
FROM stg_ev_raw
WHERE brand IS NOT NULL AND btrim(brand) <> ''
  AND btrim(country_of_origin) <> ''
  AND btrim(battery_technology) <> ''
  AND is_numeric(year)                  AND year::SMALLINT BETWEEN 1990 AND 2100
  AND is_numeric(battery_capacity_kwh)  AND battery_capacity_kwh::NUMERIC > 0
  AND is_numeric(driving_range_miles)   AND driving_range_miles::NUMERIC > 0
  AND is_numeric(price_usd)             AND price_usd::NUMERIC > 0
  AND is_numeric(annual_sales_units)    AND annual_sales_units::NUMERIC >= 0
  AND is_numeric(customer_rating)       AND customer_rating::NUMERIC BETWEEN 1 AND 5;

TRUNCATE ev_variant_sales RESTART IDENTITY CASCADE;
TRUNCATE vehicle_model RESTART IDENTITY CASCADE;
TRUNCATE country RESTART IDENTITY CASCADE;

INSERT INTO country (country_name, grid_intensity_kgco2_per_kwh)
SELECT country_of_origin, MAX(grid_intensity_kgco2_per_kwh)
FROM v_stg_clean
GROUP BY country_of_origin;

INSERT INTO vehicle_model
    (brand, model_name, country_of_origin, body_type, first_model_year, last_model_year)
SELECT brand, model_name, country_of_origin, body_type,
       MIN(model_year), MAX(model_year)
FROM v_stg_clean
GROUP BY brand, model_name, country_of_origin, body_type;

INSERT INTO ev_variant_sales (
    model_id, model_year, variant_name, market_segment, powertrain_type,
    battery_technology, battery_capacity_kwh, driving_range_miles, driving_range_km,
    energy_consumption_wh_per_mi, peak_charging_kw, charging_time_min_10_80,
    acceleration_0_60_mph, top_speed_mph, horsepower, seating_capacity, price_usd,
    annual_sales_units, customer_rating, safety_rating,
    est_manufacturing_co2e_tonnes, est_annual_co2e_saved_tonnes)
SELECT
    m.model_id, s.model_year, s.variant_name, s.market_segment, s.powertrain_type,
    s.battery_technology, s.battery_capacity_kwh, s.driving_range_miles, s.driving_range_km,
    s.energy_consumption_wh_per_mi, s.peak_charging_kw, s.charging_time_min_10_80,
    s.acceleration_0_60_mph, s.top_speed_mph, s.horsepower, s.seating_capacity, s.price_usd,
    s.annual_sales_units, s.customer_rating, s.safety_rating,
    s.est_manufacturing_co2e_tonnes, s.est_annual_co2e_saved_tonnes
FROM v_stg_clean s
JOIN vehicle_model m
  ON  m.brand = s.brand
  AND m.model_name = s.model_name
  AND m.country_of_origin = s.country_of_origin
  AND m.body_type = s.body_type;

COMMIT;

-- Load report.
SELECT 'staging_rows'    AS metric, COUNT(*)::TEXT AS value FROM stg_ev_raw
UNION ALL SELECT 'clean_rows', COUNT(*)::TEXT FROM v_stg_clean
UNION ALL SELECT 'rejected_rows',
       ((SELECT COUNT(*) FROM stg_ev_raw)
        - (SELECT COUNT(*) FROM v_stg_clean))::TEXT
UNION ALL SELECT 'countries',  COUNT(*)::TEXT FROM country
UNION ALL SELECT 'models',     COUNT(*)::TEXT FROM vehicle_model
UNION ALL SELECT 'fact_rows',  COUNT(*)::TEXT FROM ev_variant_sales
UNION ALL SELECT 'total_units',
       TO_CHAR(SUM(annual_sales_units), 'FM999,999,999') FROM ev_variant_sales
UNION ALL SELECT 'year_span',
       MIN(model_year)::TEXT || '-' || MAX(model_year)::TEXT FROM ev_variant_sales
UNION ALL SELECT 'distinct_chem', COUNT(DISTINCT battery_technology)::TEXT FROM ev_variant_sales;
