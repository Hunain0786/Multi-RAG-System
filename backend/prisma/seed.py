"""Seed the demo e-commerce database with realistic data.

Run once (after `prisma db push`) via:
    python -m prisma.seed

Deterministic (seeded RNG) so numbers are stable across runs.
"""

from __future__ import annotations

import asyncio
import random
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal

import psycopg
from psycopg.rows import tuple_row

from multirag.config import get_settings

# psycopg's async client refuses the default Windows ProactorEventLoop.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

RNG = random.Random(42)

# Lightweight seed profile for hosted DBs (Neon): keep row counts small so
# seeding completes quickly during development.
CUSTOMER_COUNT = 480
ORDER_COUNT = 500
MAX_ITEMS_PER_ORDER = 1

COUNTRIES = ["US", "GB", "IN", "DE", "FR", "CA", "AU", "SG", "AE", "JP"]
CITIES = {
    "US": ["New York", "San Francisco", "Austin", "Seattle"],
    "GB": ["London", "Manchester", "Bristol"],
    "IN": ["Bengaluru", "Mumbai", "Delhi", "Pune"],
    "DE": ["Berlin", "Munich"],
    "FR": ["Paris", "Lyon"],
    "CA": ["Toronto", "Vancouver"],
    "AU": ["Sydney", "Melbourne"],
    "SG": ["Singapore"],
    "AE": ["Dubai"],
    "JP": ["Tokyo"],
}
SEGMENTS = ["consumer", "consumer", "consumer", "sme", "sme", "enterprise"]

PRODUCT_CATALOG: list[tuple[str, str, float]] = [
    # (name, category, price)
    ("Aurora 27\" 4K Monitor", "electronics", 429.00),
    ("Nimbus Wireless Earbuds", "electronics", 129.00),
    ("Vertex Mechanical Keyboard", "electronics", 189.00),
    ("Halo Smart Speaker", "electronics", 79.00),
    ("Pulse Fitness Tracker", "electronics", 149.00),
    ("Terra Standing Desk", "home", 349.00),
    ("Comet Ergonomic Chair", "home", 279.00),
    ("Zen Air Purifier", "home", 199.00),
    ("Lumen Desk Lamp", "home", 59.00),
    ("Nomad Insulated Bottle", "home", 34.00),
    ("Field Merino Tee", "apparel", 45.00),
    ("Range Hoodie", "apparel", 89.00),
    ("Trailhead Cap", "apparel", 24.00),
    ("Summit Trail Runners", "apparel", 129.00),
    ("Basalt Backpack 25L", "apparel", 119.00),
    ("Compendium: The Craft of Software", "books", 32.00),
    ("Everyday Systems", "books", 22.00),
    ("Distant Signals: A Novel", "books", 18.00),
    ("Cook, Slowly", "books", 27.00),
    ("Field Guide to Modern Design", "books", 39.00),
    ("Amber Roast Coffee 1kg", "grocery", 18.00),
    ("Wildflower Honey 500g", "grocery", 12.00),
    ("Alpine Sparkling Water 12pk", "grocery", 15.00),
    ("Harvest Muesli 800g", "grocery", 9.50),
    ("Ember Dark Chocolate 100g", "grocery", 5.00),
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
]
LAST_NAMES = [
    "Patel", "Chen", "Ahmed", "Kim", "Silva", "O'Neil", "Novak", "Cortez",
    "Yamamoto", "Adeyemi", "Vasquez", "Weber", "Kaur", "Rossi", "Dubois", "Ivanov",
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


async def seed() -> None:
    settings = get_settings()
    print(f"Seeding {settings.database_url}...")

    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor(row_factory=tuple_row) as cur:
            # ------- wipe (dev only) -------
            await cur.execute(
                "TRUNCATE transactions, order_items, orders, inventory, warehouses, "
                "products, employees, customers, docs RESTART IDENTITY CASCADE;"
            )
            print("  cleared existing rows")

            # ------- customers -------
            customer_ids: list[str] = []
            for i in range(CUSTOMER_COUNT):
                cid = f"cus_{i:04d}"
                first = RNG.choice(FIRST_NAMES)
                last = RNG.choice(LAST_NAMES)
                country = RNG.choice(COUNTRIES)
                city = RNG.choice(CITIES[country])
                seg = RNG.choice(SEGMENTS)
                created = _random_date_between(date(2023, 1, 1), date(2026, 6, 1))
                await cur.execute(
                    "INSERT INTO customers (id, email, first_name, last_name, country, "
                    "city, segment, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s);",
                    (cid, f"{first.lower()}.{last.lower().replace(chr(39),'')}.{i}@ex.com",
                     first, last, country, city, seg, created),
                )
                customer_ids.append(cid)
            print(f"  inserted {len(customer_ids)} customers")

            # ------- products -------
            product_ids: list[str] = []
            for i, (name, cat, price) in enumerate(PRODUCT_CATALOG):
                pid = f"prd_{i:04d}"
                sku = f"SKU-{cat[:3].upper()}-{i:04d}"
                await cur.execute(
                    "INSERT INTO products (id, sku, name, category, price, currency, "
                    "created_at) VALUES (%s,%s,%s,%s,%s,%s,%s);",
                    (pid, sku, name, cat, Decimal(str(price)), "USD",
                     datetime(2023, 1, 1)),
                )
                product_ids.append(pid)
            print(f"  inserted {len(product_ids)} products")

            # ------- warehouses -------
            warehouse_ids: list[str] = []
            for i, (name, country, city) in enumerate(WAREHOUSES):
                wid = f"wh_{i:04d}"
                await cur.execute(
                    "INSERT INTO warehouses (id, name, country, city) VALUES (%s,%s,%s,%s);",
                    (wid, name, country, city),
                )
                warehouse_ids.append(wid)
            print(f"  inserted {len(warehouse_ids)} warehouses")

            # ------- inventory (product x warehouse) -------
            inv_count = 0
            for pid in product_ids:
                for wid in warehouse_ids:
                    qty = RNG.choice([0, 0, RNG.randint(1, 400)])
                    reorder = RNG.choice([15, 20, 25, 30])
                    await cur.execute(
                        "INSERT INTO inventory (id, product_id, warehouse_id, "
                        "quantity_on_hand, reorder_level, updated_at) "
                        "VALUES (%s,%s,%s,%s,%s,NOW());",
                        (f"inv_{inv_count:05d}", pid, wid, qty, reorder),
                    )
                    inv_count += 1
            print(f"  inserted {inv_count} inventory rows")

            # ------- employees -------
            employee_ids: list[str] = []
            for i in range(30):
                eid = f"emp_{i:04d}"
                first = RNG.choice(FIRST_NAMES)
                last = RNG.choice(LAST_NAMES)
                dept = RNG.choice(list(DEPARTMENTS_ROLES.keys()))
                role = RNG.choice(DEPARTMENTS_ROLES[dept])
                hired = _random_date_between(date(2020, 1, 1), date(2026, 5, 1))
                salary = Decimal(str(RNG.randint(45000, 210000)))
                await cur.execute(
                    "INSERT INTO employees (id, first_name, last_name, department, "
                    "role, hired_at, salary, currency) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s);",
                    (eid, first, last, dept, role, hired, salary, "USD"),
                )
                employee_ids.append(eid)
            print(f"  inserted {len(employee_ids)} employees")

            sales_employee_ids = [
                eid for eid in employee_ids
                if RNG.random() < 0.5  # ~half of employees are sales-attributable
            ]

            # ------- orders + order_items + transactions -------
            order_count = ORDER_COUNT
            item_count = 0
            txn_count = 0
            for i in range(order_count):
                oid = f"ord_{i:05d}"
                cid = RNG.choice(customer_ids)
                eid = RNG.choice(sales_employee_ids) if sales_employee_ids and RNG.random() < 0.85 else None
                status = _weighted(ORDER_STATUSES_WEIGHTS)
                created = _random_date_between(date(2024, 1, 1), date(2026, 5, 15))
                delivered = created + timedelta(days=RNG.randint(1, 10)) if status in ("delivered", "shipped") else None

                # Order lines
                # Keep downstream table sizes bounded (order_items/transactions)
                # so total rows stay manageable on hosted DBs.
                n_items = RNG.randint(1, MAX_ITEMS_PER_ORDER)
                chosen = RNG.sample(product_ids, k=n_items)
                total = Decimal("0.00")
                lines: list[tuple[str, str, int, Decimal]] = []
                for pid in chosen:
                    qty = RNG.randint(1, 3)
                    # lookup product price from PRODUCT_CATALOG order
                    idx = int(pid.split("_")[1])
                    unit_price = Decimal(str(PRODUCT_CATALOG[idx][2]))
                    lines.append((f"oi_{item_count:06d}", pid, qty, unit_price))
                    item_count += 1
                    total += unit_price * qty

                await cur.execute(
                    "INSERT INTO orders (id, customer_id, employee_id, status, total, "
                    "currency, created_at, delivered_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s);",
                    (oid, cid, eid, status, total, "USD", created, delivered),
                )
                for iid, pid, qty, unit_price in lines:
                    await cur.execute(
                        "INSERT INTO order_items (id, order_id, product_id, quantity, unit_price) "
                        "VALUES (%s,%s,%s,%s,%s);",
                        (iid, oid, pid, qty, unit_price),
                    )

                # At most one transaction per order (except cancelled).
                if status not in ("cancelled",):
                    method = _weighted(TXN_METHODS_WEIGHTS)
                    tstatus = "refunded" if status == "refunded" else "succeeded"
                    # Sprinkle in some failures for non-refunded orders.
                    if status != "refunded" and RNG.random() < 0.03:
                        tstatus = _weighted(TXN_STATUS_WEIGHTS)
                    processed = created + timedelta(minutes=RNG.randint(1, 90))
                    refunded_at = (
                        processed + timedelta(days=RNG.randint(1, 14))
                        if tstatus == "refunded"
                        else None
                    )
                    await cur.execute(
                        "INSERT INTO transactions (id, order_id, method, status, "
                        "amount, currency, processed_at, refunded_at) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s);",
                        (
                            f"txn_{txn_count:06d}",
                            oid,
                            method,
                            tstatus,
                            total,
                            "USD",
                            processed,
                            refunded_at,
                        ),
                    )
                    txn_count += 1

            print(f"  inserted {order_count} orders + {item_count} order_items + {txn_count} transactions")
            await conn.commit()

    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
