"""Unit tests for synthetic data generators."""

from __future__ import annotations

import pytest

from memory.models import TicketCategory
from synthetic_data.customer_generator import generate_customers
from synthetic_data.order_generator import generate_orders
from synthetic_data.ticket_generator import generate_tickets


class TestCustomerGenerator:
    def test_generates_correct_count(self):
        customers = generate_customers(10)
        assert len(customers) == 10

    def test_all_have_ids(self):
        customers = generate_customers(5)
        ids = {c.customer_id for c in customers}
        assert len(ids) == 5  # all unique

    def test_tiers_are_valid(self):
        customers = generate_customers(20)
        valid_tiers = {"standard", "premium", "vip"}
        assert all(c.tier in valid_tiers for c in customers)

    def test_email_present(self):
        customers = generate_customers(5)
        assert all("@" in c.email for c in customers)


class TestOrderGenerator:
    def test_generates_orders_for_customers(self):
        customers = generate_customers(5)
        orders = generate_orders(customers, orders_per_customer=(2, 2))
        assert len(orders) == 10  # 5 customers × 2 each

    def test_orders_linked_to_customers(self):
        customers = generate_customers(3)
        customer_ids = {c.customer_id for c in customers}
        orders = generate_orders(customers)
        assert all(o.customer_id in customer_ids for o in orders)

    def test_valid_statuses(self):
        customers = generate_customers(5)
        orders = generate_orders(customers)
        valid = {"delivered", "shipped", "processing", "returned", "refunded", "pending"}
        assert all(o.status in valid for o in orders)


class TestTicketGenerator:
    def test_generates_correct_count(self):
        customers = generate_customers(10)
        from synthetic_data.order_generator import generate_orders
        orders = generate_orders(customers)
        tickets = generate_tickets(customers, orders, n=50)
        assert len(tickets) == 50

    def test_all_categories_represented(self):
        customers = generate_customers(50)
        from synthetic_data.order_generator import generate_orders
        orders = generate_orders(customers)
        tickets = generate_tickets(customers, orders, n=500)
        categories = {t.category for t in tickets}
        assert TicketCategory.BILLING_DISPUTE in categories
        assert TicketCategory.POLICY_QUESTION in categories
        assert TicketCategory.OFF_TOPIC in categories

    def test_tickets_have_non_empty_bodies(self):
        customers = generate_customers(10)
        from synthetic_data.order_generator import generate_orders
        orders = generate_orders(customers)
        tickets = generate_tickets(customers, orders, n=20)
        assert all(len(t.body) > 10 for t in tickets)

    def test_ticket_customer_ids_match(self):
        customers = generate_customers(5)
        customer_ids = {c.customer_id for c in customers}
        from synthetic_data.order_generator import generate_orders
        orders = generate_orders(customers)
        tickets = generate_tickets(customers, orders, n=20)
        assert all(t.customer_id in customer_ids for t in tickets)
