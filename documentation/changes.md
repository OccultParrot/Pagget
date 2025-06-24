# Changes

### 6/24/25

- Removed `/affliction roll-minor`
- Added Seasonal Afflictions
- Reworked Rolling for Afflictions:
  - `/affliction roll dino:[name] type:[general / minor / birth] season:[wet or dry]`
- Updated Edit and Add Affliction to reflect affliction rework
- Afflictions now hold the following information:
  - name: str
  - description: str
  - rarity: "common" | "uncommon" | "rare" | "ultra rare"
  - is_minor: boolean
  - is_birth_defect: boolean
  - season: "wet" | "dry" | null