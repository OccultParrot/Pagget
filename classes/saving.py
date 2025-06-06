import json
import os
import threading
import time
from typing import List, Dict, Type, TypeVar

from classes.typepairs import *

# Type variable for generic loading
T = TypeVar('T')


class Data:
    # Data Directories
    _afflictions: dict[int, List[Affliction]]  # Afflictions, indexed by guild ID
    _configs: dict[int, GuildConfig]  # Guild configurations, indexed by guild ID
    _balances: dict[int, int]  # User balances, indexed by user ID
    _hunt_outcomes: dict[int, List[GatherOutcome]]  # Hunt outcomes, indexed by guild ID
    _steal_outcomes: dict[int, List[GatherOutcome]]  # Steal outcomes, indexed by guild ID

    # Autosave Thread Variables
    _autosave_thread: threading.Thread = None
    _autosave_running: bool = False  # Flag to control autosave thread
    autosave_interval: int = 1800  # Autosave interval in seconds (default: 1/2 hour)
    autosave_interval = 10  # TEMP: for testing purposes, remove later

    def __init__(self):
        pass

    # --- Methods for saving and loading --- #
    def load(self):
        self._configs = self._load_json("guild_configs.json", GuildConfig)
        self._afflictions = self._load_json("afflictions.json", List[Affliction])
        self._balances = self._load_json("balances.json", int)
        self._hunt_outcomes = self._load_json("hunt_outcomes.json", List[GatherOutcome])
        self._steal_outcomes = self._load_json("steal_outcomes.json", List[GatherOutcome])

    def save(self):
        """ Saves all data to JSON files. """
        print("Saving data...")
        self._save_json("guild_configs.json", self._configs)
        self._save_json("afflictions.json", self._afflictions)
        self._save_json("balances.json", self._balances)
        self._save_json("hunt_outcomes.json", self._hunt_outcomes)
        self._save_json("steal_outcomes.json", self._steal_outcomes)
        print("Data saved successfully.")

    @staticmethod
    def _save_json(directory_name: str, data: dict) -> None:
        print(data)

    @staticmethod
    def _load_json(file_name: str, value_type: Type[T]) -> Dict[int, T]:
        """ Loads data from JSON file in the specified directory and converts values to specified type. """
        file_path = os.path.join("data", file_name)

        if not os.path.exists(file_path):
            print(f"Directory '{file_path}' does not exist. Returning empty dictionary.")
            return {}

        with open(file_path, "r") as file:
            try:
                raw_data = json.load(file)
                print(f"Loaded data from {file_path}: {raw_data}")

                # Convert the raw data to the expected format
                typed_data: Dict[int, T] = {}

                for key, value in raw_data.items():
                    # Convert string keys to integers
                    int_key = int(key)

                    # Convert value to the specified type
                    if value_type == int:
                        typed_data[int_key] = value
                    elif hasattr(value_type, '__origin__') and value_type.__origin__ is list:
                        # Handle List types (e.g., List[Affliction], List[GatherOutcome])
                        list_item_type = value_type.__args__[0] if value_type.__args__ else dict
                        if isinstance(value, list):
                            typed_data[int_key] = [list_item_type(**item) if isinstance(item, dict) else item for item
                                                   in value]
                        else:
                            typed_data[int_key] = []
                    else:
                        # Handle single object types (e.g., GuildConfig)
                        if isinstance(value, dict):
                            typed_data[int_key] = value_type(**value)
                        else:
                            typed_data[int_key] = value_type(value)

                return typed_data

            except json.JSONDecodeError as e:
                print(f"Error loading JSON from {file_path}: {e}")
                return {}
            except (ValueError, TypeError) as e:
                print(f"Error converting data types from {file_path}: {e}")
                return {}

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

    def get_hunt_outcome_list(self, guild_id: int) -> List[GatherOutcome]:
        return self._hunt_outcomes[guild_id]

    def get_steal_outcome_list(self, guild_id: int) -> List[GatherOutcome]:
        return self._hunt_outcomes[guild_id]

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

    def append_hunt_outcome(self, guild_id: int, hunt_outcome: GatherOutcome) -> None:
        if self._hunt_outcomes[guild_id]:
            self._hunt_outcomes[guild_id].append(hunt_outcome)
        else:
            self._hunt_outcomes[guild_id] = [hunt_outcome]

    def append_steal_outcome(self, guild_id: int, steal_outcome: GatherOutcome) -> None:
        if self._steal_outcomes[guild_id]:
            self._steal_outcomes[guild_id].append(steal_outcome)
        else:
            self._steal_outcomes[guild_id] = [steal_outcome]

    # --- Methods for removing information from dictionaries --- #
    def remove_affliction(self, index) -> None:
        self._afflictions.pop(index)

    def remove_hunt_outcome(self, index) -> None:
        self._hunt_outcomes.pop(index)

    def remove_steal_outcome(self, index) -> None:
        self._steal_outcomes.pop(index)

    def get_user_balance(self, user_id: int) -> int:
        """ Returns the user's balance, or the guild default if not found. """
        pass

    # --- Methods for validating information --- #
    @staticmethod
    def _validate_directory(directory: str) -> bool:
        if not os.path.exists(directory):
            print(f"Directory '{directory}' does not exist. Attempting to create it.")
            try:
                os.makedirs(directory)
                return True
            except Exception as e:
                return False  # Return if directory creation fails
        return True
