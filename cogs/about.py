"""/about and !about -> coin metadata embed (name, supply, market cap, logo)."""
import discord
from discord import app_commands
from discord.ext import commands

import config
import utils
from data import prices


def build_about_embed(info: dict, logo_override: str = None) -> discord.Embed:
    embed = discord.Embed(
        title=f"About the ticker {info['ticker']}", color=config.COLOR_ABOUT
    )
    embed.add_field(name="🪙 Ticker:", value=info["ticker"], inline=False)
    embed.add_field(name="💎 Name:", value=info["name"], inline=False)
    embed.add_field(
        name="🔄 Circulating:",
        value=utils.fmt_num(info["circulating_supply"]),
        inline=False,
    )
    embed.add_field(
        name="💰 MarketCap:", value=utils.fmt_num(info["market_cap"], "$ "), inline=False
    )
    logo = logo_override or info.get("logo_url")
    if logo:
        embed.set_image(url=logo)
    embed.set_footer(text=config.FOOTER_TEXT)
    return embed


async def _about(guild_id, coin):
    coin, _, _, logo = utils.resolve_context(guild_id, coin)
    info = await prices.fetch_coin_info(coin)
    # Prefer the server's custom logo if one was set, else CoinGecko's.
    override = logo if logo and logo != config.DEFAULT_LOGO_URL else None
    return build_about_embed(info, override)


class About(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="about", description="Coin info: name, supply, market cap")
    @app_commands.describe(coin="Ticker, e.g. BTC (defaults to this server's coin)")
    async def about_slash(self, interaction: discord.Interaction, coin: str = None):
        await interaction.response.defer()
        try:
            embed = await _about(interaction.guild_id, coin)
            await interaction.followup.send(embed=embed)
        except prices.MarketError as e:
            await interaction.followup.send(f"⚠️ {e}")

    @commands.command(name="about")
    async def about_prefix(self, ctx, coin: str = None):
        try:
            embed = await _about(ctx.guild.id if ctx.guild else None, coin)
            await ctx.send(embed=embed)
        except prices.MarketError as e:
            await ctx.send(f"⚠️ {e}")


async def setup(bot):
    await bot.add_cog(About(bot))
