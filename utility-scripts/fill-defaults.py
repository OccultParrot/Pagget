import json
from rich import print_json
from pathlib import Path

DEFAULTS_PATH = Path("../defaults")

highest = 0

for file in DEFAULTS_PATH.iterdir():
    if file.is_dir() or file.name not in "default-hunts.json default-steals.json".split():
        continue

    data = json.loads(file.read_text())

    for o in data:
        if o["description"] is None:
            o["description"] = "[MISSING DESCRIPTION]"
        if o.get("rarity", None) is None:
            o["rarity"] = "common"
        if o.get("is_robbery", None) is None:
            o["is_robbery"] = False
        if o.get("value", None) is None:
            o["value"] = 0

        if file.name == "default-steals.json":
            o["is_robbery"] = True

        value = abs(int(o.get("value", 0)))
        if value > 250:
            o["rarity"] = "uncommon"
        if value > 500:
            o["rarity"] = "rare"
        if value > 750:
            o["rarity"] = "legendary"

    with open(file, "w") as f:
        f.write(json.dumps(data, indent=2))

    print_json(data=data)
