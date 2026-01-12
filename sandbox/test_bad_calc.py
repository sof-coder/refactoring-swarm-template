import pytest

from bad_calc import (
    sum_upto,
    is_even,
    add_item,
    average,
    contains_negative,
    max_value,
    apply_discount,
    all_positive,
)


def test_sum_upto():
    assert sum_upto(5) == 15
    assert sum_upto(1) == 1


def test_is_even():
    assert is_even(2) is True
    assert is_even(3) is False


def test_add_item_independent_calls():
    first = add_item(1)
    second = add_item(2)

    # Each call should start with a fresh list
    assert first == [1]
    assert second == [2]


def test_average():
    assert average([2.0, 4.0, 6.0]) == 4.0
    assert average([]) == 0.0


def test_contains_negative():
    assert contains_negative([1, 2, -3, 4]) is True
    assert contains_negative([1, 2, 3]) is False


def test_max_value():
    assert max_value([1, 5, 3]) == 5
    assert max_value([-5, -2, -10]) == -2


def test_apply_discount():
    assert apply_discount(200.0, 10.0) == 180.0
    assert apply_discount(100.0, 0.0) == 100.0


def test_all_positive():
    assert all_positive([1, 2, 3]) is True
    assert all_positive([1, -2, 3]) is False