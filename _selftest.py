"""Quick offline self-test of the data layer (no Discord token required)."""
import asyncio

from data import prices, charts


async def main():
    print("1) fetch_ticker BTC/USDT on binance ...")
    t = await prices.fetch_ticker("BTC", "USDT", "binance")
    print("   price:", t["price"], "high:", t["high"], "low:", t["low"])

    print("2) fetch_coin_info BTC (CoinGecko) ...")
    info = await prices.fetch_coin_info("BTC")
    print("   name:", info["name"], "mcap:", info["market_cap"], "logo:", bool(info["logo_url"]))

    print("3) fetch_ohlcv + render chart ...")
    ohlcv = await prices.fetch_ohlcv("BTC", "USDT", "binance", "1h", 30)
    buf = await charts.render_candles(ohlcv, "Chart for BTC/USDT on Binance")
    size = len(buf.getvalue())
    print("   chart PNG bytes:", size)

    print("4) list_exchanges count:", len(prices.list_exchanges()))
    print("\nALL GOOD")


if __name__ == "__main__":
    asyncio.run(main())
