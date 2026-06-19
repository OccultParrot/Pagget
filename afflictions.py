import random

import discord

import models


def get_rarity_color(rarity: models.Rarity):
    match rarity:
        case models.Rarity.COMMON:
            return discord.Color.green()
        case models.Rarity.UNCOMMON:
            return discord.Color.blue()
        case models.Rarity.RARE:
            return discord.Color.purple()
        case models.Rarity.LEGENDARY:
            return discord.Color.yellow()
        case _:
            return discord.Color.default()


def list_afflictions(afflictions: list[models.Affliction]):
    sorted_afflictions = sort_afflictions(afflictions)
    result = []
    for affliction_group in sorted_afflictions:
        affliction_group = sorted(affliction_group, key=lambda affliction: affliction.title.lower())
        result.extend(affliction_group)

    return result

def affliction_exists(name: str, afflictions: list[models.Affliction]):
    return any(a.title.lower() == name.lower() for a in afflictions)

def get_embed(affliction: models.Affliction):
    header_lines = [f"-# {affliction.rarity.value.title()}"]

    if affliction.is_minor:
        header_lines.append("-# *Minor Affliction*")

    if affliction.seasons:
        season_str = ', '.join(
            [s.value.title() if s != models.Season.ANY else 'Any Season' for s in affliction.seasons])
        header_lines.append(f"-# *{season_str}*")

    footer_lines = []

    if affliction.is_birth_defect:
        footer_lines.append("-# This is a birth defect")

    sections = ["\n".join(header_lines), affliction.description]
    if footer_lines:
        sections.append("\n".join(footer_lines))

    description = "\n\n".join(sections)

    return discord.Embed(
        title=affliction.title.title(),
        description=description,
        color=get_rarity_color(affliction.rarity),
    )


def sort_afflictions(afflictions: list[models.Affliction]) -> tuple[
    list[models.Affliction],
    list[models.Affliction],
    list[models.Affliction],
    list[models.Affliction],
]:
    commons = [a for a in afflictions if a.rarity == models.Rarity.COMMON]
    uncommons = [a for a in afflictions if a.rarity == models.Rarity.UNCOMMON]
    rares = [a for a in afflictions if a.rarity == models.Rarity.RARE]
    legendaries = [a for a in afflictions if a.rarity == models.Rarity.LEGENDARY]

    return commons, uncommons, rares, legendaries


def filter_seasonal_afflictions(
        afflictions: list[models.Affliction], season: models.Season
) -> tuple[
    list[models.Affliction],
    ...
]:
    return tuple(
        [a for a in group if models.Season.ANY in a.seasons or season in a.seasons]
        for group in sort_afflictions(afflictions)
    )


def roll_afflictions(afflictions: list[models.Affliction], chance: float, season: models.Season) -> list[
    models.Affliction]:
    result = []
    available_afflictions = afflictions.copy()

    # Cap iterations at the total number of afflictions
    for _ in range(len(afflictions)):
        if not available_afflictions:
            break

        if random.random() > chance:
            break

        rarity_groups = filter_seasonal_afflictions(available_afflictions, season)
        rarity_weights = [60, 25, 10, 5]

        non_empty_groups = []
        non_empty_weights = []

        for group, weight in zip(rarity_groups, rarity_weights):
            if group:
                non_empty_groups.append(group)
                non_empty_weights.append(weight)

        if not non_empty_groups:
            break

        selected_group = random.choices(non_empty_groups, weights=non_empty_weights, k=1)[0]
        selected_affliction = random.choice(selected_group)

        result.append(selected_affliction)
        available_afflictions = [a for a in available_afflictions if a is not selected_affliction]

    return result
