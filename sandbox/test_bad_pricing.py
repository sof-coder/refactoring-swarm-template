import pytest

from bad_pricing import calculate_order_total


def test_regular_customer_no_coupon():
    items = [
        {"price": 30.0, "quantity": 1},
        {"price": 20.0, "quantity": 2},
    ]

    total = calculate_order_total(
        items=items,
        is_premium_customer=False,
        coupon_code=None,
    )

    # Base = 70
    # Shipping = 15
    # Tax = 19%
    assert total == 101.15


def test_premium_customer_discount():
    items = [
        {"price": 50.0, "quantity": 1},
        {"price": 50.0, "quantity": 1},
    ]

    total = calculate_order_total(
        items=items,
        is_premium_customer=True,
        coupon_code=None,
    )

    # Base = 100
    # Premium 10% => 90
    # Free shipping
    # Tax
    assert total == 107.1


def test_bulk_discount_applied():
    items = [
        {"price": 10.0, "quantity": 6},
        {"price": 5.0, "quantity": 5},
    ]

    total = calculate_order_total(
        items=items,
        is_premium_customer=False,
        coupon_code=None,
    )

    # Base = 85
    # Bulk discount 5% => 80.75
    # Shipping = 15
    # Tax
    assert total == 113.64


def test_welcome_coupon():
    items = [
        {"price": 60.0, "quantity": 1},
        {"price": 50.0, "quantity": 1},
    ]

    total = calculate_order_total(
        items=items,
        is_premium_customer=False,
        coupon_code="WELCOME10",
    )

    # Base = 110
    # Coupon 10% => 99
    # Free shipping
    # Tax
    assert total == 117.81


def test_free_shipping_coupon_only():
    items = [
        {"price": 40.0, "quantity": 1},
    ]

    total = calculate_order_total(
        items=items,
        is_premium_customer=False,
        coupon_code="FREESHIP",
    )

    # Base = 40
    # Free shipping via coupon
    # Tax
    assert total == 47.6


def test_combined_discounts():
    items = [
        {"price": 20.0, "quantity": 6},
        {"price": 10.0, "quantity": 6},
    ]

    total = calculate_order_total(
        items=items,
        is_premium_customer=True,
        coupon_code="WELCOME10",
    )

    # Base = 180
    # Premium 10% => 162
    # Bulk 5% => 153.9
    # Coupon 10% => 138.51
    # Free shipping
    # Tax
    assert total == 164.93