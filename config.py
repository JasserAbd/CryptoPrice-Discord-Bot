"""Central configuration loaded from the .env file / environment variables."""
import os

from dotenv import load_dotenv

load_dotenv()

# --- Discord ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "!").strip() or "!"

# --- Market data defaults ---
DEFAULT_EXCHANGE = os.getenv("DEFAULT_EXCHANGE", "binance").strip().lower() or "binance"
DEFAULT_QUOTE = os.getenv("DEFAULT_QUOTE", "USDT").strip().upper() or "USDT"

# --- CoinGecko (optional key) ---
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "").strip()

# --- Storage ---
DB_PATH = os.getenv("DB_PATH", "tyr_pricebot.db").strip() or "tyr_pricebot.db"

# --- Branding ---
# Fallback logo shown in embeds when a server hasn't set its own.
DEFAULT_LOGO_URL = os.getenv(
    "DEFAULT_LOGO_URL",
    "https://cryptologos.cc/logos/bitcoin-btc-logo.png",
).strip()

FOOTER_TEXT = os.getenv("FOOTER_TEXT", "Powered by Tyr").strip()

# Embed accent colors (integers). Matches the green/blue/purple bars in the reference bot.
COLOR_PRICE = 0x2ECC71   # green
COLOR_CHART = 0x2ECC71   # green
COLOR_ABOUT = 0x9B59B6   # purple
COLOR_INFO = 0x3498DB    # blue
COLOR_ERROR = 0xE74C3C   # red


def validate() -> None:
    """Raise a helpful error early if the token is missing."""
    if not DISCORD_TOKEN or DISCORD_TOKEN == "paste_your_token_here":
        raise SystemExit(
            "\n[ERROR] No DISCORD_TOKEN found.\n"
            "  1. Copy .env.example to .env\n"
            "  2. Paste your bot token from https://discord.com/developers/applications\n"
        )
