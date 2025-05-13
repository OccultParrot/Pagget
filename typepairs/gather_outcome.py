import json


class GatherOutcome:
    """Class representing a hunt outcome with title, value, and description."""

    def __init__(self, value: int, description: str, rarity: str):
        self.value = value
        self.description = description
        self.rarity = rarity

    @classmethod
    def from_dict(cls, data: dict):
        """Create a HuntOutcome instance from a dictionary."""
        return cls(
            value=data.get("value", 0),
            description=data.get("description", ""),
            rarity=data.get("rarity", "")
        )


class GatherOutcomeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, GatherOutcome):
            return {
                "value": obj.value,
                "description": obj.description,
                "rarity": obj.rarity
            }
        return json.JSONEncoder.default(self, obj)
