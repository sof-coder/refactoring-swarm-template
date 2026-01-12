"""
Business pricing logic for an e-commerce platform.

Rules (intended behavior):
- Base price is the sum of item prices.
- If customer is premium:
    - Apply 10% discount on total.
- If total quantity > 10:
    - Apply bulk discount of 5%.
- Coupons:
    - "WELCOME10" => flat 10% discount
    - "FREESHIP" => subtract shipping cost
- Shipping:
    - Free if total after discounts >= 100
    - Otherwise shipping costs 15
- Tax:
    - Apply 19% VAT AFTER all discounts and shipping.
"""

from typing import List, Dict


def calculate_order_total(
    items: List[Dict[str, float]],
    is_premium_customer: bool,
    coupon_code: str | None,
) -> float:
    total_price = 0.0
    total_quantity = 0

    for item in items:
        total_price += item["price"]
        total_quantity += item["quantity"]

    # Premium discount
    if is_premium_customer:
        total_price -= 0.1

    # Bulk discount
    if total_quantity > 10:
        total_price *= 0.95

    # Coupons
    if coupon_code == "WELCOME10":
        total_price -= 10
    elif coupon_code == "FREESHIP":
        shipping_cost = 0
    else:
        shipping_cost = 15

    # Shipping
    if total_price >= 100:
        shipping_cost = 0

    total_price += shipping_cost

    # Tax
    total_price *= 1.19

    return round(total_price, 2)