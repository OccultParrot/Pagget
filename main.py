"""
Discord bot for the Parasaurolophus herd Longcrest Fellowship on the Path of Titans server Dynasty Realism.
Discord: https://discord.gg/mgSZqp9PFD

The bot handles affliction management for Parasaurolophus characters with the following commands:
    - /roll_affliction: Rolls for the afflictions that affect your Parasaurolophus
    - /list_afflictions: Lists all the available afflictions
    - /info [affliction]: Describes the supplied affliction if it exists
    
All afflictions are stored in a text file called afflictions.json. Its an array of objects with the following keys:
    - name: The name of the affliction
    - description: The description of the affliction
    - rarity: The rarity of the affliction (common, uncommon, rare, very rare)
"""
import os
import sys
import json
import random
from typing import List, Optional

import discord
from discord import app_commands
import dotenv
from rich.console import Console

from logger import Logger

# Constants
AFFLICTION_CHANCE = 50  # Percentage chance to roll for an affliction
AFFLICTION_FILE = "afflictions.json"
LOG_FILE = "log.txt"


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


class AfflictionBot:
    """Main bot class to handle Discord interactions and affliction management."""

    def __init__(self):
        """Initialize the bot with required configurations and load afflictions."""
        # Load environment variables
        dotenv.load_dotenv()

        # Setup console and logging
        self.console = Console()
        self.logger = Logger(LOG_FILE)

        # Load afflictions
        self.afflictions = self._load_json_afflictions()
        self.rarity_list = [("rare", "sparkles"), ("ultra rare", "star2")]

        # Configure Discord client
        intents = discord.Intents(messages=True, guilds=True)
        intents.message_content = True
        self.client = discord.Client(intents=intents)
        self.tree = app_commands.CommandTree(self.client)

        # Register commands and events
        self._register_commands()
        self._register_events()

    def _load_json_afflictions(self) -> List[Affliction]:
        """
        Load afflictions from a JSON file.
        
        :return: 
            A list of Affliction objects
        """
        try:
            with open(AFFLICTION_FILE, 'r') as f:
                raw_data = json.load(f)

                afflictions: List[Affliction] = []
                for item in raw_data:
                    if not all(key in item for key in ["name", "description", "rarity"]):
                        self.console.print(f"[yellow]Warning: Skipping invalid affliction entry: {item}")
                        self.logger.log(f"Skipping invalid affliction entry: {item}", "Json")
                        continue

                    affliction: Affliction = Affliction.from_dict(item)
                    afflictions.append(affliction)

                return afflictions

        except FileNotFoundError:
            self.console.print(f"[red bold]Error: {AFFLICTION_FILE} not found", justify="center")
            exit(1)

        except json.JSONDecodeError:
            self.console.print(f"[red bold]Error: {AFFLICTION_FILE} is not a valid JSON file", justify="center")
            exit(1)

        except Exception as e:
            self.console.print(f"[red bold]Error loading afflictions: {e}", justify="center")
            exit(1)

    def _register_commands(self):
        """Register all Discord slash commands."""

        @self.tree.command(name="roll-affliction", description="Rolls for afflictions affecting your Parasaurolophus")
        @app_commands.describe(para="Your Parasaurolophus")
        async def roll_affliction(interaction: discord.Interaction, para: str = None):
            try:
                afflictions: List[Affliction] = self._roll_for_afflictions()

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

                self.logger.log(f"{para} rolled {len(afflictions)} afflictions: \n{afflictions}",
                                "Bot")
                await interaction.response.send_message(response)

            except Exception as e:
                self.logger.log(f"Error in roll_affliction: {e}", "Bot")
                await interaction.response.send_message("An error occurred while rolling for afflictions",
                                                        ephemeral=True)

        @self.tree.command(name="list-afflictions", description="Lists all available afflictions")
        async def list_afflictions(interaction: discord.Interaction):
            try:
                response = "**Available Afflictions:**"

                common = sorted([a for a in self.afflictions if a.rarity.lower() == "common"],
                                key=lambda a: a.name.lower())
                uncommon = sorted([a for a in self.afflictions if a.rarity.lower() == "uncommon"],
                                  key=lambda a: a.name.lower())
                rare = sorted([a for a in self.afflictions if a.rarity.lower() == "rare"], key=lambda a: a.name.lower())
                ultra_rare = sorted([a for a in self.afflictions if a.rarity.lower() == "ultra rare"],
                                    key=lambda a: a.name.lower())

                sorted_afflictions = common + uncommon + rare + ultra_rare

                for affliction in sorted_afflictions:
                    self.console.print(affliction.name)
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
                found_affliction = self._find_affliction(affliction)

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

    def _register_events(self):
        """Register Discord client events."""

        @self.client.event
        async def on_ready():
            self.console.clear()
            self.console.rule(f"{self.client.user.name}")

            self.console.print(f"Bot activated as {self.client.user}", justify="center")
            self.logger.log(f"{self.client.user.name} has logged in as {self.client.user}", "Bot")

            self.console.print("Connected Guilds:")
            self.logger.log(f"{self.client.user.name} connected to {len(self.client.guilds)} guilds:", "Bot")

            for guild in self.client.guilds:
                member_str = f"{guild.member_count} member{'s' if guild.member_count > 1 else ''}"
                self.console.print(f"    * [green]Guild: {guild.name} ({guild.id}) {member_str}")
                self.logger.log(f"    * Guild: {guild.name} ({guild.id}) {member_str}", "Bot")

            await self.tree.sync()
            self.console.print("[green]Command tree synced", justify="center")
            self.logger.log("Command tree synced", "Bot")

    def _roll_for_afflictions(self) -> List[Affliction]:
        """
        Roll for afflictions based on the configured chance and rarity.
        
        Returns:
            A list of afflictions the character has
        """
        result = []
        available_afflictions = self.afflictions.copy()

        # Roll for each possible affliction
        for _ in range(len(self.afflictions)):
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
                    self.console.print("[red]Error: Rarity weights must sum to 100", justify="center")
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

    def _find_affliction(self, search_term: str) -> Optional[Affliction]:
        """
        Find an affliction by a search term.
        
        Args:
            search_term: The term to search for
            
        Returns:
            The full affliction string if found, None otherwise
        """
        search_term = search_term.lower()

        for affliction in self.afflictions:
            name = affliction.lower()
            if search_term in name or search_term == name.split()[0]:
                return affliction

        return None

    def _get_rarity_emoji(self, rarity: str) -> str:
        for r, emoji in self.rarity_list:
            if rarity.lower() == r.lower():
                return f":{emoji}:"

        else:
            return ""

    def run(self):
        """Run the Discord bot."""
        if len(sys.argv) >= 2 and sys.argv[1] == "-P":
            token = os.getenv("PRODUCTION_TOKEN")
        else:
            token = os.getenv("TEST_TOKEN")
        if not token:
            self.console.print("[red bold]Error: Discord TOKEN not found in environment variables", justify="center")
            exit(1)

        self.client.run(token)


if __name__ == "__main__":
    bot = AfflictionBot()
    bot.run()
