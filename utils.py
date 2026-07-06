"""Small shared helpers for formatting and per-guild defaults."""
from typing import Optional

import config
import db


def fmt_num(value: Optional[float], prefix: str = "") -> str:
    """Human-friendly number: thousands separators, trims useless decimals."""
    if value is None:
        return "N/A"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if value == 0:
        return f"{prefix}0"
    # Big numbers: no decimals. Small prices: keep precision.
    if abs(value) >= 1000:
        return f"{prefix}{value:,.2f}"
    if abs(value) >= 1:
        return f"{prefix}{value:,.4f}".rstrip("0").rstrip(".")
    return f"{prefix}{value:,.8f}".rstrip("0").rstrip(".")


def resolve_context(guild_id: Optional[int], coin: Optional[str]) -> tuple[str, str, str, Optional[str]]:
    """Resolve (coin, exchange, quote, logo_url) using the guild config as defaults.

    If `coin` is given it overrides the server's default coin.
    """
    if guild_id is None:
        # DMs: fall back to global defaults.
        return (
            (coin or "BTC").upper(),
            config.DEFAULT_EXCHANGE,
            config.DEFAULT_QUOTE,
            config.DEFAULT_LOGO_URL,
        )
    cfg = db.get_guild_config(guild_id)
    return (
        (coin or cfg["coin"] or "BTC").upper(),
        cfg["exchange"] or config.DEFAULT_EXCHANGE,
        cfg["quote"] or config.DEFAULT_QUOTE,
        cfg["logo_url"] or config.DEFAULT_LOGO_URL,
    )
