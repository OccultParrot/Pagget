import threading
import time
from typing import List

from classes.typepairs import *


class Data:
    # Data Directories
    _afflictions: dict[int, List[Affliction]]
    _configs: dict[int, GuildConfig]
    _outcomes: dict[int, List[GatherOutcome]]
    
    # Autosave Thread Variables
    _autosave_thread: threading.Thread = None
    _autosave_running: bool = False  # Flag to control autosave thread
    autosave_interval: int = 3600  # Autosave interval in seconds (default: 1 hour)
    autosave_interval = 10 # TEMP: for testing purposes, remove later

    def __init__(self):
        pass

    # --- Methods for saving and loading --- #
    def load(self):
        pass

    def save(self):
        pass
    
    # --- Autosave thread methods --- #
    def _autosave(self):
        """ This method is run in a separate thread to autosave data periodically. """
        self._autosave_running = True
        
        while self._autosave_running:
            self.save()
            print("Autosave completed at", time.ctime())
            threading.Event().wait(self.autosave_interval)
    
    def start_autosave_thread(self):
        """ Starts the autosave thread if not already running. """
        if self._autosave_running:
            print("Autosave thread is already running.")
            return
        print("Starting autosave thread...")
        self._autosave_thread = threading.Thread(target=self._autosave, daemon=True)
        self._autosave_thread.start()
    
    def stop_autosave_thread(self):
        """ Stops the autosave thread if it is running. """
        if not self._autosave_running:
            print("Autosave thread is not running.")
            return
        self._autosave_running = False
        if self._autosave_thread is not None:
            self._autosave_thread.join()
            self._autosave_thread = None
        print("Autosave thread stopped.")

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
    def remove_affliction(self, index) -> None:
        self._afflictions.pop(index)

    def remove_outcome(self, index) -> None:
        self._outcomes.pop(index)

    def get_user_balance(self, user_id: int) -> int:
        """ Returns the user's balance, or the guild default if not found. """
        pass