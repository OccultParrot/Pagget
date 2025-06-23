import atexit
import json
import math
import os
import random
import sys
from typing import List, Optional, Literal

import discord
import dotenv
import requests
from discord import app_commands
from rich.console import Console

from classes.afflictions import AfflictionController
from classes.gambling import Roulette, Blackjack, Slots
from classes.logger import Logger
from classes.permissions import has_admin_check
from classes.saving import Data
from classes.typepairs import Affliction, GuildConfig, GatherOutcome

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
        await interaction[0].response.send_message("An error occurred while running the command",
                                                   ephemeral=True)


def get_paths(directory_name: str, guild_id: int) -> (str, str):
    return os.path.join(DATA_DIRECTORY, directory_name), os.path.join(DATA_DIRECTORY, directory_name,
                                                                      f"{guild_id}.json")


def get_outcome_color(value: int) -> discord.Color:
    if value < 0:
        return discord.Color.red()
    elif value == 0:
        return discord.Color.greyple()
    else:
        return discord.Color.green()


def get_outcome_embed(gather_type: Literal["hunt", "steal"], outcome: GatherOutcome, old_balance: int, new_balance: int,
                      target: Optional[discord.Member], interaction: discord.Interaction) -> discord.Embed:
    """Create a Discord embed for a hunt outcome."""

    embed = discord.Embed(
        title=f"Successful {gather_type.title()}!" if outcome.value > 0 else f"Failed {gather_type.title()}!",
        description=outcome.description.format(target=target.display_name.split(' |')[
            0] if target else "", value=abs(outcome.value)) + f"{f'\n-# Target: {target.display_name}\n' if target else ''}",
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


def organise_rarities(dictionary: dict[int, List[Affliction | GatherOutcome]], index: int):
    commons = [item for item in dictionary[index] if item.rarity.lower() == "common"]
    uncommons = [item for item in dictionary[index] if
                 item.rarity.lower() == "uncommon"]
    rares = [item for item in dictionary[index] if item.rarity.lower() == "rare"]
    ultra_rares = [item for item in dictionary[index] if
                   item.rarity.lower() == "ultra rare"]

    return [commons, uncommons, rares, ultra_rares], [60, 25, 10, 5]


class Pagget:
    """Main bot class to handle Discord interactions and affliction management."""

    def __init__(self):
        """Initialize the bot with required configurations and load afflictions."""
        # Load environment variables
        dotenv.load_dotenv()

        # Setup console and logging
        self.console = Console()
        self.logger = Logger(LOG_FILE)

        # Data class
        self.data: Data = Data()

        self.roulette_bet_types: dict[str, str] = {
            "red": "Red",
            "black": "Black",
            "green": "Green",
            "even": "Even",
            "odd": "Odd",
            "low": "1-18",
            "high": "19-36",
            "dozen1": "1-12",
            "dozen2": "13-24",
            "dozen3": "25-36"
        }

        # Configure Discord client
        intents = discord.Intents(messages=True, guilds=True, members=True)
        intents.message_content = True
        self.client = discord.Client(intents=intents)
        self.tree = app_commands.CommandTree(self.client)

        # Clear any existing commands if we're syncing
        if any(arg == "--sync" for arg in sys.argv):
            self.tree.clear_commands(guild=None)  # Clear before registering

        # Register commands and events
        self._register_commands()
        self._register_events()

    def _register_commands(self):
        """Register all Discord slash commands."""

        @self.tree.command(name="set-configs",
                           description="Sets the guild configuration. Dont enter any changes to view the current configuration")
        @app_commands.describe(species="Species of the dinosaur",
                               chance="Percent chance of rolling afflictions (0-100)",
                               minor_chance="Percent chance of rolling minor afflictions (0-100)")
        @app_commands.checks.has_permissions(administrator=True)
        async def set_configs(interaction: discord.Interaction, species: str = None, chance: int = None,
                              minor_chance: bool = None, starting_pay: int = None, minimum_bet: int = None):
            try:
                guild_config: GuildConfig = self.data.get_guild_config(interaction.guild_id)

                if species is not None:
                    guild_config.species = species
                if chance is not None:
                    guild_config.chance = chance
                if minor_chance is not None:
                    guild_config.minor_chance = minor_chance
                if starting_pay is not None:
                    guild_config.starting_pay = starting_pay
                if minimum_bet is not None:
                    guild_config.minimum_bet = minimum_bet

                self.data.set_guild_config(interaction.guild_id, guild_config)

                embed = discord.Embed(title=f"{interaction.guild.name}'s Configuration",
                                      description="Guild configuration has been updated.")
                embed.add_field(name="Species", value=guild_config.species, inline=False)
                embed.add_field(name="Affliction Chance", value=f"{guild_config.chance}%",
                                inline=False)
                embed.add_field(name="Minor Affliction Chance",
                                value=f"{guild_config.minor_chance}%", inline=False)
                embed.add_field(name="Starting Pay", value=f"{guild_config.starting_pay}",
                                inline=False)
                embed.add_field(name="Minimum Bet", value=f"{guild_config.minimum_bet}",
                                inline=False)

                await interaction.response.send_message(f"Guild configuration updated.", embed=embed, ephemeral=True)
                self.logger.log(f"{interaction.user.name} updated guild configuration for guild {interaction.guild_id}",
                                "Bot")

            except Exception as e:
                self.logger.log(f"Error in set_configs: {e}", "Bot")
                await interaction.response.send_message("An error occurred while setting the guild configuration",
                                                        ephemeral=True)

        set_configs.error(self.command_error_handler)

        # Add affliction commands to the tree
        self.tree.add_command(self._register_affliction_commands())

        # Add the berry commands to the command tree
        self.tree.add_command(self._register_berry_commands())

        # @self.tree.add_command(name="help")

    def _register_affliction_commands(self) -> app_commands.Group:
        group = app_commands.Group(name="affliction", description="Affliction commands")

        async def roll(interaction: discord.Interaction, dino: str, chance: float, is_minor: bool):
            afflictions = AfflictionController.roll(self.data.get_affliction_list(interaction.guild_id), chance,
                                                    is_minor)

            dino = dino.capitalize()

            if not afflictions:
                await interaction.response.send_message(f"{dino} has **no** afflictions")
                return

            if len(afflictions) == 1:
                await interaction.response.send_message(
                    f"{dino} has **{afflictions[0].name}**.",
                    embed=AfflictionController.get_embed(afflictions[0])
                )
                return

            await interaction.response.send_message(f"{dino} has the following afflictions:",
                                                    embeds=[AfflictionController.get_embed(affliction) for affliction in
                                                            afflictions])

        @group.command(name="roll", description="Rolls for afflictions affecting your dinosaur")
        @app_commands.describe(dino="Your dinosaur's name")
        @app_commands.checks.cooldown(1, 3600, key=lambda i: i.user.id)  # Uncomment to enable cooldown
        async def roll_general(interaction: discord.Interaction, dino: str):
            await roll(interaction, dino, self.data.get_guild_config(interaction.guild_id).chance, False)

        @group.command(name="roll-minor", description="Rolls for minor afflictions affecting your dinosaur")
        @app_commands.describe(dino="Your dinosaur's name")
        @app_commands.checks.cooldown(1, 3600, key=lambda i: i.user.id)  # Uncomment to enable cooldown
        async def roll_minor(interaction: discord.Interaction, dino: str):
            await roll(interaction, dino, self.data.get_guild_config(interaction.guild_id).chance, True)

        @group.command(name="list", description="Lists all available afflictions")
        @app_commands.describe(page="What page to display")
        async def list_afflictions(interaction: discord.Interaction, page: int = 1):
            sorted_afflictions = AfflictionController.list_afflictions(
                self.data.get_affliction_list(interaction.guild_id),
                page)

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
            embeds = [AfflictionController.get_embed(affliction) for affliction in sorted_afflictions]

            # Add page number to the last embed's footer
            if embeds:
                embeds[-1].set_footer(text=f"Page {page}/{pages}")

            await interaction.response.send_message(f"**Available Afflictions:** (Page {page}/{pages})",
                                                    embeds=embeds)
            self.logger.log(f"{interaction.user.name} listed all afflictions", "Bot")

        @group.command(name="add", description="Adds a new affliction to the database")
        @app_commands.describe(name="Name of the affliction", description="Description of the affliction",
                               rarity="Rarity of the affliction",
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
        async def add_affliction(interaction: discord.Interaction, name: str, description: str,
                                 rarity: app_commands.Choice[str], is_minor: bool = False):
            # Check if the affliction already exists
            if self._if_affliction_exists(name, interaction.guild_id):
                await interaction.response.send_message(f"Affliction '{name}' already exists.", ephemeral=True)
                return

            new_affliction = Affliction(name=name, description=description, rarity=rarity.value, is_minor=is_minor)
            self.data.get_affliction_list(interaction.guild_id).append(new_affliction)

            await interaction.response.send_message(f"Affliction '{name}' added successfully.",
                                                    embed=AfflictionController.get_embed(new_affliction),
                                                    ephemeral=True)
            self.logger.log(f"{interaction.user.name} added affliction {name}", "Bot")

        @group.command(name="remove", description="Removes an affliction from the list")
        @app_commands.describe(name="Name of the affliction")
        @app_commands.checks.has_permissions(administrator=True)
        async def remove_affliction(interaction: discord.Interaction, name: str):
            # Check if the affliction does not exist
            if not self._if_affliction_exists(name, interaction.guild_id):
                await interaction.response.send_message(f"Affliction '{name}' does not exist.", ephemeral=True)
                return

            affliction_to_remove = self._get_affliction_from_name(name, interaction.guild_id)[0]
            self.data.get_affliction_list(interaction.guild_id).remove(affliction_to_remove)

            embed = AfflictionController.get_embed(affliction_to_remove)
            embed.set_footer(text="Affliction removed")

            await interaction.response.send_message(f"Affliction '{name}' removed successfully.", embed=embed,
                                                    ephemeral=True)
            self.logger.log(f"{interaction.user.name} removed affliction {name}", "Bot")

        @group.command(name="edit", description="Edits an affliction from the list")
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

            self.data.get_affliction_list(interaction.guild_id)[index] = affliction_to_edit

            await interaction.response.send_message(f"Affliction '{affliction}' edited successfully.",
                                                    embed=AfflictionController.get_embed(affliction_to_edit),
                                                    ephemeral=True)
            self.logger.log(f"{interaction.user.name} edited affliction {affliction}", "Bot")

        # --- Handling Errors --- #
        roll_general.error(self.command_error_handler)
        roll_minor.error(self.command_error_handler)
        list_afflictions.error(self.command_error_handler)
        add_affliction.error(self.command_error_handler)
        remove_affliction.error(self.command_error_handler)
        edit_affliction.error(self.command_error_handler)

        return group

    def _register_berry_commands(self) -> app_commands.Group:
        """Register berry-related commands as a command group."""

        # Create the berries group and add it to the command tree
        berries_group = app_commands.Group(name="berries", description="Berry commands")

        async def gather(interaction: discord.Interaction, gather_type: Literal["hunt", "steal"],
                         target: Optional[discord.Member]):
            old_balance = self._validate_user(interaction.user.id, interaction.guild_id)
            outcome: GatherOutcome = self._roll_for_gathering_occurrence(interaction.guild_id, gather_type)

            # If we steal, we need to remove the berries from the target's balance, but cant put them in negatives
            if gather_type == "steal" and target:
                if target.id == interaction.user.id:
                    await interaction.response.send_message(
                        "You cannot steal from yourself! Try hunting instead.",
                        ephemeral=True)
                    return
                target_balance = self._validate_user(target.id, interaction.guild_id)
                if target_balance <= 0:
                    await interaction.response.send_message(
                        f"{target.display_name} has no berries to steal from.",
                        ephemeral=True)
                    return

                # Calculate how much we can actually steal (don't go below 0)
                if outcome.value >= 0:
                    actual_steal_amount = min(outcome.value, target_balance)
                else:
                    actual_steal_amount = outcome.value
                target_new_balance = target_balance - actual_steal_amount

                print(
                    f"Target balance: {target_balance}, Attempted steal: {outcome.value}, Actual steal: {actual_steal_amount}")
                print(f"Target new balance: {target_new_balance}")

                # Update the outcome value to reflect what was actually stolen
                outcome.value = actual_steal_amount

                self.data.set_user_balance(target.id, target_new_balance)

            self.data.set_user_balance(interaction.user.id,
                                       self.data.get_user_balance(interaction.user.id) + outcome.value)
 
            await interaction.response.send_message(
                embed=get_outcome_embed(gather_type, outcome, old_balance,
                                        self.data.get_user_balance(interaction.user.id),
                                        target if target else None, interaction),
                ephemeral=False)

        @berries_group.command(name="hunt", description="Hunt for some berries")
        @app_commands.checks.cooldown(1, 43200, key=lambda i: i.user.id)  # Uncomment to enable cooldown
        async def hunt(interaction: discord.Interaction):
            await gather(interaction, "hunt", None)

        @berries_group.command(name="steal", description="Attempt to steal berries from the herd")
        @app_commands.describe(target="User to steal from")
        @app_commands.checks.cooldown(1, 43200, key=lambda i: i.user.id)  # Uncomment to enable cooldown
        async def steal(interaction: discord.Interaction, target: discord.Member):
            await gather(interaction, "steal", target)

        @berries_group.command(name="balance", description="Check your berry balance")
        @app_commands.checks.cooldown(5, 120, key=lambda i: i.user.id)  # Uncomment to enable cooldown
        async def balance(interaction: discord.Interaction):
            # Retrieve user's current balance
            current_balance = self._validate_user(interaction.user.id, interaction.guild_id)

            embed = discord.Embed(
                title="🍒 Berry Balance",
                description=f"You currently have **{current_balance}** berries.",
                color=discord.Color.blue()
            )

            await interaction.response.send_message(embed=embed, ephemeral=False)

        @berries_group.command(name="gift", description="Gift berries to another user")
        @app_commands.describe(user="User to gift berries to", amount="Amount of berries to gift")
        @app_commands.checks.cooldown(5, 60, key=lambda i: i.user.id)  # Uncomment to enable cooldown
        async def gift_berries(interaction: discord.Interaction, user: discord.Member, amount: int):
            # Initialize user
            self._validate_user(user.id, interaction.guild_id)

            # Check if the user has enough berries
            if amount > self._validate_user(interaction.user.id, interaction.guild_id):
                await interaction.response.send_message(
                    f"You don't have enough berries to gift that much.\n-# Your balance: {self._validate_user(interaction.user.id, interaction.guild_id)}.",
                    ephemeral=True)
                return
            if amount < 1:
                await interaction.response.send_message(
                    f"You can't gift less than 1 berry.",
                    ephemeral=True)
                return
            # Deduct berries from the user's balance
            user_balance = self.data.get_user_balance(interaction.user.id)
            recipient_balance = self.data.get_user_balance(user.id)

            self.data.set_user_balance(interaction.user.id, user_balance - amount)
            self.data.set_user_balance(user.id, recipient_balance + amount)

            # Let them know that berries were gifted
            await interaction.response.send_message(
                f"{interaction.user.display_name.split(' |')[0]} gave {user.display_name.split(' |')[0]} {amount} berries!")

        @berries_group.command(name="set", description="Set the balance of a user")
        @app_commands.describe(user="User to edit balance", new_balance="New balance")
        @app_commands.checks.has_permissions(administrator=True)
        async def set_berries(interaction: discord.Interaction, user: discord.Member, new_balance: int):
            # Initialize user
            self._validate_user(user.id, interaction.guild_id)

            # Add berries to the user's balance
            self.data.set_user_balance(user.id, new_balance)

            await interaction.response.send_message(f"Added {new_balance} berries to {user.name}'s balance.",
                                                    ephemeral=True)

        # Handling errors
        hunt.error(self.command_error_handler)
        steal.error(self.command_error_handler)
        balance.error(self.command_error_handler)
        set_berries.error(self.command_error_handler)

        # Add gambling commands to the berries group
        berries_group.add_command(self._register_gambling_commands())

        return berries_group

    def _register_gambling_commands(self) -> app_commands.Group:
        gambling_group = app_commands.Group(name="gambling", description="Gambling commands")

        @gambling_group.command(name="roulette", description="Play roulette with your berries")
        @app_commands.describe(bet="Amount of berries to bet")
        @app_commands.choices(
            bet_type=[
                app_commands.Choice(name=name, value=value) for value, name in self.roulette_bet_types.items()
            ]
        )
        @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)  # Uncomment to enable cooldown
        async def roulette(interaction: discord.Interaction, bet: int, bet_type: str):
            if bet > self._validate_user(interaction.user.id, interaction.guild_id):
                await interaction.response.send_message(
                    f"You don't have enough berries to bet that much.\n-# Your balance: {self._validate_user(interaction.user.id, interaction.guild_id)}.",
                    ephemeral=True)
                return
            if self.data.get_guild_config(interaction.guild_id).minimum_bet > bet:
                await interaction.response.send_message(
                    f"You bet *{bet}*, but the minimum bet is **{self.data.get_guild_config(interaction.guild_id).minimum_bet}**.")
                return

            balance = self.data.get_user_balance(interaction.user.id)

            self.data.set_user_balance(interaction.user.id, balance - bet)

            game = Roulette(interaction.user, bet, bet_type, self.roulette_bet_types, self.data,
                            self._validate_user,
                            self.data.get_guild_config(interaction.guild_id).minimum_bet)
            await game.run(interaction)

        @gambling_group.command(name="slots", description="Play slots with your berries")
        @app_commands.describe(bet="Amount of berries to bet")
        @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)  # Uncomment to enable cooldown
        async def slots(interaction: discord.Interaction, bet: int):
            if bet > self._validate_user(interaction.user.id, interaction.guild_id):
                await interaction.response.send_message(
                    f"You don't have enough berries to bet that much.\n-# Your balance: {self._validate_user(interaction.user.id, interaction.guild_id)}.",
                    ephemeral=True)
                return
            if self.data.get_guild_config(interaction.guild_id).minimum_bet > bet:
                await interaction.response.send_message(
                    f"You bet *{bet}*, but the minimum bet is **{self.data.get_guild_config(interaction.guild_id).minimum_bet}**.",
                    ephemeral=True)
                return

            game = Slots(interaction.user, bet, self.data,
                         self.data.get_guild_config(interaction.guild_id).minimum_bet)
            await game.run(interaction)

        @gambling_group.command(name="blackjack", description="Play blackjack with your berries")
        @app_commands.describe(bet="Amount of berries to bet")
        @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)  # Uncomment to enable cooldown
        async def blackjack(interaction: discord.Interaction, bet: int):
            # If the minimum bet is greater than the bet, or the bet is greater than the user's balance, return an error
            if bet > self._validate_user(interaction.user.id, interaction.guild_id):
                await interaction.response.send_message(
                    f"You don't have enough berries to bet that much.\n-# Your balance: {self._validate_user(interaction.user.id, interaction.guild_id)}.",
                    ephemeral=True)
                return
            if self.data.get_guild_config(interaction.guild_id).minimum_bet > bet:
                await interaction.response.send_message(
                    f"You bet *{bet}*, but the minimum bet is **{self.data.get_guild_config(interaction.guild_id).minimum_bet}**.",
                    ephemeral=True)
                return

            user_balance = self.data.get_user_balance(interaction.user.id)
            self.data.set_user_balance(interaction.user.id, user_balance - bet)

            game = Blackjack(interaction.user, bet, self.data.balances)
            await game.run(interaction)

        @roulette.error
        async def set_configs_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            await read_error([interaction], error, self.logger)

        @slots.error
        async def set_configs_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            await read_error([interaction], error, self.logger)

        @blackjack.error
        async def set_configs_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            await read_error([interaction], error, self.logger)

        return gambling_group

    async def command_error_handler(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        await read_error([interaction], error, self.logger)

    def _register_events(self):
        """Register Discord client events."""

        @self.client.event
        async def on_ready():
            # Clear all commands and re-sync
            
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

                    # Sets the initial indentation and path for items under this top-level group.
                    initial_sub_item_indent = "    "
                    sorted_sub_items = sorted(group.commands, key=lambda c: c.name)  # Sort sub-items
                    for sub_item in sorted_sub_items:
                        # Pass the group's name as the initial part of the path
                        self._print_command_item_recursive(sub_item, initial_sub_item_indent, [group.name])

            if standalone_commands:
                self.console.print("\n[green bold]Standalone Commands:[/]")
                for command in sorted(standalone_commands, key=lambda x: x.name):  # Sort standalone commands
                    try:
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

            # Load data and start autosaving
            self.data.load()
            self.data.start_autosave_thread()

            # Final ready message
            self.console.print("\n[bold green]Bot is ready and online![/]")
            self.logger.log("Bot is ready and online!", "Bot")

        @self.client.event
        async def on_message(message: discord.Message):
            favored_ones = [767047725333086209, 953401260306989118, 757757494192767017]

            if message.author == self.client.user:
                return

            # Handle messages here if needed
            if (any(mention.id == self.client.user.id for mention in message.mentions) and
                    message.content.startswith("-#")):
                await message.channel.send("-# What was that? I couldn't hear you.")

            # Only listen to the favored ones 😇
            if message.author.id in favored_ones:
                split_message = message.content.split(" ")
                if "berries pls" in message.content.lower():
                    if random.random() < 0.5:
                        amount = random.randint(1, 1000)
                        self.data.balances[message.author.id] = + amount
                        await message.channel.send(f"Ok poor boy, I'll give you *{amount}* berries")
                    else:
                        await message.channel.send(f"Bro, stop being such a whiner. Just work :skull:")

                for index, word in enumerate(split_message):
                    if (word == "bless" and
                            index + 2 < len(split_message) and
                            split_message[index + 1].strip() and
                            split_message[index + 2] == "with"):

                        blessed_one: int = 0

                        try:
                            # Striping the users id out of the mention
                            blessed_one = int(split_message[index + 1].translate(str.maketrans('', '', '<>@!')))
                            if blessed_one == message.author.id:
                                await message.channel.send(
                                    f"What on earth are you trying to do? Blessing your self?? smh")
                                break
                            if blessed_one == self.client.user.id:
                                await message.channel.send(
                                    "I really love that you are trying to bless me, it really is nice... but I dont need them.")
                                break

                        except ValueError:
                            print("Invalid mention")
                            break

                        if self._get_user_from_id(blessed_one, message.guild) is None:
                            print("Mentioned non existent user.")

                        blessing = split_message[index + 3]

                        try:
                            blessing = int(blessing)

                            blessing_messages = [
                                "{name}, I bless you with {blessing} berries... and stuff :/",
                                "-# psst {name} I am giving you {blessing} out of the goodness of my heart, they dont really control me :wink:",
                                "The skies open above {name} and rains berries. {name} picks up {blessing}.",
                                "Hey {name}, catch!\n-# {blessing} berries fly towards {name}"
                            ]

                            self._validate_user(blessed_one, message.guild.id)
                            self.data.balances[blessed_one] += blessing

                            await message.channel.send(random.choice(blessing_messages).format(
                                name=self._name_from_user(self._get_user_from_id(blessed_one, message.guild)),
                                blessing=blessing))
                        except ValueError:
                            await message.channel.send(
                                f"{self._name_from_user(self._get_user_from_id(blessed_one, message.guild))}, I bless you with {blessing}")
                
                # Helpful for seeing how many berries people have
                if "list berries" in message.content.lower():
                    channel = message.channel
                    send = ""
                    for key in self.data.balances.keys():
                        for user in message.guild.members:
                            if user.id == key:
                                send += f"{user.display_name.split(" |")[0]} has {self.data.balances[key]} berries\n"
                    await channel.send(send)
                    
                if "you suck" in message.content.lower() and "pagget" in message.content.lower():
                    channel = message.channel
                    await channel.send(":sob:")

    @staticmethod
    def _name_from_user(user: discord.User | discord.Member) -> str:
        return user.display_name.split(" |")[0]

    @staticmethod
    def _get_user_from_id(user_id: int, guild: discord.Guild) -> Optional[discord.Member]:
        for member in guild.members:
            print(member.display_name, ":", member.id)
            if member.id == user_id:
                return member

        return None

    def _print_command_item_recursive(self, command_item, base_indent_str, parent_group_path_parts_for_log):
        """
        Recursively prints a command item (command or group) and its children if it's a group.
        This is the core logic for handling nested groups.
        """
        prefix = "• "

        current_full_path_parts = parent_group_path_parts_for_log + [command_item.name]
        log_full_path = " ".join(current_full_path_parts)

        # Determine if the command requires admin privileges (ensure has_admin_check is accessible)
        try:
            # Assuming has_admin_check is defined elsewhere and accessible
            is_admin = has_admin_check(command_item)
        except NameError:
            # Fallback or default if it has_admin_check is not found - adjust as needed
            self.logger.log(
                f"Warning: has_admin_check function not found for command '{log_full_path}'. Assuming USER.", "Bot")
            is_admin = False

        admin_status = "[purple]ADMIN[/]" if is_admin else "[green]USER[/]"
        description = getattr(command_item, 'description', 'No description available')

        self.console.print(
            f"{base_indent_str}{prefix}[bold]{command_item.name}[/] {admin_status} - {description}"
        )

        item_type_for_log = "Sub-Group" if isinstance(command_item, app_commands.Group) else "Subcommand"
        self.logger.log(
            f"{base_indent_str}{prefix}{item_type_for_log}: /{log_full_path} {admin_status} - {description}",
            "Bot"
        )

        if isinstance(command_item, app_commands.Group):
            child_base_indent_str = base_indent_str + "  "

            sorted_sub_items = sorted(command_item.commands, key=lambda c: c.name)
            for sub_item in sorted_sub_items:
                self._print_command_item_recursive(sub_item, child_base_indent_str, current_full_path_parts)

    def _roll_for_afflictions(self, guild_id: int, is_minor: bool = False) -> List[Affliction]:
        """
        Roll for afflictions based on the configured chance and rarity.
        
        Returns:
            A list of afflictions the character has
        """
        result = []
        available_afflictions = self.data.get_affliction_list(guild_id).copy()

        # Roll for each possible affliction
        for _ in range(len(self.data.get_affliction_list(guild_id))):
            if not available_afflictions:
                break

            # Check if we get any affliction at all
            if random.random() < (
                    self.data.get_guild_config(guild_id).minor_chance if is_minor else self.data.get_guild_config(
                        guild_id).chance) / 100:
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

        for affliction in self.data.get_affliction_list(guild_id):
            name = affliction.name.lower()
            if search_term in name or search_term == name.split()[0]:
                return affliction

        return None

    def _roll_for_gathering_occurrence(self, guild_id: int, gather_type: Literal["hunt", "steal"]) -> GatherOutcome:
        """
        Roll for a hunting occurrence based on the configured chance.
        
        Returns:
            A HuntOutcome object representing the outcome of the hunt
        """
        if gather_type == "hunt":
            rarity_groups, rarity_weights = self.data.get_hunt_outcomes_and_weights(guild_id)
        else:
            rarity_groups, rarity_weights = self.data.get_steal_outcomes_and_weights(guild_id)

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
            (a, i) for i, a in enumerate(self.data.get_affliction_list(guild_id)) if
            a.name.lower() == affliction_name.lower())

    def _if_affliction_exists(self, affliction: str, guild_id: int) -> bool:
        """ Checks if affliction exists in the guild's affliction list """
        return any(a.name.lower() == affliction.lower() for a in self.data.get_affliction_list(guild_id))

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
        if user_id in self.data.balances:
            return self.data.balances[user_id]

        self.data.balances[user_id] = self.data.get_guild_config(guild_id).starting_pay
        self.console.print("User balance created:", user_id)
        self.logger.log(f"User balance created: {user_id}", "Bot")
        return self.data.get_guild_config(guild_id).starting_pay

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

        # Stop autosave thread if running
        self.data.stop_autosave_thread()
        self.data.save()

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
    Pagget().run()
