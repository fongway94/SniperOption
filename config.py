import os
from dotenv import load_dotenv

load_dotenv()

# ==================== TRADING MODE & EXECUTION SWITCHES ====================
TRADING_MODE = "paper" # 'paper' or 'live'
USE_REAL_PAPER_TRADING = True
EXECUTE_TRADES = True                    # Master Switch: True = Execute Orders | False = Alert Only (No Orders)
FORCE_SIMULATION_TEST = False            # True = Instant Pipeline & Telegram Test (Ignores market hours)

# ==================== SYMBOLS ====================
SYMBOLS = ["SPY", "QQQ"]

# ==================== TIME SETTINGS (US Eastern) ====================
MARKET_OPEN_TIME = "09:30"
BOX_WINDOW_MINUTES = 30                  # 9:30 - 10:00 AM EST (30-min Box)
ENTRY_WINDOW_CUTOFF = "11:00"            # No new entries after 11:00 AM EST
MARKET_CLOSE_TIME = "16:00"
FORCE_CLOSE_BUFFER_MINUTES = 10          # Force close at 3:50 PM EST if held all day

# ==================== GOLDEN SNIPER STRATEGY SETTINGS ====================
PROFIT_TARGET_PCT = 0.20                 # +20% Take Profit
STOP_LOSS_PCT = 0.25                     # -25% Stop Loss
STRIKE_OFFSET = -2                       # 2 Strikes In-The-Money (2 ITM)
MAX_HOLD_MINUTES = 90                    # 90-minute time stop
MAX_TRADES_PER_SYMBOL = 1                # Strict discipline: 1 trade per ETF per day

# ==================== RISK & CAPITAL SAFEGUARDS ====================
DEFAULT_EQUITY = 25000
MAX_DAILY_LOSS = 500
MAX_PREMIUM_PER_CONTRACT = 400.0         # Max allowable cost per contract ($4.00 option price)
UNFILLED_ORDER_CANCEL_SECONDS = 60       # Cancel unfilled limit orders after 60 seconds
MAX_BID_ASK_SPREAD = 0.15                # Master Safety Fix: Max allowable options spread width ($0.15)

# ==================== TELEGRAM ====================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ==================== MOOMOO / OpenD ====================
MOOMOO_HOST = "127.0.0.1"
MOOMOO_PORT = 11111
MOOMOO_TRADING_PASSWORD = os.getenv("MOOMOO_TRADING_PASSWORD", "")

# ==================== LOGGING ====================
LOG_FILE = "logs/golden_sniper_trade_log.csv"
