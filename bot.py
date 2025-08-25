import os
import discord
# import requests
# import json
import asyncio
import aiohttp
import time
from typing import List

MEME_API = 'https://meme-api.com/gimme'

def chunk(iterable, n):

    it = list(iterable)
    for i in range(0, len(it), n):
        yield it[i:i+n]

class MyClient(discord.Client):
    #init bot
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.http_session: aiohttp.ClientSession | None = None
        self.commands: dict[str, callable] = {} #only matches exact string command

    #setup hook
    async def setup_hook(self) -> None:
        #one shared session for bot lifetime
        timeout = aiohttp.ClientTimeout(total=10)
        self.http_session = aiohttp.ClientSession(timeout=timeout)

        # -------------- COMMAND PALETTE ---------------
        self.commands = {
            "$hello": {"handler": self.cmd_hello, "desc": "Say hello to the bot", "emoji": "👋"},
            "$meme":  {"handler": self.cmd_meme,  "desc": "Fetch a random meme", "emoji": "😂"},
            "$ping":  {"handler": self.cmd_ping,  "desc": "Check latency", "emoji": "🏓"},
            "$help":  {"handler": self.cmd_help,  "desc": "Show this help", "emoji": "📖"},
        }

    #close
    async def close_self(self) -> None:
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()
        await super().close()

    #log on bot
    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))

    #-----------------------HELPER FUNCTIONS------------------------------------

    async def get_meme(self) -> str | None:
        assert self.http_session is not None
        try:
            #get response from meme website
            async with self.http_session.get(MEME_API) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json(content_type=None)
                #returned api
                return data.get("url")
        except asyncio.TimeoutError:
            return None
        except aiohttp.ClientError:
            return None
        
    async def build_help_embed(self) -> List[discord.Embed]:

        color = discord.Color.blurple()
        title = "Available Commands"
        description = "Exact match only; type a command as shown!"

        fields: list[tuple[str, str]] = []

        for cmd, info in self.commands.items():
            emoji = info.get("emoji","•")
            desc = info.get("desc", "")
            #puts command in bold
            name = f"{emoji}  **{cmd}**"
            val = desc or "\u200b" #zero-width space if desc does not exist or is invalid
            fields.append((name, val))

        embeds: list[discord.Embed] = []

        for i in range(0, len(fields), 25):
            embed = discord.Embed(
                title=title if i == 0 else f"{title} (cont.)",
                description=description if i == 0 else discord.Embed.Empty,
                color=color
            )
            if self.user and self.user.display_avatar:
                embed.set_thumbnail(url=self.user.display_avatar.url)
            for name, value in fields[i:i+25]:
                embed.add_field(name=name, value=value, inline=False)
            embeds.append(embed)
        return embeds
        
    # ---------------- Command handler -------------------------
    async def cmd_hello(self, message : discord.Message) -> None:
        await message.channel.send("Hello World!")

    async def cmd_meme(self, message : discord.Message) -> None:
        url = await self.get_meme()
        if url:
            await message.channel.send(url)
        else:
            await message.channel.send("Can't fetch a meme right now, try again later!")

    async def cmd_ping(self, message : discord.Message) -> None:
        #starts time
        start = time.perf_counter()

        msg = await message.channel.send("Pong!")

        end = time.perf_counter()
        elapsed = (end - start) * 1000

        await msg.edit(content=f"Pong!\n({elapsed:.2f} ms)")

    async def cmd_help(self, message : discord.Message) -> None:
        try:
            embeds = await self.build_help_embed()

            await message.channel.send(embed=embeds[0])
            for extra in embeds[1:]:
                await message.channel.send(embed=extra)
        except Exception as e:
            await message.channel.send(f"Help render error: `{type(e).__name__}: {e}`")
            lines = [f"{info.get('emoji','•')} {cmd} — {info.get('desc','')}"
                 for cmd, info in self.commands.items()]
            await message.channel.send("\n".join(lines))

    # ---------------- Message handler -------------------------
    async def on_message(self, message : discord.Message):
        if message.author.bot:
            return
        
        content = message.content.strip()

        cmd_info = self.commands.get(content)
        if not cmd_info:
            return

        handler = cmd_info["handler"]

        try:
            await handler(message)
        except Exception as e:
            await message.channel.send("Oops, that command failed. Try again")

# -----------Booting the Bot-------------
intents = discord.Intents.default()
intents.message_content = True

client = MyClient(intents=intents)
client.run(os.environ["DISCORD_TOKEN"])