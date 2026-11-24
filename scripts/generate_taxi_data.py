import csv
import os
import random
from datetime import datetime, timedelta

os.makedirs("data/raw/yellow", exist_ok=True)
os.makedirs("data/raw/January2017", exist_ok=True)

random.seed(42)

VENDORS = ["1", "2"]  # 1 = Creative Mobile Technologies, 2 = VeriFone Inc.
PAYTYPES = ["1", "2", "3", "4", "5", "6"]  # 1 = Credit card, 2 = Cash, etc.
PAY_WEIGHTS = [0.67, 0.30, 0.01, 0.01, 0.005, 0.005]

def generate_rows(num_rows: int):
    start_date = datetime(2017, 1, 1, 0, 0, 0)
    all_rows = []
    jan_rows = []

    for _ in range(num_rows):
        vendor = random.choice(VENDORS)
        # Spread trips across all 365 days of 2017
        pickup = start_date + timedelta(
            days=random.randint(0, 364),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59),
        )
        duration_mins = random.randint(3, 55)
        dropoff = pickup + timedelta(minutes=duration_mins)
        passenger_count = random.choices([1, 2, 3, 4, 5], weights=[0.7, 0.15, 0.07, 0.05, 0.03])[0]
        distance = random.randint(1, 25)
        ratecode = "1"
        storeflag = "N"
        pulocid = str(random.randint(1, 263))
        dolocid = str(random.randint(1, 263))
        paytype = random.choices(PAYTYPES, weights=PAY_WEIGHTS)[0]

        fare = round(2.50 + distance * 2.50 + random.uniform(0, 8), 2)
        # Inject occasional high-value airport/long trips (>= $100) for Task 5 query
        if random.random() < 0.005:
            distance = random.randint(35, 65)
            fare = round(random.uniform(95.0, 160.0), 2)

        extra = random.choice([0.0, 0.5, 1.0])
        mta_tax = 0.50
        tip = round(fare * random.uniform(0.15, 0.25), 2) if paytype == "1" else 0.0
        tolls = random.choice([0.0, 0.0, 0.0, 5.76])
        surcharge = 0.30
        total = round(fare + extra + mta_tax + tip + tolls + surcharge, 2)

        row = [
            vendor,
            pickup.strftime("%Y-%m-%d %H:%M:%S"),
            dropoff.strftime("%Y-%m-%d %H:%M:%S"),
            passenger_count,
            distance,
            ratecode,
            storeflag,
            pulocid,
            dolocid,
            paytype,
            fare,
            extra,
            mta_tax,
            tip,
            tolls,
            surcharge,
            total,
        ]
        all_rows.append(row)
        if pickup.month == 1:
            jan_rows.append(row)

    return all_rows, jan_rows

if __name__ == "__main__":
    print("Generating 200,000 synthetic 2017 NYC Taxi trips...")
    all_rows, jan_rows = generate_rows(200_000)

    with open("data/raw/yellow/yellow_tripdata_2017.csv", "w", newline="") as f:
        csv.writer(f).writerows(all_rows)

    with open("data/raw/January2017/yellow_tripdata_2017-01.csv", "w", newline="") as f:
        csv.writer(f).writerows(jan_rows)

    print(f"Done! Full 2017 rows: {len(all_rows):,} | January 2017 rows: {len(jan_rows):,}")