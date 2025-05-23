import json


class GuildConfig:
    """Class representing a guild configuration with species and afflictions."""

    AFFLICTION_CHANCE = 25  # Default chance for afflictions

    def __init__(self, species: str, chance: int = AFFLICTION_CHANCE, minor_chance: int = AFFLICTION_CHANCE + 10, starting_pay = 100, minimum_bet: int = 100):
        self.species = species
        self.chance = chance
        self.minor_chance = minor_chance
        self.starting_pay = starting_pay
        self.minimum_bet = minimum_bet

    def __str__(self):
        return f"{self.species.title()} ({self.chance}%)"

    @classmethod
    def from_dict(cls, data: dict):
        """Create a GuildConfig instance from a dictionary."""
        return cls(
            species=data.get("species", ""),
            chance=data.get("chance", cls.AFFLICTION_CHANCE),
            minor_chance=data.get("minor_chance", cls.AFFLICTION_CHANCE + 10),
            starting_pay = data.get("starting_pay", 100),
            minimum_bet=data.get("minimum_bet", 100)
        )


class GuildConfigEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, GuildConfig):
            return {
                "species": obj.species,
                "chance": obj.chance,
                "minor_chance": obj.minor_chance,
                "starting_pay": obj.starting_pay,
                "minimum_bet": obj.minimum_bet,
            }
        return json.JSONEncoder.default(self, obj)
