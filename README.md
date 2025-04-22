# Pagget
A discord bot I wrote for the herd Longcrest Fellowship on the Path of Titans server Dynasty Realism.

## Table of Contents

- [Installation](#installation)
- [Commands](#commands)
    - [Public Commands](#public-commands)
        - [`/roll-affliction`](#roll-affliction)
        - [`/roll-minor-affliction`](#roll-minor-affliction)
        - [`/list-afflictions`](#list-afflictions)
    - [Admin Commands](#admin-commands)
        - [`/add-affliction`](#add-affliction)
        - [`/remove-affliction`](#remove-affliction)
        - [`/edit-affliction`](#edit-affliction)
        - [`/set-configs`](#set-configs)
- [Configuration](#configuration)
- [How is Data Stored?](#how-is-data-stored)

## Installation

1. Clone repository from [GitHub](https://github.com/OccultParrot/Pagget).
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy the `.env.example` file to `.env` and fill in the required values.
    - `PRODUCTION_TOKEN` holds the token for the one you want to use on the servers.
    - `TEST_TOKEN` holds the token for the one you want to use on a test server.
4. Run the bot with `python pagget.py` for test mode to ensure that the bot is working.
5. If the bot is functioning, you can run it in production mode with `python pagget.py -P`.
    - When you first run the bot, or when you install a new update, add the `--sync` flag to sync the commands with
      Discord.
        - `python pagget.py -P --sync`

It should now be working!

## Commands

There are **two** types of commands: Public Commands, and Admin Commands.

- [Public Commands](#public-commands) are available to all users.
- [Admin Commands](#admin-commands) are only available to users with the `Administrator` permission in the server.

### Public Commands

- [`/roll-affliction`](#roll-affliction)
- [`/roll-minor-affliction`](#roll-minor-affliction)
- [`/list-afflictions`](#list-afflictions)

### Admin Commands

- [`/add-affliction`](#add-affliction)
- [`/remove-affliction`](#remove-affliction)
- [`/edit-affliction`](#edit-affliction)
- [`/set-configs`](#set-configs)

### Public Commands

---

#### `/roll-affliction`



You have a percent chance (Defined in [`set-configs`](#set-configs)) to roll an affliction.
**IF** you roll an affliction, you will get a random affliction from the list of afflictions, weighted by rarity, and
will roll again for a chance to get another affliction.

It takes a single argument, `dino` which is the name of the dino that you want to roll for.

#### `/roll-minor-affliction`

You have a percent chance (Defined in [`set-configs`](#set-configs)) to roll a minor affliction.
**IF** you roll a minor affliction, you will get a random minor affliction from the list of minor afflictions.
And you will roll again for a chance to get another minor affliction.

It takes a single argument, `dino` which is the name of the dino that you want to roll for.

#### `/list-afflictions`

This command will list all the afflictions that are currently in the database, sorted alphabetically, then by rarity.

### Admin Commands

---

#### `/add-affliction`

This command will add an affliction to the database.

It takes the following arguments:
- `name` - The name of the affliction.
- `description` - The description of the affliction.
- `rarity` - The rarity of the affliction. It takes one of the following values:
    - `common`
    - `uncommon`
    - `rare`
    - `ultra rare`
    - `true`
    - `false`

#### `/remove-affliction`
This command will remove an affliction from the database.
It takes the following argument:
- `name` - The name of the affliction.

#### `/edit-affliction`
This command will edit an affliction in the database.
It takes the following arguments:
- `affliction` - The **current** name of the affliction.
- `name` - The new name of the affliction. (Optional)
- `description` - The new description of the affliction. (Optional)
- `rarity` - The new rarity of the affliction. (Optional)
    - `common`
    - `uncommon`
    - `rare`
    - `ultra rare`
    - `true`
    - `false`
- `is_minor` - The new minor status of the affliction. (Optional)
    - `true`
    - `false`

#### `/set-configs`
This command will set the configs for the bot. If you don't give any arguments, it will list the current configs.
It takes the following arguments:

- `roll_affliction_chance` - The chance to roll an affliction. (Default: 25)
- `roll_minor_affliction_chance` - The chance to roll a minor affliction. (Default: 35)
- `species` - The species of the dino. (Default: `Parasaurolophus`)

## Configuration

via the `/set-configs` command, you can change the following configs:
- `roll_affliction_chance` - The chance to roll an affliction. (Default: 25)
- `roll_minor_affliction_chance` - The chance to roll a minor affliction. (Default: 35)
- `species` - The species of the dino. (Default: `Parasaurolophus`)

## How is Data Stored?

The data is stored in .json files in the `data` folder.

There is two folders, `guild_configs` and `afflictions`.

- `guild_configs` - This folder contains the configs for each guild. The file name is the guild id.
    - Each config file has the following fields:
        - `roll_affliction_chance` - The chance to roll an affliction. (Default: 25)
        - `roll_minor_affliction_chance` - The chance to roll a minor affliction. (Default: 35)
        - `species` - The species of the dino. (Default: `Parasaurolophus`)
- `afflictions` - This folder contains the afflictions that each guild has made. The file name is the guild id.
    - Each affliction has the following fields:
        - `name` - The name of the affliction.
        - `description` - The description of the affliction.
        - `rarity` - The rarity of the affliction. It takes one of the following values:
            - `common`
            - `uncommon`
            - `rare`
            - `ultra rare`
        - `is_minor` - Whether the affliction is a minor affliction. (Default: false)

