import random
from typing import Optional, Literal, List

import discord


class Card:
    def __init__(self, suit: Literal["hearts", "diamonds", "clubs", "spades"],
                 rank: Literal["2", "3", "4", "5", "6", "7", "8", "9", "10", "Jack", "Queen", "King", "Ace"]):
        self.suit = suit
        self.rank = rank

    def __str__(self):
        return f"{self.rank.title()} :{self.suit}:"

    def __int__(self):
        royals = ["jack", "queen", "king"]
        if self.rank.lower() in royals:
            return 10
        elif self.rank.lower() == "ace":
            return 11
        return int(self.rank)


class Blackjack:
    def __init__(self, user: discord.User, bet: int, users_dict: dict[int, int]):
        self.users_dict = users_dict
        self.user = user
        self.bet = bet
        self.game_over = False
        self.message: Optional[discord.Message] = None

        self.deck: List[Card] = []
        self.player_hand: List[Card] = []
        self.dealer_hand: List[Card] = []

        self._initialize_deck()
        self._initial_deal()

        self.view = discord.ui.View(timeout=180)
        self.view.on_timeout = self._on_timeout

        hit_button = discord.ui.Button(label="Hit", style=discord.ButtonStyle.primary)
        hit_button.callback = self._hit_callback
        self.view.add_item(hit_button)

        stand_button = discord.ui.Button(label="Stand", style=discord.ButtonStyle.success)
        stand_button.callback = self._stand_callback
        self.view.add_item(stand_button)

    def _initialize_deck(self):
        suits = ["hearts", "spades", "diamonds", "clubs"]

        for suit in suits:
            for rank in range(2, 11):
                self.deck.append(Card(suit, str(rank)))

            for rank in ["jack", "queen", "king", "ace"]:
                self.deck.append(Card(suit, rank))

        random.shuffle(self.deck)

    def _initial_deal(self):
        self.player_hand.append(self.deck.pop(0))
        self.player_hand.append(self.deck.pop(0))

        self.dealer_hand.append(self.deck.pop(0))
        self.dealer_hand.append(self.deck.pop(0))

        player_score = self._get_hand_score(self.player_hand)
        dealer_score = self._get_hand_score(self.dealer_hand)

        if player_score == 21 and dealer_score == 21:
            self.game_over = True
            self.result = "push"
        elif player_score == 21:
            self.game_over = True
            self.result = "blackjack"
        elif dealer_score == 21:
            self.game_over = True
            self.result = "dealer_blackjack"

    async def run(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self._get_embed("play"), view=self.view)

        if self.game_over:
            if hasattr(interaction, "original_response"):
                self.message = await interaction.original_response()
                await self._end_game()

    @staticmethod
    def _get_hand_score(hand: List[Card]) -> int:
        score = sum(int(card) for card in hand)

        ace_count = sum(1 for card in hand if card.rank == "ace")

        while score > 21 and ace_count > 0:
            score -= 10
            ace_count -= 1

        return score

    def _dealer_play(self):
        while self._get_hand_score(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deck.pop(0))

        dealer_score = self._get_hand_score(self.dealer_hand)
        player_score = self._get_hand_score(self.player_hand)

        if dealer_score > 21:
            self.result = "dealer_bust"
        elif dealer_score > player_score:
            self.result = "dealer_wins"
        elif dealer_score < player_score:
            self.result = "player_wins"
        else:
            self.result = "push"

    def _handle_payout(self):
        user_id = self.user.id

        if user_id not in self.users_dict:
            self.users_dict[user_id] = 0

        if self.result == "blackjack":
            self.users_dict[user_id] += int(self.bet * 2.5)
        elif self.result in ["player_wins", "dealer_bust"]:
            self.users_dict[user_id] += self.bet * 2
        elif self.result == "push":
            self.users_dict[user_id] += self.bet

    def _get_embed(self, status: Literal["play", "ended"]) -> discord.Embed:
        player_score = self._get_hand_score(self.player_hand)

        if status == "play" and not self.game_over:
            embed = discord.Embed(
                title="Blackjack",
                description="Try to get as close to 21 as you can, but don't go over!",
                color=discord.Color.blue()
            )
            embed.set_footer(text="Hit to draw another card. Stand to end your turn.")

            dealer_visible_score = int(self.dealer_hand[0])
            dealer_cards = f"{self.dealer_hand[0]} and 1 hidden card"

        else:
            dealer_score = self._get_hand_score(self.dealer_hand)
            dealer_visible_score = dealer_score
            dealer_cards = ", ".join(str(card) for card in self.dealer_hand)

            if hasattr(self, 'result'):
                if self.result == "blackjack":
                    title = "Blackjack! You Win!"
                    description = f"You got a blackjack! You won {int(self.bet * 1.5)} extra berries!"
                    color = discord.Color.gold()
                elif self.result == "dealer_blackjack":
                    title = "Dealer Blackjack! You Lose"
                    description = f"The dealer got a blackjack. You lost {self.bet} berries."
                    color = discord.Color.red()
                elif self.result == "player_wins":
                    title = "You Win!"
                    description = f"Your score was higher than the dealer. You won {self.bet} extra berries!"
                    color = discord.Color.green()
                elif self.result == "dealer_bust":
                    title = "Dealer Bust! You Win!"
                    description = f"The dealer went over 21. You won {self.bet} extra berries!"
                    color = discord.Color.green()
                elif self.result == "dealer_wins":
                    title = "Dealer Wins"
                    description = f"The dealer's score was higher. You lost {self.bet} berries."
                    color = discord.Color.red()
                elif self.result == "player_bust":
                    title = "Bust! You Lose"
                    description = f"You went over 21. You lost {self.bet} berries."
                    color = discord.Color.red()
                elif self.result == "push":
                    title = "Push (Tie)"
                    description = "It's a tie! Your bet has been returned."
                    color = discord.Color.light_grey()
            else:
                title = "Game Over"
                description = "The game has ended."
                color = discord.Color.light_grey()

            embed = discord.Embed(title=title, description=description, color=color)

        embed.add_field(name="Your Score", value=player_score, inline=True)
        embed.add_field(name="Dealer Score", value=dealer_visible_score, inline=True)
        embed.add_field(name="Your Bet", value=self.bet, inline=True)
        embed.add_field(name="Your Hand", value=", ".join(str(card) for card in self.player_hand), inline=False)
        embed.add_field(name="Dealer's Hand", value=dealer_cards, inline=False)

        return embed

    async def _update_message(self):
        if self.message:
            await self.message.edit(embed=self._get_embed("ended"), view=None)

    async def _end_game(self):
        self.game_over = True
        self._handle_payout()
        await self._update_message()

    async def _on_timeout(self):
        if not self.game_over:
            self.result = "timeout"
            await self._end_game()

    async def _hit_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Only the user that started the game can play.", ephemeral=True)
            return

        if not self.message:
            self.message = interaction.message

        if self.game_over:
            await interaction.response.send_message("This game has already ended.", ephemeral=True)
            return

        self.player_hand.append(self.deck.pop(0))
        player_score = self._get_hand_score(self.player_hand)

        if player_score > 21:
            self.result = "player_bust"
            self.game_over = True
            await interaction.response.defer()
            await self._end_game()
        else:
            await interaction.response.edit_message(embed=self._get_embed("play"), view=self.view)

    async def _stand_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Only the user that started the game can play.", ephemeral=True)
            return

        if not self.message:
            self.message = interaction.message

        if self.game_over:
            await interaction.response.send_message("This game has already ended.", ephemeral=True)
            return

        self._dealer_play()
        self.game_over = True

        await interaction.response.defer()
        await self._end_game()
