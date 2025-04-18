"""
Discord bot for the Parasaurolophus herd Longcrest Fellowship on the Path of Titans server Dynasty Realism.
Discord: https://discord.gg/mgSZqp9PFD

The bot handles affliction management for Parasaurolophus characters with the following commands:
    - /roll_affliction: Rolls for the afflictions that affect your Parasaurolophus
    - /list_afflictions: Lists all the available afflictions
    - /info [affliction]: Describes the supplied affliction if it exists
    
All afflictions are stored in a text file called afflictions.txt in the format: [affliction name] - [description]
"""
import os
import sys
import json
import random
import warnings
from typing import List, Optional

import discord
from discord import app_commands
import dotenv
from rich.console import Console

from logger import Logger

# Constants
AFFLICTION_CHANCE = 25  # Percentage chance to roll for an affliction
AFFLICTION_FILE = "afflictions.txt"
LOG_FILE = "log.txt"


def get_affliction_name(affliction: str) -> str:
    """Extract and format the name portion of an affliction."""
    return affliction.split(' - ')[0].replace('_', ' ').title()


def get_affliction_description(affliction: str) -> str:
    """Extract the description portion of an affliction."""
    parts = affliction.split(' - ', 1)
    return parts[1] if len(parts) > 1 else ""


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

        # Configure Discord client
        intents = discord.Intents(messages=True, guilds=True)
        intents.message_content = True
        self.client = discord.Client(intents=intents)
        self.tree = app_commands.CommandTree(self.client)

        # Register commands and events
        self._register_commands()
        self._register_events()

    def _load_json_afflictions(self) -> List[Affliction]:
        try:
            with open("afflictions.json", 'r') as f:
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

        @self.tree.command(name="roll_affliction", description="Rolls for afflictions affecting your Parasaurolophus")
        async def roll_affliction(interaction: discord.Interaction):
            try:
                afflictions: List[Affliction] = self._roll_for_afflictions()

                if not afflictions:
                    self.logger.log(f"{interaction.user.name} rolled no afflictions.", "Bot")
                    await interaction.response.send_message("You have **no** afflictions")
                    return

                if len(afflictions) == 1:
                    self.logger.log(f"{interaction.user.name} rolled 1 affliction: {afflictions[0].name}", "Bot")
                    await interaction.response.send_message(
                        f"You have **{afflictions[0].name}** - {afflictions[0].description}")
                    return

                response = "You have the following afflictions:"
                for affliction in afflictions:
                    response += f"\n- **{affliction.name.title()}** - {affliction.description}"

                self.logger.log(f"{interaction.user.name} rolled {len(afflictions)} afflictions: \n{afflictions}",
                                "Bot")
                await interaction.response.send_message(response)

            except Exception as e:
                self.logger.log(f"Error in roll_affliction: {e}", "Bot")
                await interaction.response.send_message("An error occurred while rolling for afflictions",
                                                        ephemeral=True)

        @self.tree.command(name="list_afflictions", description="Lists all available afflictions")
        async def list_afflictions(interaction: discord.Interaction):
            try:
                response = "**Available Afflictions:**"

                for affliction in self.afflictions:
                    self.console.print(affliction.name)
                    response += f"\n- **{affliction.name.title()}** | Run /info {affliction.name.lower().split(' ')[0]}"

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
        Roll for afflictions based on the configured chance.
        
        Returns:
            A list of afflictions the character has
        """
        result = []
        available_afflictions = self.afflictions.copy()

        # Roll for each possible affliction
        for _ in range(len(self.afflictions)):
            if not available_afflictions:
                break

            if random.random() < AFFLICTION_CHANCE / 100:
                choice = random.choice(available_afflictions)
                result.append(choice)
                available_afflictions.remove(choice)
            else:
                # Stop rolling once we fail a roll
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
