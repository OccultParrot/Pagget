from enum import Enum
from dataclasses import dataclass


class Rarity(Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    LEGENDARY = "legendary"


class Season(Enum):
    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"
    WINTER = "winter"
    ANY = None


@dataclass
class Affliction:
    id: int
    server_id: int
    title: str
    description: str
    rarity: Rarity
    is_minor: bool = False
    is_birth_defect: bool = False
    seasons: list[Season] = Season.ANY


@dataclass
class Server:
    id: int
    name: str
    affliction_chance: float = 0.25
    minor_affliction_chance: float = 0.35
    starting_pay: int = 100
    minimum_bet: int = 100

@dataclass
class User:
    id: int
    server_id: int
    balance: int

@dataclass
class GatherOutcome:
    id: int
    server_id: int
    description: str
    rarity: Rarity
    is_robbery: bool = False
    value: int = 0
