"""/exchanges and !exchanges -> paginated list of supported exchanges."""
import discord
from discord import app_commands
from discord.ext import commands

import config
from data import prices

PER_PAGE = 60


def build_embed(page: int, total_pages: int, names: list[str]) -> discord.Embed:
    chunk = names[page * PER_PAGE : (page + 1) * PER_PAGE]
    embed = discord.Embed(
        title=f"Supported Exchanges ({len(names)} total)",
        description="`" + "`  `".join(chunk) + "`",
        color=config.COLOR_INFO,
    )
    embed.set_footer(text=f"{config.FOOTER_TEXT} • Page {page + 1}/{total_pages}")
    return embed


class ExchangesView(discord.ui.View):
    def __init__(self, names: list[str]):
        super().__init__(timeout=120)
        self.names = names
        self.page = 0
        self.total_pages = (len(names) + PER_PAGE - 1) // PER_PAGE

    def _sync_buttons(self):
        self.prev.disabled = self.page == 0
        self.next.disabled = self.page >= self.total_pages - 1

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary, disabled=True)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = max(0, self.page - 1)
        self._sync_buttons()
        await interaction.response.edit_message(
            embed=build_embed(self.page, self.total_pages, self.names), view=self
        )

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = min(self.total_pages - 1, self.page + 1)
        self._sync_buttons()
        await interaction.response.edit_message(
            embed=build_embed(self.page, self.total_pages, self.names), view=self
        )


class Exchanges(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _send(self, send):
        names = prices.list_exchanges()
        view = ExchangesView(names)
        await send(embed=build_embed(0, view.total_pages, names), view=view)

    @app_commands.command(name="exchanges", description="List all supported exchanges")
    async def exchanges_slash(self, interaction: discord.Interaction):
        await self._send(interaction.response.send_message)

    @commands.command(name="exchanges")
    async def exchanges_prefix(self, ctx):
        await self._send(ctx.send)


async def setup(bot):
    await bot.add_cog(Exchanges(bot))
