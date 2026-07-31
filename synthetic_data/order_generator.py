"""Generate synthetic order records."""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker

from memory.models import Customer, Order

fake = Faker()
Faker.seed(42)
random.seed(42)

PRODUCTS = [
    "Wireless Headphones", "Laptop Stand", "USB-C Hub", "Mechanical Keyboard",
    "Monitor", "Webcam", "Desk Lamp", "Office Chair", "Mouse Pad", "Notebook",
    "Phone Case", "Tablet", "Smart Watch", "Portable Charger", "Cable Pack",
]

ORDER_STATUSES = ["delivered", "delivered", "delivered", "shipped", "processing", "returned", "refunded"]


def generate_orders(customers: list[Customer], orders_per_customer: tuple[int, int] = (1, 5)) -> list[Order]:
    orders: list[Order] = []
    base = datetime.utcnow()
    for customer in customers:
        n = random.randint(*orders_per_customer)
        for _ in range(n):
            days_ago = random.randint(1, 365)
            created = base - timedelta(days=days_ago)
            status = random.choice(ORDER_STATUSES)
            delivered = created + timedelta(days=random.randint(1, 7)) if status in ("delivered", "returned") else None
            orders.append(Order(
                customer_id=customer.customer_id,
                product_name=random.choice(PRODUCTS),
                amount=round(random.uniform(9.99, 499.99), 2),
                status=status,
                created_at=created,
                delivered_at=delivered,
            ))
    return orders


def save_orders(path: Path, customers: list[Customer]) -> list[Order]:
    orders = generate_orders(customers)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump([o.model_dump(mode="json") for o in orders], f, indent=2, default=str)
    return orders


if __name__ == "__main__":
    from synthetic_data.customer_generator import generate_customers
    customers = generate_customers(200)
    out = Path(__file__).parent.parent / "data" / "orders.json"
    orders = save_orders(out, customers)
    print(f"Generated {len(orders)} orders → {out}")
