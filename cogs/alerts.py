"""Price alerts -> the extra feature the original bot didn't have.

/alert BTC above 70000   -> notifies the channel when BTC crosses 70000.
A background loop checks every open alert on an interval and fires once, then
removes the alert.
"""
import discord
from discord import app_commands
from discord.ext import commands, tasks

import config
import db
import utils
from data import prices

CHECK_INTERVAL_SECONDS = 60


class Alerts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_alerts.start()

    def cog_unload(self):
        self.check_alerts.cancel()

    # ----------------------------------------------------------------- #
    # Commands
    # ----------------------------------------------------------------- #
    async def _create(self, user_id, channel_id, guild_id, coin, direction, target):
        direction = direction.lower()
        if direction not in {"above", "below"}:
            return "⚠️ Direction must be `above` or `below`."
        coin, exchange, quote, _ = utils.resolve_context(guild_id, coin)
        # Validate the market exists before storing the alert.
        try:
            await prices.fetch_ticker(coin, quote, exchange)
        except prices.MarketError as e:
            return f"⚠️ {e}"
        alert_id = db.add_alert(
            user_id, channel_id, guild_id, coin, direction, float(target), exchange, quote
        )
        return (
            f"🔔 Alert **#{alert_id}** set: notify when **{coin}/{quote}** goes "
            f"**{direction} {utils.fmt_num(target, '$ ')}** (on {exchange})."
        )

    @app_commands.command(name="alert", description="Get pinged when a coin crosses a price")
    @app_commands.describe(
        coin="Ticker, e.g. BTC",
        direction="above or below",
        target="Target price",
    )
    @app_commands.choices(
        direction=[
            app_commands.Choice(name="above", value="above"),
            app_commands.Choice(name="below", value="below"),
        ]
    )
    async def alert_slash(
        self,
        interaction: discord.Interaction,
        coin: str,
        direction: app_commands.Choice[str],
        target: float,
    ):
        await interaction.response.defer(ephemeral=True)
        msg = await self._create(
            interaction.user.id,
            interaction.channel_id,
            interaction.guild_id,
            coin,
            direction.value,
            target,
        )
        await interaction.followup.send(msg, ephemeral=True)

    @commands.command(name="alert")
    async def alert_prefix(self, ctx, coin: str, direction: str, target: float):
        msg = await self._create(
            ctx.author.id,
            ctx.channel.id,
            ctx.guild.id if ctx.guild else None,
            coin,
            direction,
            target,
        )
        await ctx.send(msg)

    @app_commands.command(name="alerts", description="List your active price alerts")
    async def alerts_slash(self, interaction: discord.Interaction):
        rows = db.get_user_alerts(interaction.user.id)
        await interaction.response.send_message(
            self._format_list(rows), ephemeral=True
        )

    @commands.command(name="alerts")
    async def alerts_prefix(self, ctx):
        rows = db.get_user_alerts(ctx.author.id)
        await ctx.send(self._format_list(rows))

    @app_commands.command(name="delalert", description="Delete one of your alerts by id")
    @app_commands.describe(alert_id="The alert number shown in /alerts")
    async def delalert_slash(self, interaction: discord.Interaction, alert_id: int):
        ok = db.delete_alert(alert_id, interaction.user.id)
        await interaction.response.send_message(
            f"🗑️ Deleted alert #{alert_id}." if ok else "⚠️ No such alert of yours.",
            ephemeral=True,
        )

    @commands.command(name="delalert")
    async def delalert_prefix(self, ctx, alert_id: int):
        ok = db.delete_alert(alert_id, ctx.author.id)
        await ctx.send(
            f"🗑️ Deleted alert #{alert_id}." if ok else "⚠️ No such alert of yours."
        )

    @staticmethod
    def _format_list(rows: list[dict]) -> str:
        if not rows:
            return "You have no active alerts. Set one with `/alert`."
        lines = ["**Your alerts:**"]
        for r in rows:
            lines.append(
                f"• #{r['id']}  {r['coin']}/{r['quote']}  {r['direction']} "
                f"{utils.fmt_num(r['target'], '$ ')}  ({r['exchange']})"
            )
        return "\n".join(lines)

    # ----------------------------------------------------------------- #
    # Background checker
    # ----------------------------------------------------------------- #
    @tasks.loop(seconds=CHECK_INTERVAL_SECONDS)
    async def check_alerts(self):
        rows = db.get_all_alerts()
        for r in rows:
            try:
                t = await prices.fetch_ticker(r["coin"], r["quote"], r["exchange"])
            except prices.MarketError:
                continue
            price = t.get("price")
            if price is None:
                continue
            hit = (
                (r["direction"] == "above" and price >= r["target"])
                or (r["direction"] == "below" and price <= r["target"])
            )
            if hit:
                await self._fire(r, price)
                db.delete_alert(r["id"])

    async def _fire(self, r: dict, price: float):
        channel = self.bot.get_channel(r["channel_id"])
        embed = discord.Embed(
            title=f"🔔 Price Alert: {r['coin']}/{r['quote']}",
            description=(
                f"<@{r['user_id']}> — **{r['coin']}** is now "
                f"**{utils.fmt_num(price, '$ ')}**, "
                f"{r['direction']} your target of {utils.fmt_num(r['target'], '$ ')}."
            ),
            color=config.COLOR_PRICE,
        )
        embed.set_footer(text=config.FOOTER_TEXT)
        try:
            if channel is not None:
                await channel.send(content=f"<@{r['user_id']}>", embed=embed)
            else:
                user = await self.bot.fetch_user(r["user_id"])
                await user.send(embed=embed)
        except discord.DiscordException:
            pass

    @check_alerts.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Alerts(bot))
