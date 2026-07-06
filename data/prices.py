"""Market-data helpers.

Two sources:
  - CCXT  -> live ticker (price/volume/high/low) and OHLCV candles from real exchanges.
  - CoinGecko -> coin metadata (full name, market cap, circulating supply, logo image).

Everything here is async-friendly: CCXT calls are run in a thread executor so they
don't block the Discord event loop, and CoinGecko is queried with aiohttp.
"""
import asyncio
from typing import Optional

import aiohttp
import ccxt

import config

# Cache one CCXT exchange client per exchange id so we don't rebuild markets each call.
_exchange_clients: dict[str, ccxt.Exchange] = {}

# In-memory cache of resolved symbol -> coingecko-id so repeat lookups are fast.
_coingecko_ids: dict[str, str] = {}

# A few well-known tickers pinned to their canonical CoinGecko id. This avoids any
# ambiguity for the coins people actually ask about most.
_KNOWN_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "USDT": "tether",
    "BNB": "binancecoin",
    "SOL": "solana",
    "XRP": "ripple",
    "USDC": "usd-coin",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "TRX": "tron",
    "TON": "the-open-network",
    "AVAX": "avalanche-2",
    "SHIB": "shiba-inu",
    "DOT": "polkadot",
    "LINK": "chainlink",
    "MATIC": "matic-network",
    "LTC": "litecoin",
    "BCH": "bitcoin-cash",
    "XMR": "monero",
}

_COINGECKO_BASE = "https://api.coingecko.com/api/v3"


class MarketError(Exception):
    """Raised when a symbol/exchange can't be resolved or fetched."""


def _get_client(exchange_id: str) -> ccxt.Exchange:
    exchange_id = (exchange_id or config.DEFAULT_EXCHANGE).lower()
    if exchange_id not in _exchange_clients:
        if not hasattr(ccxt, exchange_id):
            raise MarketError(f"Unknown exchange `{exchange_id}`.")
        klass = getattr(ccxt, exchange_id)
        _exchange_clients[exchange_id] = klass({"enableRateLimit": True})
    return _exchange_clients[exchange_id]


def _symbol(coin: str, quote: str) -> str:
    return f"{coin.upper()}/{quote.upper()}"


# --------------------------------------------------------------------------- #
# CCXT: live price + candles
# --------------------------------------------------------------------------- #
def _fetch_ticker_sync(exchange_id: str, symbol: str) -> dict:
    client = _get_client(exchange_id)
    return client.fetch_ticker(symbol)


async def fetch_ticker(coin: str, quote: str, exchange_id: str) -> dict:
    """Return a normalized ticker dict for coin/quote on the given exchange."""
    symbol = _symbol(coin, quote)
    loop = asyncio.get_running_loop()
    try:
        t = await loop.run_in_executor(None, _fetch_ticker_sync, exchange_id, symbol)
    except ccxt.BadSymbol:
        raise MarketError(f"`{symbol}` isn't listed on `{exchange_id}`.")
    except ccxt.BaseError as e:
        raise MarketError(f"Exchange error: {type(e).__name__}")
    return {
        "symbol": symbol,
        "exchange": exchange_id,
        "price": t.get("last"),
        "volume": t.get("baseVolume") or t.get("quoteVolume"),
        "high": t.get("high"),
        "low": t.get("low"),
        "change_pct": t.get("percentage"),
    }


def _fetch_ohlcv_sync(exchange_id: str, symbol: str, timeframe: str, limit: int) -> list:
    client = _get_client(exchange_id)
    return client.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)


async def fetch_ohlcv(
    coin: str, quote: str, exchange_id: str, timeframe: str = "1h", limit: int = 50
) -> list:
    """Return raw OHLCV rows: [timestamp, open, high, low, close, volume]."""
    symbol = _symbol(coin, quote)
    loop = asyncio.get_running_loop()
    try:
        rows = await loop.run_in_executor(
            None, _fetch_ohlcv_sync, exchange_id, symbol, timeframe, limit
        )
    except ccxt.BadSymbol:
        raise MarketError(f"`{symbol}` isn't listed on `{exchange_id}`.")
    except ccxt.BaseError as e:
        raise MarketError(f"Exchange error: {type(e).__name__}")
    if not rows:
        raise MarketError(f"No candle data for `{symbol}`.")
    return rows


def list_exchanges() -> list[str]:
    """All exchange ids CCXT supports."""
    return sorted(ccxt.exchanges)


# --------------------------------------------------------------------------- #
# CoinGecko: coin metadata + logo
# --------------------------------------------------------------------------- #
def _cg_headers() -> dict:
    if config.COINGECKO_API_KEY:
        return {"x-cg-demo-api-key": config.COINGECKO_API_KEY}
    return {}


async def _resolve_coin_id(session: aiohttp.ClientSession, coin: str) -> str:
    """Resolve a ticker symbol to its canonical CoinGecko id.

    Order of preference:
      1. cached result
      2. hard-coded well-known coins
      3. CoinGecko /search (results are ranked by market cap, so the real coin
         wins over the countless copycats sharing the same symbol)
    """
    coin = coin.upper()
    if coin in _coingecko_ids:
        return _coingecko_ids[coin]
    if coin in _KNOWN_IDS:
        _coingecko_ids[coin] = _KNOWN_IDS[coin]
        return _coingecko_ids[coin]

    async with session.get(
        f"{_COINGECKO_BASE}/search", params={"query": coin}, headers=_cg_headers()
    ) as r:
        if r.status != 200:
            raise MarketError("CoinGecko search failed. Try again shortly.")
        data = await r.json()

    candidates = data.get("coins", [])
    # Prefer an exact symbol match (highest market-cap rank first), else the top hit.
    exact = [c for c in candidates if c.get("symbol", "").upper() == coin]
    chosen = (exact or candidates)
    if not chosen:
        raise MarketError(f"Couldn't find coin `{coin}` on CoinGecko.")
    cg_id = chosen[0]["id"]
    _coingecko_ids[coin] = cg_id
    return cg_id


async def fetch_coin_info(coin: str) -> dict:
    """Return name, symbol, market cap, circulating supply and logo url for a coin."""
    coin = coin.upper()
    async with aiohttp.ClientSession() as session:
        cg_id = await _resolve_coin_id(session, coin)

        url = (
            f"{_COINGECKO_BASE}/coins/{cg_id}"
            "?localization=false&tickers=false&market_data=true"
            "&community_data=false&developer_data=false&sparkline=false"
        )
        async with session.get(url, headers=_cg_headers()) as r:
            if r.status != 200:
                raise MarketError("CoinGecko request failed. Try again shortly.")
            data = await r.json()

    market = data.get("market_data", {})
    return {
        "ticker": coin,
        "name": data.get("name", coin),
        "logo_url": (data.get("image") or {}).get("large"),
        "market_cap": (market.get("market_cap") or {}).get("usd"),
        "circulating_supply": market.get("circulating_supply"),
        "current_price": (market.get("current_price") or {}).get("usd"),
    }


async def fetch_logo(coin: str) -> Optional[str]:
    """Best-effort logo lookup used to auto-fill a server's branding."""
    try:
        info = await fetch_coin_info(coin)
        return info.get("logo_url")
    except MarketError:
        return None
