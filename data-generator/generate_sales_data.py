"""
generate_sales_data.py

Generates sample daily store-sales CSV files for the HDFS storage
optimization project. Files are written locally under sample_data/,
mirroring the target HDFS partition structure:

    sample_data/<year>/<month>/<day>/<store_id>/sales_<store_id>_<date>.csv

Why not literally 500 stores x ~100 MB each:
    That's 50 GB, which proves nothing extra for this exercise and just
    burns disk/time. We generate a representative slice (5 stores x 3 days
    at ~5 MB each) to exercise the directory hierarchy and upload/replication
    steps, plus ONE deliberately oversized ~150 MB file. That file is the
    one that actually demonstrates the block-size decision: at the 128 MB
    default it would split into 2 blocks, at our chosen 256 MB block size
    it stays as 1 block -- visible directly in `hdfs fsck -files -blocks`.

Run:
    python generate_sales_data.py
"""

import csv
import os
import random
import uuid
from datetime import date, timedelta

from faker import Faker

fake = Faker()
random.seed(42)

OUTPUT_ROOT = "sample_data"
PRODUCT_CATEGORIES = ["Grocery", "Electronics", "Apparel", "Home", "Toys", "Pharmacy"]
PAYMENT_METHODS = ["credit_card", "debit_card", "cash", "upi", "gift_card"]

# Rough average bytes per CSV row for this schema -- used to hit an
# approximate target file size without checking size row-by-row.
AVG_ROW_BYTES = 130


def write_store_file(store_id: str, txn_date: date, target_mb: float) -> str:
    year, month, day = f"{txn_date.year:04d}", f"{txn_date.month:02d}", f"{txn_date.day:02d}"
    out_dir = os.path.join(OUTPUT_ROOT, year, month, day, store_id)
    os.makedirs(out_dir, exist_ok=True)

    filename = f"sales_{store_id}_{txn_date.isoformat()}.csv"
    out_path = os.path.join(out_dir, filename)

    num_rows = max(1000, int((target_mb * 1024 * 1024) / AVG_ROW_BYTES))

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "transaction_id", "store_id", "timestamp", "product_id",
            "product_category", "quantity", "unit_price", "total_amount",
            "payment_method", "customer_id",
        ])
        for _ in range(num_rows):
            quantity = random.randint(1, 5)
            unit_price = round(random.uniform(1.5, 250.0), 2)
            writer.writerow([
                str(uuid.uuid4()),
                store_id,
                fake.date_time_between(
                    start_date=txn_date, end_date=txn_date + timedelta(days=1)
                ).isoformat(),
                f"PROD-{random.randint(1000, 9999)}",
                random.choice(PRODUCT_CATEGORIES),
                quantity,
                unit_price,
                round(quantity * unit_price, 2),
                random.choice(PAYMENT_METHODS),
                f"CUST-{random.randint(10000, 99999)}",
            ])

    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    print(f"  {out_path}  ({size_mb:.1f} MB, {num_rows:,} rows)")
    return out_path


def main():
    stores = [f"STORE_{i:03d}" for i in range(1, 6)]              # 5 sample stores
    start_date = date(2026, 8, 1)
    days = [start_date + timedelta(days=i) for i in range(3)]     # 3 sample days

    print(f"Generating {len(stores)} stores x {len(days)} days at ~5 MB each...")
    for d in days:
        for store in stores:
            write_store_file(store, d, target_mb=5)

    print("\nGenerating one peak-day file (~150 MB) to test block sizing...")
    write_store_file("STORE_001", date(2026, 8, 3), target_mb=150)

    print("\nDone. Files are under ./sample_data/")


if __name__ == "__main__":
    main()
