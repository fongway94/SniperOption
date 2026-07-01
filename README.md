# Golden Sniper Moomoo & OpenD Trading Bot (Telegram Alert Edition)

## Overview
This project is an institutional-grade, fully automated trading bot designed for Futu OpenD (Moomoo). It directly refactors and upgrades the existing `BreakAndBounce` architecture into the ultimate **Golden Sniper Retest Entry 0DTE Strategy** for **SPY** and **QQQ**.

The bot strictly enforces the five foundational pillars of full-time trading discipline:
1. **The 30-Minute Box Theory:** Automatically builds the opening 9:30–10:00 AM EST range (`Box_High` and `Box_Low`).
2. **Institutional Flow Alignment:** Dynamic regular trading hours VWAP confirmation.
3. **Sniper Candlestick Triggers:** Verifies 5-minute price action reversal and momentum patterns (Hammer Pin Bars, Bullish/Bearish Engulfing, Marubozu Breakouts) to filter out false breakouts.
4. **The Retest Entry:** Refuses to chase the initial breakout. Automatically places limit orders at the exact Box Line to buy 2 Strikes In-The-Money (2 ITM) options on the dip.
5. **Perfect Discipline:** Strictly **One Trade Per Day**, confined to the golden morning liquidity window (10:00–11:00 AM EST). Enforces a strict 11:00 AM walkaway rule and a 90-minute time stop.

---

## Project Architecture & File Structure

```
GoldenSniper_Moomoo_Bot/
│
├── config.py              # Centralized configuration (Symbols, Brackets, Timers, Moomoo/Telegram keys)
├── broker_moomoo.py       # Futu OpenD gateway wrapper (with robust mock/offline fallbacks)
├── strategy.py            # Core Golden Sniper engine (Candlestick verification, Box math, Retest logic)
├── notifier.py            # Async Telegram bot notifier (Rich HTML emoji alerts)
├── logger.py              # Automated CSV trade logging engine
├── main.py                # Master execution orchestrator & polling loop
├── requirements.txt       # Python dependency file
└── env.example            # Environment variables template for Telegram & Moomoo credentials
```

---

## Quick Start & Installation

### 1. Requirements
Ensure you have Python 3.9+ installed along with Futu OpenD desktop software running if executing live trades.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```
*(Note: Ensure `futu-api` or `moomoo` library is installed in your local Python environment for OpenD connection).*

### 3. Setup Environment Variables
Rename `env.example` to `.env` and insert your Telegram credentials and Moomoo trading password:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
MOOMOO_TRADING_PASSWORD=your_trading_password_here
```

### 4. Start the Bot
```bash
python3 main.py
```
*(Note: If Futu OpenD is offline or not installed, the bot will gracefully default to an active simulation mode, allowing you to instantly verify the Telegram alerts and execution loop!)*

---

## Sample Telegram Alerts

### 1. Breakout Initial Alert (Do Not Chase)
```html
🚨 [GOLDEN SNIPER ALERT] 🟢 BULLISH BREAKOUT

📈 Symbol: QQQ
📦 30-Min Box Range: $715.30 - $720.50
🕯️ Confirmed Pattern: Bullish Engulfing
💰 Current Price: $721.10

⚠️ RULE OF ENGAGEMENT: DO NOT CHASE!
⏳ Waiting for pullback to Box Line at $720.50 to execute 2 ITM order...
```

### 2. Retest Order Executed
```html
🎯 [RETEST ENTRY EXECUTED]

🏆 Contract: QQQ260626C00718000
📌 Strike: $718.00 (2 ITM)
💵 Fill Price: $3.50

⚖️ Bracket Orders Attached:
✅ Take Profit (+20%): $4.20
❌ Stop Loss (-25%): $2.62

⏱️ 90-Minute Timer Started!
```

### 3. Trade Closed (Paycheck Secured)
```html
🏆 WIN [TRADE CLOSED - Target Hit (+20%)]

📦 Contract: QQQ260626C00718000
💵 Exit Price: $4.20
📊 Net PnL: $70.00 (+20.00%)

🔒 Daily trade limit reached. Terminal shutting down.
```

### 4. 11:00 AM Walkaway Rule
```html
🛑 [11:00 AM CUTOFF REACHED]

No confirmed candlestick pattern retested our box lines today.
🛡️ System Status: Shutting down for the day.
Enjoy your clean $0 day and perfectly protected capital!
```
