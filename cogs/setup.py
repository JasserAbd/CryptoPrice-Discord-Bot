"""/setup and !add -> button-driven wizard to configure the server's coin & logo.

Mirrors the reference bot's welcome panel with Ticker / Logo / Exit And Save buttons.
"""
import discord
from discord import app_commands
from discord.ext import commands

import config
import db
from data import prices


class TickerModal(discord.ui.Modal, title="Set the server's coin"):
    ticker = discord.ui.TextInput(
        label="Ticker symbol", placeholder="e.g. BTC", max_length=15
    )

    def __init__(self, guild_id: int):
        super().__init__()
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        coin = str(self.ticker).strip().upper()
        db.set_guild_field(self.guild_id, "coin", coin)
        # Try to auto-fill a logo from CoinGecko if none set yet.
        cfg = db.get_guild_config(self.guild_id)
        if not cfg.get("logo_url"):
            logo = await prices.fetch_logo(coin)
            if logo:
                db.set_guild_field(self.guild_id, "logo_url", logo)
        await interaction.response.send_message(
            f"✅ Default coin set to **{coin}**.", ephemeral=True
        )


class LogoModal(discord.ui.Modal, title="Set a custom logo"):
    url = discord.ui.TextInput(
        label="Logo image URL",
        placeholder="https://.../logo.png",
        required=True,
    )

    def __init__(self, guild_id: int):
        super().__init__()
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        url = str(self.url).strip()
        if not url.lower().startswith(("http://", "https://")):
            await interaction.response.send_message(
                "⚠️ That doesn't look like a valid URL.", ephemeral=True
            )
            return
        db.set_guild_field(self.guild_id, "logo_url", url)
        await interaction.response.send_message("✅ Logo updated.", ephemeral=True)


class SetupView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=180)
        self.guild_id = guild_id

    @discord.ui.button(label="Ticker", emoji="🪙", style=discord.ButtonStyle.primary)
    async def ticker(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TickerModal(self.guild_id))

    @discord.ui.button(label="Logo", emoji="🖼️", style=discord.ButtonStyle.primary)
    async def logo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(LogoModal(self.guild_id))

    @discord.ui.button(label="Exit And Save", emoji="💾", style=discord.ButtonStyle.success)
    async def save(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = db.get_guild_config(self.guild_id)
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content=(
                f"💾 Saved!  Coin: **{cfg['coin']}** · "
                f"Exchange: **{cfg['exchange']}** · Quote: **{cfg['quote']}**"
            ),
            view=self,
        )
        self.stop()


def build_welcome_embed(guild_name: str, logo_url: str) -> discord.Embed:
    embed = discord.Embed(
        title="MarketEye",
        description=f"Welcome to MarketEye. Configure **{guild_name}** below.",
        color=config.COLOR_INFO,
    )
    if logo_url:
        embed.set_image(url=logo_url)
    embed.set_footer(text=config.FOOTER_TEXT)
    return embed


class Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _open(self, guild, send):
        if guild is None:
            await send("⚠️ Setup can only be used inside a server.")
            return
        cfg = db.get_guild_config(guild.id)
        logo = cfg.get("logo_url") or config.DEFAULT_LOGO_URL
        await send(
            embed=build_welcome_embed(guild.name, logo),
            view=SetupView(guild.id),
        )

    @app_commands.command(name="setup", description="Configure this server's coin and logo")
    async def setup_slash(self, interaction: discord.Interaction):
        await self._open(interaction.guild, interaction.response.send_message)

    # Keep the original "!add" name too.
    @commands.command(name="add")
    async def add_prefix(self, ctx):
        await self._open(ctx.guild, ctx.send)


async def setup(bot):
    await bot.add_cog(Setup(bot))
