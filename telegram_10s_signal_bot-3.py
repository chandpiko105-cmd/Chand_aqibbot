"""
Telegram 10-second UP/DOWN signal bot (signal-only).

IMPORTANT:
- This bot does NOT place trades on Quotex.
- It generates educational signals from candle data supplied by a data feed.
- You must connect a legitimate/authorized market-data source yourself.
- Do not paste your Telegram bot token into public chats or source-control.

Install:
    pip install python-telegram-bot pandas

Environment:
    TELEGRAM_BOT_TOKEN=YOUR_TOKEN

Run:
    python bot.py

Expected candle format for the strategy function:
    timestamp, open, high, low, close
with timestamp in ascending order and candles preferably <= 10 seconds.

Strategy (simple momentum filter):
- EMA(5) > EMA(13), close above EMA(5), RSI(7) >= 55, and the
  latest 3 closes are rising => UP
- EMA(5) < EMA(13), close below EMA(5), RSI(7) <= 45, and the
  latest 3 closes are falling => DOWN
- Otherwise => NO TRADE

This is not a prediction guarantee. Test on demo/paper data first.
"""

import os
import math
import pandas as pd
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("Set TELEGRAM_BOT_TOKEN in your environment first.")


def rsi(series: pd.Series, period: int = 7) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, math.nan)
    return 100 - (100 / (1 + rs))


def signal_from_candles(candles: pd.DataFrame) -> str:
    """Return UP, DOWN, or NO TRADE from recent OHLC candles."""
    required = {"open", "high", "low", "close"}
    if not required.issubset(candles.columns) or len(candles) < 20:
        return "NO TRADE"

    df = candles.copy()
    df["ema5"] = df["close"].ewm(span=5, adjust=False).mean()
    df["ema13"] = df["close"].ewm(span=13, adjust=False).mean()
    df["rsi7"] = rsi(df["close"], 7)

    last = df.iloc[-1]
    recent = df["close"].tail(3)

    rising = recent.iloc[0] < recent.iloc[1] < recent.iloc[2]
    falling = recent.iloc[0] > recent.iloc[1] > recent.iloc[2]

    if (
        last["ema5"] > last["ema13"]
        and last["close"] > last["ema5"]
        and last["rsi7"] >= 55
        and rising
    ):
        return "UP"

    if (
        last["ema5"] < last["ema13"]
        and last["close"] < last["ema5"]
        and last["rsi7"] <= 45
        and falling
    ):
        return "DOWN"

    return "NO TRADE"


# Replace this function with candles from your authorized data provider.
def get_latest_candles() -> pd.DataFrame:
    """
    Example only. Return a DataFrame with:
    timestamp, open, high, low, close

    Do NOT scrape or automate an exchange/broker interface unless
    its terms and API explicitly allow it.
    """
    raise NotImplementedError(
        "Connect an authorized market-data source in get_latest_candles()."
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bot تیار ہے۔ /signal بھیج کر تازہ سگنل چیک کریں۔\n"
        "یہ signal-only bot ہے اور خود trade نہیں لگاتا۔"
    )


async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        candles = get_latest_candles()
        result = signal_from_candles(candles)

        if result == "UP":
            msg = "📈 UP signal\n⏱️ 10-second setup\n⚠️ Educational signal — guarantee نہیں۔"
        elif result == "DOWN":
            msg = "📉 DOWN signal\n⏱️ 10-second setup\n⚠️ Educational signal — guarantee نہیں۔"
        else:
            msg = "⏸️ NO TRADE\nConditions واضح نہیں ہیں۔"

        await update.message.reply_text(msg)

    except NotImplementedError:
        await update.message.reply_text(
            "⚠️ ابھی market-data source connect نہیں کیا گیا۔\n"
            "get_latest_candles() میں اپنے مجاز data provider کی feed لگائیں۔"
        )
    except Exception as exc:
        await update.message.reply_text(f"⚠️ Signal error: {exc}")


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("signal", signal))
    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
