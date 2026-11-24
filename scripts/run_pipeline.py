import os
import time
import duckdb

os.makedirs("data/curated/creditcard_parquet", exist_ok=True)
con = duckdb.connect("data/warehouse.duckdb")

# --- TASK 1: Create Database Schema & External CSV Tables ---
con.execute("CREATE SCHEMA IF NOT EXISTS taxidata;")
con.execute("USE taxidata;")

columns_ddl = """
    vendor VARCHAR,
    pickup TIMESTAMP,
    dropoff TIMESTAMP,
    count INTEGER,
    distance INTEGER,
    ratecode VARCHAR,
    storeflag VARCHAR,
    pulocid VARCHAR,
    dolocid VARCHAR,
    paytype VARCHAR,
    fare DECIMAL(10,2),
    extra DECIMAL(10,2),
    mta_tax DECIMAL(10,2),
    tip DECIMAL(10,2),
    tolls DECIMAL(10,2),
    surcharge DECIMAL(10,2),
    total DECIMAL(10,2)
"""

con.execute(f"""
    CREATE OR REPLACE VIEW yellow AS
    SELECT * FROM read_csv('data/raw/yellow/*.csv', header=false, columns={{
        'vendor': 'VARCHAR', 'pickup': 'TIMESTAMP', 'dropoff': 'TIMESTAMP',
        'count': 'INTEGER', 'distance': 'INTEGER', 'ratecode': 'VARCHAR',
        'storeflag': 'VARCHAR', 'pulocid': 'VARCHAR', 'dolocid': 'VARCHAR',
        'paytype': 'VARCHAR', 'fare': 'DECIMAL(10,2)', 'extra': 'DECIMAL(10,2)',
        'mta_tax': 'DECIMAL(10,2)', 'tip': 'DECIMAL(10,2)', 'tolls': 'DECIMAL(10,2)',
        'surcharge': 'DECIMAL(10,2)', 'total': 'DECIMAL(10,2)'
    }});
""")

con.execute("""
    CREATE OR REPLACE VIEW jan AS
    SELECT * FROM read_csv('data/raw/January2017/*.csv', header=false, columns={
        'vendor': 'VARCHAR', 'pickup': 'TIMESTAMP', 'dropoff': 'TIMESTAMP',
        'count': 'INTEGER', 'distance': 'INTEGER', 'ratecode': 'VARCHAR',
        'storeflag': 'VARCHAR', 'pulocid': 'VARCHAR', 'dolocid': 'VARCHAR',
        'paytype': 'VARCHAR', 'fare': 'DECIMAL(10,2)', 'extra': 'DECIMAL(10,2)',
        'mta_tax': 'DECIMAL(10,2)', 'tip': 'DECIMAL(10,2)', 'tolls': 'DECIMAL(10,2)',
        'surcharge': 'DECIMAL(10,2)', 'total': 'DECIMAL(10,2)'
    });
""")

# --- TASK 2: Bucketizing Optimization (Full Year vs January Bucket) ---
t0 = time.perf_counter()
con.execute("""
    SELECT count(count) AS "Number of trips", sum(total) AS "Total fares", pickup AS "Trip date"
    FROM yellow
    WHERE pickup BETWEEN TIMESTAMP '2017-01-01 00:00:00' AND TIMESTAMP '2017-02-01 00:00:01'
    GROUP BY pickup;
""").fetchall()
t_full_csv = (time.perf_counter() - t0) * 1000

t0 = time.perf_counter()
con.execute("""
    SELECT count(count) AS "Number of trips", sum(total) AS "Total fares", pickup AS "Trip date"
    FROM jan
    GROUP BY pickup;
""").fetchall()
t_jan_csv = (time.perf_counter() - t0) * 1000

# --- TASK 3: Partitioning + Columnar Parquet Conversion ---
con.execute("""
    COPY (SELECT * FROM yellow WHERE paytype = '1')
    TO 'data/curated/creditcard_parquet'
    (FORMAT PARQUET, PARTITION_BY (paytype), OVERWRITE_OR_IGNORE 1);
""")

t0 = time.perf_counter()
res_csv = con.execute("SELECT sum(total), paytype FROM yellow WHERE paytype = '1' GROUP BY paytype;").fetchone()
t_unpartitioned = (time.perf_counter() - t0) * 1000

t0 = time.perf_counter()
res_parquet = con.execute("""
    SELECT sum(total), paytype
    FROM read_parquet('data/curated/creditcard_parquet/**/*.parquet', hive_partitioning=true)
    WHERE paytype = '1'
    GROUP BY paytype;
""").fetchone()
t_partitioned = (time.perf_counter() - t0) * 1000

# --- TASK 4: Create & Query Analytical Views ---
con.execute("""
    CREATE OR REPLACE VIEW cctrips AS
    SELECT sum(fare) AS CreditCardFares FROM yellow WHERE paytype = '1';
""")
con.execute("""
    CREATE OR REPLACE VIEW cashtrips AS
    SELECT sum(fare) AS CashFares FROM yellow WHERE paytype = '2';
""")
con.execute("""
    CREATE OR REPLACE VIEW comparepay AS
    WITH
      cc AS (SELECT sum(fare) AS cctotal, vendor FROM yellow WHERE paytype = '1' GROUP BY paytype, vendor),
      cs AS (SELECT sum(fare) AS cashtotal, vendor FROM yellow WHERE paytype = '2' GROUP BY paytype, vendor)
    SELECT cc.vendor, cc.cctotal, cs.cashtotal
    FROM cc JOIN cs ON cc.vendor = cs.vendor
    ORDER BY cc.vendor;
""")

# --- TASK 5 Query Test: Fares Over $100 ---
high_fares = con.execute("""
    SELECT distance, paytype, fare, tip, tolls, surcharge, total
    FROM yellow
    WHERE total >= 100.0
    ORDER BY total DESC
    LIMIT 5;
""").fetchall()

# Print Results & Benchmarks
raw_size_mb = os.path.getsize("data/raw/yellow/yellow_tripdata_2017.csv") / (1024 * 1024)
parquet_size_mb = sum(
    os.path.getsize(os.path.join(dp, f))
    for dp, _, fn in os.walk("data/curated/creditcard_parquet")
    for f in fn
) / (1024 * 1024)

print("\n=== BENCHMARK RESULTS ===")
print(f"Raw CSV Size (Full 2017):        {raw_size_mb:.2f} MB")
print(f"Partitioned Parquet Size (CC):   {parquet_size_mb:.2f} MB")
print(f"Task 2 - Full CSV Scan:          {t_full_csv:.2f} ms vs Jan Bucket Scan: {t_jan_csv:.2f} ms")
print(f"Task 3 - Unpartitioned CSV:      {t_unpartitioned:.2f} ms vs Partitioned Parquet: {t_partitioned:.2f} ms")

print("\n=== TASK 4: comparepay VIEW OUTPUT ===")
for row in con.execute("SELECT * FROM comparepay").fetchall():
    print(f"Vendor {row[0]} -> Credit Card Total: ${row[1]:,.2f} | Cash Total: ${row[2]:,.2f}")

print("\n=== TASK 5: TOP 5 FARES >= $100 ===")
for r in high_fares:
    print(r)