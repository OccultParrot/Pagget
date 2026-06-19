import random
from typing import Optional

import discord

import models


def roll_gathering_outcome(outcomes: list[models.GatherOutcome]):
    rarity_groups = sort_gathering_outcomes(outcomes)
    rarity_weights = [60, 25, 10, 5]

    selected_group = random.choices(rarity_groups, weights=rarity_weights)

    return random.choice(selected_group)


def sort_gathering_outcomes(outcomes: list[models.GatherOutcome]) -> tuple[
    list[models.GatherOutcome],
    list[models.GatherOutcome],
    list[models.GatherOutcome],
    list[models.GatherOutcome],
]:
    commons = [o for o in outcomes if o.rarity == models.Rarity.COMMON]
    uncommons = [o for o in outcomes if o.rarity == models.Rarity.UNCOMMON]
    rares = [o for o in outcomes if o.rarity == models.Rarity.RARE]
    legendaries = [o for o in outcomes if o.rarity == models.Rarity.LEGENDARY]

    return commons, uncommons, rares, legendaries


def get_outcome_color(value: int):
    if value < 0:
        return discord.Color.red()
    elif value == 0:
        return discord.Color.blurple()
    else:
        return discord.Color.green()


def get_embed(outcome: models.GatherOutcome, old_balance: int, new_balance: int, target: Optional[discord.member],
              interaction: discord.Interaction):
    title = f"Successful {'Robbery' if outcome.is_robbery else 'Hunt'}!" if outcome.value > 0 else f"Failed {'Robbery' if outcome.is_robbery else 'Hunt'}!"
    description = outcome.description.format(
        target = target.display_name if target else "",
        value = outcome.value,
    ) + f"\n\nTarget: {target.display_name}" if target else ""
    color = get_outcome_color(outcome.value)

    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url)
    embed.set_footer(text=f"{new_balance} total berries.")

    return embed
