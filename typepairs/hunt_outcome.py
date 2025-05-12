import json


class HuntOutcome:
    """Class representing a hunt outcome with title, value, and description."""

    def __init__(self, title: str, value: str, description: str):
        self.title = title
        self.value = value
        self.description = description

    def __str__(self):
        return f"{self.title} - {self.value}"

    @classmethod
    def from_dict(cls, data: dict):
        """Create a HuntOutcome instance from a dictionary."""
        return cls(
            title=data.get("title", ""),
            value=data.get("value", ""),
            description=data.get("description", "")
        )


class HuntOutcomeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, HuntOutcome):
            return {
                "title": obj.title,
                "value": obj.value,
                "description": obj.description
            }
        return json.JSONEncoder.default(self, obj)
