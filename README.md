# Pagget
A discord bot I wrote for the herd Longcrest Fellowship on the Path of Titans server Dynasty Realism.

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Commands](#commands)
- [How is Data Stored?](#how-is-data-stored)
- [Bot Building Tips and Tricks](#bot-building-tips-and-tricks)

## Installation

1. Clone repository from [GitHub](https://github.com/OccultParrot/Pagget).
2. Make a bot from the [Discord Developer Portal](https://discord.com/developers/applications)
3. Make a python virtual environment (`python -m venv .venv`)
4. Install required packages with `.venv/Scripts/pip install requirements.txt`. In on linux use `.venv/bin/pip`
5. Run `.venv/Scripts/python main.py -sync` and enter the bot token when asked to.


It should now be working!

## Configuration

via the `/set-configs` command, you can change any of the guild configs. If you dont supply and changes, it will reply with the current guild configs.

## Commands

Commands are seperated three groups, `affliction`, `berries`, `gambling`. (Gambling is an odd case because it's actually a child group of berries)

### Affliction Commands

- `/affliction roll` - Rolls for a random set of afflictions. High chance to get nothing.
  - Take three parameters:
    - `dino` - The name of the dinosaur you are rolling for
    - `type` - The type of affliction you are rolling for. Options:
      - General
      - Minor
      - Birth Defect
    - season - The season the server is currently in. Options
      - Wet Season
      - Dry Season
- `/affliction list` - Lists all afflictions available to the guild.
- `/affliction add` - Adds an affliction to the guild
  - Many parameters that correlate to the affliction, to lazy to write them all.
- `/affliction edit`
  - Takes the name of the affliction you are wanting to change, and the things you want to change it with
- `/affliction remove`
  - Takes name of the affliction to remove

### Berries Commands

- `/berries hunt` - Gives the user a semi random amount of berries
- `/berries steal` - Steals berries from the selected member
- `/berries set` - Sets the amount of berries the selected user has
- `/berries give` - Gives the specified amount of berries from your account to the specified user

### Gambling Commands

- `/berries gambling blackjack` - Play blackjack with your berries
- `/berries gambling roulette` - Play roulette with your berries
- `/berries gambling slots` - Play slots with your berries

## How is Data Stored?

The data is stored in `.json` files in the `data` folder, along with a `.txt` that holds the bot token

Each of the .json files holds an object that holds pairs of guild IDs and an array of the data connected to that guild.

## Bot Building Tips and Tricks

Some useful tips and tricks for building discord bots.

### Json Saving

While not really a tip or trick, I thought it would be useful to have a small section on how to save data to json files.

Python has a built-in module called `json` that can be used to save data to json files. 
is good for saving types that python has built in, but is a *bit* more completed for saving classes.

If you have a class, you will need to make a function that converts the class to a dictionary.

I did this via making another class named `[ClassName]Encoder` that inherits from `json.JSONEncoder` and overrides the `default` method.

```python
import json

class MyClass:
    """Class representing a guild configuration with species and afflictions."""

    def __init__(self, name: str):
        self.name = name

    @classmethod
    def from_dict(cls, data: dict):
        """Create a GuildConfig instance from a dictionary."""
        return cls(
            name=data.get("name", ""),
        )

class GuildConfigEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, MyClass):
            return {
                "name": obj.name
            }
        return json.JSONEncoder.default(self, obj)
```

Then you can use the `json.dump` function to save the data to a file.

```python
data = MyClass("John Smith")

with open("data.json", "w") as f:
    json.dump(data, f, cls=GuildConfigEncoder)
```



### Making Commands

Discord.py has a built-in command system that can be used to make commands.

You make commands by decorating a function with the `@self.tree.command` decorator.

```python
@self.tree.command(name="hello", description="Says hello")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message("Hello!")
```

You can also make commands that take arguments by adding parameters to the function. You need to describe the arguments with the `@app_commands.describe` decorator.

```python
@self.tree.command(name="hello", description="Says hello")
@app_commands.describe(name="The name of the person to say hello to")
async def hello(interaction: discord.Interaction,
                name: str):  # MAKE SURE TO ADD THE ARGUMENT TO THE FUNCTION PARAMETERS!!!!
    await interaction.response.send_message(f"Hello {name}!")
```

You can also make commands that take choices by using the `@app_commands.choices` decorator.
A Choice is always going to be of type `app_commands.Choice[type]`.

```python
@self.tree.command(name="hello", description="Says hello")
@app_commands.describe(name="The name of the person to say hello to")
@app_commands.choices(name=[
    app_commands.Choice(name="John", value="John"),
    app_commands.Choice(name="Jane", value="Jane"),
])
async def hello(interaction: discord.Interaction,
                name: app_commands.Choice[str]):  # MAKE SURE TO ADD THE ARGUMENT TO THE FUNCTION PARAMETERS!!!!
    await interaction.response.send_message(f"Hello {name.value}!")
```

The `name` parameter is the name of the choice, and the `value` parameter is the value we receive when we select the choice.

You can access information about the interaction via the `interaction` parameter.

```python
@self.tree.command(name="hello", description="Says hello")
async def hello(interaction: discord.Interaction):
    user = interaction.user
    await interaction.response.send_message(f"Hello {user.name}!")
```
