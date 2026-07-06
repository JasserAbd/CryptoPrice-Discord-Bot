"""MarketEye — entry point.

Loads config, initializes the database, registers all cogs, syncs slash
commands and starts the bot.

Run:  python bot.py
"""
import asyncio
import logging

import discord
from discord.ext import commands

import config
import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("marketeye")

COGS = [
    "cogs.general",
    "cogs.price",
    "cogs.chart",
    "cogs.about",
    "cogs.exchanges",
    "cogs.setup",
    "cogs.alerts",
]


class MarketEyeBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # needed for the "!" prefix commands
        super().__init__(
            command_prefix=commands.when_mentioned_or(config.COMMAND_PREFIX),
            intents=intents,
            help_command=None,  # we ship our own /help
            case_insensitive=True,
        )

    async def setup_hook(self):
        for ext in COGS:
            await self.load_extension(ext)
            log.info("Loaded %s", ext)
        # Sync slash commands globally. (May take up to an hour to appear the
        # very first time; per-guild sync is instant — see README.)
        synced = await self.tree.sync()
        log.info("Synced %d slash commands", len(synced))

    async def on_ready(self):
        log.info("Logged in as %s (id: %s)", self.user, self.user.id)
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, name="crypto prices | /help"
            )
        )

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"⚠️ Missing argument: `{error.param.name}`. Try `!help`.")
            return
        if isinstance(error, commands.BadArgument):
            await ctx.send("⚠️ Bad argument. Try `!help` for usage.")
            return
        log.exception("Command error", exc_info=error)
        await ctx.send("⚠️ Something went wrong running that command.")


async def main():
    config.validate()
    db.init()
    bot = MarketEyeBot()
    async with bot:
        await bot.start(config.DISCORD_TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Shutting down.")
