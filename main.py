"""
TODO:
GAMBLING!!!

write blackjack, roulette, slots
"""

import os
import sys
import json
import random
import math
import requests
from json import JSONEncoder
from typing import List, Optional, Literal
import atexit

import discord
from discord import app_commands
import dotenv
from discord.ext.commands import CommandOnCooldown
from rich.console import Console

from logger import Logger
from permissions import has_admin_check
from typepairs import Affliction, AfflictionEncoder, GuildConfig, GuildConfigEncoder, GatherOutcome, \
    GatherOutcomeEncoder

# Constants
DATA_DIRECTORY = "data"
LOG_FILE = "log.txt"


async def read_error(interaction: List[discord.Interaction], error: app_commands.AppCommandError, logger: Logger):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction[0].response.send_message("You don't have permission to use this command.",
                                                   ephemeral=True)
    elif isinstance(error, app_commands.CommandOnCooldown):
        await interaction[0].response.send_message(error, ephemeral=True)
    else:
        logger.log(f"Error while processing command: {error}", "Bot")
        await interaction[0].response.send_message("An error occurred while rolling for afflictions",
                                                   ephemeral=True)


def get_paths(directory_name: str, guild_id: int) -> (str, str):
    return os.path.join(DATA_DIRECTORY, directory_name), os.path.join(DATA_DIRECTORY, directory_name,
                                                                      f"{guild_id}.json")


def get_rarity_color(rarity: str) -> discord.Color:
    """Get the color associated with a rarity."""
    if rarity.lower() == "common":
        return discord.Color.green()
    elif rarity.lower() == "uncommon":
        return discord.Color.blue()
    elif rarity.lower() == "rare":
        return discord.Color.purple()
    elif rarity.lower() == "ultra rare":
        return discord.Color.yellow()
    else:
        return discord.Color.default()


def get_outcome_color(value: int) -> discord.Color:
    if value < 0:
        return discord.Color.red()
    elif value == 0:
        return discord.Color.greyple()
    else:
        return discord.Color.green()


def get_affliction_embed(affliction: Affliction) -> discord.Embed:
    """Create a Discord embed for an affliction."""
    return discord.Embed(
        title=affliction.name.title(),
        description=f"-# {affliction.rarity.title()}\n{'-# *Minor Affliction*' if affliction.is_minor else ''}\n\n{affliction.description}",
        color=get_rarity_color(affliction.rarity)
    )


def get_outcome_embed(outcome: GatherOutcome, old_balance: int, new_balance: int,
                      interaction: discord.Interaction) -> discord.Embed:
    """Create a Discord embed for a hunt outcome."""
    embed = discord.Embed(
        title="Successful Hunt!" if outcome.value > 0 else "Failed Hunt!",
        description=outcome.description,
        color=get_outcome_color(outcome.value)
    )
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url)

    embed.set_footer(text=f"{new_balance} total berries")

    return embed


def validate_discord_token(token: str) -> bool:
    """ Validates a given Discord token """
    if not token:
        return False

    url = "https://discord.com/api/v10/users/@me"
    headers = {"Authorization": f"Bot {token}"}

    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return False

        data = response.json()
        print(f"Token is valid! Bot name: {data.get('username')}")
        return True
    except Exception as e:
        print("Error validating token:", e)
        return False


class AfflictionBot:
    """Main bot class to handle Discord interactions and affliction management."""

    afflictions_dict: dict[int, List[Affliction]]
    guild_configs: dict[int, GuildConfig]
    hunt_outcomes_dict: dict[int, List[GatherOutcome]]
    steal_outcomes_dict: dict[int, List[GatherOutcome]]
    balances_dict: dict[int, int]

    def __init__(self):
        """Initialize the bot with required configurations and load afflictions."""
        # Load environment variables
        dotenv.load_dotenv()

        # Setup console and logging
        self.console = Console()
        self.logger = Logger(LOG_FILE)

        self.rarity_list = [("rare", "sparkles"), ("ultra rare", "star2")]

        # Configure Discord client
        intents = discord.Intents(messages=True, guilds=True)
        intents.message_content = True
        self.client = discord.Client(intents=intents)
        self.tree = app_commands.CommandTree(self.client)

        # Register commands and events
        self._register_commands()
        self._register_events()

    def _load_json_afflictions(self, guild_id: int) -> List[Affliction]:
        """
        Load afflictions from a JSON file.
        
        :return: 
            A list of Affliction objects
        """

        affliction_directory, affliction_path = get_paths("afflictions", guild_id)

        affliction_path, valid = self._validate_json_load(affliction_directory, affliction_path,
                                                          "defaults/afflictions.default.json")
        if not valid:
            return []

        try:
            with open(affliction_path, 'r') as f:
                raw_data = json.load(f)

                afflictions: List[Affliction] = []
                for item in raw_data:
                    if not all(key in item for key in ["name", "description", "rarity"]):
                        self.console.print(f"[yellow]Warning: Skipping invalid affliction entry: {item}")
                        self.logger.log(f"Skipping invalid affliction entry: {item}", "Json")
                        continue

                    affliction: Affliction = Affliction.from_dict(item)
                    afflictions.append(affliction)

                self.console.print(f"[green]Loaded {len(afflictions)} afflictions from {affliction_path}")
                return afflictions

        except FileNotFoundError:
            self.console.print(f"[red bold]Error: {affliction_path} not found")
            self.logger.log(f"Error: {affliction_path} not found", "Json")
            return []  # Return empty list if file not found

        except json.JSONDecodeError:
            self.console.print(f"[red bold]Error: {affliction_path} is not a valid JSON file")
            self.logger.log(f"Error: {affliction_path} is not a valid JSON file", "Json")
            return []  # Return empty list instead of exiting

        except Exception as e:
            self.console.print(f"[red bold]Error loading afflictions: {e}")
            self.logger.log(f"Error loading afflictions: {e}", "Json")
            return []  # Return empty list instead of exiting

    def _load_json_configs(self, guild_id: int) -> GuildConfig:
        """ Loads the config for the guild from a JSON file """
        config_directory = os.path.join(DATA_DIRECTORY, "guild_configs")
        config_path = os.path.join(config_directory, f"{guild_id}.json")

        # Create directory if it doesn't exist
        if not self._validate_directory(config_directory):
            return GuildConfig("Parasaurolophus")  # Return default species if directory creation fails

        # Return default species if guild-specific file doesn't exist
        if not os.path.isfile(config_path):
            self.console.print(f"[yellow]Warning: {config_path} not found. Using default configs.")
            self.logger.log(f"{config_path} not found. Using default configs.", "Json")
            return GuildConfig("Parasaurolophus")

        try:
            with open(config_path, 'r') as f:
                raw_data = json.load(f)
                guild_config = GuildConfig.from_dict(raw_data)
                self.console.print(f"[green]Loaded configs from {config_path}")
                return guild_config

        except FileNotFoundError:
            self.console.print(f"[red bold]Error: {config_path} not found")
            self.logger.log(f"Error: {config_path} not found", "Json")
            return GuildConfig("Parasaurolophus")  # Return default species if file not found

    def _load_json_hunt_outcomes(self, guild_id: int) -> List[GatherOutcome]:
        """
        Load hunt outcomes from a JSON file.
        
        :return: 
            A list of HuntOutcome objects
        """
        outcome_directory, outcome_path = get_paths("hunt_outcomes", guild_id)
        outcome_path, valid = self._validate_json_load(outcome_directory, outcome_path,
                                                       "defaults/hunt_outcomes.default.json")
        if not valid:
            return []

        try:
            with open(outcome_path, 'r', encoding="utf-8") as f:
                raw_data = json.load(f)

                outcomes: List[GatherOutcome] = []
                for item in raw_data:
                    if not all(key in item for key in ["rarity", "value", "description"]):
                        self.console.print(f"[yellow]Warning: Skipping invalid outcome entry: {item}")
                        self.logger.log(f"Skipping invalid outcome entry: {item}", "Json")
                        continue

                    outcome: GatherOutcome = GatherOutcome.from_dict(item)
                    outcomes.append(outcome)

                self.console.print(f"[green]Loaded {len(outcomes)} outcomes from {outcome_path}")
                return outcomes

        except FileNotFoundError:
            self.console.print(f"[red bold]Error: {outcome_path} not found")
            self.logger.log(f"Error: {outcome_path} not found", "Json")
            return []  # Return empty list if file not found

    def _load_json_steal_outcomes(self, guild_id: int) -> List[GatherOutcome]:
        def _load_json_hunt_outcomes(self, guild_id: int) -> List[GatherOutcome]:
            """
            Load hunt outcomes from a JSON file.
            
            :return: 
                A list of HuntOutcome objects
            """

        outcome_directory, outcome_path = get_paths("steal_outcomes", guild_id)
        outcome_path, valid = self._validate_json_load(outcome_directory, outcome_path,
                                                       "defaults/steal_outcomes.default.json")
        if not valid:
            return []

        try:
            with open(outcome_path, 'r', encoding="utf-8") as f:
                raw_data = json.load(f)

                outcomes: List[GatherOutcome] = []
                for item in raw_data:
                    if not all(key in item for key in ["rarity", "value", "description"]):
                        self.console.print(f"[yellow]Warning: Skipping invalid outcome entry: {item}")
                        self.logger.log(f"Skipping invalid outcome entry: {item}", "Json")
                        continue

                    outcome: GatherOutcome = GatherOutcome.from_dict(item)
                    outcomes.append(outcome)

                self.console.print(f"[green]Loaded {len(outcomes)} outcomes from {outcome_path}")
                return outcomes

        except FileNotFoundError:
            self.console.print(f"[red bold]Error: {outcome_path} not found")
            self.logger.log(f"Error: {outcome_path} not found", "Json")
            return []  # Return empty list if file not found

    def _load_json_balances(self):
        """
        Loads everyone's balances from a JSON file.
        :return: 
            A dictionary of user IDs and their balances
        """
        balances_directory, balances_path = get_paths("balances", 0)
        balances_path, valid = self._validate_json_load(balances_directory, balances_path,
                                                        "defaults/balances.default.json")
        if not valid:
            return {}  # Return an empty dictionary

        try:
            with open(balances_path, 'r') as f:
                raw_data = json.load(f)

                # Ensure raw_data is a dictionary
                if not isinstance(raw_data, dict):
                    self.console.print("[yellow]Warning: Balances file is not in dictionary format. Converting...")
                    raw_data = {}

                return raw_data

        except FileNotFoundError:
            self.console.print(f"[red bold]Error: {balances_path} not found")
            self.logger.log(f"Error: {balances_path} not found", "Json")
            return {}

    def _save_json(self, guild_id: int, directory_name: str, data: any, cls: JSONEncoder | None = None) -> None:
        directory, path = get_paths(directory_name, guild_id)

        if not self._validate_directory(directory):
            return

        try:
            with open(path, 'w') as f:
                json.dump(data, f, cls=cls, indent=4)

        except Exception as e:
            self.console.print(f"[red bold]Error saving {directory_name}: {e}")
            self.logger.log(f"Error saving {directory_name}: {e}", "Json")
            return

    def _register_commands(self):
        """Register all Discord slash commands."""

        # region Affliction Commands
        @self.tree.command(name="roll-affliction", description="Rolls for standard afflictions affecting your dinosaur")
        @app_commands.describe(dino="Your dinosaur's name")
        @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)  # Uncomment to enable cooldown
        async def roll_affliction(interaction: discord.Interaction, dino: str):
            try:
                afflictions: List[Affliction] = self._roll_for_afflictions(interaction.guild_id, is_minor=False)

                dino = dino.capitalize()

                if not afflictions:
                    await interaction.response.send_message(f"{dino} has **no** afflictions")
                    return

                if len(afflictions) == 1:
                    await interaction.response.send_message(
                        f"{dino} has **{afflictions[0].name}**.",
                        embed=get_affliction_embed(afflictions[0])
                    )
                    return

                await interaction.response.send_message(f"{dino} has the following afflictions:",
                                                        embeds=[get_affliction_embed(affliction) for affliction in
                                                                afflictions])

            except CommandOnCooldown as e:
                self.logger.log(f"Command on cooldown")
                await interaction.response.send_message(e, ephemeral=True)

            except Exception as e:
                self.logger.log(f"Error in roll_affliction: {e}", "Bot")
                await interaction.response.send_message("An error occurred while rolling for afflictions",
                                                        ephemeral=True)

        @self.tree.command(name="roll-minor-affliction",
                           description="Rolls for minor afflictions affecting your dinosaur")
        @app_commands.describe(dino="Your dinosaur's name")
        @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)  # Uncomment to enable cooldown
        async def roll_minor_affliction(interaction: discord.Interaction, dino: str):
            try:
                afflictions: List[Affliction] = self._roll_for_afflictions(interaction.guild_id, is_minor=True)

                dino = dino.capitalize()

                if not afflictions:
                    await interaction.response.send_message(f"{dino} has **no** minor afflictions")
                    return

                if len(afflictions) == 1:
                    await interaction.response.send_message(
                        f"{dino} has **{afflictions[0].name}**.",
                        embed=get_affliction_embed(afflictions[0]))
                    return

                await interaction.response.send_message(f"{dino} has the following minor afflictions:",
                                                        embeds=[get_affliction_embed(affliction) for affliction in
                                                                afflictions])

            except Exception as e:
                self.logger.log(f"Error in roll_minor_affliction: {e}", "Bot")
                await interaction.response.send_message("An error occurred while rolling for minor afflictions",
                                                        ephemeral=True)

        @self.tree.command(name="list-afflictions", description="Lists all available afflictions")
        @app_commands.describe(page="What page to display")
        async def list_afflictions(interaction: discord.Interaction, page: int = 1):
            try:
                common = sorted(
                    [a for a in self.afflictions_dict[interaction.guild_id] if a.rarity.lower() == "common"],
                    key=lambda a: a.name.lower())

                uncommon = sorted(
                    [a for a in self.afflictions_dict[interaction.guild_id] if a.rarity.lower() == "uncommon"],
                    key=lambda a: a.name.lower())

                rare = sorted([a for a in self.afflictions_dict[interaction.guild_id] if a.rarity.lower() == "rare"],
                              key=lambda a: a.name.lower())

                ultra_rare = sorted(
                    [a for a in self.afflictions_dict[interaction.guild_id] if a.rarity.lower() == "ultra rare"],
                    key=lambda a: a.name.lower())

                sorted_afflictions = common + uncommon + rare + ultra_rare

                length = len(sorted_afflictions)

                pages = math.ceil(length / 10)

                if page < 1 or page > pages:
                    await interaction.response.send_message(
                        f"Page {page} does not exist. There are only {pages} pages.")
                    return

                start = (page - 1) * 10
                end = start + 10
                sorted_afflictions = sorted_afflictions[start:end]

                # Create embeds for each affliction
                embeds = [get_affliction_embed(affliction) for affliction in sorted_afflictions]

                # Add page number to the last embed's footer
                if embeds:
                    embeds[-1].set_footer(text=f"Page {page}/{pages}")

                await interaction.response.send_message(f"**Available Afflictions:** (Page {page}/{pages})",
                                                        embeds=embeds)
                self.logger.log(f"{interaction.user.name} listed all afflictions", "Bot")

            except Exception as e:
                self.logger.log(f"Error in list_afflictions: {e}", "Bot")
                await interaction.response.send_message("An error occurred while listing afflictions", ephemeral=True)

        # endregion

        # region Admin Commands

        ## Affliction Admin Commands
        @self.tree.command(
            name="add-affliction",
            description="Adds an affliction to the list")
        @app_commands.describe(
            name="Name of the affliction",
            description="Description of the affliction",
            rarity="Rarity of the affliction",
            is_minor="Whether the affliction is minor or not. ONLY AFFECTS COMMON RARITY"
        )
        @app_commands.choices(
            rarity=[
                app_commands.Choice(name="Common", value="common"),
                app_commands.Choice(name="Uncommon", value="uncommon"),
                app_commands.Choice(name="Rare", value="rare"),
                app_commands.Choice(name="Ultra Rare", value="ultra rare")
            ]
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def add_affliction(interaction: discord.Interaction, name: str, description: str,
                                 rarity: app_commands.Choice[str], is_minor: bool = False):
            try:
                # Check if the affliction already exists
                if self._if_affliction_exists(name, interaction.guild_id):
                    await interaction.response.send_message(f"Affliction '{name}' already exists.", ephemeral=True)
                    return

                new_affliction = Affliction(name=name, description=description, rarity=rarity.value, is_minor=is_minor)
                self.afflictions_dict[interaction.guild_id].append(new_affliction)
                self._save_json(interaction.guild_id, "afflictions", self.afflictions_dict[interaction.guild_id],
                                cls=AfflictionEncoder)

                await interaction.response.send_message(f"Affliction '{name}' added successfully.",
                                                        embed=get_affliction_embed(new_affliction), ephemeral=True)
                self.logger.log(f"{interaction.user.name} added affliction {name}", "Bot")

            except Exception as e:
                self.logger.log(f"Error in add_affliction: {e}", "Bot")
                await interaction.response.send_message("An error occurred while adding the affliction", ephemeral=True)

        @self.tree.command(name="remove-affliction", description="Removes an affliction from the list")
        @app_commands.describe(name="Name of the affliction")
        @app_commands.checks.has_permissions(administrator=True)
        async def remove_affliction(interaction: discord.Interaction, name: str):
            try:
                # Check if the affliction does not exist
                if not self._if_affliction_exists(name, interaction.guild_id):
                    await interaction.response.send_message(f"Affliction '{name}' does not exist.", ephemeral=True)
                    return

                affliction_to_remove = self._get_affliction_from_name(name, interaction.guild_id)[0]
                self.afflictions_dict[interaction.guild_id].remove(affliction_to_remove)
                self._save_json(interaction.guild_id, "afflictions", self.afflictions_dict[interaction.guild_id],
                                cls=AfflictionEncoder)

                embed = get_affliction_embed(affliction_to_remove)
                embed.set_footer(text="Affliction removed")

                await interaction.response.send_message(f"Affliction '{name}' removed successfully.", embed=embed,
                                                        ephemeral=True)
                self.logger.log(f"{interaction.user.name} removed affliction {name}", "Bot")

            except Exception as e:
                self.logger.log(f"Error in remove_affliction: {e}", "Bot")
                await interaction.response.send_message("An error occurred while removing the affliction",
                                                        ephemeral=True)

        @self.tree.command(name="edit-affliction", description="Edits an affliction from the list")
        @app_commands.describe(affliction="Current name of the affliction",
                               name="New name for the affliction",
                               description="New description of the affliction",
                               rarity="New rarity of the affliction",
                               is_minor="Whether the affliction is minor or not. ONLY AFFECTS COMMON RARITY")
        @app_commands.choices(
            rarity=[
                app_commands.Choice(name="Common", value="common"),
                app_commands.Choice(name="Uncommon", value="uncommon"),
                app_commands.Choice(name="Rare", value="rare"),
                app_commands.Choice(name="Ultra Rare", value="ultra rare")
            ]
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def edit_affliction(interaction: discord.Interaction, affliction: str, name: str = None,
                                  description: str = None, rarity: app_commands.Choice[str] = None,
                                  is_minor: bool = False):
            try:
                # Check if the affliction exists
                if not self._if_affliction_exists(affliction, interaction.guild_id):
                    await interaction.response.send_message(f"Affliction '{affliction}' does not exist.",
                                                            ephemeral=True)
                    return

                # Check if the new name already exists (if name is being changed)
                if name and name != affliction and self._if_affliction_exists(name, interaction.guild_id):
                    await interaction.response.send_message(f"Affliction with name '{name}' already exists.",
                                                            ephemeral=True)
                    return

                affliction_to_edit, index = self._get_affliction_from_name(affliction, interaction.guild_id)

                if name:
                    affliction_to_edit.name = name
                if description:
                    affliction_to_edit.description = description
                if rarity:
                    affliction_to_edit.rarity = rarity.value
                if is_minor:
                    affliction_to_edit.is_minor = is_minor

                self.afflictions_dict[interaction.guild_id][index] = affliction_to_edit
                self._save_json(interaction.guild_id, "afflictions", self.afflictions_dict[interaction.guild_id],
                                cls=AfflictionEncoder)

                await interaction.response.send_message(f"Affliction '{affliction}' edited successfully.",
                                                        embed=get_affliction_embed(affliction_to_edit),
                                                        ephemeral=True)
                self.logger.log(f"{interaction.user.name} edited affliction {affliction}", "Bot")

            except Exception as e:
                self.logger.log(f"Error in edit_affliction: {e}", "Bot")
                await interaction.response.send_message("An error occurred while editing the affliction",
                                                        ephemeral=True)

        @self.tree.command(name="set-configs",
                           description="Sets the guild configuration. Dont enter any changes to view the current configuration")
        @app_commands.describe(species="Species of the dinosaur",
                               chance="Percent chance of rolling afflictions (0-100)",
                               minor_chance="Percent chance of rolling minor afflictions (0-100)")
        @app_commands.checks.has_permissions(administrator=True)
        async def set_configs(interaction: discord.Interaction, species: str = None, chance: int = None,
                              minor_chance: bool = None, starting_pay: int = None):
            try:
                if species is not None:
                    self.guild_configs[interaction.guild_id].species = species
                if chance is not None:
                    self.guild_configs[interaction.guild_id].chance = chance
                if minor_chance is not None:
                    self.guild_configs[interaction.guild_id].minor_chance = minor_chance
                if starting_pay is not None:
                    self.guild_configs[interaction.guild_id].starting_pay = starting_pay

                embed = discord.Embed(title=f"{interaction.guild.name}'s Configuration",
                                      description="Guild configuration has been updated.")
                embed.add_field(name="Species", value=self.guild_configs[interaction.guild_id].species, inline=False)
                embed.add_field(name="Affliction Chance", value=f"{self.guild_configs[interaction.guild_id].chance}%",
                                inline=False)
                embed.add_field(name="Minor Affliction Chance",
                                value=f"{self.guild_configs[interaction.guild_id].minor_chance}%", inline=False)
                embed.add_field(name="Starting Pay", value=f"{self.guild_configs[interaction.guild_id].starting_pay}",
                                inline=False)

                self._save_json(interaction.guild_id, "guild_configs", self.guild_configs[interaction.guild_id],
                                cls=GuildConfigEncoder)

                await interaction.response.send_message(f"Guild configuration updated.", embed=embed, ephemeral=True)
                self.logger.log(f"{interaction.user.name} updated guild configuration for guild {interaction.guild_id}",
                                "Bot")

            except Exception as e:
                self.logger.log(f"Error in set_configs: {e}", "Bot")
                await interaction.response.send_message("An error occurred while setting the guild configuration",
                                                        ephemeral=True)

        # endregion

        # region Error Handling
        @roll_affliction.error
        async def roll_affliction_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            await read_error([interaction], error, self.logger)

        @roll_minor_affliction.error
        async def roll_minor_affliction_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            await read_error([interaction], error, self.logger)

        @list_afflictions.error
        async def list_afflictions_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            await read_error([interaction], error, self.logger)

        @add_affliction.error
        async def add_affliction_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            await read_error([interaction], error, self.logger)

        @remove_affliction.error
        async def remove_affliction_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            await read_error([interaction], error, self.logger)

        @set_configs.error
        async def set_configs_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            await read_error([interaction], error, self.logger)

        # endregion

        # Add the berry commands to the command tree
        self.tree.add_command(self._register_berry_commands())

    def _register_berry_commands(self) -> app_commands.Group:
        """Register berry-related commands as a command group."""

        # Create the berries group and add it to the command tree
        berries_group = app_commands.Group(name="berries", description="Berry commands")

        async def gather(interaction: discord.Interaction, type: str):
            old_balance = self._validate_user(interaction.user.id, interaction.guild_id)
            outcome: GatherOutcome = self._roll_for_gathering_occurrence(interaction.guild_id, type)
            self.balances_dict[interaction.user.id] += outcome.value

            await interaction.response.send_message(
                embed=get_outcome_embed(outcome, old_balance, self.balances_dict[interaction.user.id], interaction),
                ephemeral=False)

        @berries_group.command(name="hunt", description="Hunt for some berries")
        async def hunt(interaction: discord.Interaction):
            await gather(interaction, "hunt")

        @berries_group.command(name="steal", description="Steal berries from another parasaur")
        async def steal(interaction: discord.Interaction):
            await gather(interaction, "steal")

        @berries_group.command(name="balance", description="Check your berry balance")
        async def balance(interaction: discord.Interaction):
            # Retrieve user's current balance
            current_balance = self._validate_user(interaction.user.id, interaction.guild_id)

            embed = discord.Embed(
                title="🍒 Berry Balance",
                description=f"You currently have **{current_balance}** berries.",
                color=discord.Color.blue()
            )

            await interaction.response.send_message(embed=embed, ephemeral=False)

        # Add gambling commands to the berries group
        berries_group.add_command(self._register_gambling_commands())

        return berries_group

    def _register_gambling_commands(self) -> app_commands.Group:
        gambling_group = app_commands.Group(name="gambling", description="Gambling commands")

        # TODO: Add gambling commands
        @gambling_group.command(name="roulette", description="Play roulette with your berries")
        @app_commands.describe(bet="Amount of berries to bet")
        # @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)  # Uncomment to enable cooldown
        async def roulette(interaction: discord.Interaction, bet: int):
            if 0 > bet > self._validate_user(interaction.user.id, interaction.guild_id):
                await interaction.response.send_message("You don't have enough berries to bet that much.",
                                                        ephemeral=True)
                return
            pass

        @gambling_group.command(name="slots", description="Play slots with your berries")
        @app_commands.describe(bet="Amount of berries to bet")
        # @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)  # Uncomment to enable cooldown
        async def slots(interaction: discord.Interaction, bet: int):
            if 0 > bet > self._validate_user(interaction.user.id, interaction.guild_id):
                await interaction.response.send_message("You don't have enough berries to bet that much.",
                                                        ephemeral=True)
                return
            pass

        @gambling_group.command(name="blackjack", description="Play blackjack with your berries")
        @app_commands.describe(bet="Amount of berries to bet")
        # @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)  # Uncomment to enable cooldown
        async def blackjack(interaction: discord.Interaction, bet: int):
            if 0 > bet > self._validate_user(interaction.user.id, interaction.guild_id):
                await interaction.response.send_message("You don't have enough berries to bet that much.",
                                                        ephemeral=True)
                return
            pass

        return gambling_group

    def _register_events(self):
        """Register Discord client events."""

        @self.client.event
        async def on_ready():
            self.console.clear()
            self.console.rule(f"[bold]{self.client.user.name}[/]")  # Added bold for emphasis

            self.console.print(f"Bot activated as {self.client.user}")
            self.logger.log(f"{self.client.user.name} has logged in as {self.client.user}", "Bot")

            self.console.print("\nConnected Guilds:")
            self.logger.log(f"{self.client.user.name} connected to {len(self.client.guilds)} guilds:", "Bot")

            for guild in self.client.guilds:
                member_str = f"{guild.member_count} member{'s' if guild.member_count > 1 else ''}"
                self.console.print(f"  • [green]{guild.name}[/] ({guild.id}) - {member_str}")
                self.logger.log(f"    * Guild: {guild.name} ({guild.id}) {member_str}", "Bot")

            # Load afflictions for each guild
            self.console.print("\n[green]Loading afflictions...[/]")
            self.logger.log("Loading afflictions...", "Bot")
            self.afflictions_dict = {guild.id: self._load_json_afflictions(guild.id) for guild in self.client.guilds}
            self.console.print(
                f"[green]Loaded[/] {len(self.afflictions_dict)} [green]guild(s) with afflictions[/]")  # Added closing [/]

            # Load hunt outcomes for each guild
            self.console.print("\n[green]Loading hunt outcomes...[/]")
            self.logger.log("Loading hunt outcomes...", "Bot")
            self.hunt_outcomes_dict = {guild.id: self._load_json_hunt_outcomes(guild.id) for guild in
                                       self.client.guilds}
            self.console.print(
                f"[green]Loaded[/] {len(self.hunt_outcomes_dict)} [green]guild(s) with hunt outcomes[/]")  # Added closing [/]

            # Load steal outcomes for each guild
            self.console.print("\n[green]Loading steal outcomes...[/]")
            self.logger.log("Loading steal outcomes...", "Bot")
            self.steal_outcomes_dict = {guild.id: self._load_json_steal_outcomes(guild.id) for guild in
                                        self.client.guilds}
            self.console.print(
                f"[green]Loaded[/] {len(self.steal_outcomes_dict)} [green]guild(s) with steal outcomes[/]")  # Added closing [/]

            # Load balances of each user
            self.console.print("\n[green]Loading user balances...[/]")
            self.logger.log("Loading user balances...", "Bot")
            self.balances_dict = self._load_json_balances()
            # Consider logging count after loading if successful
            self.console.print(f"[green]Loaded[/] {len(self.balances_dict)} [green]user balances[/]")
            # This second print might be redundant if the previous line shows the count
            # self.console.print("[green]User balances loaded[/]") 

            # Load guild configurations
            self.console.print("\n[green]Loading guild configurations...[/]")
            self.logger.log("Loading guild configurations...", "Bot")
            self.guild_configs = {guild.id: self._load_json_configs(guild.id) for guild in self.client.guilds}
            self.console.print(f"[green]Loaded[/] {len(self.guild_configs)} [green]guild(s) with configurations[/]")
            # This second print might be redundant
            # self.console.print("[green]Guild configurations loaded[/]")

            # If syncing is enabled, sync the command tree
            # NOTE: Using 'bot.tree' in the guild sync section, ensure 'bot' is defined or use 'self.tree' consistently
            if any(arg == "--sync" for arg in sys.argv):
                self.console.print("\n[green]Syncing command tree globally...[/]")
                self.logger.log("Syncing command tree globally...", "Bot")
                self.console.print("[yellow]Warning: Avoid syncing commands too often to avoid rate limits...[/]")
                self.console.print("[yellow]Warning: Syncing commands may take a while...[/]")
                try:
                    await self.tree.sync()
                    self.console.print("[green]Command tree synced globally[/]")
                    self.logger.log("Command tree synced globally", "Bot")
                except Exception as e:
                    self.console.print(f"[red]Error syncing command tree globally: {e}[/]")
                    self.logger.log(f"Error syncing command tree globally: {e}", "BotError")


            elif any(arg == "--sync-guild" for arg in sys.argv):
                self.console.print("\nPlease select a guild to sync the command tree with:")
                if not self.client.guilds:
                    self.console.print("[yellow]Bot is not in any guilds to sync with.[/]")
                    self.logger.log("Sync-guild attempted but bot is not in any guilds.", "Bot")
                else:
                    for i, guild in enumerate(self.client.guilds):
                        self.console.print(
                            f"  • [cyan]{i + 1}[/] {guild.name} ({guild.id})")  # Changed color for number

                    try:
                        guild_choice = input("Enter the number of the guild to sync with (or 0 to cancel): ")
                        guild_index = int(guild_choice) - 1
                        if guild_choice == '0':
                            self.console.print("[yellow]Syncing cancelled.[/]")
                            self.logger.log("Guild sync cancelled by user.", "Bot")
                        elif 0 <= guild_index < len(self.client.guilds):
                            guild = self.client.guilds[guild_index]
                            self.console.print(f"\n[green]Syncing command tree with {guild.name} ({guild.id})...[/]")
                            self.logger.log(f"Syncing command tree with guild: {guild.name} ({guild.id})", "Bot")
                            self.console.print(
                                "[yellow]Clearing existing commands in guild and copying global commands...[/]")

                            # Ensure using self.tree consistently
                            self.tree.clear_commands(guild=guild)
                            self.tree.copy_global_to(guild=guild)
                            await self.tree.sync(guild=guild)

                            self.console.print(f"[green]Command tree synced with {guild.name} ({guild.id})[/]")
                            self.logger.log(f"Command tree synced with guild: {guild.name} ({guild.id})", "Bot")
                        else:
                            self.console.print("[red]Invalid guild number. Syncing aborted.[/]")
                            self.logger.log("Invalid guild number provided for sync. Syncing aborted.", "Bot")
                    except ValueError:
                        self.console.print("[red]Invalid input. Please enter a number. Syncing aborted.[/]")
                        self.logger.log("Non-numeric input for guild sync selection. Syncing aborted.", "Bot")
                    except Exception as e:
                        self.console.print(f"[red]Error syncing command tree with guild: {e}[/]")
                        self.logger.log(f"Error syncing command tree with guild: {e}", "BotError")

            # ================================================================
            # List all registered commands (using recursive approach)
            # ================================================================
            self.console.print("\n[bold underline]Registered Commands:[/]")
            self.logger.log("Registered Commands:", "Bot")

            # Separate top-level groups and standalone commands
            groups = {}
            standalone_commands = []

            # Initial categorization of top-level commands
            for command in self.tree.get_commands():
                if isinstance(command, app_commands.Group):
                    groups[command.name] = command
                else:
                    standalone_commands.append(command)

            # Print command groups (top-level)
            if groups:
                self.console.print("\n[green bold]Command Groups:[/]")
                for group_name, group in sorted(groups.items()):  # Sort top-level groups
                    try:
                        # Assuming has_admin_check is defined elsewhere and accessible
                        is_admin_group = has_admin_check(group)
                    except NameError:
                        self.logger.log(
                            f"Warning: has_admin_check function not found for group '{group_name}'. Assuming USER.",
                            "Bot")
                        is_admin_group = False

                    admin_status_group = "[purple]ADMIN[/]" if is_admin_group else "[green]USER[/]"
                    self.console.print(f"  [bold]/{group.name}[/] {admin_status_group} - {group.description}")
                    self.logger.log(f"  Group: /{group.name} {admin_status_group} - {group.description}",
                                    "Bot")  # Added status to log

                    # === Key: Initial call to the recursive function for sub-items ===
                    # Sets the initial indentation and path for items under this top-level group.
                    initial_sub_item_indent = "    "
                    sorted_sub_items = sorted(group.commands, key=lambda c: c.name)  # Sort sub-items
                    for sub_item in sorted_sub_items:
                        # Pass the group's name as the initial part of the path
                        self._print_command_item_recursive(sub_item, initial_sub_item_indent, [group.name])

            # Print standalone commands (top-level)
            if standalone_commands:
                self.console.print("\n[green bold]Standalone Commands:[/]")
                for command in sorted(standalone_commands, key=lambda x: x.name):  # Sort standalone commands
                    try:
                        # Assuming has_admin_check is defined elsewhere and accessible
                        is_admin_cmd = has_admin_check(command)
                    except NameError:
                        self.logger.log(
                            f"Warning: has_admin_check function not found for command '{command.name}'. Assuming USER.",
                            "Bot")
                        is_admin_cmd = False

                    admin_status_cmd = "[purple]ADMIN[/]" if is_admin_cmd else "[green]USER[/]"
                    self.console.print(f"  [bold]/{command.name}[/] {admin_status_cmd} - {command.description}")
                    self.logger.log(f"  Command: /{command.name} {admin_status_cmd} - {command.description}",
                                    "Bot")  # Added status to log

            if not groups and not standalone_commands:
                self.console.print("  [yellow]No application commands found or registered.[/]")
                self.logger.log("No application commands found or registered.", "Bot")

            # Final ready message
            self.console.print("\n[bold green]Bot is ready and online![/]")
            self.logger.log("Bot is ready and online!", "Bot")

        @self.client.event
        async def on_message(message: discord.Message):
            if message.author == self.client.user:
                return
                # Handle messages here if needed
            pass  # TODO: Remove pass when implementing message handling

    # --- Add this method to your class ---
    def _print_command_item_recursive(self, command_item, base_indent_str, parent_group_path_parts_for_log):
        """
        Recursively prints a command item (command or group) and its children if it's a group.
        This is the core logic for handling nested groups.
        """
        prefix = "• "

        # Construct the full command path for logging (e.g., "settings user profile")
        current_full_path_parts = parent_group_path_parts_for_log + [command_item.name]
        log_full_path = " ".join(current_full_path_parts)

        # Determine if the command requires admin privileges (ensure has_admin_check is accessible)
        try:
            # Assuming has_admin_check is defined elsewhere and accessible
            is_admin = has_admin_check(command_item)
        except NameError:
            # Fallback or default if has_admin_check is not found - adjust as needed
            self.logger.log(
                f"Warning: has_admin_check function not found for command '{log_full_path}'. Assuming USER.", "Bot")
            is_admin = False

        admin_status = "[purple]ADMIN[/]" if is_admin else "[green]USER[/]"
        description = getattr(command_item, 'description', 'No description available')

        # Console output: Display only the current command/group name, nested visually
        self.console.print(
            f"{base_indent_str}{prefix}[bold]{command_item.name}[/] {admin_status} - {description}"
        )

        # Logger output: Log with the full path for clarity
        item_type_for_log = "Sub-Group" if isinstance(command_item, app_commands.Group) else "Subcommand"
        self.logger.log(
            f"{base_indent_str}{prefix}{item_type_for_log}: /{log_full_path} {admin_status} - {description}",
            "Bot"
        )

        # If the current item is a group, recurse for its children
        if isinstance(command_item, app_commands.Group):
            # Increase indentation for the next level of nesting
            child_base_indent_str = base_indent_str + "  "

            # Sort sub-items by name for consistent output at this level
            sorted_sub_items = sorted(command_item.commands, key=lambda c: c.name)
            for sub_item in sorted_sub_items:
                # Recursive call for each sub-item of the current group
                self._print_command_item_recursive(sub_item, child_base_indent_str, current_full_path_parts)

    def _roll_for_afflictions(self, guild_id: int, is_minor: bool = False) -> List[Affliction]:
        """
        Roll for afflictions based on the configured chance and rarity.
        
        Returns:
            A list of afflictions the character has
        """
        result = []
        available_afflictions = self.afflictions_dict[guild_id].copy()

        # Roll for each possible affliction
        for _ in range(len(self.afflictions_dict[guild_id])):
            if not available_afflictions:
                break

            # Check if we get any affliction at all
            if random.random() < (
                    self.guild_configs[guild_id].minor_chance if is_minor else self.guild_configs[
                        guild_id].chance) / 100:
                # Group remaining afflictions by rarity
                commons = [a for a in available_afflictions if a.rarity.lower() == "common"]
                uncommons = [a for a in available_afflictions if a.rarity.lower() == "uncommon"]
                rares = [a for a in available_afflictions if a.rarity.lower() == "rare"]
                ultra_rares = [a for a in available_afflictions if a.rarity.lower() == "ultra rare"]

                if is_minor:
                    commons = [a for a in commons if a.is_minor]
                    rarity_groups = [commons]
                    rarity_weights = [100]
                else:
                    # Rarity groups and their weights
                    rarity_groups = [commons, uncommons, rares, ultra_rares]
                    rarity_weights = [60, 25, 10, 5]

                if sum(rarity_weights) != 100:
                    self.console.print("[red]Error: Rarity weights must sum to 100")
                    self.logger.log("[red]Error: Rarity weights must sum to 100")
                    return []

                # Filter out empty groups
                non_empty_groups = []
                non_empty_weights = []

                for group, weight in zip(rarity_groups, rarity_weights):
                    if group:
                        non_empty_groups.append(group)
                        non_empty_weights.append(weight)

                # Select a group based on rarity weights, then select random affliction from that group
                if non_empty_groups:
                    selected_group = random.choices(non_empty_groups, weights=non_empty_weights, k=1)[0]
                    selected_affliction = random.choice(selected_group)

                    result.append(selected_affliction)
                    available_afflictions.remove(selected_affliction)
                else:
                    # No afflictions left in any rarity group
                    break
            else:
                # Failed the roll, stop adding afflictions
                break

        return result

    def _find_affliction(self, search_term: str, guild_id: int) -> Optional[Affliction]:
        """
        Find an affliction by a search term.
        
        Args:
            search_term: The term to search for
            
        Returns:
            The full affliction string if found, None otherwise
        """
        search_term = search_term.lower()

        for affliction in self.afflictions_dict[guild_id]:
            name = affliction.name.lower()
            if search_term in name or search_term == name.split()[0]:
                return affliction

        return None

    def _roll_for_gathering_occurrence(self, guild_id: int, type: Literal["hunt", "steal"]) -> GatherOutcome:
        """
        Roll for a hunting occurrence based on the configured chance.
        
        Returns:
            A HuntOutcome object representing the outcome of the hunt
        """
        # TODO: Make a function do this, return rarity groups and rarity weights
        if type == "hunt":
            commons = [outcome for outcome in self.hunt_outcomes_dict[guild_id] if outcome.rarity.lower() == "common"]
            uncommons = [outcome for outcome in self.hunt_outcomes_dict[guild_id] if
                         outcome.rarity.lower() == "uncommon"]
            rares = [outcome for outcome in self.hunt_outcomes_dict[guild_id] if outcome.rarity.lower() == "rare"]
            ultra_rares = [outcome for outcome in self.hunt_outcomes_dict[guild_id] if
                           outcome.rarity.lower() == "ultra rare"]
        else:
            commons = [outcome for outcome in self.steal_outcomes_dict[guild_id] if outcome.rarity.lower() == "common"]
            uncommons = [outcome for outcome in self.steal_outcomes_dict[guild_id] if
                         outcome.rarity.lower() == "uncommon"]
            rares = [outcome for outcome in self.steal_outcomes_dict[guild_id] if outcome.rarity.lower() == "rare"]
            ultra_rares = [outcome for outcome in self.steal_outcomes_dict[guild_id] if
                           outcome.rarity.lower() == "ultra rare"]

        rarity_groups = [commons, uncommons, rares, ultra_rares]
        rarity_weights = [60, 25, 10, 5]

        if sum(rarity_weights) != 100:
            self.console.print("[red]Error: Rarity weights must sum to 100")
            self.logger.log("[red]Error: Rarity weights must sum to 100")
            return None

        selected_group = random.choices(rarity_groups, weights=rarity_weights, k=1)[0]
        return random.choice(selected_group)

    def _get_affliction_from_name(self, affliction_name: str, guild_id: int) -> (Affliction, int):
        """
        Returns the affliction object and its index in the afflictions list.
        :param affliction_name: The name of the affliction to search for
        :param guild_id: The ID of the guild to search in
        :return: Returns the affliction object and its index in the afflictions list
        """
        return next(
            (a, i) for i, a in enumerate(self.afflictions_dict[guild_id]) if
            a.name.lower() == affliction_name.lower())

    def _if_affliction_exists(self, affliction: str, guild_id: int) -> bool:
        """ Checks if affliction exists in the guild's affliction list """
        return any(a.name.lower() == affliction.lower() for a in self.afflictions_dict[guild_id])

    def _validate_directory(self, directory: str) -> bool:
        if not os.path.exists(directory):
            self.console.print(
                f"[yellow]Warning: Directory not found. Creating directory: {directory}.")
            self.logger.log(f"Directory not found. Creating directory: {directory}", "Json")
            try:
                os.makedirs(directory)
                return True
            except Exception as e:
                self.console.print(f"[red bold]Error creating directory: {e}")
                self.logger.log(f"Error creating directory: {e}", "Json")
                return False  # Return if directory creation fails
        return True

    def _validate_json_load(self, directory: str, path: str, default_path: str) -> tuple[str, bool]:
        if not self._validate_directory(directory):
            return path, False

        if not os.path.exists(path):
            self.console.print(f"[yellow]Warning: {path} not found. Using default values.")
            self.logger.log(f"{path} not found. Using default values.", "Json")
            path = default_path

            if not os.path.exists(path):
                self.console.print(f"[yellow]Warning: Default file not found. Creating empty file")
                self.logger.log(f"Default file not found. Creating empty file", "Json")
                try:
                    with open(path, 'w') as f:
                        json.dump([], f)
                except Exception as e:
                    self.console.print(f"[red bold]Error creating default file: {e}")
                    self.logger.log(f"Error creating default file: {e}", "Json")
                    return path, False

        return path, True

    def _validate_user(self, user_id: int, guild_id: int) -> int:
        """ Returns the balance of the user, and sets users balance to the guilds starting balance from configs """
        if user_id in self.balances_dict:
            return self.balances_dict[user_id]

        self.balances_dict[user_id] = self.guild_configs[guild_id].starting_pay
        self.console.print("User balance created:", user_id)
        self.logger.log(f"User balance created: {user_id}", "Bot")
        return self.guild_configs[guild_id].starting_pay

    def _write_token_file(self, token: str):

        if not self._validate_directory("data/"):
            return

        try:
            with open("data/bot_token.txt", "w") as f:
                f.write(token)
            self.console.print("[green]Token saved to data/bot_token.txt[/]")
            self.logger.log("Token saved to data/bot_token.txt", "Bot")
        except Exception as e:
            self.console.print(f"[red]Error saving token to data/bot_token.txt: {e}")
            self.logger.log(f"Error saving token to data/bot_token.txt: {e}", "Bot")

    def _exit_handler(self):
        self.console.print("\n[red]Bot shutting down...[/]")
        self.logger.log("Bot shutting down...", "Bot")

        if hasattr(self, "afflictions_dict") and self.afflictions_dict:
            self.console.print("[green]Saving afflictions...[/]")
            for guild_id in self.afflictions_dict:
                self.console.print(f"  • Saving for guild {guild_id}")
                self.logger.log(f"    Saving afflictions for guild {guild_id}", "Bot")
                self._save_json(guild_id, "afflictions", self.afflictions_dict[guild_id], cls=AfflictionEncoder)

            self.console.print("[green]Afflictions saved[/]")
            self.logger.log("Afflictions saved", "Bot")

        if hasattr(self, "guild_configs") and self.guild_configs:
            self.console.print("\n[green]Saving guild configurations...[/]")
            for guild_id in self.guild_configs:
                self.console.print(f"  • Saving for guild {guild_id}")
                self.logger.log(f"    Saving guild configuration for guild {guild_id}", "Bot")
                self._save_json(guild_id, "guild_configs", self.guild_configs[guild_id], cls=GuildConfigEncoder)

            self.console.print("[green]Guild configurations saved[/]")
            self.logger.log("Guild configurations saved", "Bot")

        if hasattr(self, "hunt_outcomes_dict") and self.hunt_outcomes_dict:
            self.console.print("\n[green]Saving hunt outcomes...[/]")
            for guild_id in self.hunt_outcomes_dict:
                self.console.print(f"  • Saving for guild {guild_id}")
                self.logger.log(f"    Saving hunt outcomes for guild {guild_id}", "Bot")
                self._save_json(guild_id, "hunt_outcomes", self.hunt_outcomes_dict[guild_id], cls=GatherOutcomeEncoder)

            self.console.print("[green]Hunt outcomes saved[/]")
            self.logger.log("Hunt outcomes saved", "Bot")

        if hasattr(self, "balances_dict") and self.balances_dict:
            self.console.print("\n[green]Saving user balances...[/]")
            self.logger.log("Saving user balances...", "Bot")
            self._save_json(0, "balances", self.balances_dict)

            self.console.print("[green]User balances saved[/]")
            self.logger.log("User balances saved", "Bot")

    def run(self):
        """Run the Discord bot."""
        atexit.register(self._exit_handler)
        token = None

        # First try to get token from data/bot_token.txt
        try:
            with open("data/bot_token.txt", "r") as f:
                token = f.read().strip()
                if not validate_discord_token(token):
                    self.console.print(
                        "[red]Token file holds invalid Discord token, checking args. If args do not contain '--token=' then collecting manual input.[/]")
                    token = None
        except FileNotFoundError:
            self.console.print(
                "[yellow]Token file not found, checking args. If args do not contain '--token=' then collecting manual input.[/]")

        for arg in sys.argv:
            if arg == "--debug":
                self.console.print("[yellow]Debug mode enabled[/]")
                self.logger.log("Debug mode enabled", "Bot")
                self.client.debug = True
            elif arg.startswith("--token="):
                token = arg.split("=")[1]

                if not validate_discord_token(token):
                    token = None
                    self.console.print("[red]Invalid token. Please enter your token.[/]")
                    break

                self._write_token_file(token)
                break

        if token is None:
            while True:
                token = input("Enter your bot token > ")
                if token == "":
                    self.console.print("[red]Error: No token provided")
                    self.logger.log("No token provided", "Bot")
                    continue

                if validate_discord_token(token):
                    self._write_token_file(token)
                    break
                print("Invalid token")

        self.client.run(token)

    def exit(self):
        """Exit the bot gracefully."""
        self._exit_handler()
        self.client.close()


if __name__ == "__main__":
    bot = AfflictionBot()
    bot.run()
