import random
from typing import List, Optional, Literal

import discord

from classes.typepairs import Affliction


class AfflictionController:
    """ This class does everything with afflictions """

    @staticmethod
    def search_affliction(afflictions: List[Affliction], search_term: str) -> Optional[Affliction]:
        """
        Find an affliction by a search term.
        
        Args:
            search_term: The term to search for
            afflictions: The list of afflictions to search in
            
        Returns:
            The full affliction string if found, None otherwise
        """
        search_term = search_term.lower()

        for affliction in afflictions:
            name = affliction.name.lower()
            if search_term in name or search_term == name.split()[0]:
                return affliction

        return None

    @staticmethod
    def list_afflictions(afflictions: List[Affliction], page: int):
        commons, uncommons, rares, ultra_rares = AfflictionController._sort_rarities(afflictions)
        commons = sorted(commons, key=lambda affliction: affliction.name.lower())
        uncommons = sorted(uncommons, key=lambda affliction: affliction.name.lower())
        rares = sorted(rares, key=lambda affliction: affliction.name.lower())
        ultra_rares = sorted(ultra_rares, key=lambda affliction: affliction.name.lower())

        return commons + uncommons + rares + ultra_rares

    @staticmethod
    def roll(afflictions: List[Affliction], affliction_chance: float, is_minor: bool, season: str) -> (Affliction,
                                                                                                       bool):
        result = []
        available_afflictions = afflictions.copy()

        for _ in range(len(afflictions)):
            # If there are no more available affliction, break the loop
            if not available_afflictions:
                break

            if random.random() < affliction_chance / 100:
                commons, uncommons, rares, ultra_rares = AfflictionController._sort_seasonal_rarities(available_afflictions, season)

                if is_minor:
                    # Minor afflictions are only common
                    # so we filter those out and only roll from the filtered common
                    commons = [a for a in commons if a.is_minor]
                    rarity_groups = [commons]
                    rarity_weights = [100]
                else:
                    rarity_groups = [commons, uncommons, rares, ultra_rares]
                    rarity_weights = [60, 25, 10, 5]

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

    @staticmethod
    def get_embed(affliction: Affliction) -> discord.Embed:
        seasonal_emoji = ":sunny:" if affliction.season == "dry" else ":cloud_rain:" if affliction.season == "wet" else ""
        return discord.Embed(
            title=f"{affliction.name.title()}",
            description=f"-# {affliction.rarity.title()}\n{'-# *Minor Affliction*' if affliction.is_minor else ''}\n\n{affliction.description}",
            color=AfflictionController.get_rarity_color(affliction.rarity)
        )

    @staticmethod
    def get_rarity_color(rarity: str) -> discord.Color:
        """Get the color associated with a rarity."""
        if rarity.lower() == "common":
            return discord.Color.green()
        elif rarity.lower() == "uncommon":
            return discord.Color.blue()
        elif rarity.lower() == "rare":
            return discord.Color.purple()
        elif rarity.lower() == "ultra rare":
            return discord.Color.yellow()
        else:
            return discord.Color.default()

    @staticmethod
    def _sort_seasonal_rarities(unsorted_afflictions: List[Affliction], season: str):
        # I HATE this way of doing it. TODO: Please find a better way to do this
        opposite_season = "wet" if season == "dry" else "dry"
        
        commons = [a for a in unsorted_afflictions if a.rarity == "common" and a.season != opposite_season]
        uncommons = [a for a in unsorted_afflictions if a.rarity == "uncommon" and a.season != opposite_season]
        rares = [a for a in unsorted_afflictions if a.rarity.lower() == "rare" and a.season != opposite_season]
        ultra_rares = [a for a in unsorted_afflictions if a.rarity.lower() == "ultra rare" and a.season != opposite_season]

        return commons, uncommons, rares, ultra_rares

    @staticmethod
    def _sort_rarities(unsorted_afflictions: List[Affliction]):

        commons = [a for a in unsorted_afflictions if a.rarity == "common"]
        uncommons = [a for a in unsorted_afflictions if a.rarity == "uncommon"]
        rares = [a for a in unsorted_afflictions if a.rarity.lower() == "rare"]
        ultra_rares = [a for a in unsorted_afflictions if a.rarity.lower() == "ultra rare"]

        return commons, uncommons, rares, ultra_rares
