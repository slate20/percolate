"""Individual plot state — wraps a TimedProcess for growing."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from percolate.models.timed_process import TimedProcess


@dataclass
class Plot:
    bean_id: str | None = None
    process: TimedProcess | None = None

    @property
    def is_empty(self) -> bool:
        return self.bean_id is None

    def plant(self, bean_id: str, growth_time: float, now: float) -> None:
        self.bean_id = bean_id
        self.process = TimedProcess(started_at=now, duration=growth_time)

    def is_ready(self, now: float) -> bool:
        return self.process is not None and self.process.is_ready(now)

    def progress(self, now: float) -> float:
        if self.process is None:
            return 0.0
        return self.process.progress(now)

    def harvest(self) -> str:
        """Clear the plot and return the harvested bean id."""
        if self.bean_id is None:
            raise ValueError("Cannot harvest an empty plot.")
        bean_id = self.bean_id
        self.bean_id = None
        self.process = None
        return bean_id

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Plot:
        process = data.get("process")
        return cls(
            bean_id=data.get("bean_id"),
            process=TimedProcess.from_dict(process) if process else None,
        )
