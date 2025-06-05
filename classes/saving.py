from typing import List

from typepairs import Affliction, GatherOutcome, GuildConfig


class Data:
    # Data Directories
    _afflictions: dict[int, List[Affliction]]
    _configs: dict[int, GuildConfig]
    _outcomes: dict[int, List[GatherOutcome]]

    def __init__(self):
        pass

    # --- Methods for saving and loading --- #
    def load(self):
        pass

    def save(self):
        pass

    # --- Methods for getting information --- #
    def get_guild_config(self, guild_id: int) -> GuildConfig:
        return self._configs[guild_id]

    def get_affliction_list(self, guild_id: int) -> List[Affliction]:
        return self._afflictions[guild_id]

    def get_gather_outcome_list(self, guild_id: int) -> List[GatherOutcome]:
        return self._outcomes[guild_id]

    # --- Methods for editing information --- #
    def set_guild_config(self, guild_id: int, config: GuildConfig) -> bool:
        pass

    def set_affliction_list(self, guild_id: int, afflictions: List[Affliction]) -> bool:
        pass

    def set_gather_outcome_list(self, guild_id: int, gather_outcomes: List[GatherOutcome]) -> bool:
        pass

    # --- Methods for appending information to dictionaries --- #
    def append_affliction(self, guild_id: int, affliction: Affliction) -> None:
        if self._afflictions[guild_id]:
            self._afflictions[guild_id].append(affliction)
        else:
            self._afflictions[guild_id] = [affliction]

    def append_gather_outcome(self, guild_id: int, gather_outcome: GatherOutcome) -> None:
        if self._outcomes[guild_id]:
            self._outcomes[guild_id].append(gather_outcome)
        else:
            self._outcomes[guild_id] = [gather_outcome]

    # --- Methods for removing information from dictionaries --- #
    def remove_affliction(self, index):
        self._afflictions.pop(index)

    def remove_outcome(self, index):
        self._outcomes.pop(index)
