-- EV Analytics Hub — Postgres schema
-- Grain of the fact table: one row per (model, year, variant, battery technology).

BEGIN;

DROP TABLE IF EXISTS ev_variant_sales CASCADE;
DROP TABLE IF EXISTS vehicle_model CASCADE;
DROP TABLE IF EXISTS country CASCADE;

CREATE TABLE country (
    country_name                    VARCHAR(64) PRIMARY KEY,
    grid_intensity_kgco2_per_kwh    NUMERIC(6,3) NOT NULL CHECK (grid_intensity_kgco2_per_kwh > 0)
);

CREATE TABLE vehicle_model (
    model_id            SERIAL PRIMARY KEY,
    brand               VARCHAR(64)  NOT NULL,
    model_name          VARCHAR(96)  NOT NULL,
    country_of_origin   VARCHAR(64)  NOT NULL REFERENCES country(country_name),
    body_type           VARCHAR(32)  NOT NULL,
    first_model_year    SMALLINT     NOT NULL,
    last_model_year     SMALLINT     NOT NULL,
    UNIQUE (brand, model_name, country_of_origin, body_type),
    CHECK (last_model_year >= first_model_year)
);

CREATE TABLE ev_variant_sales (
    fact_id                            SERIAL PRIMARY KEY,
    model_id                           INT NOT NULL REFERENCES vehicle_model(model_id),
    model_year                         SMALLINT NOT NULL,
    variant_name                       VARCHAR(32) NOT NULL,
    market_segment                     VARCHAR(32) NOT NULL,
    powertrain_type                    VARCHAR(16) NOT NULL,
    battery_technology                 VARCHAR(32) NOT NULL,
    battery_capacity_kwh               NUMERIC(8,2) NOT NULL CHECK (battery_capacity_kwh > 0),
    driving_range_miles                NUMERIC(8,1) NOT NULL CHECK (driving_range_miles > 0),
    driving_range_km                   NUMERIC(8,1) NOT NULL CHECK (driving_range_km > 0),
    energy_consumption_wh_per_mi       NUMERIC(9,1) NOT NULL CHECK (energy_consumption_wh_per_mi > 0),
    peak_charging_kw                   NUMERIC(7,1) NOT NULL CHECK (peak_charging_kw > 0),
    charging_time_min_10_80            NUMERIC(8,1) NOT NULL CHECK (charging_time_min_10_80 >= 0),
    acceleration_0_60_mph              NUMERIC(6,1) NOT NULL,
    top_speed_mph                      NUMERIC(6,1) NOT NULL,
    horsepower                         NUMERIC(7,1) NOT NULL,
    seating_capacity                   SMALLINT NOT NULL,
    price_usd                          NUMERIC(11,2) NOT NULL CHECK (price_usd > 0),
    annual_sales_units                 NUMERIC(14,2) NOT NULL CHECK (annual_sales_units >= 0),
    customer_rating                    NUMERIC(4,2) NOT NULL CHECK (customer_rating BETWEEN 1 AND 5),
    safety_rating                      NUMERIC(3,1) NOT NULL,
    est_manufacturing_co2e_tonnes      NUMERIC(8,2) NOT NULL,
    est_annual_co2e_saved_tonnes       NUMERIC(8,2) NOT NULL,
    UNIQUE (model_id, model_year, variant_name, battery_technology)
);

CREATE INDEX idx_fact_year      ON ev_variant_sales(model_year);
CREATE INDEX idx_fact_tech      ON ev_variant_sales(battery_technology);
CREATE INDEX idx_fact_model     ON ev_variant_sales(model_id);
CREATE INDEX idx_model_country  ON vehicle_model(country_of_origin);
CREATE INDEX idx_model_brand    ON vehicle_model(brand);

COMMIT;

-- ---------------------------------------------------------------------------
-- Views. Tableau consumes these directly, so the analytical logic lives in
-- SQL rather than being duplicated as calculated fields.
-- ---------------------------------------------------------------------------

-- Primary wide table for dashboard authoring.
CREATE OR REPLACE VIEW v_ev_data AS
SELECT
    m.model_id, m.brand, m.model_name, m.body_type, m.country_of_origin,
    f.model_year, f.variant_name, f.market_segment, f.powertrain_type,
    f.battery_technology, f.battery_capacity_kwh, f.driving_range_miles,
    f.driving_range_km, f.energy_consumption_wh_per_mi, f.peak_charging_kw,
    f.charging_time_min_10_80, f.acceleration_0_60_mph, f.top_speed_mph,
    f.horsepower, f.seating_capacity, f.price_usd, f.annual_sales_units,
    f.customer_rating, f.safety_rating,
    f.est_manufacturing_co2e_tonnes, f.est_annual_co2e_saved_tonnes,
    c.grid_intensity_kgco2_per_kwh,
    ROUND(f.annual_sales_units * f.battery_capacity_kwh / 1000000.0, 3) AS gwh_battery_demand,
    ROUND(f.annual_sales_units * f.est_annual_co2e_saved_tonnes, 1)   AS co2e_avoided_tonnes,
    ROUND(f.price_usd / NULLIF(f.driving_range_miles, 0) / 1000.0, 2) AS usd_per_1000_miles,
    ROUND(f.price_usd / NULLIF(f.battery_capacity_kwh, 0), 1)         AS usd_per_kwh
FROM vehicle_model m
JOIN ev_variant_sales f ON f.model_id = m.model_id
JOIN country c          ON c.country_name = m.country_of_origin;

-- Manufacturer performance with share of dataset sales.
CREATE OR REPLACE VIEW v_manufacturer_yearly AS
SELECT
    brand,
    model_year,
    SUM(annual_sales_units)                                            AS units,
    ROUND(AVG(customer_rating), 2)                                     AS avg_rating,
    ROUND(AVG(price_usd), 0)                                           AS avg_price_usd,
    ROUND(AVG(driving_range_miles), 1)                                 AS avg_range_miles,
    COUNT(DISTINCT model_id)                                           AS active_models,
    ROUND(100.0 * SUM(annual_sales_units)
          / NULLIF(SUM(SUM(annual_sales_units)) OVER (PARTITION BY model_year), 0), 2)
                                                                       AS pct_of_year_units
FROM v_ev_data
GROUP BY brand, model_year;

-- Total units by year with year-over-year growth.
CREATE OR REPLACE VIEW v_yearly_growth AS
WITH y AS (
    SELECT model_year,
           SUM(annual_sales_units) AS units,
           ROUND(SUM(annual_sales_units * battery_capacity_kwh) / 1000000.0, 1) AS gwh_demand,
           ROUND(SUM(driving_range_miles * annual_sales_units)
                 / NULLIF(SUM(annual_sales_units), 0), 1)      AS avg_range_miles_weighted,
           ROUND(SUM(price_usd * annual_sales_units)
                 / NULLIF(SUM(annual_sales_units), 0), 0)      AS avg_price_usd_weighted
    FROM v_ev_data GROUP BY model_year
)
SELECT model_year, units, gwh_demand, avg_range_miles_weighted, avg_price_usd_weighted,
       LAG(units) OVER (ORDER BY model_year)                              AS prior_year_units,
       ROUND(100.0 * (units - LAG(units) OVER (ORDER BY model_year))
             / NULLIF(LAG(units) OVER (ORDER BY model_year), 0), 2)       AS yoy_growth_pct
FROM y;

-- Vehicle category contribution.
CREATE OR REPLACE VIEW v_category_summary AS
SELECT
    body_type,
    SUM(annual_sales_units)                                       AS units,
    ROUND(100.0 * SUM(annual_sales_units)
          / NULLIF(SUM(SUM(annual_sales_units)) OVER (), 0), 2)   AS pct_of_dataset_units,
    COUNT(DISTINCT model_id)                                      AS models,
    ROUND(AVG(driving_range_miles), 1)                            AS avg_range_miles,
    ROUND(AVG(battery_capacity_kwh), 1)                           AS avg_capacity_kwh,
    ROUND(AVG(charging_time_min_10_80), 1)                        AS avg_charge_min,
    ROUND(AVG(price_usd), 0)                                      AS avg_price_usd,
    ROUND(AVG(customer_rating), 2)                                AS avg_rating
FROM v_ev_data GROUP BY body_type;

-- Battery technology adoption and performance.
CREATE OR REPLACE VIEW v_battery_tech_summary AS
SELECT
    battery_technology,
    SUM(annual_sales_units)                                       AS units,
    ROUND(100.0 * SUM(annual_sales_units)
          / NULLIF(SUM(SUM(annual_sales_units)) OVER (), 0), 2)   AS pct_of_dataset_units,
    ROUND(SUM(annual_sales_units * battery_capacity_kwh) / 1000000.0, 1) AS gwh_demand,
    COUNT(DISTINCT model_id)                                      AS models,
    COUNT(DISTINCT brand)                                         AS brands,
    ROUND(AVG(battery_capacity_kwh), 1)                           AS avg_capacity_kwh,
    ROUND(AVG(driving_range_miles), 1)                            AS avg_range_miles,
    ROUND(AVG(peak_charging_kw), 1)                               AS avg_peak_kw,
    ROUND(AVG(est_manufacturing_co2e_tonnes), 2)                  AS avg_mfg_co2e_tonnes,
    ROUND(AVG(price_usd), 0)                                      AS avg_price_usd,
    MIN(model_year)                                               AS first_model_year,
    MAX(model_year)                                               AS last_model_year
FROM v_ev_data GROUP BY battery_technology;

-- Year-on-year change in range and capacity per chemistry: the innovation trend.
CREATE OR REPLACE VIEW v_tech_evolution AS
SELECT
    battery_technology,
    model_year,
    ROUND(AVG(battery_capacity_kwh), 1)   AS avg_capacity_kwh,
    ROUND(AVG(driving_range_miles), 1)    AS avg_range_miles,
    ROUND(AVG(energy_consumption_wh_per_mi), 1) AS avg_wh_per_mi,
    ROUND(AVG(peak_charging_kw), 1)       AS avg_peak_kw,
    COUNT(*)                              AS variant_rows
FROM v_ev_data
GROUP BY battery_technology, model_year;

-- Manufacturing geography.
CREATE OR REPLACE VIEW v_country_manufacturing AS
SELECT
    country_of_origin,
    grid_intensity_kgco2_per_kwh,
    SUM(annual_sales_units)                                       AS units,
    ROUND(100.0 * SUM(annual_sales_units)
          / NULLIF(SUM(SUM(annual_sales_units)) OVER (), 0), 2)   AS pct_of_dataset_units,
    ROUND(SUM(annual_sales_units * battery_capacity_kwh) / 1000000.0, 1) AS gwh_demand,
    ROUND(SUM(annual_sales_units * est_annual_co2e_saved_tonnes), 0)  AS co2e_avoided_tonnes,
    COUNT(DISTINCT brand)                                         AS brands,
    COUNT(DISTINCT model_id)                                      AS models,
    ROUND(AVG(customer_rating), 2)                                AS avg_rating,
    ROUND(AVG(driving_range_miles), 1)                            AS avg_range_miles
FROM v_ev_data GROUP BY country_of_origin, grid_intensity_kgco2_per_kwh;

-- Brand x category satisfaction matrix for the heatmap.
CREATE OR REPLACE VIEW v_satisfaction_matrix AS
SELECT
    brand, body_type,
    ROUND(AVG(customer_rating), 2)   AS avg_rating,
    SUM(annual_sales_units)          AS units,
    COUNT(DISTINCT model_id)         AS models
FROM v_ev_data
GROUP BY brand, body_type;

-- Top-rated models, volume-filtered so low-count vehicles cannot lead the ranking.
CREATE OR REPLACE VIEW v_top_rated_models AS
WITH agg AS (
    SELECT brand, model_name, body_type, battery_technology,
           ROUND(AVG(customer_rating), 2)  AS avg_rating,
           ROUND(AVG(driving_range_miles), 1) AS avg_range_miles,
           ROUND(AVG(price_usd), 0)        AS avg_price_usd,
           SUM(annual_sales_units)         AS lifetime_units,
           COUNT(DISTINCT model_year)      AS years_on_market
    FROM v_ev_data
    GROUP BY brand, model_name, body_type, battery_technology
)
SELECT * FROM agg
WHERE lifetime_units >= 50000
ORDER BY avg_rating DESC, lifetime_units DESC;

-- Model-level detail for the comparison table.
CREATE OR REPLACE VIEW v_model_detail AS
SELECT
    brand, model_name, body_type, market_segment, country_of_origin,
    battery_technology,
    MIN(model_year)                             AS first_year,
    MAX(model_year)                             AS last_year,
    ROUND(MIN(battery_capacity_kwh), 1)         AS min_capacity_kwh,
    ROUND(MAX(battery_capacity_kwh), 1)         AS max_capacity_kwh,
    ROUND(MAX(driving_range_miles), 0)          AS best_range_miles,
    ROUND(MIN(charging_time_min_10_80), 1)      AS best_charge_min,
    ROUND(MIN(price_usd), 0)                    AS entry_price_usd,
    ROUND(MAX(price_usd), 0)                    AS top_price_usd,
    ROUND(AVG(customer_rating), 2)              AS avg_rating,
    SUM(annual_sales_units)                     AS lifetime_units,
    ROUND(SUM(annual_sales_units * est_annual_co2e_saved_tonnes), 0) AS co2e_avoided_tonnes
FROM v_ev_data
GROUP BY brand, model_name, body_type, market_segment, country_of_origin, battery_technology;
