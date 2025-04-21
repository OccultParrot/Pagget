# Pagget

Discord bot for the Parasaurolophus herd Longcrest Fellowship on the Path of Titans server Dynasty Realism.

Discord: https://discord.gg/mgSZqp9PFD

The bot handles affliction management for Parasaurolophus characters with the following commands:
    
     - /roll_affliction: Rolls for the afflictions that affect your Parasaurolophus
     - /list_afflictions: Lists all the available afflictions
     - /info [affliction]: Describes the supplied affliction if it exists
    
All afflictions are stored in a text file called afflictions.txt in the format: [affliction name] - [description]


## Modules

You need to install the following modules to be able to run the bot:

- Discord.py (For the actual bot part)
- python-dotenv (For environment variables
- Rich (for console formatting)

## Requirements

You need to make a .env file in the root of the project and add the variable "TOKEN" which you add the discord bot token to

## Installation and Running

First "cd" into the project directory and run `pip install -r requirements.txt`

There are a few command line arguments you can use. 

The default way to run it is `python main.py`. This runs it in testing mode using your testing token.

To run on production, add the `-P` arg. Example: `python main.py -P`

To sync the command tree, which you should always do when adding a command or after installing a new version, add the `--sync` arg. Example: `python main.py --sync`

After an update, I run the following command

```bash
python main.py -P --sync
```
