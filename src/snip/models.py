from dataclasses import dataclass
from datetime import datetime


@dataclass
class Snippet:
    id: int | None
    code: str
    language: str
    description: str
    tags: list[str]
    created_at: datetime
