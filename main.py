import os
from code import interact
from typing import Optional

import discord
import math
from discord import Client, app_commands

import gathers
import models
import afflictions as af
from blackjack import Blackjack
from roulette import RouletteBet, Roulette
from database_utils import DatabaseClient
from slots import Slots


class Pagget(Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.messages = True
        intents.message_content = True
        super().__init__(intents=intents)

        self.database = DatabaseClient()
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        self._register_commands()
        print(f"Syncing command tree")
        await self.tree.sync()

    async def on_ready(self):
        print(f"Logged in as {self.user.display_name} | {self.user.id}")

    def _register_commands(self):
        @self.tree.command(name="set-configs",
                           description="Sets the guild configuration. Dont enter any changes to view the current configuration")
        @app_commands.describe(chance="Percent chance of rolling afflictions (0-100)",
                               minor_chance="Percent chance of rolling minor afflictions (0-100)")
        @app_commands.checks.has_permissions(administrator=True)
        async def set_configs(interaction: discord.Interaction, chance: int = None,
                              minor_chance: bool = None, starting_pay: int = None, minimum_bet: int = None):
            try:
                server = self.database.get_server(interaction.guild_id, interaction.guild.name)

                if server is None:
                    server = models.Server(
                        id=interaction.guild_id,
                        name=interaction.guild.name,
                    )

                if chance is not None:
                    server.affliction_chance = chance / 100
                if minor_chance is not None:
                    server.minor_affliction_chance = minor_chance / 100
                if starting_pay is not None:
                    server.starting_pay = starting_pay
                if minimum_bet is not None:
                    server.minimum_bet = minimum_bet

                self.database.add_server(server)

                embed = discord.Embed(title=f"{interaction.guild.name}'s Configuration",
                                      description="Guild configuration has been updated.")
                embed.add_field(name="Affliction Chance", value=f"{server.chance}%",
                                inline=False)
                embed.add_field(name="Minor Affliction Chance",
                                value=f"{server.minor_chance}%", inline=False)
                embed.add_field(name="Starting Pay", value=f"{server.starting_pay}",
                                inline=False)
                embed.add_field(name="Minimum Bet", value=f"{server.minimum_bet}",
                                inline=False)

                await interaction.response.send_message(f"Guild configuration updated.", embed=embed, ephemeral=True)

            except Exception as e:
                print(f"Error in set_configs command! {e}")
                await interaction.response.send_message("An error occurred while setting the guild configuration",
                                                        ephemeral=True)

        self.tree.add_command(self._register_affliction_commands())
        self.tree.add_command(self._register_berry_commands())
        self.tree.add_command(self._register_gambling_commands())

    def _register_affliction_commands(self) -> app_commands.Group:
        group = app_commands.Group(name="affliction", description="Affliction commands")

        async def roll(interaction: discord.Interaction, dino: str, chance: float, season: models.Season,
                       affliction_pool: list[models.Affliction]):
            dino = dino.title()

            afflictions: list[models.Affliction] = af.roll_afflictions(affliction_pool, chance, season)

            if not afflictions:
                await interaction.response.send_message(f"{dino} has **no** afflictions")
                return

            if len(afflictions) == 1:
                await interaction.response.send_message(
                    f"{dino} has **{afflictions[0].title}**.",
                    embed=af.get_embed(afflictions[0])
                )
                return

            await interaction.response.send_message(f"{dino} has the following afflictions:",
                                                    embeds=[af.get_embed(a) for a in afflictions])

        @group.command(name="roll", description="Rolls for afflictions affecting your dinosaur")
        @app_commands.describe(dino="Your dinosaur's name", roll_type="The type of affliction you are rolling for",
                               season="The season the server is")
        @app_commands.choices(season=[
            app_commands.Choice(name="Spring", value="spring"),
            app_commands.Choice(name="Summer", value="summer"),
            app_commands.Choice(name="Winter", value="winter"),
            app_commands.Choice(name="Fall", value="fall"),
        ], roll_type=[
            app_commands.Choice(name="General", value="general"),
            app_commands.Choice(name="Minor", value="minor"),
            app_commands.Choice(name="Birth Defect", value="birth"),
        ])
        @app_commands.checks.cooldown(1, 3600, key=lambda i: i.user.id)  # Uncomment to enable cooldown
        async def roll_general(interaction: discord.Interaction, dino: str, roll_type: str, season: str):
            server: models.Server = self.database.get_server(interaction.guild_id, interaction.guild.name)
            server_afflictions: list[models.Affliction] = self.database.get_afflictions(server.id)

            if roll_type == "birth":
                affliction_pool = [a for a in server_afflictions if a.is_birth_defect]
            elif roll_type == "minor":
                affliction_pool = [a for a in server_afflictions if a.is_minor]
            else:
                affliction_pool = [a for a in server_afflictions if not a.is_birth_defect]

            await roll(
                interaction,
                dino,
                server.minor_affliction_chance if roll_type == "minor" else server.affliction_chance,
                models.Season(season),
                affliction_pool
            )

        @group.command(name="list", description="Lists all available afflictions")
        @app_commands.describe(page="What page to display")
        async def list_afflictions(interaction: discord.Interaction, page: int = 1):
            server: models.Server = self.database.get_server(interaction.guild_id, interaction.guild.name)
            server_afflictions: list[models.Affliction] = self.database.get_afflictions(server.id)
            sorted_afflictions: list[models.Affliction] = af.list_afflictions(server_afflictions)

            pages = math.ceil(len(sorted_afflictions) / 10)

            if page < 1 or page > pages:
                await interaction.response.send_message(
                    f"Page {page} does not exist. There are only {pages} pages."
                )
                return

            start = (page - 1) * 10
            end = start + 10
            sorted_afflictions = sorted_afflictions[start: end]

            embeds = [af.get_embed(a) for a in sorted_afflictions]

            if embeds:
                embeds[-1].set_footer(text=f"Page {page}/{pages}")

            await interaction.response.send_message(f"**Available Afflictions:** (Page {page}/{pages})", embeds=embeds)

        @group.command(name="add", description="Adds a new affliction to the database")
        @app_commands.describe(name="Name of the affliction", description="Description of the affliction",
                               rarity="Rarity of the affliction",
                               is_minor="Whether the affliction is minor or not. ONLY AFFECTS COMMON RARITY",
                               is_birth_defect="Whether the affliction is birth defect",
                               seasons="Seasons that the affliction can occur. Separate with commas (,) and type any for any season")
        @app_commands.choices(
            rarity=[
                app_commands.Choice(name="Common", value="common"),
                app_commands.Choice(name="Uncommon", value="uncommon"),
                app_commands.Choice(name="Rare", value="rare"),
                app_commands.Choice(name="Legendary", value="legendary")
            ]
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def add_affliction(
                interaction: discord.Interaction,
                name: str, description: str,
                rarity: str, is_minor: bool = False,
                is_birth_defect: bool = False, seasons: str = "any"):
            if af.affliction_exists(name, self.database.get_afflictions(interaction.guild_id)):
                await interaction.response.send_message(f"Affliction `{name}` already exists.", ephemeral=True)
                return

            seasons_input = [s.strip().lower() for s in seasons.split(",")]
            valid_season_values = [s.value for s in models.Season]
            invalid_seasons = [s for s in seasons_input if s not in valid_season_values]

            if invalid_seasons:
                await interaction.response.send_message(
                    f"Invalid seasons: `{', '.join(invalid_seasons)}`. Valid options are: `{', '.join(valid_season_values)}`",
                    ephemeral=True
                )
                return

            new_affliction = models.Affliction(
                id=-1,  # Temporary setting of ID, we discard this value and use databases generated serial
                server_id=-1,  # We discard this one too
                title=name,
                description=description,
                rarity=models.Rarity(rarity),
                is_minor=is_minor,
                is_birth_defect=is_birth_defect,
                seasons=[models.Season(s) for s in seasons_input],
            )
            self.database.add_affliction(interaction.guild_id, new_affliction)

            await interaction.response.send_message(f"Affliction `{name}` added.", embed=af.get_embed(new_affliction),
                                                    ephemeral=True)

        @group.command(name="remove", description="Removes an affliction from the list")
        @app_commands.describe(affliction_id="The ID of the affliction")
        @app_commands.checks.has_permissions(administrator=True)
        async def remove_affliction(interaction: discord.Interaction, affliction_id: int):
            affliction = self.database.get_affliction(affliction_id)
            self.database.remove_affliction(affliction_id)
            await interaction.response.send_message(f"Affliction {affliction.title} removed.", ephemeral=True)

        @remove_affliction.autocomplete("affliction_id")
        async def remove_affliction_autocomplete(interaction: discord.Interaction, current: str):
            return await affliction_autocomplete(interaction, current)

        @group.command(name="edit", description="Edits an affliction")
        @app_commands.describe(affliction_id="The ID of the affliction",
                               name="Name of the affliction", description="Description of the affliction",
                               rarity="Rarity of the affliction",
                               is_minor="Whether the affliction is minor or not. ONLY AFFECTS COMMON RARITY",
                               is_birth_defect="Whether the affliction is birth defect",
                               seasons="Seasons that the affliction can occur. Separate with commas (,) and type any for any season")
        @app_commands.choices(
            rarity=[
                app_commands.Choice(name="Common", value="common"),
                app_commands.Choice(name="Uncommon", value="uncommon"),
                app_commands.Choice(name="Rare", value="rare"),
                app_commands.Choice(name="Legendary", value="legendary")
            ]
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def edit_affliction(interaction: discord.Interaction,
                                  affliction_id: int, name: str = None, description: str = None,
                                  rarity: str = None, is_minor: bool = None, is_birth_defect: bool = None,
                                  seasons: str = None):
            afflictions = self.database.get_afflictions(interaction.guild_id)
            if af.affliction_exists(name, afflictions):
                await interaction.response.send_message(f"Affliction `{name}` already exists.", ephemeral=True)
                return

            original_affliction = next((a for a in afflictions if a.id == affliction_id), None)
            if original_affliction is None:
                await interaction.response.send_message(f"Affliction `{affliction_id}` does not exist.", ephemeral=True)
                return

            seasons_input = [s.strip().lower() for s in seasons.split(",")]
            valid_season_values = [s.value for s in models.Season]
            invalid_seasons = [s for s in seasons_input if s not in valid_season_values]

            if invalid_seasons:
                await interaction.response.send_message(
                    f"Invalid seasons: `{', '.join(invalid_seasons)}`. Valid options are: `{', '.join(valid_season_values)}`",
                    ephemeral=True
                )
                return

            new_affliction = models.Affliction(
                id=affliction_id,
                server_id=original_affliction.server_id,
                title=name if name is not None else original_affliction.title,
                description=description if description is not None else original_affliction.description,
                rarity=models.Rarity(rarity) if rarity is not None else original_affliction.rarity,
                is_minor=is_minor if is_minor is not None else original_affliction.is_minor,
                is_birth_defect=is_birth_defect if is_birth_defect is not None else original_affliction.is_birth_defect,
                seasons=[models.Season(s) for s in
                         seasons_input] if seasons is not None else original_affliction.seasons
            )

            self.database.edit_affliction(interaction.guild_id, affliction_id, new_affliction)

        @edit_affliction.autocomplete("affliction_id")
        async def edit_affliction_autocomplete(interaction: discord.Interaction, current: str):
            return await affliction_autocomplete(interaction, current)

        async def affliction_autocomplete(interaction: discord.Interaction, current: str):
            filtered = [
                a for a in self.database.get_afflictions(interaction.guild_id)
                if a.title.startswith(current)
            ]
            return [
                app_commands.Choice(
                    name=f"Title: {a.title} | ID: {a.id}",
                    value=a.id
                ) for a in filtered[:25]
            ]

        return group

    def _register_berry_commands(self) -> app_commands.Group:
        group = app_commands.Group(name="berries", description="Berry commands")

        async def gather(interaction: discord.Interaction, outcomes, target: Optional[discord.Member]):
            old_balance = self.database.get_berries_balance(interaction.user.id, interaction.guild_id)
            outcome: models.GatherOutcome = gathers.roll_gathering_outcome(outcomes)

            if target is None:
                # Just gather, ignore robberies
                pass
            else:
                if target.id == interaction.user.id:
                    await interaction.response.send_message("You can't steam from yourself! Try hunting instead.",
                                                            ephemeral=True)
                    return
                target_balance = self.database.get_berries_balance(target.id, interaction.guild_id)
                if target_balance <= 0:
                    await interaction.response.send_message(f"{target.display_name} has no berries to steal from.",
                                                            ephemeral=True)
                    return

                if outcome.value >= 0:
                    actual_steal_amount = min(outcome.value, target_balance)
                else:
                    actual_steal_amount = outcome.value

                target_new_balance = target_balance - actual_steal_amount

                outcome.value = actual_steal_amount
                self.database.set_berries_balance(target.id, interaction.guild_id, target_new_balance)

            new_balance = old_balance + outcome.value
            self.database.set_berries_balance(interaction.user.id, interaction.guild_id, new_balance)

            await interaction.response.send_message(
                embed=gathers.get_embed(outcome, old_balance, new_balance, target, interaction),
                ephemeral=False
            )

        @group.command(name="hunt", description="Hunt for some berries")
        @app_commands.checks.cooldown(1, 43200, key=lambda i: i.user.id)
        async def hunt(interaction: discord.Interaction):
            outcomes = self.database.get_gather_outcomes(interaction.guild_id)
            await gather(interaction, [o for o in outcomes if not o.is_robbery], None)

        @group.command(name="steal", description="Steal some berries")
        @app_commands.describe(target="User to steal from")
        @app_commands.checks.cooldown(1, 43200, key=lambda i: i.user.id)
        async def steal(interaction: discord.Interaction, target: discord.Member):
            outcomes = self.database.get_gather_outcomes(interaction.guild_id)
            await gather(interaction, [o for o in outcomes if o.is_robbery], target)

        @group.command(name="balance", description="Check your berry balance")
        @app_commands.checks.cooldown(1, 120, key=lambda i: i.user.id)
        async def balance(interaction: discord.Interaction):
            current_balance = self.database.get_berries_balance(interaction.user.id, interaction.guild_id)

            embed = discord.Embed(
                title=":cherries: Berry Balance",
                description=f"You currently have **{current_balance}** berries.",
                color=discord.Color.blue()
            )

            await interaction.response.send_message(embed=embed, ephemeral=False)

        @group.command(name="gift", description="Gift some berries to another user")
        @app_commands.describe(target="User to gift to", amount="The amount of berries to give")
        @app_commands.checks.cooldown(1, 120, key=lambda i: i.user.id)
        async def gift(interaction: discord.Interaction, target: discord.Member, amount: int):
            old_balance = self.database.get_berries_balance(interaction.user.id, interaction.guild_id)
            target_balance = self.database.get_berries_balance(target.id, interaction.guild_id)

            if amount < 1:
                await interaction.response.send_message("You can't send less than 1 berry.", ephemeral=True)
                return
            if amount > old_balance:
                await interaction.response.send_message(
                    f"You dont have enough berries to gift that much. \n-# Your balance: {old_balance}.",
                    ephemeral=True)
                return

            new_balance = old_balance - amount
            target_new_balance = target_balance + amount

            self.database.set_berries_balance(interaction.user.id, interaction.guild_id, new_balance)
            self.database.set_berries_balance(target.id, interaction.guild_id, target_new_balance)

            await interaction.response.send_message(
                f"{interaction.user.display_name} gave {target.display_name} {amount} berries.", ephemeral=False)

        @group.command(name="set", description="Sets the balance of a user")
        @app_commands.describe(target="User to set", new_balance="The new balance of the user")
        @app_commands.checks.has_permissions(administrator=True)
        async def set_balance(interaction: discord.Interaction, target: discord.Member, new_balance: int):
            self.database.set_berries_balance(interaction.user.id, interaction.guild_id, new_balance)
            await interaction.response.send_message(f"Set {target.display_name} balance to {new_balance}.",
                                                    ephemeral=True)

        @group.command(name="leaderboard", description="Show a leaderboard of who has the most berries")
        @app_commands.checks.cooldown(1, 120, key=lambda i: i.user.id)
        async def leaderboard(interaction: discord.Interaction):
            embed = discord.Embed(title="━━━ Berries Leaderboard ━━━", description="", color=discord.Color.blue())

            sorted_berries = sorted(self.database.get_berries(interaction.guild_id), key=lambda u: u.balance,
                                    reverse=True)

            for i, user in enumerate(sorted_berries):
                if i > min(10, len(sorted_berries)):
                    break
                member = interaction.guild.get_member(user.id)
                if not member:
                    continue
                elif member.id == self.user.id:
                    continue
                embed.description += f"{i + 1} | {':crown:' if i == 0 else ''} {member.display_name} {user.balance}\n"
                i += 1

            await interaction.response.send_message(embed=embed, ephemeral=False)

        return group

    def _register_gambling_commands(self) -> app_commands.Group:
        group = app_commands.Group(name="gambling", description="Gambling commands")

        @group.command(name="roulette", description="Play roulette with your berries")
        @app_commands.describe(bet="Amount of berries to bet")
        @app_commands.choices(
            bet_type=[
                app_commands.Choice(
                    name=bet.value.title(), value=bet.name
                ) for bet in RouletteBet
            ]
        )
        @app_commands.checks.cooldown(1, 120, key=lambda i: i.user.id)
        async def roulette(interaction: discord.Interaction, bet: int, bet_type: str):
            server = self.database.get_server(interaction.guild_id, interaction.guild.name)
            user_balance = self.database.get_berries_balance(interaction.user.id, interaction.guild_id)
            if bet > user_balance:
                await interaction.response.send_message(
                    f"You dont have enough berries to bet that much.\n-# You have {user_balance} berries.",
                    ephemeral=True)
                return

            if bet < server.minimum_bet:
                await interaction.response.send_message(
                    f"You bet *{bet}*, but the minimum bet is **{server.minimum_bet}**.",
                    ephemeral=True)

            self.database.add_berries_balance(interaction.user.id, interaction.guild_id, -bet)
            game = Roulette(interaction.user, bet, RouletteBet(bet_type), self.database, server)
            await game.run(interaction)

        @group.command(name="slots", description="Play slots with your berries")
        @app_commands.describe(bet="Amount of berries to bet")
        @app_commands.checks.cooldown(1, 120, key=lambda i: i.user.id)
        async def slots(interaction: discord.Interaction, bet: int):
            server = self.database.get_server(interaction.guild_id, interaction.guild.name)
            user_balance = self.database.get_berries_balance(interaction.user.id, interaction.guild_id)
            if bet > user_balance:
                await interaction.response.send_message(
                    f"You dont have enough berries to bet that much.\n-# You have {user_balance} berries.",
                    ephemeral=True)
                return

            if bet < server.minimum_bet:
                await interaction.response.send_message(
                    f"You bet *{bet}*, but the minimum bet is **{server.minimum_bet}**.",
                    ephemeral=True)
                return

            game = Slots(interaction.user, bet, self.database, server)
            await game.run(interaction)

        @group.command(name="blackjack", description="Play blackjack with your berries")
        @app_commands.describe(bet="Amount of berries to bet")
        @app_commands.checks.cooldown(1, 120, key=lambda i: i.user.id)
        async def blackjack(interaction: discord.Interaction, bet: int):
            server = self.database.get_server(interaction.guild_id, interaction.guild.name)
            user_balance = self.database.get_berries_balance(interaction.user.id, interaction.guild_id)
            if bet > user_balance:
                await interaction.response.send_message(
                    f"You dont have enough berries to bet that much.\n-# You have {user_balance} berries.",
                    ephemeral=True)
                return

            if bet < server.minimum_bet:
                await interaction.response.send_message(
                    f"You bet *{bet}*, but the minimum bet is **{server.minimum_bet}**.", ephemeral=True)
                return

            self.database.add_berries_balance(interaction.user.id, interaction.guild_id, -bet)
            game = Blackjack(interaction.user, bet, self.database, server)
            await game.run(interaction)

        return group

if __name__ == '__main__':
    Pagget().run(os.environ['DISCORD_TOKEN'])
