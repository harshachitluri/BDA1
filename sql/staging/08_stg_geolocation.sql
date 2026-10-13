-- stg_geolocation: the raw file has ~1M rows with many points per zip prefix.
-- We collapse it to one row per zip prefix (average coordinates).
DROP TABLE IF EXISTS stg_geolocation;
CREATE TABLE stg_geolocation AS
SELECT
    trim(geolocation_zip_code_prefix)   AS zip_prefix,
    AVG(CAST(geolocation_lat AS REAL))  AS lat,
    AVG(CAST(geolocation_lng AS REAL))  AS lng,
    COUNT(*)                            AS n_points
FROM raw_geolocation
GROUP BY trim(geolocation_zip_code_prefix);
