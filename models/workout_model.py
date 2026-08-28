from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Union
from models.model_methods import estimate_cadence_from_power, _is_bike_sport, _optional_str

ZwoValue = Union[str, int, float, bool, None]
ZwoNode = Dict[str, Any]


@dataclass(frozen=True)
class Interval:
    duration: float
    power: Optional[float] = None
    power_low: Optional[float] = None
    power_high: Optional[float] = None
    cadence: Optional[float] = None
    cadence_low: Optional[float] = None
    cadence_high: Optional[float] = None
    type: Optional[str] = None

    def __post_init__(self):
        if (self.power is None or self.power == 0.0):
            if (self.power_low is not None and self.power_high is not None
                and self.power_low != 0.0 and self.power_high != 0.0):
                object.__setattr__(
                    self,
                    "power",
                    (self.power_low + self.power_high) / 2
                )
            elif self.power_low is not None and self.power_low != 0.0:
                object.__setattr__(
                    self,
                    "power",
                    self.power_low
                )
            elif self.power_high is not None and self.power_high != 0.0:
                object.__setattr__(
                    self,
                    "power",
                    self.power_high
                )
            else:
                object.__setattr__(
                    self,
                    "power",
                    0.6
                )

        if (self.cadence is None or self.cadence == 0.0):
            if (self.cadence_low is not None
                and self.cadence_high is not None
                and self.cadence_low != 0.0
                and self.cadence_high != 0.0):
                object.__setattr__(
                    self,
                    "cadence",
                    round((self.cadence_low + self.cadence_high) / 2)
                )
            elif self.cadence_low is not None and self.cadence_low != 0.0:
                object.__setattr__(
                    self,
                    "cadence",
                    self.cadence_low
                )
            elif self.cadence_high is not None and self.cadence_high != 0.0:
                object.__setattr__(
                    self,
                    "cadence",
                    self.cadence_high
                )
            else:
                object.__setattr__(
                    self,
                    "cadence",
                    estimate_cadence_from_power(self.power)
                )


@dataclass(frozen=True)
class Workout:
    name: Optional[str] = None
    author: Optional[str] = None
    sport_type: Optional[ZwoValue] = None
    tags: List[str] = field(default_factory=list)
    description: Optional[str] = None
    intervals: List[Interval] = field(default_factory=list)

    @property
    def total_duration(self) -> float:
        return sum(interval.duration for interval in self.intervals)

    @classmethod
    def from_dict(cls, data: dict) -> "Workout":
        if not isinstance(data, dict):
            raise ValueError("Workout data must be a dict")
        return cls(
            name=_optional_str(data.get("name")),
            author=_optional_str(data.get("author")),
            sport_type=_optional_str(data.get("sport_type_is_bike")),
            tags=list(data.get("tags", [])),
            description=_optional_str(data.get("description")),
            intervals=[Interval(**interval) for interval in data.get("intervals")],
        )

    def to_record(self) -> Dict[str, Any]:
            return {
                "name": self.name,
                "author": self.author,
                "sport_type_is_bike": _is_bike_sport(self.sport_type),
                "tags": self.tags,
                "description": self.description,
                "intervals": [asdict(interval) for interval in self.intervals],
            }