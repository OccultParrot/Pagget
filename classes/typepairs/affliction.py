import json
from typing import Literal


class Affliction:
    """Class representing an affliction with name, description, and rarity."""

    def __init__(self, name: str, description: str, rarity: str, is_minor: bool = False, season: Literal["wet", "dry", None] = None):
        self.name = name
        self.description = description
        self.rarity = rarity
        self.is_minor = is_minor
        self.season = season

    def __str__(self):
        return f"{self.name.title()}"

    @classmethod
    def from_dict(cls, data: dict):
        """Create an Affliction instance from a dictionary."""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            rarity=data.get("rarity", ""),
            is_minor=data.get("is_minor", False),
            season=data.get("season", None),
        )


class AfflictionEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Affliction):
            return {
                "name": obj.name,
                "description": obj.description,
                "rarity": obj.rarity,
                "is_minor": obj.is_minor, 
                "season": obj.season,
            }
        return json.JSONEncoder.default(self, obj)
