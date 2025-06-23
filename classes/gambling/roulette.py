import asyncio
import random
from typing import Optional, Literal, List

import discord

from classes.saving import Data

class Player:
    def __init__(self, user: discord.User, bet: int, bet_type: str):
        self.user: discord.User = user
        self.bet: int = bet
        self.bet_type: str = bet_type
        self.payout: int = 0

    def calculate_payout(self):
        """
        Calculate the payout based on the bet type.
        The payout is calculated as follows:
        - Straight Up: 35:1
        - Split: 17:1
        - Street: 11:1
        - Corner: 8:1
        - Line: 5:1
        - Red/Black, Odd/Even, High/Low, Dozens: 1:1
        
        Sets the payout variable to the calculated payout.
        """
        if self.bet_type in "red black even odd low high".split():
            self.payout = self.bet * 2
        elif self.bet_type in "dozen1 dozen2 dozen3".split():
            self.payout = self.bet * 3
        elif self.bet_type == "green":
            self.payout = self.bet * 35


class RouletteJoinView(discord.ui.View):
    def __init__(self, roulette_instance):
        super().__init__(timeout=180)
        self.values: dict[str, str] = {}
        self.roulette_instance: Roulette = roulette_instance
        self.last_interaction: Optional[discord.Interaction] = None
        self.last_message_id: int = 0
        self.bet_types: dict[str, str] = roulette_instance.bet_types

        bet_type_select = discord.ui.Select(
            placeholder="Select a bet type",
            options=[
                discord.SelectOption(label=label, value=value) for value, label in self.bet_types.items()
            ]
        )
        bet_type_select.callback = self._bet_type_callback
        self.add_item(bet_type_select)

    async def _bet_type_callback(self, interaction: discord.Interaction):
        self.values["bet_type"] = interaction.data.get("values")[0]
        print(self.values)
        self.clear_items()

        amount_button = discord.ui.Button(label="Enter Bet Amount", style=discord.ButtonStyle.primary)
        amount_button.callback = self._amount_callback
        self.add_item(amount_button)

        await interaction.response.edit_message(embed=self.embed("amount"), view=self)

    async def _amount_callback(self, interaction: discord.Interaction):
        self.last_interaction = interaction
        self.last_message_id = interaction.message.id
        await interaction.response.send_modal(BetAmountModal(self._submit_amount_callback, self.values,
                                                             self.roulette_instance.data.get_user_balance(interaction.user.id),
                                                             self.roulette_instance.min_bet))

    async def _submit_amount_callback(self):
        print(self.values)
        self.clear_items()

        submit_button = discord.ui.Button(label="Submit", style=discord.ButtonStyle.success)
        submit_button.callback = self._submit_callback
        self.add_item(submit_button)

        cancel_button = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.danger)
        cancel_button.callback = self._cancel_callback
        self.add_item(cancel_button)

        await self.last_interaction.followup.edit_message(message_id=self.last_message_id, embed=self.embed("submit"),
                                                          view=self)

    def embed(self, action: Literal["select", "amount", "submit", "done", "canceled"] = "select") -> discord.Embed:
        if action == "select":
            embed = discord.Embed(
                title="Select a bet type",
                description="Select a bet type from the dropdown menu below.",
                color=discord.Color.blue()
            )
            embed.set_footer(text="Select a bet type to continue.")
        elif action == "amount":
            embed = discord.Embed(
                title="Enter your bet amount",
                description="Enter your bet amount in the modal below.",
                color=discord.Color.blue()
            )
            embed.add_field(name="Bet Type", value=self.bet_types[self.values["bet_type"]], inline=True)
            embed.set_footer(text="Enter your bet amount to continue.")
        elif action == "submit":
            embed = discord.Embed(
                title="Submit your bet",
                description="Click the button below to submit your bet.",
                color=discord.Color.blue()
            )
            embed.add_field(name="Bet Type", value=self.bet_types[self.values["bet_type"]], inline=True)
            embed.add_field(name="Bet Amount", value=self.values["bet_amount"], inline=True)
            embed.set_footer(text="Click 'Submit' to continue. Click cancel to cancel your bet.")
        elif action == "done":
            embed = discord.Embed(
                title="Bet Submitted",
                description="Your bet has been submitted. Funds removed from account.",
                color=discord.Color.green()
            )
        elif action == "canceled":
            embed = discord.Embed(
                title="Bet Canceled",
                description="Your bet has been canceled.",
                color=discord.Color.red()
            )

        else:
            embed = discord.Embed(
                title="How the hell did you do this? Action is a literal with specific handled values!",
                description="This is a bug, please report it to the developer.",
                color=discord.Color.red()
            )

        return embed

    async def _submit_callback(self, interaction: discord.Interaction):
        # Add the player to the game
        player = Player(interaction.user, int(self.values["bet_amount"]), self.values["bet_type"])
        player_balance = self.roulette_instance.data.get_user_balance(interaction.user.id)
        self.roulette_instance.data.set_user_balance(interaction.user.id, player_balance - player.bet)
        self.roulette_instance.players.append(player)

        # Update the original message
        await self.roulette_instance.update_message("queue")

        # Update the current view
        self.clear_items()
        await interaction.response.edit_message(embed=self.embed("done"), view=self)

    async def _cancel_callback(self, interaction: discord.Interaction):
        self.clear_items()
        await interaction.response.edit_message(embed=self.embed("canceled"), view=self)


class BetAmountModal(discord.ui.Modal):
    def __init__(self, callback, values: dict[str, str], user_balance: int, min_bet: int):
        super().__init__(title="Enter Bet Amount")
        self.amount = discord.ui.TextInput(label="Bet Amount",
                                           placeholder=f"Balance: {user_balance}, Min Bet: {min_bet}", required=True)
        self.add_item(self.amount)

        self.submit_callback = callback
        self.min_bet = min_bet
        self.user_balance = user_balance
        self.values = values

    async def on_submit(self, interaction: discord.Interaction):
        try:
            bet_amount = int(self.amount.value)
            if bet_amount < self.min_bet:
                await interaction.response.send_message(
                    f"Bet amount must be at least the minimum bet.\n-# Minimum Bet: {self.min_bet}", ephemeral=True)
                return
            elif bet_amount > self.user_balance:
                await interaction.response.send_message(
                    f"Bet amount must be less than your balance.\n-# Balance: {self.user_balance}", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("Bet amount must be a number.", ephemeral=True)
            return

        await interaction.response.defer()

        self.values["bet_amount"] = str(bet_amount)
        await self.submit_callback()


class Roulette:
    def __init__(self, host: discord.User, hosts_bet: int, hosts_bet_type: str, bet_types: dict[str, str],
                 data: Data, verify_callback: callable, min_bet: int):
        """
        The class that is used to play roulette.
        :param host: The user object that is the person that ran the original command
        :param hosts_bet: The hosts bet
        :param hosts_bet_type: The option that host bet on
        :param bet_types: The bet types that are available to the players
        :param data: The data class that the root bot uses for saving data
        :param min_bet: The minimum bet (Per Server)
        """
        self.data = data
        self.host = Player(host, hosts_bet, hosts_bet_type)  # The person that started the game
        self.players: List[Player] = [self.host]
        self.min_bet = min_bet
        self.verify_callback = verify_callback

        self.message: discord.Message  # the root message that all updates are sent to
        self.bet_types: dict[str, str] = bet_types

        self.rolled_color = ""  # The color that is rolled at the end of the game
        self.rolled_number = 0  # The number that is rolled at the end of the game
        self.game_over = False

        self.countdown = 60  # Game Start countdown in seconds

        # Setting up the buttons for start, join, and cancel
        self.view = discord.ui.View(timeout=180)
        self.view.on_timeout = self._on_timeout

        # The start button
        start_button = discord.ui.Button(label="Start", style=discord.ButtonStyle.success)
        start_button.callback = self._start_callback
        self.view.add_item(start_button)

        # The join button
        join_button = discord.ui.Button(label="Join", style=discord.ButtonStyle.primary)
        join_button.callback = self._join_callback
        self.view.add_item(join_button)

        # The cancel button
        cancel_button = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.danger)
        cancel_button.callback = self._cancel_callback
        self.view.add_item(cancel_button)

    async def run(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self._get_embed("queue"), view=self.view)
        # Store the message after it's sent
        self.message = await interaction.original_response()

        # Wait for the countdown to finish. If the host presses start it will skip it
        while self.countdown > 0:
            # If the game is over we don't want to do anything
            if self.game_over:
                return

            # Update the displayed countdown every 5 seconds, unless it's the final 5 seconds where we update every second
            if self.countdown % 5 == 0 or self.countdown < 5:
                await self.message.edit(embed=self._get_embed("queue"), view=self.view)
            # Sleeping for one second. We use asyncio.sleep instead of time.sleep to not block the event loop
            await asyncio.sleep(1)
            self.countdown -= 1

        # Clear the view so that the buttons are removed
        self.view.clear_items()
        # Roll the values and calculate payouts!
        self._roll_values()
        self._handle_payout()

        # Set the old message the ended embed so the user knows that the game is over
        await self.message.edit(embed=self._get_embed("ended"), view=self.view)

        # send the message containing results, mentioning the players that participated
        await self.message.reply(content=", ".join([player.user.mention for player in self.players]),
                                 embed=self._get_embed("finished"), view=self.view)

    def _roll_values(self):
        """
        Rolls a random number and color for the roulette game.
        The rolled number is between 0 and 36, inclusive.
        The rolled color is either "red", "black", or "green".
        """
        self.rolled_number = random.randint(0, 36)
        if self.rolled_number == 0:
            self.rolled_color = "green"
        elif self.rolled_number % 2 == 0:
            self.rolled_color = "red"
        else:
            self.rolled_color = "black"

    async def _cancel_game(self):
        self.game_over = True
        await self.update_message("canceled")

    async def _on_timeout(self):
        if not self.game_over:
            await self._cancel_game()

    def _get_embed(self, status: Literal["play", "finished", "canceled", "queue", "ended"]) -> discord.Embed:
        # Queue Embed
        if status == "queue":
            embed = discord.Embed(
                title="Roulette",
                description=f"Join the game by clicking the button below!\n\n-# The game starts in {self.countdown} seconds.",
                color=discord.Color.blue()
            )
            # List players participating
            for player in self.players:
                embed.add_field(
                    name=f"{player.user.display_name} {':crown:' if self.players.index(player) == 0 else ''}",
                    value=f"Bet: {player.bet} on {self.bet_types[player.bet_type]}", inline=False)
            embed.set_footer(text="Click 'Join' to participate.")
        # Canceled Embed
        elif status == "canceled":
            self.view = None
            embed = discord.Embed(
                title="Roulette (Canceled)",
                description="The game has been canceled",
                color=discord.Color.red()
            )
        # Finished Embed
        elif status == "finished":
            embed = discord.Embed(
                title="Roulette",
                description=f"The ball landed on :{self.rolled_color if self.rolled_color != 'black' else f'{self.rolled_color}_large'}_square: {self.rolled_number}.",
                color=discord.Color.red() if self.rolled_color == 'red' else discord.Color.greyple() if self.rolled_color == 'black' else discord.Color.green()
            )
            # Display the users if there are any
            winners = [player for player in self.players if player.payout > 0]
            if winners:
                winner_text = "\n".join(
                    [f"🎉 {player.user.display_name}: +{player.payout} :cherries:" for player in winners])
                embed.add_field(name="Winners", value=winner_text, inline=False)
            else:
                embed.add_field(name="Results", value="No winners this round!", inline=False)
        # Ended embed. Just a small one to let them know to look at the message
        elif status == "ended":
            embed = discord.Embed(
                title="Roulette (Game Ended)",
                description=f"The game has ended. Check post with your name mentioned to see the results!",
                color=discord.Color.greyple()
            )
        else:
            self.view = None
            embed = discord.Embed(
                title="How the hell did you do this one!",
                description="I could have sworn this wasn't possible. Hmm...",
                color=discord.Color.red()
            )
        return embed

    def _handle_payout(self):
        # Looping through every player
        for player in self.players:
            # if they bet the color
            player_balance = self.data.get_user_balance(player.user.id)
            if player.bet_type == self.rolled_color:
                player.calculate_payout()
                self.data.set_user_balance(player.user.id, player_balance + player.payout)
            # If they bet even and it was even
            elif player.bet_type == "even" and self.rolled_number % 2 == 0:
                player.calculate_payout()
                self.data.set_user_balance(player.user.id, player_balance + player.payout)
            # If they bet odd and it was odd
            elif player.bet_type == "odd" and self.rolled_number % 2 != 0:
                player.calculate_payout()
                self.data.set_user_balance(player.user.id, player_balance + player.payout)
            # If they bet low, and it was in the low range (lower than 19)
            elif player.bet_type == "low" and self.rolled_number <= 18:
                player.calculate_payout()
                self.data.set_user_balance(player.user.id, player_balance + player.payout)
            # If they bet high, and it was in the high range (higher than 18)
            elif player.bet_type == "high" and self.rolled_number > 18:
                player.calculate_payout()
                self.data.set_user_balance(player.user.id, player_balance + player.payout)
            # If they bet dozen1, and it was in the first dozen (1-12)
            elif player.bet_type == "dozen1" and 1 <= self.rolled_number <= 12:
                player.calculate_payout()
                self.data.set_user_balance(player.user.id, player_balance + player.payout)
            # If they bet dozen2, and it was in the second dozen (13-24)
            elif player.bet_type == "dozen2" and 13 <= self.rolled_number <= 24:
                player.calculate_payout()
                self.data.set_user_balance(player.user.id, player_balance + player.payout)
            # If they bet dozen3, and it was in the third dozen (25-36)
            elif player.bet_type == "dozen3" and 25 <= self.rolled_number <= 36:
                player.calculate_payout()
                self.data.set_user_balance(player.user.id, player_balance + player.payout)
            # If their bet was not right, set their payout to a negative value. Unused if negative, but may be used later if I want to
            else:
                player.payout = - player.bet

    async def update_message(self, action: Literal["play", "finished", "canceled", "queue"], interaction=None):
        await self.message.edit(embed=self._get_embed(action), view=self.view)

    async def _join_callback(self, interaction: discord.Interaction):
        if interaction.user.id in [player.user.id for player in self.players]:
            await interaction.response.send_message("You are already in the game!", ephemeral=True)
            return

        self.verify_callback(interaction.user.id, interaction.guild_id)

        view = RouletteJoinView(self)
        await interaction.response.send_message(embed=view.embed(), view=view, ephemeral=True)

    async def _start_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.players[0].user.id:
            await interaction.response.send_message("Only host can start the game", ephemeral=True)
            return
        self.countdown = 0
        # Defer is basically like saying, we got it but, we don't need to send anything
        await interaction.response.defer()

    async def _cancel_callback(self, interaction: discord.Interaction):
        for player in self.players:
            if interaction.user.id == player.user.id:
                player_balance = self.data.get_user_balance(player.user.id)
                self.data.set_user_balance(player.user.id, player_balance + player.bet)
                self.players.remove(player)
                await interaction.response.send_message("You left the game. Bet refunded", ephemeral=True)
                await self.update_message("queue", interaction)

                break

        if len(self.players) == 0:
            self.game_over = True
            await self.update_message("canceled", interaction)
