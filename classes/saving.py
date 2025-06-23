import json
import os
import threading
import time
from json import JSONEncoder
from typing import List, Dict, Type, TypeVar

from classes.typepairs import *

# Type variable for generic loading
T = TypeVar('T')


class Data:
    # Data Directories
    _afflictions: dict[int, List[Affliction]]  # Afflictions, indexed by guild ID
    _configs: dict[int, GuildConfig]  # Guild configurations, indexed by guild ID
    balances: dict[int, int]  # User balances, indexed by user ID
    _hunt_outcomes: dict[int, List[GatherOutcome]]  # Hunt outcomes, indexed by guild ID
    _steal_outcomes: dict[int, List[GatherOutcome]]  # Steal outcomes, indexed by guild ID

    # Autosave Thread Variables
    _autosave_thread: threading.Thread = None
    _autosave_running: bool = False  # Flag to control autosave thread
    autosave_interval: int = 1800  # Autosave interval in seconds (default: 1/2 hour)

    def __init__(self):
        self._autosave_stop_event = threading.Event()
        pass

    # --- Methods for saving and loading --- #
    def load(self):
        self._configs = self._load_json("guild_configs.json", GuildConfig)
        self._afflictions = self._load_json("afflictions.json", List[Affliction])
        self.balances = self._load_json("balances.json", int)
        self._hunt_outcomes = self._load_json("hunt_outcomes.json", List[GatherOutcome])
        self._steal_outcomes = self._load_json("steal_outcomes.json", List[GatherOutcome])

    def save(self):
        """ Saves all data to JSON files. """
        print("Saving data...")
        self._save_json("guild_configs.json", self._configs, GuildConfigEncoder)
        self._save_json("afflictions.json", self._afflictions, AfflictionEncoder)
        self._save_json("balances.json", self.balances)
        self._save_json("hunt_outcomes.json", self._hunt_outcomes, GatherOutcomeEncoder)
        self._save_json("steal_outcomes.json", self._steal_outcomes, GatherOutcomeEncoder)
        print("Data saved successfully.")

    @staticmethod
    def _save_json(file_name: str, data: dict, cls: type[JSONEncoder] | None = None) -> None:
        """ Saves data to JSON file in the specified directory. """
        file_path = os.path.join("data", file_name)

        if not Data._validate_directory(os.path.dirname(file_path)):
            print(f"Failed to create directory for {file_path}. Data not saved.")
            return

        with open(file_path, "w") as file:
            try:
                json.dump(data, file, indent=4, cls=cls)
                # print(f"Data saved to {file_path}: {len(data)} entries.")
            except (IOError, TypeError) as e:
                print(f"Error saving JSON to {file_path}: {e}")

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
                print(f"Loaded data from {file_path}: {len(raw_data)} entries.")

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
            if self._autosave_stop_event.wait(self.autosave_interval):
                break  # Stop even was set, exit immediately

    def start_autosave_thread(self):
        """ Starts the autosave thread if not already running. """
        if self._autosave_running:
            print("Autosave thread is already running.")
            return
        print("Starting autosave thread...")
        self._autosave_stop_event.clear()  # Resetting stop event
        self._autosave_thread = threading.Thread(target=self._autosave, daemon=True)
        self._autosave_thread.start()

    def stop_autosave_thread(self):
        """ Stops the autosave thread if it is running. """
        if not self._autosave_running:
            print("Autosave thread is not running.")
            return
        self._autosave_running = False
        self._autosave_stop_event.set()  # Signal to stop autosave
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

    def get_user_balance(self, user_id: int) -> int:
        """ Returns the user's balance, or the guild default if not found. """
        return self.balances.get(user_id, 0)

    # --- Methods for editing information --- #
    def set_guild_config(self, guild_id: int, config: GuildConfig) -> bool:
        if guild_id in self._configs:
            self._configs[guild_id] = config
            return True
        else:
            print(f"Guild ID {guild_id} not found in configs.")
            return False

    def set_affliction_list(self, guild_id: int, afflictions: List[Affliction]) -> bool:
        if guild_id in self._afflictions:
            self._afflictions[guild_id] = afflictions
            return True
        else:
            print(f"Guild ID {guild_id} not found in afflictions.")
            return False

    def set_gather_outcome_list(self, guild_id: int, gather_outcomes: List[GatherOutcome]) -> bool:
        if guild_id in self._hunt_outcomes:
            self._hunt_outcomes[guild_id] = gather_outcomes
            return True
        else:
            print(f"Guild ID {guild_id} not found in hunt outcomes.")
            return False

    def set_user_balance(self, user_id: int, new_balance: int):
        self.balances[user_id] = new_balance

    # --- Methods for appending information to dictionaries --- #
    def append_affliction(self, guild_id: int, new_affliction: Affliction) -> None:
        if self._afflictions[guild_id]:
            self._afflictions[guild_id].append(new_affliction)
        else:
            self._afflictions[guild_id] = [new_affliction]

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

    # --- Methods for getting rarities and weights for rolling --- #
    def get_hunt_outcomes_and_weights(self, guild_id: int):
        return self._organise_rarities(self._hunt_outcomes[guild_id])

    def get_steal_outcomes_and_weights(self, guild_id: int):
        return self._organise_rarities(self._steal_outcomes[guild_id])

    def get_afflictions_and_weights(self, guild_id: int):
        return self._organise_rarities(self._afflictions[guild_id])

    def get_minor_afflictions_and_weights(self, guild_id: int):
        afflictions, _ = self._organise_rarities(self._afflictions[guild_id])
        return [afflictions[0]], [100]

    # ---------------------- Static methods ---------------------- #
    @staticmethod
    def _organise_rarities(collection: list[Affliction | GatherOutcome]):
        commons = [obj for obj in collection if obj.rarity.lower() == "common"]
        uncommons = [obj for obj in collection if obj.rarity.lower() == "uncommon"]
        rares = [obj for obj in collection if obj.rarity.lower() == "rare"]
        ultra_rares = [obj for obj in collection if obj.rarity.lower() == "ultra rare"]

        return [commons, uncommons, rares, ultra_rares], [60, 25, 10, 5]

    # --- Methods for validating data --- #
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
