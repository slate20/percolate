"""Tests for percolate/models/weather.py — deterministic weather rolls and
the weighted growth-time integral used by Plot.is_ready/progress/remaining.
"""

from __future__ import annotations

from percolate.models import weather

# Arbitrary fixed epoch — not "now", so the test is stable across runs
# regardless of the real current date/weather roll.
_FIXED_EPOCH = 1_700_000_000.0


def test_weather_for_bucket_is_deterministic():
    first = weather.weather_for_bucket(_FIXED_EPOCH, "midday")
    second = weather.weather_for_bucket(_FIXED_EPOCH, "midday")
    assert first == second


def test_weather_for_bucket_returns_a_known_state():
    result = weather.weather_for_bucket(_FIXED_EPOCH, "midday")
    assert result in weather.GROWTH_MULTIPLIERS


def test_effective_elapsed_is_zero_when_now_is_before_started_at():
    assert weather.effective_elapsed(_FIXED_EPOCH + 1000, _FIXED_EPOCH) == 0.0


def test_effective_elapsed_scales_by_the_buckets_weather_multiplier():
    name, bucket_start, bucket_end = weather.current_bucket(_FIXED_EPOCH)
    now = min(bucket_start + 100, bucket_end)
    multiplier = weather.GROWTH_MULTIPLIERS[
        weather.weather_for_bucket(bucket_start, name)
    ]
    expected = (now - bucket_start) * multiplier

    assert weather.effective_elapsed(bucket_start, now) == expected


def test_effective_elapsed_sums_across_a_bucket_boundary():
    name, bucket_start, bucket_end = weather.current_bucket(_FIXED_EPOCH)
    now = bucket_end + 100
    next_name, next_start, _next_end = weather.current_bucket(bucket_end)
    first_segment = (bucket_end - bucket_start) * weather.GROWTH_MULTIPLIERS[
        weather.weather_for_bucket(bucket_start, name)
    ]
    second_segment = (
        100
        * weather.GROWTH_MULTIPLIERS[weather.weather_for_bucket(next_start, next_name)]
    )
    expected = first_segment + second_segment

    assert weather.effective_elapsed(bucket_start, now) == expected
