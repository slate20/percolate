"""Shared start/duration/is_ready primitive.

Growing a plot and roasting a batch are mechanically the same shape: start a
clock, wait, become ready. Both compose their own independent instance of
this class rather than sharing state — the math is shared, the clocks never
are.

Elapsed time is used strictly as a boolean gate against `duration`. It must
never scale a bonus, yield, or quality outcome — waiting longer than
`duration` earns nothing extra.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class TimedProcess:
    started_at: float
    duration: float

    def elapsed(self, now: float) -> float:
        return max(0.0, now - self.started_at)

    def is_ready(self, now: float) -> bool:
        return self.elapsed(now) >= self.duration

    def progress(self, now: float) -> float:
        """Fraction complete, clamped to [0, 1]. For display purposes only."""
        if self.duration <= 0:
            return 1.0
        return min(1.0, self.elapsed(now) / self.duration)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> TimedProcess:
        return cls(started_at=data["started_at"], duration=data["duration"])
