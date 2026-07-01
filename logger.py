import os
import csv
from datetime import datetime
from config import LOG_FILE

class TradeLogger:
    def __init__(self):
        self.log_file = LOG_FILE
        self._ensure_log_file()

    def _ensure_log_file(self):
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Timestamp", "Symbol", "Option_Symbol", "Action", "Strike",
                    "Pattern", "Mkt_Price", "Option_Price", "Take_Profit", "Stop_Loss", "Outcome", "Mode"
                ])

    def log_trade(self, symbol, option_symbol, action, strike, pattern, mkt_price, opt_price, tp, sl, outcome, mode):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp, symbol, option_symbol, action, strike,
                pattern, mkt_price, opt_price, tp, sl, outcome, mode
            ])
        print(f"[LOG] {action} {option_symbol} @ ${opt_price:.2f} | Pattern: {pattern}")
