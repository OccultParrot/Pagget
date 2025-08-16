import os

import discord
from dotenv import load_dotenv

from aistuff import PaggetAIClient

if not os.path.exists(".env"):
    print("No .env file found")
    exit(1)

load_dotenv()


class PaggetClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True

        self.ai_client = PaggetAIClient(10)

        super().__init__(intents=intents)

    async def on_ready(self):
        print(f"Logged in as {self.user}!")

    async def on_message(self, message):
        if message.author == self.user:
            return

        if f"<@{self.user.id}>" in message.content:
            content = message.content.replace(f"<@{self.user.id}>", "Pagget")
            print(f"{message.author} asked {self.user}: {content}")
            response = self.ai_client.ask(message, self.user.id)
            await message.channel.send(response.output_text)

client = PaggetClient()
client.run(os.getenv('DISCORD_API_TOKEN'))
