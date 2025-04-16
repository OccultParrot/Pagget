import dotenv
import os
import discord
import random
from rich.console import Console
from discord import app_commands

CHANCE = 100

dotenv.load_dotenv()

console = Console()

intents = discord.Intents(messages=True, guilds=True)
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


def affliction_chance(afflictions=None, available_afflictions=None):
    if afflictions is None:
        afflictions = []

    # One out of x chance

    # If chance is rolled, AND there are available afflictions
    if 0 == random.randint(0, CHANCE):
        console.log("CHANCE")
        with open("./afflictions.txt", "r") as file:
            lines = file.readlines()
            if lines.__contains__("\n"):
                lines.remove("\n")

            if available_afflictions is None:
                available_afflictions = lines

            affliction = random.choice(available_afflictions)
            afflictions.append(affliction.capitalize().removesuffix('\n'))

            available_afflictions.remove(affliction)

        affliction_chance(afflictions, available_afflictions)

    return afflictions


@tree.command(name="roll_affliction", description="Rolls for the affliction that affects your Parasaurolophus")
async def test(interaction: discord.Interaction):
    afflictions: list[str] = affliction_chance()

    console.log(afflictions)

    if len(afflictions) < 1:
        console.log(f"{interaction.user.name} rolled no afflictions.")
        await interaction.response.send_message("You have **no** afflictions")
        return
    elif len(afflictions) == 1:
        console.log(f"{interaction.user.name} rolled 1 affliction: {afflictions[0]}")
        await interaction.response.send_message(f"You have **{afflictions[0]}**")
        return

    response = "You have the following afflictions:"

    for affliction in afflictions:
        response += f"\n- **{affliction.replace('_', '')}**"

    console.log(f"{interaction.user.name} rolled {len(afflictions)} afflictions: \n{afflictions}")
    await interaction.response.send_message(response)


@tree.command(name="list_afflictions", description="Lists all afflictions")
async def list_afflictions(interaction: discord.Interaction):
    with open("./afflictions.txt", "r") as file:
        lines = file.readlines()
        if lines.__contains__("\n"):
            lines.remove("\n")

        response = ""
        for i in range(len(lines)):
            affliction = lines[i].split(' - ')[0].replace('_', ' ').title()
            response += f"\n- **{affliction}** | Run /info {affliction.lower().split(' ')[0]}"

        await interaction.response.send_message(str(response))


@tree.command(name="info", description="Describes the affliction")
@app_commands.describe(affliction="Affliction")
async def info(interaction: discord.Interaction, affliction: str):
    with open("./afflictions.txt", "r") as file:
        lines = file.readlines()
        if lines.__contains__("\n"):
            lines.remove("\n")
        for line in lines:
            affliction_full = line.split(' - ')[0].replace('_', ' ').lower().split(' ')[0]
            if affliction_full == affliction.replace('_', ' ').lower().split(' ')[0]:
                await interaction.response.send_message(line)
                return

    await interaction.response.send_message("Affliction not found, make sure you spelled it right!", ephemeral=True)


@client.event
async def on_ready():
    console.print(f"[green]Bot activated as {client.user}")
    for guild in client.guilds:
        console.print(f"[green]Guild: {guild.name} ({guild.id})")

    await tree.sync()
    console.print("[green]Command tree synced")


client.run(os.getenv("TOKEN"))
