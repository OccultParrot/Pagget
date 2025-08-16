from typing import Dict, List

from openai import OpenAI
from openai.types.responses import Response


class PaggetAIClient:
    def __init__(self, memory_length: int):
        self.client = OpenAI()
        self.prior_conversation: List[Dict[str, str]] = []

        self.memory_length = memory_length

    def ask(self, message, user_id) -> Response:
        message.content = message.content.replace(f"<@{user_id}>", "Pagget")
        self.prior_conversation.append({"author": message.author.display_name, "content": message.content})
        
        prompt = self._prompt(message)
        print(prompt)
        response = self.client.responses.create(
            model="gpt-4o-mini",
            input=prompt,
        )

        self.prior_conversation.append({"author": "You", "content": response.output_text})

        while len(self.prior_conversation) > self.memory_length:
            self.prior_conversation.pop(0)

        return response

    def _prompt(self, message) -> str:
        conversation_history = "\n".join([f"{entry['author']} said: {entry['content']}" for entry in self.prior_conversation])
        return (
f"""You are Pagget, a parasaurolophus who has a serious gambling problem.
You were made my OccultParrot (Parrot), who also has a gambling problem.

In the prehistoric world you live in, berries are the currency, at least among parasaurolophus. You live during the Campanian period.

Please try to keep replies to a reasonable size, also feel free to use discord flavored markdown to italicise, bold, or anything else you can do with markdown in discord! 
If someone has been talking to you, dont bother welcoming them to the conversation, you are in a conversation lol.
Dont over use emojis.
Here is the history of the conversation:
{conversation_history}

{message.author.display_name} just said something to you: {message.content}
"""
    )
