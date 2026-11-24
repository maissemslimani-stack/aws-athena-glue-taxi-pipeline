-- ============================================================================
-- Task 1: Create AWS Glue Database & External CSV Table in Amazon Athena
-- ============================================================================
CREATE DATABASE IF NOT EXISTS taxidata;

CREATE EXTERNAL TABLE IF NOT EXISTS taxidata.yellow (
  `vendor` string,
  `pickup` timestamp,
  `dropoff` timestamp,
  `count` int,
  `distance` int,
  `ratecode` string,
  `storeflag` string,
  `pulocid` string,
  `dolocid` string,
  `paytype` string,
  `fare` decimal(10,2),
  `extra` decimal(10,2),
  `mta_tax` decimal(10,2),
  `tip` decimal(10,2),
  `tolls` decimal(10,2),
  `surcharge` decimal(10,2),
  `total` decimal(10,2)
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'
WITH SERDEPROPERTIES (
  'serialization.format' = ',',
  'field.delim' = ','
)
LOCATION 's3://aws-tc-largeobjects/CUR-TF-200-ACDSCI-1/Lab2/yellow/'
TBLPROPERTIES ('has_encrypted_data'='false');

-- ============================================================================
-- Task 2: Query Optimization via Bucketizing (High-Cardinality Pickup Dates)
-- ============================================================================
CREATE EXTERNAL TABLE IF NOT EXISTS taxidata.jan (
  `vendor` string,
  `pickup` timestamp,
  `dropoff` timestamp,
  `count` int,
  `distance` int,
  `ratecode` string,
  `storeflag` string,
  `pulocid` string,
  `dolocid` string,
  `paytype` string,
  `fare` decimal(10,2),
  `extra` decimal(10,2),
  `mta_tax` decimal(10,2),
  `tip` decimal(10,2),
  `tolls` decimal(10,2),
  `surcharge` decimal(10,2),
  `total` decimal(10,2)
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'
WITH SERDEPROPERTIES (
  'serialization.format' = ',',
  'field.delim' = ','
)
LOCATION 's3://aws-tc-largeobjects/CUR-TF-200-ACDSCI-1/Lab2/January2017/'
TBLPROPERTIES ('has_encrypted_data'='false');

-- Baseline full-year scan vs. January bucket scan
SELECT count(count) AS "Number of trips",
       sum(total) AS "Total fares",
       pickup AS "Trip date"
FROM taxidata.yellow
WHERE pickup BETWEEN TIMESTAMP '2017-01-01 00:00:00'
                 AND TIMESTAMP '2017-02-01 00:00:01'
GROUP BY pickup;

SELECT count(count) AS "Number of trips",
       sum(total) AS "Total fares",
       pickup AS "Trip date"
FROM taxidata.jan
GROUP BY pickup;

-- ============================================================================
-- Task 3: Query Optimization via Partitioning + Columnar Apache Parquet (CTAS)
-- ============================================================================
CREATE TABLE taxidata.creditcard
WITH (
  format = 'PARQUET',
  parquet_compression = 'SNAPPY',
  partitioned_by = ARRAY['paytype']
) AS
SELECT vendor, pickup, dropoff, count, distance, ratecode, storeflag,
       pulocid, dolocid, fare, extra, mta_tax, tip, tolls, surcharge, total, paytype
FROM taxidata.yellow
WHERE paytype = '1';

-- Compare unpartitioned CSV scan (9.32 GB) vs. partitioned Parquet scan (73.22 MB)
SELECT sum(total), paytype FROM taxidata.yellow WHERE paytype = '1' GROUP BY paytype;
SELECT sum(total), paytype FROM taxidata.creditcard WHERE paytype = '1' GROUP BY paytype;

-- ============================================================================
-- Task 4: Analytical Views for Downstream Consumers
-- ============================================================================
CREATE OR REPLACE VIEW taxidata.cctrips AS
SELECT sum(fare) AS "CreditCardFares"
FROM taxidata.yellow
WHERE paytype = '1';

CREATE OR REPLACE VIEW taxidata.cashtrips AS
SELECT sum(fare) AS "CashFares"
FROM taxidata.yellow
WHERE paytype = '2';

CREATE OR REPLACE VIEW taxidata.comparepay AS
WITH
  cc AS (
    SELECT sum(fare) AS cctotal, vendor
    FROM taxidata.yellow
    WHERE paytype = '1'
    GROUP BY paytype, vendor
  ),
  cs AS (
    SELECT sum(fare) AS cashtotal, vendor, paytype
    FROM taxidata.yellow
    WHERE paytype = '2'
    GROUP BY paytype, vendor
  )
SELECT cc.cctotal, cs.cashtotal
FROM cc
JOIN cs ON cc.vendor = cs.vendor;