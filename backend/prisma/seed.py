"""Seed the demo e-commerce database with realistic data.

Run once (after `prisma db push`) via:
    python -m prisma.seed

Deterministic (seeded RNG) so numbers are stable across runs.
Date ranges are dynamic — they always extend to today so the current
month always contains fresh data.

Uses sync psycopg with batched multi-row INSERTs for fast seeding over
high-latency connections (e.g. Neon pooler).
"""

from __future__ import annotations

import random
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from io import StringIO

import psycopg
from psycopg.rows import tuple_row

from multirag.config import get_settings

RNG = random.Random(42)
TODAY = date.today()

CUSTOMER_COUNT = 1500
ORDER_COUNT = 2000
MAX_ITEMS_PER_ORDER = 4
EMPLOYEE_COUNT = 50

COUNTRIES = ["US", "GB", "IN", "DE", "FR", "CA", "AU", "SG", "AE", "JP", "BR", "KR", "NL", "SE"]
CITIES = {
    "US": ["New York", "San Francisco", "Austin", "Seattle", "Chicago", "Denver", "Miami", "Boston"],
    "GB": ["London", "Manchester", "Bristol", "Edinburgh", "Birmingham"],
    "IN": ["Bengaluru", "Mumbai", "Delhi", "Pune", "Hyderabad", "Chennai"],
    "DE": ["Berlin", "Munich", "Hamburg", "Frankfurt"],
    "FR": ["Paris", "Lyon", "Marseille", "Toulouse"],
    "CA": ["Toronto", "Vancouver", "Montreal", "Calgary"],
    "AU": ["Sydney", "Melbourne", "Brisbane", "Perth"],
    "SG": ["Singapore"],
    "AE": ["Dubai", "Abu Dhabi"],
    "JP": ["Tokyo", "Osaka", "Yokohama"],
    "BR": ["São Paulo", "Rio de Janeiro", "Brasília"],
    "KR": ["Seoul", "Busan"],
    "NL": ["Amsterdam", "Rotterdam"],
    "SE": ["Stockholm", "Gothenburg"],
}
SEGMENTS = ["consumer", "consumer", "consumer", "sme", "sme", "enterprise"]

PRODUCT_CATALOG: list[tuple[str, str, float]] = [
    # (name, category, price)
    ("Aurora 27\" 4K Monitor", "electronics", 429.00),
    ("Nimbus Wireless Earbuds", "electronics", 129.00),
    ("Vertex Mechanical Keyboard", "electronics", 189.00),
    ("Halo Smart Speaker", "electronics", 79.00),
    ("Pulse Fitness Tracker", "electronics", 149.00),
    ("Orion Webcam 4K", "electronics", 99.00),
    ("Nova USB-C Hub", "electronics", 64.00),
    ("Eclipse Noise-Cancel Headphones", "electronics", 249.00),
    ("Terra Standing Desk", "home", 349.00),
    ("Comet Ergonomic Chair", "home", 279.00),
    ("Zen Air Purifier", "home", 199.00),
    ("Lumen Desk Lamp", "home", 59.00),
    ("Nomad Insulated Bottle", "home", 34.00),
    ("Drift Smart Thermostat", "home", 179.00),
    ("Cedar Bookshelf 5-Tier", "home", 159.00),
    ("Field Merino Tee", "apparel", 45.00),
    ("Range Hoodie", "apparel", 89.00),
    ("Trailhead Cap", "apparel", 24.00),
    ("Summit Trail Runners", "apparel", 129.00),
    ("Basalt Backpack 25L", "apparel", 119.00),
    ("Cirrus Rain Jacket", "apparel", 165.00),
    ("Peak Performance Shorts", "apparel", 55.00),
    ("Compendium: The Craft of Software", "books", 32.00),
    ("Everyday Systems", "books", 22.00),
    ("Distant Signals: A Novel", "books", 18.00),
    ("Cook, Slowly", "books", 27.00),
    ("Field Guide to Modern Design", "books", 39.00),
    ("Data-Driven Decisions", "books", 35.00),
    ("The Art of Simplicity", "books", 28.00),
    ("Amber Roast Coffee 1kg", "grocery", 18.00),
    ("Wildflower Honey 500g", "grocery", 12.00),
    ("Alpine Sparkling Water 12pk", "grocery", 15.00),
    ("Harvest Muesli 800g", "grocery", 9.50),
    ("Ember Dark Chocolate 100g", "grocery", 5.00),
    ("Matcha Green Tea 200g", "grocery", 22.00),
    ("Sunrise Granola Bars 8pk", "grocery", 8.50),
    ("Artisan Olive Oil 750ml", "grocery", 16.00),
]

WAREHOUSES = [
    ("Bay Area DC", "US", "Oakland"),
    ("London DC", "GB", "London"),
    ("Bengaluru DC", "IN", "Bengaluru"),
    ("Frankfurt DC", "DE", "Frankfurt"),
]

DEPARTMENTS_ROLES = {
    "sales": ["AE", "SDR", "Sales Manager", "RevOps Analyst"],
    "support": ["Support Agent", "Support Lead", "Solutions Engineer"],
    "engineering": ["Software Engineer", "Senior Engineer", "Engineering Manager", "SRE"],
    "ops": ["Warehouse Ops", "Ops Manager", "Logistics Coordinator"],
    "finance": ["Accountant", "Financial Analyst", "Finance Manager"],
}

ORDER_STATUSES_WEIGHTS = [
    ("delivered", 0.55),
    ("shipped", 0.15),
    ("paid", 0.10),
    ("pending", 0.05),
    ("cancelled", 0.05),
    ("refunded", 0.10),
]

TXN_METHODS_WEIGHTS = [
    ("card", 0.75),
    ("wallet", 0.15),
    ("bank_transfer", 0.07),
    ("cod", 0.03),
]

TXN_STATUS_WEIGHTS = [
    ("succeeded", 0.90),
    ("failed", 0.05),
    ("refunded", 0.04),
    ("chargeback", 0.01),
]

FIRST_NAMES = [
    "Ada", "Ravi", "Emma", "Wei", "Priya", "Marcus", "Sofia", "Jamal", "Yuki", "Leo",
    "Amir", "Chen", "Nia", "Aarav", "Elena", "Kofi", "Zara", "Diego", "Anna", "Kenji",
    "Isla", "Omar", "Grace", "Hiro", "Mira", "Rohit", "Zoe", "Yara", "Kai", "Farah",
    "Liam", "Noah", "Olivia", "Maya", "Ethan", "Aria", "Lucas", "Amara", "Soren", "Ines",
    "Tariq", "Leila", "Viktor", "Nadia", "Renzo", "Ananya", "Felix", "Sakura", "Andre", "Clara",
]
LAST_NAMES = [
    "Patel", "Chen", "Ahmed", "Kim", "Silva", "O'Neil", "Novak", "Cortez",
    "Yamamoto", "Adeyemi", "Vasquez", "Weber", "Kaur", "Rossi", "Dubois", "Ivanov",
    "Müller", "Park", "Santos", "Nguyen", "Fischer", "Tanaka", "Jensen", "Okafor",
    "Morales", "Schmidt", "Larsson", "Gupta", "Ali", "Fernandez", "Hoffman", "Nair",
]


def _weighted(choices: list[tuple[str, float]]) -> str:
    r = RNG.random()
    acc = 0.0
    for name, w in choices:
        acc += w
        if r <= acc:
            return name
    return choices[-1][0]


def _random_date_between(start: date, end: date) -> datetime:
    delta = (end - start).days
    day_offset = RNG.randint(0, max(delta - 1, 0))
    hour = RNG.randint(0, 23)
    minute = RNG.randint(0, 59)
    return datetime.combine(start + timedelta(days=day_offset), datetime.min.time()).replace(
        hour=hour, minute=minute
    )


def _copy_rows(cur: psycopg.Cursor, table: str, columns: list[str], rows: list[tuple]) -> None:
    """Bulk-load rows via COPY … FROM STDIN (fastest path over the wire)."""
    col_list = ", ".join(columns)
    buf = StringIO()
    for row in rows:
        line = "\t".join(_pg_escape(v) for v in row)
        buf.write(line + "\n")
    buf.seek(0)
    with cur.copy(f"COPY {table} ({col_list}) FROM STDIN") as copy:
        while chunk := buf.read(8192):
            copy.write(chunk.encode("utf-8"))


def _pg_escape(val: object) -> str:
    """Escape a Python value for COPY text format."""
    if val is None:
        return "\\N"
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, Decimal):
        return str(val)
    s = str(val)
    return s.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")


def seed() -> None:
    settings = get_settings()
    dsn = settings.database_url
    print(f"Seeding {dsn[:dsn.index('@') + 1]}…")

    with psycopg.connect(dsn) as conn:
        conn.autocommit = False
        with conn.cursor(row_factory=tuple_row) as cur:
            # ------- wipe -------
            cur.execute(
                "TRUNCATE transactions, order_items, orders, inventory, warehouses, "
                "products, employees, customers, docs RESTART IDENTITY CASCADE;"
            )
            print("  cleared existing rows")

            # ------- customers -------
            customer_rows: list[tuple] = []
            customer_ids: list[str] = []
            for i in range(CUSTOMER_COUNT):
                cid = f"cus_{i:04d}"
                first = RNG.choice(FIRST_NAMES)
                last = RNG.choice(LAST_NAMES)
                country = RNG.choice(COUNTRIES)
                city = RNG.choice(CITIES[country])
                seg = RNG.choice(SEGMENTS)
                created = _random_date_between(date(2023, 1, 1), TODAY)
                email = f"{first.lower()}.{last.lower().replace(chr(39), '')}.{i}@ex.com"
                customer_rows.append((cid, email, first, last, country, city, seg, created))
                customer_ids.append(cid)
            _copy_rows(cur, "customers",
                       ["id", "email", "first_name", "last_name", "country", "city", "segment", "created_at"],
                       customer_rows)
            print(f"  inserted {len(customer_ids)} customers")

            # ------- products -------
            product_rows: list[tuple] = []
            product_ids: list[str] = []
            for i, (name, cat, price) in enumerate(PRODUCT_CATALOG):
                pid = f"prd_{i:04d}"
                sku = f"SKU-{cat[:3].upper()}-{i:04d}"
                product_rows.append((pid, sku, name, cat, Decimal(str(price)), "USD", datetime(2023, 1, 1)))
                product_ids.append(pid)
            _copy_rows(cur, "products",
                       ["id", "sku", "name", "category", "price", "currency", "created_at"],
                       product_rows)
            print(f"  inserted {len(product_ids)} products")

            # ------- warehouses -------
            warehouse_rows: list[tuple] = []
            warehouse_ids: list[str] = []
            for i, (name, country, city) in enumerate(WAREHOUSES):
                wid = f"wh_{i:04d}"
                warehouse_rows.append((wid, name, country, city))
                warehouse_ids.append(wid)
            _copy_rows(cur, "warehouses", ["id", "name", "country", "city"], warehouse_rows)
            print(f"  inserted {len(warehouse_ids)} warehouses")

            # ------- inventory (product x warehouse) -------
            inv_rows: list[tuple] = []
            inv_count = 0
            for pid in product_ids:
                for wid in warehouse_ids:
                    qty = RNG.choice([0, 0, RNG.randint(1, 400)])
                    reorder = RNG.choice([15, 20, 25, 30])
                    inv_rows.append((f"inv_{inv_count:05d}", pid, wid, qty, reorder, datetime.now()))
                    inv_count += 1
            _copy_rows(cur, "inventory",
                       ["id", "product_id", "warehouse_id", "quantity_on_hand", "reorder_level", "updated_at"],
                       inv_rows)
            print(f"  inserted {inv_count} inventory rows")

            # ------- employees -------
            employee_rows: list[tuple] = []
            employee_ids: list[str] = []
            for i in range(EMPLOYEE_COUNT):
                eid = f"emp_{i:04d}"
                first = RNG.choice(FIRST_NAMES)
                last = RNG.choice(LAST_NAMES)
                dept = RNG.choice(list(DEPARTMENTS_ROLES.keys()))
                role = RNG.choice(DEPARTMENTS_ROLES[dept])
                hired = _random_date_between(date(2020, 1, 1), TODAY)
                salary = Decimal(str(RNG.randint(45000, 210000)))
                employee_rows.append((eid, first, last, dept, role, hired, salary, "USD"))
                employee_ids.append(eid)
            _copy_rows(cur, "employees",
                       ["id", "first_name", "last_name", "department", "role", "hired_at", "salary", "currency"],
                       employee_rows)
            print(f"  inserted {len(employee_ids)} employees")

            sales_employee_ids = [
                eid for eid in employee_ids
                if RNG.random() < 0.5
            ]

            # ------- orders + order_items + transactions -------
            order_rows: list[tuple] = []
            item_rows: list[tuple] = []
            txn_rows: list[tuple] = []
            item_count = 0
            txn_count = 0

            for i in range(ORDER_COUNT):
                oid = f"ord_{i:05d}"
                cid = RNG.choice(customer_ids)
                eid = RNG.choice(sales_employee_ids) if sales_employee_ids and RNG.random() < 0.85 else None
                status = _weighted(ORDER_STATUSES_WEIGHTS)
                created = _random_date_between(date(2024, 1, 1), TODAY)
                delivered = created + timedelta(days=RNG.randint(1, 10)) if status in ("delivered", "shipped") else None

                n_items = RNG.randint(1, MAX_ITEMS_PER_ORDER)
                chosen = RNG.sample(product_ids, k=n_items)
                total = Decimal("0.00")
                for pid in chosen:
                    qty = RNG.randint(1, 3)
                    idx = int(pid.split("_")[1])
                    unit_price = Decimal(str(PRODUCT_CATALOG[idx][2]))
                    item_rows.append((f"oi_{item_count:06d}", oid, pid, qty, unit_price))
                    item_count += 1
                    total += unit_price * qty

                order_rows.append((oid, cid, eid, status, total, "USD", created, delivered))

                if status not in ("cancelled",):
                    method = _weighted(TXN_METHODS_WEIGHTS)
                    tstatus = "refunded" if status == "refunded" else "succeeded"
                    if status != "refunded" and RNG.random() < 0.03:
                        tstatus = _weighted(TXN_STATUS_WEIGHTS)
                    processed = created + timedelta(minutes=RNG.randint(1, 90))
                    refunded_at = (
                        processed + timedelta(days=RNG.randint(1, 14))
                        if tstatus == "refunded"
                        else None
                    )
                    txn_rows.append((
                        f"txn_{txn_count:06d}", oid, method, tstatus,
                        total, "USD", processed, refunded_at,
                    ))
                    txn_count += 1

            _copy_rows(cur, "orders",
                       ["id", "customer_id", "employee_id", "status", "total", "currency", "created_at", "delivered_at"],
                       order_rows)
            _copy_rows(cur, "order_items",
                       ["id", "order_id", "product_id", "quantity", "unit_price"],
                       item_rows)
            _copy_rows(cur, "transactions",
                       ["id", "order_id", "method", "status", "amount", "currency", "processed_at", "refunded_at"],
                       txn_rows)
            print(f"  inserted {ORDER_COUNT} orders + {item_count} order_items + {txn_count} transactions")

            conn.commit()

    print("Seed complete.")


if __name__ == "__main__":
    seed()
