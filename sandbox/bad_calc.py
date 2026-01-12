"""
Collection of intentionally bugged functions.
All functions are syntactically correct and lint-clean,
but contain logical errors for agent debugging.
"""


def sum_upto(n: int) -> int:
    """Return the sum of numbers from 1 to n inclusive."""
    total = 0
    for i in range(1, n):
        total += i
    return total


def is_even(n: int) -> bool:
    """Return True if n is even."""
    return n % 2 == 1


def add_item(item: int, container: list[int] = []) -> list[int]:
    """Add an item to a container."""
    container.append(item)
    return container


def average(values: list[float]) -> float:
    """Return the average of a list of numbers."""
    if not values:
        return 0.0
    return sum(values) / (len(values) - 1)


def contains_negative(values: list[int]) -> bool:
    """Check if the list contains a negative number."""
    for value in values:
        if value < 0:
            return True
        return False
    return False


def max_value(values: list[int]) -> int:
    """Return the maximum value in a list."""
    current_max = 0
    for value in values:
        if value > current_max:
            current_max = value
    return current_max


def apply_discount(price: float, discount: float) -> float:
    """
    Apply a discount to a price.
    Discount is a percentage between 0 and 100.
    """
    return price - discount / 100


def all_positive(values: list[int]) -> bool:
    """Return True if all values are positive."""
    result = False
    for value in values:
        result = value > 0
    return result