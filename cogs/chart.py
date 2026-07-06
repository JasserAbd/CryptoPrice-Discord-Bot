"""/chart and !chart -> candlestick chart image."""
import discord
from discord import app_commands
from discord.ext import commands

import config
import utils
from data import charts, prices

# Allowed timeframes users can request.
TIMEFRAMES = {"1m", "5m", "15m", "1h", "4h", "1d"}


async def _chart(guild_id, coin, candles, timeframe):
    coin, exchange, quote, _ = utils.resolve_context(guild_id, coin)
    candles = max(5, min(int(candles), 200))  # clamp to a sane range
    timeframe = timeframe if timeframe in TIMEFRAMES else "1h"
    ohlcv = await prices.fetch_ohlcv(coin, quote, exchange, timeframe, candles)
    title = f"Chart for {coin}/{quote} on {exchange.capitalize()}"
    buf = await charts.render_candles(ohlcv, title)
    file = discord.File(buf, filename="chart.png")

    embed = discord.Embed(title=title, color=config.COLOR_CHART)
    embed.set_image(url="attachment://chart.png")
    embed.set_footer(text=f"{config.FOOTER_TEXT} • {candles} x {timeframe} candles")
    return embed, file


class Chart(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="chart", description="Candlestick chart for a coin")
    @app_commands.describe(
        candles="How many candles to show (5-200)",
        coin="Ticker, e.g. BTC (defaults to this server's coin)",
        timeframe="Candle size: 1m, 5m, 15m, 1h, 4h, 1d",
    )
    async def chart_slash(
        self,
        interaction: discord.Interaction,
        candles: int = 50,
        coin: str = None,
        timeframe: str = "1h",
    ):
        await interaction.response.defer()
        try:
            embed, file = await _chart(interaction.guild_id, coin, candles, timeframe)
            await interaction.followup.send(embed=embed, file=file)
        except prices.MarketError as e:
            await interaction.followup.send(f"⚠️ {e}")

    @commands.command(name="chart")
    async def chart_prefix(self, ctx, candles: int = 50, coin: str = None, timeframe: str = "1h"):
        try:
            embed, file = await _chart(
                ctx.guild.id if ctx.guild else None, coin, candles, timeframe
            )
            await ctx.send(embed=embed, file=file)
        except prices.MarketError as e:
            await ctx.send(f"⚠️ {e}")
        except ValueError:
            await ctx.send("⚠️ Usage: `!chart <candles> [coin] [timeframe]`")


async def setup(bot):
    await bot.add_cog(Chart(bot))
