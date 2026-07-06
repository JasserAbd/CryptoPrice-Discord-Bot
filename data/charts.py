"""Candlestick chart image generation using mplfinance.

Produces an in-memory PNG (BytesIO) that can be attached to a Discord message,
styled to look like the dark trading chart in the reference bot.
"""
import asyncio
import io

import matplotlib

matplotlib.use("Agg")  # headless backend, no display needed
import mplfinance as mpf
import pandas as pd


def _render_sync(ohlcv: list, title: str) -> io.BytesIO:
    df = pd.DataFrame(
        ohlcv, columns=["timestamp", "Open", "High", "Low", "Close", "Volume"]
    )
    df["Date"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("Date", inplace=True)

    # Dark theme close to the reference screenshots (green up / red down candles).
    market_colors = mpf.make_marketcolors(
        up="#26a69a",
        down="#ef5350",
        edge="inherit",
        wick="inherit",
        volume="in",
    )
    style = mpf.make_mpf_style(
        base_mpf_style="nightclouds",
        marketcolors=market_colors,
        facecolor="#0d1117",
        figcolor="#0d1117",
        gridcolor="#2a2e39",
        gridstyle="-",
        rc={"axes.labelcolor": "white", "xtick.color": "white", "ytick.color": "white"},
    )

    buf = io.BytesIO()
    mpf.plot(
        df,
        type="candle",
        style=style,
        volume=True,
        title=title,
        ylabel="",
        ylabel_lower="",
        figsize=(10, 6),
        tight_layout=True,
        savefig=dict(fname=buf, dpi=120, bbox_inches="tight", facecolor="#0d1117"),
    )
    buf.seek(0)
    return buf


async def render_candles(ohlcv: list, title: str) -> io.BytesIO:
    """Async wrapper: render the chart in a thread so we don't block the event loop."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _render_sync, ohlcv, title)
