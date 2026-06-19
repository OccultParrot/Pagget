import random

import discord

import database_utils
import models


class SlotsView(discord.ui.View):
    def __init__(self, spin_callback: callable):
        super().__init__(timeout=180)

        spin_button = discord.ui.Button(style=discord.ButtonStyle.success, label="Spin!")
        spin_button.callback = spin_callback
        self.add_item(spin_button)

    def on_timeout(self) -> None:
        self.clear_items()
        self.stop()


class Slots:
    message: discord.Message

    def __init__(self, user: discord.User, bet: int, database: database_utils.DatabaseClient, server: models.Server):
        self.user = user
        self.bet = bet
        self.database = database
        self.server = server

        self.slot_emoji = [
            ":moneybag:", ":gem:", ":four_leaf_clover:", ":star:", ":slot_machine:"
        ]
        self.special_emoji = [
            ":star2:"
        ]

        self.round_income = 0
        self.user_gross_income = 0
        self.rolled_slots: list[str] = []
        self.view = SlotsView(self._spin_callback)

    async def run(self, interaction: discord.Interaction):
        self.spin()
        await interaction.response.send_message(embed=self.get_embed(), view=self.view)
        self.message = await interaction.original_response()

    def spin(self):
        weights = [1, 2, 3, 4, 5]  # emoji[0] is rarest, emoji[3] is most common
        self.rolled_slots = random.choices(self.slot_emoji, weights=weights, k=3)
        self._calculate_payout()

    def get_embed(self):
        embed_description: str = "Press the button to spin the slots!"
        slots_padding: int = round((len(embed_description) / 2 - len(' | '.join('⠀'))) + 1)
        embed = discord.Embed(
            title="Slots",
            # The character we are repeating for the padding is a no break space, which discord does not cut off the start of lines
            description=embed_description + f"\n\n{' ' * slots_padding}{' | '.join(self.rolled_slots)}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Bet Amount", value=self.bet)
        embed.add_field(name="Income this round", value=self.round_income)
        embed.add_field(name="Total Income", value=self.user_gross_income, inline=False)
        embed.set_footer(text="Click 'Spin!' to play.")
        return embed

    def _calculate_payout(self):
        """
        3 of highest symbol: 50-100x bet
        3 of high symbol: 20-30x bet
        3 of medium symbol: 10-15x bet
        3 of low symbols: 2-5x bet
        2 of highest: 2x bet
        Mixed combinations: 0.5x bet (or nothing)
        """
        if len(self.rolled_slots) == 0:
            return

        # Define payouts for each symbol (index) and count combination
        payouts = {
            (0, 3): 100,  # 3 moneybags
            (0, 2): 10,  # 2 moneybags
            (1, 3): 25,  # 3 gems
            (1, 2): 3,  # 2 gems
            (2, 3): 8,  # 3 clovers
            (2, 2): 1.5,  # 2 clovers
            (3, 3): 3,  # 3 stars
            (3, 2): 0.5,  # 2 stars
            (4, 3): 1.5,  # 3 slot machines
            (4, 2): 0.2  # 2 slot machines
        }

        # Check for winning combinations
        won = False
        for emoji_index, (symbol, count) in enumerate(
                [(emoji, self.rolled_slots.count(emoji)) for emoji in self.slot_emoji]):
            if (emoji_index, count) in payouts:
                multiplier = payouts[(emoji_index, count)]
                profit = round(self.bet * multiplier)
                self.update_money(profit)
                won = True
                break

        # If no winning combination found
        if not won:
            self.round_income = 0
            self.database.add_berries_balance(self.user.id, self.server.id, -self.bet)


    async def _spin_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Only the user that started the game can play.", ephemeral=True)
            return

        if self.database.get_berries_balance(self.user.id, self.server.id) < self.server.minimum_bet:
            await interaction.response.send_message("Huh, looks like your all out of money.", ephemeral=True)
            return
        self.spin()

        await self.message.edit(embed=self.get_embed(), view=self.view)
        await interaction.response.defer()

    def update_money(self, profit):
        self.user_gross_income += profit
        self.round_income = profit
        self.database.add_berries_balance(self.user.id, self.server.id, profit)