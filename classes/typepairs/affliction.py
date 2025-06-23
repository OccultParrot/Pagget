import json


class Affliction:
    """Class representing an affliction with name, description, and rarity."""

    def __init__(self, name: str, description: str, rarity: str, is_minor: bool = False):
        self.name = name
        self.description = description
        self.rarity = rarity
        self.is_minor = is_minor

    def __str__(self):
        return f"{self.name.title()}"

    @classmethod
    def from_dict(cls, data: dict):
        """Create an Affliction instance from a dictionary."""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            rarity=data.get("rarity", ""),
            is_minor=data.get("is_minor", False)
        )


class AfflictionEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Affliction):
            return {
                "name": obj.name,
                "description": obj.description,
                "rarity": obj.rarity,
                "is_minor": obj.is_minor
            }
        return json.JSONEncoder.default(self, obj)
