import random
from typing import List

import discord


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
    """
    For slots, we need the bet, the user, and the dictionary of user balances so we can update the users balance
    """

    message: discord.Message

    def __init__(self, user: discord.User, bet: int, users_dict: dict[int, int], minimum_bet: int):
        self.user: discord.User = user
        self.bet: int = bet
        self.users_dict: dict[int, int] = users_dict
        self.minimum_bet: int = minimum_bet

        self.slot_emoji = [
            ":moneybag:", ":gem:", ":four_leaf_clover:", ":star:", ":slot_machine:"
        ]
        self.special_emoji = [
            ":star2:"
        ]

        self.round_income = 0
        self.user_gross_income = 0
        self.rolled_slots: List[str] = []
        self.view = SlotsView(self._spin_callback)

    async def run(self, interaction):
        self._spin()
        await interaction.response.send_message(embed=self._get_embed(), view=self.view)
        self.message: discord.Message = await interaction.original_response()

    async def _spin_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Only the user that started the game can play.", ephemeral=True)
            return

        if self.users_dict[self.user.id] < self.minimum_bet:
            await interaction.response.send_message("Huh, looks like your all out of money.", ephemeral=True)
            return
        self._spin()

        await self.message.edit(embed=self._get_embed(), view=self.view)
        await interaction.response.defer()

    def _spin(self):
        weights = [1, 2, 3, 4, 5]  # emoji[0] is rarest, emoji[3] is most common
        self.rolled_slots = random.choices(self.slot_emoji, weights=weights, k=3)
        self._calculate_payout()

    def _get_embed(self) -> discord.Embed:
        embed_description: str = "Press the button to spin the slots!"
        slots_padding: int = round((len(embed_description) / 2 - len(" | ".join('⠀'))) + 1)
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
        :return: 
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
                self._update_money(profit)
                won = True
                break

        # If no winning combination found
        if not won:
            self.round_income = 0
            self.users_dict[self.user.id] -= self.bet

    def _update_money(self, profit):
        self.user_gross_income += profit
        self.round_income = profit
        self.users_dict[self.user.id] += profit
