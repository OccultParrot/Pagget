import asyncio
import enum
from asyncio import timeout
from typing import List, Literal

import discord

import database_utils
import models


class RouletteBet(enum.Enum):
    RED = "red"
    BLACK = "black"
    GREEN = "green"
    EVEN = "even"
    ODD = "odd"
    LOW = "1-18"
    HIGH = "19-36"
    DOZEN1 = "1-12"
    DOZEN2 = "13-24"
    DOZEN3 = "25-36"


class RouletteColors(enum.Enum):
    RED = "red"
    BLACK = "black"
    GREEN = "green"


class Player:
    def __init__(self, user: discord.User, bet: int, bet_type: RouletteBet):
        self.user: discord.User = user
        self.bet: int = bet
        self.bet_type: RouletteBet = bet_type
        self.payout = 0

    def calculate_payout(self):
        if self.bet_type in [RouletteBet.RED, RouletteBet.BLACK, RouletteBet.EVEN, RouletteBet.ODD, RouletteBet.LOW,
                             RouletteBet.HIGH]:
            self.payout = self.bet * 2
        elif self.bet_type in [RouletteBet.DOZEN1, RouletteBet.DOZEN2, RouletteBet.DOZEN3]:
            self.payout = self.bet * 3
        elif self.bet_type == RouletteBet.GREEN:
            self.payout = self.bet * 35


class Roulette:
    message: discord.Message

    def __init__(self, host: discord.User, hosts_bet: int, hosts_bet_type: RouletteBet,
                 database: database_utils.DatabaseClient, server: models.Server):
        self.database: database_utils.DatabaseClient = database
        self.players: List[Player] = [
            Player(
                user=host,
                bet=hosts_bet,
                bet_type=hosts_bet_type
            )]

        self.server: models.Server = server

        self.rolled_color: RouletteColors = RouletteColors.RED
        self.rolled_number: int = 0
        self.is_game_over: bool = False

        self.countdown = 60  # How long the game will wait for other to join before starting

        # Settings up buttons for start, join, and cancel
        self.view = discord.ui.View(timeout=100)

        # Start button
        start_button = discord.ui.Button(label="Start", style=discord.ButtonStyle.success)
        start_button.callback = self._start_callback
        self.view.add_item(start_button)

        # Join button
        join_button = discord.ui.Button(label="Join", style=discord.ButtonStyle.blurple)
        join_button.callback = self._join_callback
        self.view.add_item(join_button)

        # Cancel button
        cancel_button = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.danger)
        cancel_button.callback = self._cancel_callback
        self.view.add_item(cancel_button)

    async def run(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self.get_embed("queue"), view=self.view)

        self.message = await interaction.original_response()

        while self.countdown > 0:
            if self.is_game_over:
                return

            if self.countdown % 5 == 0 or self.countdown < 5:
                await self.update_message("queue")
                await asyncio.sleep(5)
                self.countdown -= 1

        self.view.clear_items()
        self.roll_values()
        self.handle_payout()

        await self.update_message("ended")

        await self.message.reply(content=", ".join([p.user.mention for p in self.players]),
                                 embed=self.get_embed("finished"), view=self.view)
        
    async def update_message(self, action):
        await self.message.edit(embed=self.get_embed(action), view=self.view)

    def get_embed(self, action: Literal["play", "finished", "canceled", "queue", "ended"]) -> discord.Embed:
        match action:
            case "queue":
                embed = discord.Embed(
                    title="Roulette Queue",
                    description=f"Join the game by clicking the button below!\n\n-# The game starts in {self.countdown} seconds.",
                    color=discord.Color.blurple()
                )
                for i, player in enumerate(self.players):
                    embed.description += f"\n\n{player.user.display_name} {':crown:' if i == 0 else ''} {player.bet_type.name}"
                embed.set_footer(text="Click 'Join' to participate!")
            case "cancel":
                self.view = None
                embed = discord.Embed(
                    title="Roulette Cancelled",
                    description="The game has been cancelled.",
                    color=discord.Color.red()
                )
            case "finished":
                emoji = f":{self.rolled_color if self.rolled_color != 'black' else f'{self.rolled_color}_large'}_square:"
                color = discord.Color.red() if self.rolled_color == 'red' else discord.Color.greyple() if self.rolled_color == 'black' else discord.Color.green()
                embed = discord.Embed(
                    title="Roulette Finished",
                    description=f"The ball landed on {emoji} {self.rolled_number}.",
                    color=color
                )
                winners = [p for p in self.players if p.payout > 0]
                if winners:
                    winner_text = "\n".join(
                        [f"🎉 {player.user.display_name}: +{player.payout} :cherries:" for player in winners])
                    embed.add_field(name="Winners", value=winner_text, inline=False)
                else:
                    embed.add_field(name="Results", value="No winners this round!", inline=False)
            case "ended":
                embed = discord.Embed(
                    title="Roulette (Game Ended)",
                    description=f"The game has ended. Check post with your name mentioned to see the results!",
                    color=discord.Color.greyple()
                )
            case _:
                self.view = None
                embed = discord.Embed(
                    title="How the hell did you do this one!",
                    description="I could have sworn this wasn't possible. Hmm...",
                    color=discord.Color.red()
                )

        return embed

    async def _join_callback(self, interaction: discord.Interaction):
        if interaction.user.id in [p.user.id for p in self.players]:
            await interaction.response.send_message("You are already in the game!", ephemeral=True)
            return

        view = RouletteJoinView(self)
        await interaction.response.send_message(embed=view.embed(), view=view, ephemeral=True)

    async def _start_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.players[0].user.id:
            await interaction.response.send_message("Only the host can start the game.", ephemeral=True)
            return

        self.countdown = 0
        # Defer tells discord we got it, but we won't reply
        await interaction.response.defer()

    async def _cancel_callback(self, interaction: discord.Interaction):
        for player in self.players:
            if interaction.user.id == player.user.id:
                self.players.remove(player)
                await interaction.response.send_message("You left the game.", ephemeral=True)
                await self.update_message("queue")

        if len(self.players) < 1:
            self.is_game_over = True
            await self.update_message("canceled")


class RouletteJoinView(discord.ui.View):
    def __init__(self, game: Roulette):
        super().__init__()
