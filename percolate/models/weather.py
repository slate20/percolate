"""Deterministic weather + day/night, derived purely from wall-clock time.

No persisted state: the same real timestamp always yields the same weather,
so nothing needs saving to state.json and offline time is handled for free.
Weather changes on the same four hour-of-day windows as the existing
cosmetic day/night tinting (percolate.widgets) — see config.TOD_BUCKETS.
"""

from __future__ import annotations

import random
import time

from percolate.config import TOD_BUCKETS

# Relative odds per weather state — tweak freely, they don't need to sum to
# any particular total (random.Random.choices normalizes them).
WEATHER_WEIGHTS: dict[str, int] = {"sun": 60, "rain": 30, "snow": 10}

# How much each weather state speeds up (>1.0) or slows down (<1.0) plant
# growth. Applied via effective_elapsed(), never by rescaling a plant's
# target duration (see TimedProcess's own "boolean gate only" invariant).
GROWTH_MULTIPLIERS: dict[str, float] = {"sun": 1.0, "rain": 1.25, "snow": 0.5}

_SECONDS_PER_DAY = 86400
_SECONDS_PER_HOUR = 3600


def _day_start(t: float) -> float:
    """Epoch timestamp for local midnight of the day containing `t`."""
    lt = time.localtime(t)
    return time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1))


def current_bucket(now: float) -> tuple[str, float, float]:
    """(bucket_name, start_epoch, end_epoch) of the TOD_BUCKETS window
    containing `now`. Handles the one window ("night") that spans midnight.
    """
    names = [name for name, _ in TOD_BUCKETS]
    start_hours = dict(TOD_BUCKETS)

    hour = time.localtime(now).tm_hour
    name = names[-1]
    for candidate, start_hour in TOD_BUCKETS:
        if hour >= start_hour:
            name = candidate

    start_hour = start_hours[name]
    start = _day_start(now) + start_hour * _SECONDS_PER_HOUR
    if start > now:
        start -= _SECONDS_PER_DAY

    next_name = names[(names.index(name) + 1) % len(names)]
    end_hour = start_hours[next_name]
    end = _day_start(start) + end_hour * _SECONDS_PER_HOUR
    if end_hour <= start_hour:
        end += _SECONDS_PER_DAY

    return name, start, end


def weather_for_bucket(bucket_start: float, bucket_name: str) -> str:
    """Deterministic weighted pick for one bucket occurrence — same
    (bucket_start, bucket_name) always yields the same weather.
    """
    seed = f"{time.strftime('%Y-%m-%d', time.localtime(bucket_start))}-{bucket_name}"
    rng = random.Random(seed)
    states, weights = zip(*WEATHER_WEIGHTS.items())
    return rng.choices(states, weights=weights, k=1)[0]


def current_weather(now: float | None = None) -> str:
    """ "sun" | "rain" | "snow" for the given (or current) moment."""
    now = time.time() if now is None else now
    name, start, _end = current_bucket(now)
    return weather_for_bucket(start, name)


def effective_elapsed(started_at: float, now: float) -> float:
    """Growth-time elapsed since `started_at`, weighted by whatever weather
    was active in each bucket along the way. Replaces raw `now - started_at`
    for plant growth only — TimedProcess itself is unaffected (roasting has
    no weather).
    """
    if now <= started_at:
        return 0.0

    total = 0.0
    cursor = started_at
    while cursor < now:
        name, _start, bucket_end = current_bucket(cursor)
        segment_end = min(now, bucket_end)
        weather = weather_for_bucket(_start, name)
        total += (segment_end - cursor) * GROWTH_MULTIPLIERS[weather]
        cursor = segment_end
    return total
