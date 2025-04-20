import os
import sys
import json
import random
from typing import List, Optional
import atexit

import discord
from discord import app_commands
from discord.app_commands import checks
import dotenv
from rich.console import Console

from logger import Logger
from permissions import has_admin_check

# Constants
AFFLICTION_CHANCE = 25  # Percentage chance to roll for an affliction
AFFLICTION_DIRECTORY = "afflictions"
LOG_FILE = "log.txt"

""" Error Classes """


class AfflictionBotError(Exception):
    """ Base exception for AfflictionBot errors """
    pass


class AfflictionDirectoryError(AfflictionBotError):
    """ Exception raised when there are issues with the affliction directory """
    pass


class AfflictionFileError(AfflictionBotError):
    """ Exception raised when there are issues with the affliction files """
    pass


class Affliction:
    """Class representing an affliction with name, description, and rarity."""

    def __init__(self, name: str, description: str, rarity: str):
        self.name = name
        self.description = description
        self.rarity = rarity

    def __str__(self):
        return f"{self.name.title()}"

    @classmethod
    def from_dict(cls, data: dict):
        """Create an Affliction instance from a dictionary."""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            rarity=data.get("rarity", "")
        )


class AfflictionEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Affliction):
            return {
                "name": obj.name,
                "description": obj.description,
                "rarity": obj.rarity
            }
        return json.JSONEncoder.default(self, obj)


class AfflictionBot:
    """Main bot class to handle Discord interactions and affliction management."""

    afflictions_dict: dict[int, List[Affliction]]

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

        affliction_path = os.path.join(AFFLICTION_DIRECTORY, f"{guild_id}.json")

        # Create directory if it doesn't exist
        if not os.path.exists(AFFLICTION_DIRECTORY):
            self.console.print(
                f"[yellow]Warning: Affliction Directory not found. Creating directory: {AFFLICTION_DIRECTORY}.")
            self.logger.log(f"Affliction Directory not found. Creating directory: {AFFLICTION_DIRECTORY}", "Json")
            try:
                os.makedirs(AFFLICTION_DIRECTORY)
            except Exception as e:
                self.console.print(f"[red bold]Error creating affliction directory: {e}")
                self.logger.log(f"Error creating affliction directory: {e}", "Json")
                return []  # Return empty list if directory creation fails   

        # Use default file if guild-specific file doesn't exist
        if not os.path.exists(affliction_path):
            self.console.print(f"[yellow]Warning: {affliction_path} not found. Using default afflictions.")
            self.logger.log(f"{affliction_path} not found. Using default afflictions.", "Json")
            affliction_path = "afflictions.default.json"

            # If even default file doesn't exist, create an empty file
            if not os.path.exists(affliction_path):
                self.console.print(f"[yellow]Warning: Default affliction file not found. Creating empty file")
                self.logger.log(f"Default affliction file not found. Creating empty file", "Json")
                try:
                    with open(affliction_path, 'w') as f:
                        json.dump([], f)
                except Exception as e:
                    self.console.print(f"[red bold]Error creating default affliction file: {e}")
                    self.logger.log(f"Error creating default affliction file: {e}", "Json")
                    return []  # Return empty list if file creation fails

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

    def _save_json_affliction(self, guild_id: int) -> None:
        affliction_path = os.path.join(AFFLICTION_DIRECTORY, f"{guild_id}.json")

        # Create directory if it doesn't exist
        if not os.path.exists(AFFLICTION_DIRECTORY):
            try:
                os.makedirs(AFFLICTION_DIRECTORY)
            except Exception as e:
                self.console.print(f"[red bold]Error creating affliction directory: {e}")
                self.logger.log(f"Error creating affliction directory: {e}", "Json")
                return  # Return if directory creation fails

        try:
            with open(affliction_path, 'w') as f:
                json.dump(self.afflictions_dict[guild_id], f, cls=AfflictionEncoder, indent=4)

        except Exception as e:
            self.console.print(f"[red bold]Error saving afflictions: {e}")
            self.logger.log(f"Error saving afflictions: {e}", "Json")

    def _register_commands(self):
        """Register all Discord slash commands."""

        # Commands for everyone
        @self.tree.command(name="roll-affliction", description="Rolls for afflictions affecting your Parasaurolophus")
        @app_commands.describe(para="Your Parasaurolophus")
        async def roll_affliction(interaction: discord.Interaction, para: str = None):
            try:
                afflictions: List[Affliction] = self._roll_for_afflictions(interaction.guild_id)

                if para is None:
                    para = interaction.user.name
                else:
                    para = para.capitalize()

                if not afflictions:
                    self.logger.log(f"{para} rolled no afflictions.", "Bot")
                    await interaction.response.send_message(f"{para} has **no** afflictions")
                    return

                if len(afflictions) == 1:
                    self.logger.log(f"{para} rolled 1 affliction: {afflictions[0].name}", "Bot")
                    await interaction.response.send_message(
                        f"{para} has **{afflictions[0].name}** *({afflictions[0].rarity.title()})* - {afflictions[0].description}")
                    return

                response = f"{para} has the following afflictions:"
                for affliction in afflictions:
                    response += f"\n- **{affliction.name.title()}** *({affliction.rarity.title()})* - {affliction.description}"

                self.logger.log(f"{para} rolled {len(afflictions)} afflictions: \n{afflictions}", "Bot")
                await interaction.response.send_message(response)

            except Exception as e:
                self.logger.log(f"Error in roll_affliction: {e}", "Bot")
                await interaction.response.send_message("An error occurred while rolling for afflictions",
                                                        ephemeral=True)

        @self.tree.command(name="list-afflictions", description="Lists all available afflictions")
        async def list_afflictions(interaction: discord.Interaction):
            try:
                response = "**Available Afflictions:**"

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

                for affliction in sorted_afflictions:
                    response += f"\n- **{affliction.name.title()}** *({affliction.rarity.title()})* | Run /info {affliction.name.lower().split(' ')[0]}"

                await interaction.response.send_message(response)
                self.logger.log(f"{interaction.user.name} listed all afflictions", "Bot")

            except Exception as e:
                self.logger.log(f"Error in list_afflictions: {e}", "Bot")
                await interaction.response.send_message("An error occurred while listing afflictions", ephemeral=True)

        @self.tree.command(name="info", description="Describes an affliction")
        @app_commands.describe(affliction="Name of the affliction")
        async def info(interaction: discord.Interaction, affliction: str):
            try:
                found_affliction = self._find_affliction(affliction, interaction.guild_id)

                if found_affliction:
                    response = f"**{found_affliction.name.title()}**\n{found_affliction.description}"
                    await interaction.response.send_message(response)
                    self.logger.log(f"{interaction.user.name} got info on {found_affliction.name.title()}", "Bot")
                else:
                    await interaction.response.send_message(
                        f"Affliction '{affliction}' not found. Use /list_afflictions to see all available afflictions.",
                        ephemeral=True
                    )

            except Exception as e:
                self.logger.log(f"Error in info command: {e}", "Bot")
                await interaction.response.send_message("An error occurred while retrieving affliction info",
                                                        ephemeral=True)

        # Commands for admins
        @self.tree.command(name="add-affliction", description="Adds an affliction to the list")
        @app_commands.describe(name="Name of the affliction", description="Description of the affliction",
                               rarity="Rarity of the affliction")
        @app_commands.choices(rarity=[
            app_commands.Choice(name="Common", value="common"),
            app_commands.Choice(name="Uncommon", value="uncommon"),
            app_commands.Choice(name="Rare", value="rare"),
            app_commands.Choice(name="Ultra Rare", value="ultra rare")
        ])
        @app_commands.checks.has_permissions(administrator=True)
        async def add_affliction(interaction: discord.Interaction, name: str, description: str,
                                 rarity: app_commands.Choice[str]):
            # Check if the affliction already exists
            if any(a.name.lower() == name.lower() for a in self.afflictions_dict[interaction.guild_id]):
                await interaction.response.send_message(f"Affliction '{name}' already exists.", ephemeral=True)
                return

            try:
                new_affliction = Affliction(name=name, description=description, rarity=rarity.value)
                self.afflictions_dict[interaction.guild_id].append(new_affliction)
                self._save_json_affliction(interaction.guild_id)

                await interaction.response.send_message(f"Affliction '{name}' added successfully.", ephemeral=True)
                self.logger.log(f"{interaction.user.name} added affliction {name}", "Bot")

            except Exception as e:
                self.logger.log(f"Error in add_affliction: {e}", "Bot")
                await interaction.response.send_message("An error occurred while adding the affliction", ephemeral=True)

        @add_affliction.error
        async def add_affliction_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            if isinstance(error, app_commands.MissingPermissions):
                await interaction.response.send_message("You don't have permission to use this command.",
                                                        ephemeral=True)
            else:
                self.logger.log(f"Error in add_affliction: {error}", "Bot")
                await interaction.response.send_message("An error occurred while adding the affliction", ephemeral=True)

        @self.tree.command(name="remove-affliction", description="Removes an affliction from the list")
        @app_commands.describe(name="Name of the affliction")
        @app_commands.checks.has_permissions(administrator=True)
        async def remove_affliction(interaction: discord.Interaction, name: str):

            # Check if the affliction does not exist
            if not any(a.name.lower() == name.lower() for a in self.afflictions_dict[interaction.guild_id]):
                await interaction.response.send_message(f"Affliction '{name}' does not exist.", ephemeral=True)
                return

            try:
                affliction_to_remove = next(
                    a for a in self.afflictions_dict[interaction.guild_id] if a.name.lower() == name.lower())
                self.afflictions_dict[interaction.guild_id].remove(affliction_to_remove)
                self._save_json_affliction(interaction.guild_id)

                await interaction.response.send_message(f"Affliction '{name}' removed successfully.", ephemeral=True)
                self.logger.log(f"{interaction.user.name} removed affliction {name}", "Bot")

            except Exception as e:
                self.logger.log(f"Error in remove_affliction: {e}", "Bot")
                await interaction.response.send_message("An error occurred while removing the affliction",
                                                        ephemeral=True)

        @remove_affliction.error
        async def remove_affliction_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            if isinstance(error, app_commands.MissingPermissions):
                await interaction.response.send_message("You don't have permission to use this command.",
                                                        ephemeral=True)
            else:
                self.logger.log(f"Error in add_affliction: {error}", "Bot")
                await interaction.response.send_message("An error occurred while adding the affliction", ephemeral=True)

    def _register_events(self):
        """Register Discord client events."""

        @self.client.event
        async def on_ready():
            self.console.clear()
            self.console.rule(f"{self.client.user.name}")

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
            self.console.print(f"[green]Loaded[/] {len(self.afflictions_dict)} [green]guild(s) with afflictions")

            # If syncing is enabled, sync the command tree
            if any(arg == "--sync" for arg in sys.argv):
                self.console.print("\n[green]Syncing command tree...[/]")
                self.logger.log("Syncing command tree...", "Bot")
                self.console.print("[yellow]Warning: Avoid syncing commands too often to avoid rate limits...[/]")
                self.console.print("[yellow]Warning: Syncing commands may take a while...[/]")
                await self.tree.sync()
                self.console.print("[green]Command tree synced[/]")
                self.logger.log("Command tree synced", "Bot")

            # List all registered commands
            self.console.print("\nRegistered Commands:")
            self.console.print("Commands in purple are admin-only")
            self.logger.log("Registered Commands:", "Bot")
            for command in self.tree.get_commands():

                if has_admin_check(command):
                    self.console.print(f"  • [purple]{command.name}[/] - {command.description}")
                    self.logger.log(f"    * Command: {command.name}  ADMIN ONLY - {command.description}", "Bot")
                else:
                    self.console.print(f"  • [green]{command.name}[/] - {command.description}")
                    self.logger.log(f"    * Command: {command.name} - {command.description}", "Bot")

    def _roll_for_afflictions(self, guild_id: int) -> List[Affliction]:
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
            if random.random() < AFFLICTION_CHANCE / 100:
                # Group remaining afflictions by rarity
                commons = [a for a in available_afflictions if a.rarity.lower() == "common"]
                uncommons = [a for a in available_afflictions if a.rarity.lower() == "uncommon"]
                rares = [a for a in available_afflictions if a.rarity.lower() == "rare"]
                ultra_rares = [a for a in available_afflictions if a.rarity.lower() == "ultra rare"]

                rarity_groups = [commons, uncommons, rares, ultra_rares]
                rarity_weights = [60, 25, 10, 5]

                if sum(rarity_weights) != 100:
                    self.console.print("[red]Error: Rarity weights must sum to 100")
                    exit(1)

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

    def _get_rarity_emoji(self, rarity: str) -> str:
        for r, emoji in self.rarity_list:
            if rarity.lower() == r.lower():
                return f":{emoji}:"

        else:
            return ""

    def _exit_handler(self):
        self.console.print("[red]Bot shutting down...[/]")
        self.logger.log("Bot shutting down...", "Bot")

        if hasattr(self, "afflictions_dict") and self.afflictions_dict:
            self.console.print("[green]Saving afflictions...[/]")
            for guild_id in self.afflictions_dict:
                self.console.print(f"  • Saving for guild {guild_id}")
                self.logger.log(f"    Saving afflictions for guild {guild_id}", "Bot")
                self._save_json_affliction(guild_id)

            self.console.print("[green]Afflictions saved[/]")
            self.logger.log("Afflictions saved", "Bot")

    def run(self):
        """Run the Discord bot."""
        atexit.register(self._exit_handler)

        if any(arg == "-P" for arg in sys.argv):
            token = os.getenv("PRODUCTION_TOKEN")
        else:
            token = os.getenv("TEST_TOKEN")
        if not token:
            self.console.print("[red bold]Error: Discord TOKEN not found in environment variables")
            exit(1)

        self.client.run(token)

    def exit(self):
        """Exit the bot gracefully."""
        self._exit_handler()
        self.client.close()


if __name__ == "__main__":
    bot = AfflictionBot()
    bot.run()
