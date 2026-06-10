"""Sponsor domain modeli — tarih aralıklı, soft-delete'li kampanya kaydı."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Sponsor:
    name: str
    url: str
    message: str
    active_from: datetime
    active_until: datetime
    is_active: bool = True
    id: Optional[int] = None
