# models.py
from dataclasses import dataclass
from typing import Optional


@dataclass
class Taxi:
    id: int
    x: float
    y: float
    free: bool = True
    current_client_id: Optional[int] = None

    services: int = 0
    earnings: float = 0.0
    rating_sum: float = 0.0
    rating_count: int = 0

    @property
    def rating_avg(self) -> float:
        return (self.rating_sum / self.rating_count) if self.rating_count else 0.0

