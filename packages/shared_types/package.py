from dataclasses import dataclass


@dataclass(frozen=True)
class Package:
    id: str
    title: str
    description: str
    amount_minor: int
    currency: str
    is_digital: bool
