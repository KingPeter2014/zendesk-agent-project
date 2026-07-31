"""Generate synthetic customer records."""

from __future__ import annotations

import json
import random
from pathlib import Path

from faker import Faker

from memory.models import Customer

fake = Faker()
Faker.seed(42)
random.seed(42)

TIERS = ["standard", "standard", "standard", "premium", "premium", "vip"]


def generate_customer() -> Customer:
    tier = random.choice(TIERS)
    age_days = random.randint(30, 2000)
    total_orders = random.randint(1, 50 if tier == "vip" else 20)
    return Customer(
        name=fake.name(),
        email=fake.email(),
        tier=tier,
        account_age_days=age_days,
        total_orders=total_orders,
        lifetime_value=round(random.uniform(10, 5000 if tier == "vip" else 500), 2),
    )


def generate_customers(n: int = 200) -> list[Customer]:
    return [generate_customer() for _ in range(n)]


def save_customers(path: Path, n: int = 200) -> list[Customer]:
    customers = generate_customers(n)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump([c.model_dump(mode="json") for c in customers], f, indent=2)
    return customers


if __name__ == "__main__":
    out = Path(__file__).parent.parent / "data" / "customers.json"
    customers = save_customers(out)
    print(f"Generated {len(customers)} customers → {out}")
