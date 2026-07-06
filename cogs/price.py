"""/price and !price -> live price embed for a coin."""
import discord
from discord import app_commands
from discord.ext import commands

import config
import utils
from data import prices


def build_price_embed(t: dict, logo_url: str) -> discord.Embed:
    coin = t["symbol"].split("/")[0]
    embed = discord.Embed(
        title=f"Price Information for {coin} on {t['exchange'].capitalize()}",
        color=config.COLOR_PRICE,
    )
    embed.add_field(name="🌐 Market:", value=t["symbol"], inline=False)
    embed.add_field(name="💵 Price:", value=utils.fmt_num(t["price"], "$ "), inline=False)
    embed.add_field(name="💰 Volume:", value=utils.fmt_num(t["volume"], "$ "), inline=False)
    embed.add_field(name="📈 High:", value=utils.fmt_num(t["high"], "$ "), inline=False)
    embed.add_field(name="📉 Low:", value=utils.fmt_num(t["low"], "$ "), inline=False)
    if t.get("change_pct") is not None:
        arrow = "🟢" if t["change_pct"] >= 0 else "🔴"
        embed.add_field(
            name="📊 24h Change:", value=f"{arrow} {t['change_pct']:.2f}%", inline=False
        )
    if logo_url:
        embed.set_image(url=logo_url)
    embed.set_footer(text=config.FOOTER_TEXT)
    return embed


async def _price(guild_id, coin):
    coin, exchange, quote, logo = utils.resolve_context(guild_id, coin)
    ticker = await prices.fetch_ticker(coin, quote, exchange)
    return build_price_embed(ticker, logo)


class Price(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="price", description="Live price info for a coin")
    @app_commands.describe(coin="Ticker symbol, e.g. BTC (defaults to this server's coin)")
    async def price_slash(self, interaction: discord.Interaction, coin: str = None):
        await interaction.response.defer()
        try:
            embed = await _price(interaction.guild_id, coin)
            await interaction.followup.send(embed=embed)
        except prices.MarketError as e:
            await interaction.followup.send(f"⚠️ {e}")

    @commands.command(name="price")
    async def price_prefix(self, ctx, coin: str = None):
        try:
            embed = await _price(ctx.guild.id if ctx.guild else None, coin)
            await ctx.send(embed=embed)
        except prices.MarketError as e:
            await ctx.send(f"⚠️ {e}")


async def setup(bot):
    await bot.add_cog(Price(bot))
