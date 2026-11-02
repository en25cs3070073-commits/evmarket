-- ===========================================================================
-- EV Analytics Hub — SQL analysis layer
-- Each query is labelled with the dashboard and persona it feeds.
-- Run: psql -f db/analysis_queries.sql
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- Q1. Market size KPIs.  Dashboard 1 (Emily) — KPI cards.
-- ---------------------------------------------------------------------------
SELECT
    'Q1 market KPIs'                                   AS query,
    COUNT(DISTINCT model_id)                           AS models,
    COUNT(DISTINCT brand)                              AS brands,
    COUNT(DISTINCT country_of_origin)                  AS manufacturing_countries,
    COUNT(DISTINCT battery_technology)                 AS battery_technologies,
    ROUND(SUM(annual_sales_units), 0)                  AS lifetime_units,
    ROUND(SUM(annual_sales_units * battery_capacity_kwh) / 1000000.0, 1) AS gwh_demand,
    ROUND(AVG(customer_rating), 3)                     AS mean_rating
FROM v_ev_data;

-- ---------------------------------------------------------------------------
-- Q2. Top manufacturers by cumulative volume, with share of dataset sales.
-- Dashboard 1 (Emily, David) — bar chart. Required by the brief.
-- ---------------------------------------------------------------------------
WITH t AS (
    SELECT brand,
           SUM(annual_sales_units)                              AS units,
           COUNT(DISTINCT model_id)                             AS models,
           ROUND(SUM(price_usd * annual_sales_units)
                 / NULLIF(SUM(annual_sales_units), 0), 0)       AS avg_price_usd,
           ROUND(SUM(driving_range_miles * annual_sales_units)
                 / NULLIF(SUM(annual_sales_units), 0), 1)       AS avg_range_miles,
           ROUND(AVG(customer_rating), 2)                       AS avg_rating
    FROM v_ev_data GROUP BY brand
)
SELECT t.*,
       ROUND(100.0 * units / NULLIF(SUM(units) OVER (), 0), 2)  AS pct_of_dataset_units,
       ROW_NUMBER() OVER (ORDER BY units DESC)                  AS rank
FROM t ORDER BY units DESC LIMIT 10;

-- ---------------------------------------------------------------------------
-- Q3. Leader share by year — is the market concentrating or fragmenting?
-- Dashboard 1 (David) — competitive dynamics.
-- ---------------------------------------------------------------------------
WITH y AS (
    SELECT model_year, brand, SUM(annual_sales_units) AS units
    FROM v_ev_data GROUP BY model_year, brand
), ranked AS (
    SELECT model_year, brand, units,
           ROW_NUMBER() OVER (PARTITION BY model_year ORDER BY units DESC) AS r,
           SUM(units) OVER (PARTITION BY model_year)                        AS year_units
    FROM y
)
SELECT model_year,
       MAX(CASE WHEN r = 1 THEN brand END)                       AS leader,
       ROUND(100.0 * MAX(CASE WHEN r = 1 THEN units END)
             / NULLIF(MAX(year_units), 0), 2)                    AS leader_pct,
       ROUND(100.0 * SUM(CASE WHEN r <= 5 THEN units ELSE 0 END)
             / NULLIF(MAX(year_units), 0), 2)                    AS top5_pct,
       COUNT(*)                                                  AS active_brands
FROM ranked GROUP BY model_year ORDER BY model_year;

-- ---------------------------------------------------------------------------
-- Q4. Category contribution, measured by SHARE of each year rather than raw
-- growth. Absolute growth is unreliable here: the catalogue contains more
-- models in later years, so raw growth partly measures coverage.
-- Dashboard 1 (Emily) — treemap and high-growth segments.
-- ---------------------------------------------------------------------------
WITH per_year AS (
    SELECT body_type, model_year,
           SUM(annual_sales_units) AS units,
           COUNT(DISTINCT model_id) AS models,
           100.0 * SUM(annual_sales_units)
                 / NULLIF(SUM(SUM(annual_sales_units)) OVER (PARTITION BY model_year), 0) AS share
    FROM v_ev_data GROUP BY body_type, model_year
), lifetime AS (
    SELECT body_type, ROUND(SUM(annual_sales_units), 0) AS lifetime_units,
           ROUND(100.0 * SUM(annual_sales_units)
                 / NULLIF(SUM(SUM(annual_sales_units)) OVER (), 0), 2) AS pct_of_dataset
    FROM v_ev_data GROUP BY body_type
)
SELECT l.body_type, l.lifetime_units, l.pct_of_dataset,
       ROUND(MAX(CASE WHEN p.model_year = 2021 THEN p.share END)::NUMERIC, 2) AS share_2021_pct,
       ROUND(MAX(CASE WHEN p.model_year = 2025 THEN p.share END)::NUMERIC, 2) AS share_2025_pct,
       ROUND((MAX(CASE WHEN p.model_year = 2025 THEN p.share END)
            - MAX(CASE WHEN p.model_year = 2021 THEN p.share END))::NUMERIC, 2) AS share_change_pts,
       MAX(CASE WHEN p.model_year = 2021 THEN p.models END) AS models_2021,
       MAX(CASE WHEN p.model_year = 2025 THEN p.models END) AS models_2025
FROM lifetime l JOIN per_year p ON p.body_type = l.body_type
GROUP BY l.body_type, l.lifetime_units, l.pct_of_dataset
ORDER BY l.lifetime_units DESC;

-- ---------------------------------------------------------------------------
-- Q5. Battery technology: unit share versus energy demand share.
-- Dashboard 2 (Emily, Sarah) — donut. The two rankings differ, which is the finding.
-- ---------------------------------------------------------------------------
SELECT battery_technology,
       ROUND(SUM(annual_sales_units), 0)                          AS units,
       ROUND(100.0 * SUM(annual_sales_units)
             / NULLIF(SUM(SUM(annual_sales_units)) OVER (), 0), 2) AS pct_units,
       ROUND(SUM(annual_sales_units * battery_capacity_kwh) / 1000000.0, 1) AS gwh_demand,
       ROUND(100.0 * SUM(annual_sales_units * battery_capacity_kwh)
             / NULLIF(SUM(SUM(annual_sales_units * battery_capacity_kwh)) OVER (), 0), 2) AS pct_gwh,
       ROUND(AVG(driving_range_miles), 1)                         AS avg_range_miles,
       ROUND(AVG(est_manufacturing_co2e_tonnes), 2)               AS avg_mfg_co2e_tonnes
FROM v_ev_data
GROUP BY battery_technology
ORDER BY units DESC;

-- ---------------------------------------------------------------------------
-- Q6. LFP versus NMC, year by year. There is no single clean crossover: the
-- two are within a few points of each other throughout, with LFP ahead in
-- 2021 and 2025. Report it as a close race, not a flip.
-- Dashboard 2 (Sarah) — line chart.
-- ---------------------------------------------------------------------------
SELECT model_year,
       ROUND(SUM(CASE WHEN battery_technology = 'LFP' THEN annual_sales_units ELSE 0 END), 0) AS lfp_units,
       ROUND(SUM(CASE WHEN battery_technology = 'NMC' THEN annual_sales_units ELSE 0 END), 0) AS nmc_units,
       CASE WHEN SUM(CASE WHEN battery_technology = 'LFP' THEN annual_sales_units ELSE 0 END)
              > SUM(CASE WHEN battery_technology = 'NMC' THEN annual_sales_units ELSE 0 END)
            THEN 'LFP ahead' ELSE 'NMC ahead' END                AS leader
FROM v_ev_data
WHERE battery_technology IN ('LFP', 'NMC')
GROUP BY model_year ORDER BY model_year;

-- ---------------------------------------------------------------------------
-- Q7. Efficiency bands: why capacity alone does not predict range.
-- Dashboard 2 (Emily, Sarah) — scatter coloured by category.
-- ---------------------------------------------------------------------------
SELECT body_type,
       COUNT(*)                                                   AS variant_rows,
       ROUND(AVG(battery_capacity_kwh), 1)                        AS avg_capacity_kwh,
       ROUND(AVG(driving_range_miles), 1)                         AS avg_range_miles,
       ROUND(AVG(energy_consumption_wh_per_mi), 1)                AS avg_wh_per_mi,
       ROUND(CORR(battery_capacity_kwh, driving_range_miles)::NUMERIC, 3) AS corr_capacity_range
FROM v_ev_data
GROUP BY body_type ORDER BY avg_wh_per_mi;

-- ---------------------------------------------------------------------------
-- Q8. Charging speed and refill time by chemistry.
-- Dashboard 2 (Sarah) — bar chart.
-- ---------------------------------------------------------------------------
SELECT battery_technology,
       ROUND(AVG(peak_charging_kw), 1)                            AS avg_peak_kw,
       ROUND(MIN(peak_charging_kw), 1)                            AS min_peak_kw,
       ROUND(MAX(peak_charging_kw), 1)                            AS max_peak_kw,
       ROUND(AVG(charging_time_min_10_80), 1)                     AS avg_charge_min_10_80,
       ROUND(AVG(peak_charging_kw / NULLIF(battery_capacity_kwh, 0)), 2) AS avg_c_rate
FROM v_ev_data
GROUP BY battery_technology ORDER BY avg_c_rate DESC;

-- ---------------------------------------------------------------------------
-- Q9. Range improvement per chemistry over time — the innovation trend.
-- Story scene 3 (Sarah).
-- ---------------------------------------------------------------------------
WITH r AS (
    SELECT battery_technology, model_year,
           AVG(driving_range_miles) AS avg_range,
           AVG(battery_capacity_kwh) AS avg_kwh
    FROM v_ev_data
    GROUP BY battery_technology, model_year
), spans AS (
    SELECT battery_technology,
           MIN(model_year) AS from_yr, MAX(model_year) AS to_yr,
           ROUND(MIN(avg_range)::NUMERIC, 1) AS range_low,
           ROUND(MAX(avg_range)::NUMERIC, 1) AS range_high,
           COUNT(*) AS years_observed
    FROM r GROUP BY battery_technology
)
SELECT *,
       ROUND(100.0 * (range_high - range_low) / NULLIF(range_low, 0), 1) AS range_gain_pct
FROM spans ORDER BY range_gain_pct DESC;

-- ---------------------------------------------------------------------------
-- Q10. Manufacturing concentration, with Herfindahl-Hirschman index.
-- Dashboard 3 (David) — geographic map.
-- ---------------------------------------------------------------------------
WITH s AS (
    SELECT country_of_origin,
           SUM(annual_sales_units) AS units,
           100.0 * SUM(annual_sales_units)
                 / NULLIF(SUM(SUM(annual_sales_units)) OVER (), 0) AS pct
    FROM v_ev_data GROUP BY country_of_origin
)
SELECT 'Q10 concentration' AS query,
       ROUND(SUM(pct * pct), 0)                                     AS hhi_index,
       CASE WHEN SUM(pct * pct) >= 2500 THEN 'highly concentrated'
            WHEN SUM(pct * pct) >= 1500 THEN 'moderately concentrated'
            ELSE 'competitive' END                                  AS market_structure,
       ROUND(MAX(pct), 2)                                           AS largest_country_pct,
       COUNT(*)                                                     AS countries
FROM s;

-- ---------------------------------------------------------------------------
-- Q11. Grid effect, measured on passenger vehicles only.
-- Pooling every body type reverses the answer: the USA leads raw per-unit
-- savings only because its rows are dominated by electric trucks, whose
-- diesel baseline is enormous. Holding body type constant isolates the grid.
-- Dashboard 3 (Sarah) — sustainability.
-- ---------------------------------------------------------------------------
SELECT country_of_origin,
       grid_intensity_kgco2_per_kwh,
       ROUND(SUM(annual_sales_units), 0)                          AS passenger_units,
       ROUND(AVG(est_annual_co2e_saved_tonnes), 2)                AS t_saved_per_vehicle_year,
       ROUND(AVG(driving_range_miles), 1)                         AS avg_range_miles,
       ROUND(AVG(est_manufacturing_co2e_tonnes), 2)               AS avg_mfg_co2e_tonnes
FROM v_ev_data
WHERE body_type IN ('Sedan', 'SUV', 'Hatchback')
GROUP BY country_of_origin, grid_intensity_kgco2_per_kwh
ORDER BY t_saved_per_vehicle_year DESC;

-- ---------------------------------------------------------------------------
-- Q12. Break-even: does an EV on a coal-heavy grid still beat ICE?
-- Story scene 4 (Sarah) — the honest caveat.
-- ---------------------------------------------------------------------------
SELECT battery_technology,
       country_of_origin,
       ROUND(AVG(est_annual_co2e_saved_tonnes), 2)                AS avg_t_saved_per_year,
       ROUND(AVG(est_manufacturing_co2e_tonnes
                 / NULLIF(est_annual_co2e_saved_tonnes, 0)), 1)   AS mfg_payback_years,
       COUNT(*)                                                   AS rows
FROM v_ev_data
WHERE est_annual_co2e_saved_tonnes > 0
GROUP BY battery_technology, country_of_origin
HAVING COUNT(*) >= 8
ORDER BY mfg_payback_years NULLS LAST LIMIT 12;

-- ---------------------------------------------------------------------------
-- Q13. Satisfaction matrix, volume-weighted so tiny fleets cannot top it.
-- Dashboard 1 (Emily, David) — heatmap.
-- ---------------------------------------------------------------------------
WITH m AS (
    SELECT brand, body_type,
           ROUND(AVG(customer_rating), 2) AS avg_rating,
           SUM(annual_sales_units)        AS units
    FROM v_ev_data GROUP BY brand, body_type HAVING SUM(annual_sales_units) >= 50000
), ranked AS (
    SELECT m.*, RANK() OVER (PARTITION BY brand ORDER BY avg_rating DESC, units DESC) AS r
    FROM m
)
SELECT brand, body_type, avg_rating, ROUND(units, 0) AS units
FROM ranked WHERE r = 1 ORDER BY avg_rating DESC;

-- ---------------------------------------------------------------------------
-- Q14. Best value positioning: range delivered per dollar.
-- Dashboard 3 (David) — horizontal bar / competitive opportunity.
-- ---------------------------------------------------------------------------
SELECT brand, model_name, body_type, battery_technology,
       ROUND(AVG(driving_range_miles), 0)                         AS avg_range_miles,
       ROUND(AVG(price_usd), 0)                                   AS avg_price_usd,
       ROUND(AVG(price_usd / NULLIF(driving_range_miles, 0)), 1)  AS usd_per_mile,
       ROUND(AVG(customer_rating), 2)                             AS avg_rating,
       ROUND(SUM(annual_sales_units), 0)                          AS lifetime_units
FROM v_ev_data
WHERE body_type IN ('Sedan', 'SUV', 'Hatchback')
GROUP BY brand, model_name, body_type, battery_technology
HAVING SUM(annual_sales_units) >= 100000
ORDER BY usd_per_mile ASC LIMIT 12;

-- ---------------------------------------------------------------------------
-- Q15. Emerging chemistries compared like-for-like. Range is measured on
-- passenger vehicles only, otherwise a sodium-ion bus drags the average down
-- and hides the solid-state advantage.
-- Story scene 4 (Sarah, Emily).
-- ---------------------------------------------------------------------------
SELECT model_year,
       ROUND(SUM(CASE WHEN battery_technology = 'Semi-Solid-State'
                      THEN annual_sales_units ELSE 0 END), 0)     AS solid_state_units,
       ROUND(SUM(CASE WHEN battery_technology = 'Sodium-Ion'
                      THEN annual_sales_units ELSE 0 END), 0)     AS sodium_units,
       ROUND(100.0 * SUM(CASE WHEN battery_technology IN ('Semi-Solid-State','Sodium-Ion')
                              THEN annual_sales_units ELSE 0 END)
             / NULLIF(SUM(annual_sales_units), 0), 3)             AS emerging_pct_of_units,
       ROUND(AVG(CASE WHEN battery_technology = 'Semi-Solid-State'
                       AND body_type IN ('Sedan','SUV')
                      THEN driving_range_miles END), 1)           AS solid_range_passenger,
       ROUND(AVG(CASE WHEN battery_technology IN ('LFP','NMC','NCA')
                       AND body_type IN ('Sedan','SUV')
                      THEN driving_range_miles END), 1)           AS lithium_ion_range_passenger
FROM v_ev_data GROUP BY model_year ORDER BY model_year;

-- ---------------------------------------------------------------------------
-- Q16. Price band x segment positioning, weighted by volume.
-- Dashboard 1 (Emily) — portfolio optimisation.
-- ---------------------------------------------------------------------------
SELECT market_segment,
       CASE WHEN price_usd < 20000 THEN 'A. under 20k'
            WHEN price_usd < 40000 THEN 'B. 20k to 40k'
            WHEN price_usd < 70000 THEN 'C. 40k to 70k'
            ELSE 'D. over 70k' END                                AS price_band,
       ROUND(SUM(annual_sales_units), 0)                          AS units,
       ROUND(AVG(driving_range_miles), 1)                         AS avg_range_miles,
       ROUND(AVG(customer_rating), 2)                             AS avg_rating,
       ROUND(SUM(annual_sales_units * est_annual_co2e_saved_tonnes), 0) AS co2e_avoided
FROM v_ev_data
GROUP BY market_segment,
         CASE WHEN price_usd < 20000 THEN 'A. under 20k'
              WHEN price_usd < 40000 THEN 'B. 20k to 40k'
              WHEN price_usd < 70000 THEN 'C. 40k to 70k'
              ELSE 'D. over 70k' END
ORDER BY market_segment, price_band;
