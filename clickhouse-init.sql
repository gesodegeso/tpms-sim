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
    `sensor_id` String COMMENT 'Sensor identifier (sensor position + type or GPS)',
    `vin` String COMMENT 'Vehicle Identification Number',
    `read_at` DateTime64(3) COMMENT 'Timestamp when sensor reading was taken',
    `trigger` LowCardinality(String) COMMENT 'Anomaly indicator (1=anomaly, empty=normal)',
    `reading` Nullable(Float64) COMMENT 'Sensor reading value (PSI, temperature, or coordinates)',
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
--   AND sensor_id = 'sensor11_pressure'
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
--       AND trigger = ''  -- Exclude anomalies
--     GROUP BY vin, sensor_id
-- )
-- SELECT
--     sensor_id,
--     avg(temp_rise) as avg_temp_rise,
--     max(temp_rise) as max_temp_rise
-- FROM trip_temps
-- GROUP BY sensor_id
-- ORDER BY sensor_id;

-- ============================================
-- ANOMALY DETECTION AND ANALYSIS QUERIES
-- ============================================

-- View for anomaly statistics
CREATE VIEW IF NOT EXISTS v1__anomaly_stats AS
SELECT
    tenant,
    vin,
    toDate(read_at) as date,
    COUNT(*) as total_records,
    COUNT(CASE WHEN trigger = '1' THEN 1 END) as anomaly_count,
    COUNT(CASE WHEN trigger = '1' THEN 1 END) * 100.0 / COUNT(*) as anomaly_rate
FROM v1__sensor_reading
GROUP BY tenant, vin, date;

-- View for data quality monitoring
CREATE VIEW IF NOT EXISTS v1__data_quality AS
SELECT
    toStartOfHour(read_at) as hour,
    COUNT(*) as total_records,
    COUNT(CASE WHEN trigger = '1' THEN 1 END) as anomalies,
    COUNT(CASE WHEN reading IS NULL THEN 1 END) as null_readings,
    COUNT(CASE WHEN sensor_id LIKE '%pressure%' AND (reading < 0 OR reading > 200) THEN 1 END) as out_of_range_pressure,
    COUNT(CASE WHEN sensor_id LIKE '%temperature%' AND (reading < -50 OR reading > 300) THEN 1 END) as out_of_range_temp,
    COUNT(CASE WHEN ingested_at < read_at THEN 1 END) as timestamp_anomalies
FROM v1__sensor_reading
GROUP BY hour
ORDER BY hour DESC;

-- Detect traffic events based on anomaly patterns
-- SELECT
--     vin,
--     min(read_at) as event_start,
--     max(read_at) as event_end,
--     count(*) as anomaly_count,
--     avg(CASE WHEN sensor_id LIKE '%pressure%' THEN reading END) as avg_pressure,
--     min(CASE WHEN sensor_id LIKE '%pressure%' THEN reading END) as min_pressure
-- FROM v1__sensor_reading
-- WHERE trigger = '1'
--   AND read_at >= now() - INTERVAL 1 DAY
-- GROUP BY vin, toStartOfHour(read_at)
-- HAVING anomaly_count > 10
-- ORDER BY event_start DESC;

-- Identify potential sensor failures
-- SELECT
--     vin,
--     sensor_id,
--     COUNT(*) as error_count,
--     MIN(read_at) as first_error,
--     MAX(read_at) as last_error,
--     arrayStringConcat(groupArray(toString(reading)), ', ') as sample_readings
-- FROM v1__sensor_reading
-- WHERE trigger = '1'
--   AND (reading IS NULL OR reading < 0 OR reading > 999)
-- GROUP BY vin, sensor_id
-- HAVING error_count > 5
-- ORDER BY error_count DESC;

-- Data completeness check
-- SELECT
--     vin,
--     COUNT(DISTINCT sensor_id) as active_sensors,
--     COUNT(DISTINCT toStartOfHour(read_at)) as hours_with_data,
--     MIN(read_at) as first_reading,
--     MAX(read_at) as last_reading,
--     COUNT(*) as total_readings,
--     COUNT(CASE WHEN trigger = '1' THEN 1 END) as anomaly_readings
-- FROM v1__sensor_reading
-- WHERE read_at >= today()
-- GROUP BY vin
-- ORDER BY anomaly_readings DESC;