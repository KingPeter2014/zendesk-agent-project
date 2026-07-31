"""Generate 1,000+ synthetic support tickets covering all categories."""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker

from memory.models import (
    Customer, Order, Ticket,
    TicketCategory, TicketPriority, TicketStatus,
)

fake = Faker()
Faker.seed(42)
random.seed(42)

# ---------------------------------------------------------------------------
# Template bodies per category
# ---------------------------------------------------------------------------

BILLING_TEMPLATES = [
    "I was charged ${amount} on {date} but I never received my order #{order_id}. Please refund immediately.",
    "There are two charges of ${amount} on my account for order #{order_id}. I need the duplicate removed.",
    "My invoice for order #{order_id} shows ${amount} but the website said ${discount_amount}. Can you honour the price?",
    "I cancelled my subscription last month but was still billed ${amount}. This is unacceptable.",
    "I returned order #{order_id} three weeks ago but still haven't received my ${amount} refund.",
    "The promo code SAVE20 was not applied to my order #{order_id}. I need a ${amount} credit.",
]

ORDER_TEMPLATES = [
    "My order #{order_id} was marked delivered but I never received it. Tracking says it was left at the door.",
    "I received the wrong item in order #{order_id}. I ordered a {product} but got something else entirely.",
    "Order #{order_id} arrived damaged. The {product} is broken and I need a replacement or refund.",
    "I placed order #{order_id} 10 days ago and it still hasn't shipped. What is the delay?",
    "I need to change the delivery address for order #{order_id} — it hasn't shipped yet.",
    "Can I add an item to order #{order_id} before it ships?",
]

POLICY_TEMPLATES = [
    "What is your return policy for electronics? I purchased a {product} 40 days ago.",
    "Do you offer price matching? I found the same {product} cheaper elsewhere.",
    "Is it possible to split payments across two cards for large orders?",
    "What is the warranty coverage for the {product} I purchased?",
    "How long does the refund process take once a return is accepted?",
    "Can I exchange an item for a different colour instead of a refund?",
]

VIP_TEMPLATES = [
    "As a VIP member I expect priority service. My order #{order_id} has been delayed for two weeks with no explanation.",
    "I have been a customer for {years} years and this is the worst experience I have had. Escalate immediately.",
    "My account shows VIP status but I wasn't given free shipping on order #{order_id}. Please fix and compensate.",
    "I need to speak with a senior manager about a series of billing errors on my account totalling ${amount}.",
]

OFF_TOPIC_TEMPLATES = [
    "Can you help me write a poem?",
    "What is the weather like in London today?",
    "Please give me the winning lottery numbers for this weekend.",
    "I need help with my taxes. Do you offer accounting services?",
    "Who is the CEO of your company? I want to send them a letter.",
]

CATEGORY_CONFIG: dict[TicketCategory, dict] = {
    TicketCategory.BILLING_DISPUTE: {
        "weight": 30,
        "templates": BILLING_TEMPLATES,
        "priorities": [TicketPriority.MEDIUM, TicketPriority.HIGH, TicketPriority.HIGH],
        "subjects": ["Billing issue", "Incorrect charge", "Refund not received", "Duplicate charge"],
    },
    TicketCategory.ORDER_ISSUE: {
        "weight": 30,
        "templates": ORDER_TEMPLATES,
        "priorities": [TicketPriority.LOW, TicketPriority.MEDIUM, TicketPriority.HIGH],
        "subjects": ["Order not delivered", "Wrong item received", "Damaged goods", "Order delayed"],
    },
    TicketCategory.POLICY_QUESTION: {
        "weight": 20,
        "templates": POLICY_TEMPLATES,
        "priorities": [TicketPriority.LOW, TicketPriority.LOW, TicketPriority.MEDIUM],
        "subjects": ["Return policy query", "Price match request", "Warranty question", "Payment options"],
    },
    TicketCategory.VIP_ESCALATION: {
        "weight": 10,
        "templates": VIP_TEMPLATES,
        "priorities": [TicketPriority.HIGH, TicketPriority.CRITICAL],
        "subjects": ["VIP complaint", "Urgent escalation", "Senior manager request"],
    },
    TicketCategory.OFF_TOPIC: {
        "weight": 10,
        "templates": OFF_TOPIC_TEMPLATES,
        "priorities": [TicketPriority.LOW],
        "subjects": ["General enquiry", "Unrelated request"],
    },
}


def _fill_template(template: str, customer: Customer, order: Order | None) -> str:
    subs: dict[str, str] = {
        "order_id": order.order_id[:8] if order else "N/A",
        "amount": f"{order.amount:.2f}" if order else "0.00",
        "discount_amount": f"{(order.amount * 0.8):.2f}" if order else "0.00",
        "product": order.product_name if order else "item",
        "date": (order.created_at.strftime("%d %b %Y") if order else fake.date()),
        "years": str(customer.account_age_days // 365 or 1),
    }
    result = template
    for k, v in subs.items():
        result = result.replace("{" + k + "}", v)
    return result


def generate_tickets(customers: list[Customer], orders: list[Order], n: int = 1000) -> list[Ticket]:
    order_by_customer: dict[str, list[Order]] = {}
    for o in orders:
        order_by_customer.setdefault(o.customer_id, []).append(o)

    categories = list(CATEGORY_CONFIG.keys())
    weights = [CATEGORY_CONFIG[c]["weight"] for c in categories]

    tickets: list[Ticket] = []
    base = datetime.utcnow()

    for _ in range(n):
        customer = random.choice(customers)
        cat = random.choices(categories, weights=weights, k=1)[0]
        cfg = CATEGORY_CONFIG[cat]

        customer_orders = order_by_customer.get(customer.customer_id, [])
        order = random.choice(customer_orders) if customer_orders else None

        template = random.choice(cfg["templates"])
        body = _fill_template(template, customer, order)
        subject = random.choice(cfg["subjects"])
        priority = random.choice(cfg["priorities"])

        days_ago = random.randint(0, 30)
        created = base - timedelta(days=days_ago, hours=random.randint(0, 23))

        tickets.append(Ticket(
            customer_id=customer.customer_id,
            order_id=order.order_id if order else None,
            category=cat,
            priority=priority,
            status=TicketStatus.OPEN,
            subject=subject,
            body=body,
            created_at=created,
        ))

    return tickets


def save_all(data_dir: Path, n_customers: int = 200, n_tickets: int = 1000) -> dict:
    from synthetic_data.customer_generator import generate_customers
    from synthetic_data.order_generator import generate_orders

    data_dir.mkdir(parents=True, exist_ok=True)

    customers = generate_customers(n_customers)
    orders = generate_orders(customers)
    tickets = generate_tickets(customers, orders, n_tickets)

    with open(data_dir / "customers.json", "w") as f:
        json.dump([c.model_dump(mode="json") for c in customers], f, indent=2, default=str)
    with open(data_dir / "orders.json", "w") as f:
        json.dump([o.model_dump(mode="json") for o in orders], f, indent=2, default=str)
    with open(data_dir / "tickets.json", "w") as f:
        json.dump([t.model_dump(mode="json") for t in tickets], f, indent=2, default=str)

    print(f"Generated {len(customers)} customers, {len(orders)} orders, {len(tickets)} tickets -> {data_dir}")
    return {"customers": customers, "orders": orders, "tickets": tickets}


if __name__ == "__main__":
    out = Path(__file__).parent.parent / "data"
    save_all(out)
