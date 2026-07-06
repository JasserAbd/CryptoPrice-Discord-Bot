"""/help and !help -> command overview."""
import discord
from discord import app_commands
from discord.ext import commands

import config


def build_help_embed(prefix: str) -> discord.Embed:
    embed = discord.Embed(
        title="MarketEye — Commands",
        description="Use slash commands (`/`) or the classic prefix. Both work.",
        color=config.COLOR_INFO,
    )
    embed.add_field(
        name="📈 Market",
        value=(
            f"`/price [coin]` — live price, volume, high/low\n"
            f"`/chart [candles] [coin] [timeframe]` — candlestick chart\n"
            f"`/about [coin]` — name, supply, market cap\n"
            f"`/exchanges` — list supported exchanges"
        ),
        inline=False,
    )
    embed.add_field(
        name="🔔 Alerts",
        value=(
            "`/alert <coin> <above|below> <price>` — set an alert\n"
            "`/alerts` — list your alerts\n"
            "`/delalert <id>` — delete an alert"
        ),
        inline=False,
    )
    embed.add_field(
        name="⚙️ Setup",
        value="`/setup` (or `!add`) — set this server's default coin & logo",
        inline=False,
    )
    embed.set_footer(text=f"{config.FOOTER_TEXT} • prefix: {prefix}")
    return embed


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show all commands")
    async def help_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=build_help_embed(config.COMMAND_PREFIX)
        )

    @commands.command(name="help")
    async def help_prefix(self, ctx):
        await ctx.send(embed=build_help_embed(config.COMMAND_PREFIX))


async def setup(bot):
    await bot.add_cog(General(bot))
