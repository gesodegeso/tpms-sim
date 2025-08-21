-- TPMS Sensor Data Table Creation Script for ClickHouse
-- This script creates the table structure matching the schema in schemas.txt

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS tpms;

-- Use the database
USE tpms;

-- Drop table if exists (for clean setup)
DROP TABLE IF EXISTS v1__sensor_reading;

-- Create the sensor_reading table
CREATE TABLE IF NOT EXISTS v1__sensor_reading
(
    `tenant` LowCardinality(String) COMMENT 'Tenant identifier',
    `sensor_id` String COMMENT 'Sensor identifier (tire position + type or GPS)',
    `vin` String COMMENT 'Vehicle Identification Number',
    `read_at` DateTime64(3) COMMENT 'Timestamp when sensor reading was taken',
    `trigger` LowCardinality(String) COMMENT 'Trigger event (usually empty)',
    `reading` Float64 COMMENT 'Sensor reading value (PSI, temperature, or coordinates)',
    `ingested_at` DateTime64(3) DEFAULT now64() COMMENT 'Timestamp when data was ingested'
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(read_at)
ORDER BY (tenant, vin, read_at, sensor_id)
TTL read_at + INTERVAL 90 DAY
SETTINGS index_granularity = 8192
COMMENT 'TPMS sensor readings table for tire pressure and temperature monitoring';

-- Create materialized view for latest readings per vehicle
CREATE MATERIALIZED VIEW IF NOT EXISTS v1__sensor_reading_latest
ENGINE = ReplacingMergeTree()
ORDER BY (tenant, vin, sensor_id)
AS
SELECT
    tenant,
    vin,
    sensor_id,
    argMax(reading, read_at) AS latest_reading,
    max(read_at) AS latest_read_at,
    max(ingested_at) AS latest_ingested_at
FROM v1__sensor_reading
GROUP BY tenant, vin, sensor_id;

-- Create view for pressure alerts (example: pressure outside normal range)
CREATE VIEW IF NOT EXISTS v1__pressure_alerts AS
SELECT
    tenant,
    vin,
    sensor_id,
    reading AS pressure,
    read_at,
    CASE
        WHEN sensor_id LIKE '%pressure%' AND reading < 31 THEN 'LOW_PRESSURE'
        WHEN sensor_id LIKE '%pressure%' AND reading > 35 THEN 'HIGH_PRESSURE'
        WHEN sensor_id LIKE '%pressure%' AND reading < 85 THEN 'LOW_PRESSURE_HD'
        WHEN sensor_id LIKE '%pressure%' AND reading > 120 THEN 'HIGH_PRESSURE_HD'
        ELSE 'NORMAL'
    END AS alert_type
FROM v1__sensor_reading
WHERE sensor_id LIKE '%pressure%'
  AND (reading < 31 OR reading > 120);

-- Create aggregation table for hourly statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS v1__sensor_stats_hourly
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(hour)
ORDER BY (tenant, vin, sensor_id, hour)
AS
SELECT
    tenant,
    vin,
    sensor_id,
    toStartOfHour(read_at) AS hour,
    count() AS reading_count,
    avg(reading) AS avg_reading,
    min(reading) AS min_reading,
    max(reading) AS max_reading,
    stddevPop(reading) AS stddev_reading
FROM v1__sensor_reading
WHERE sensor_id NOT IN ('latitude', 'longitude')
GROUP BY tenant, vin, sensor_id, hour;

-- Sample query to import Parquet data
-- INSERT INTO v1__sensor_reading 
-- SELECT * FROM file('/var/lib/clickhouse/user_files/tpms_data.parquet', 'Parquet');

-- Sample queries for analysis

-- Get latest readings for a specific vehicle
-- SELECT * FROM v1__sensor_reading_latest WHERE vin = '1HGBH41JXMN109186';

-- Get pressure trend for a specific wheel over time
-- SELECT 
--     read_at,
--     reading as pressure
-- FROM v1__sensor_reading
-- WHERE vin = '1HGBH41JXMN109186'
--   AND sensor_id = 'tire11_pressure'
-- ORDER BY read_at;

-- Find vehicles with potential tire issues
-- SELECT DISTINCT
--     tenant,
--     vin,
--     sensor_id,
--     alert_type,
--     count() as alert_count
-- FROM v1__pressure_alerts
-- WHERE read_at >= now() - INTERVAL 1 DAY
-- GROUP BY tenant, vin, sensor_id, alert_type
-- ORDER BY alert_count DESC;

-- Calculate average temperature rise during trips
-- WITH trip_temps AS (
--     SELECT
--         vin,
--         sensor_id,
--         min(reading) as start_temp,
--         max(reading) as max_temp,
--         max(reading) - min(reading) as temp_rise
--     FROM v1__sensor_reading
--     WHERE sensor_id LIKE '%temperature%'
--       AND read_at >= today()
--     GROUP BY vin, sensor_id
-- )
-- SELECT
--     sensor_id,
--     avg(temp_rise) as avg_temp_rise,
--     max(temp_rise) as max_temp_rise
-- FROM trip_temps
-- GROUP BY sensor_id
-- ORDER BY sensor_id;