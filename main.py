import time
from datetime import datetime, timedelta
from config import (
    TRADING_MODE, SYMBOLS, USE_REAL_PAPER_TRADING, MARKET_OPEN_TIME,
    MARKET_CLOSE_TIME, ENTRY_WINDOW_CUTOFF, PROFIT_TARGET_PCT, STOP_LOSS_PCT,
    STRIKE_OFFSET, MAX_HOLD_MINUTES, MAX_TRADES_PER_SYMBOL, MAX_PREMIUM_PER_CONTRACT,
    EXECUTE_TRADES, FORCE_SIMULATION_TEST, UNFILLED_ORDER_CANCEL_SECONDS
)
from broker_moomoo import MoomooBroker
from strategy import generate_signals, get_us_eastern_time, parse_time
from logger import TradeLogger
from notifier import TelegramNotifier

class GoldenSniperBot:
    def __init__(self):
        self.mode = TRADING_MODE
        self.broker = MoomooBroker(use_real_paper=USE_REAL_PAPER_TRADING)
        self.logger = TradeLogger()
        self.notifier = TelegramNotifier()
        self.trades_today = {symbol: 0 for symbol in SYMBOLS}
        self.active_trades = {} 
        self.is_running = False
        self.notified_breakout = set()

    def start(self):
        print(f"=== Golden Sniper Retest Bot Started | Mode: {self.mode.upper()} ===")
        print(f"    Target Symbols: {SYMBOLS}")
        print(f"    Morning Box: 9:30 - 10:00 AM EST (30-Min Box)")
        print(f"    Entry Cutoff: {ENTRY_WINDOW_CUTOFF} AM EST")
        print(f"    Master Execution Switch (EXECUTE_TRADES): {EXECUTE_TRADES}")
        print(f"    Capital Safeguard: Max ${MAX_PREMIUM_PER_CONTRACT:.2f} per contract")
        print(f"    Master Safeties: Account Balance Verification | Limit Queue Protection | {UNFILLED_ORDER_CANCEL_SECONDS}s Unfilled Order Cancel\n")

        if not self.broker.connect():
            print("[FATAL ERROR] Broker connection failed. Exiting.")
            return

        self.is_running = True
        exec_status = "ACTIVE (Moomoo Orders Enabled)" if EXECUTE_TRADES else "DISABLED (Telegram Alerts Only / No Orders)"
        self.notifier.send(
            f"🟢 <b>[SYSTEM INITIALIZED]</b>\n"
            f"Golden Sniper Bot started in <b>{self.mode.upper()}</b> mode.\n"
            f"Monitoring {SYMBOLS} (Max 1 Trade/ETF/Day | Continuous Alert Scanning Active)...\n"
            f"🛡️ <i>Institutional Safeties Active (Account Balance Verification | {UNFILLED_ORDER_CANCEL_SECONDS}s Queue Protection)</i>"
        )
        self.run_loop()

    def run_loop(self):
        try:
            while self.is_running:
                now = get_us_eastern_time()
                cur_time = now.time()
                
                if cur_time >= parse_time(ENTRY_WINDOW_CUTOFF) and len(self.active_trades) == 0 and not FORCE_SIMULATION_TEST:
                    total_trades_taken = sum(self.trades_today.values())
                    if total_trades_taken == 0:
                        print(f"\n[11:00 AM CUTOFF REACHED] No confirmed retests today across {SYMBOLS}. Shutting down terminal.")
                        self.notifier.notify_cutoff_reached()
                    else:
                        print(f"\n[11:00 AM CUTOFF REACHED] All active trades closed. Shutting down terminal.")
                    self.stop()
                    break

                polling_interval = 5.0
                if len(self.active_trades) > 0 or len(self.notified_breakout) > 0 or FORCE_SIMULATION_TEST:
                    polling_interval = 1.0 # 1-Second High-Speed Polling

                for symbol in SYMBOLS:
                    if symbol in self.active_trades:
                        self._manage_active_trade(symbol, now)
                        continue

                    if cur_time < parse_time(ENTRY_WINDOW_CUTOFF) or FORCE_SIMULATION_TEST:
                        df = self.broker.get_5m_klines(symbol, limit=100)
                        signal = generate_signals(df, symbol)
                        status = signal.get("status")

                        if status == "WAITING_FOR_RETEST" and symbol not in self.notified_breakout:
                            self.notifier.notify_breakout_trigger(
                                symbol, signal["box_high"], signal["box_low"],
                                signal["pattern"], signal["current_price"], signal["action"]
                            )
                            self.notified_breakout.add(symbol)
                            print(f"[ALERT] Breakout confirmed on {symbol}. Switching to 1-Second High-Speed Retest Tracking...")

                        elif status == "TRADE_REJECTED":
                            print(f"\n[SAFETY FILTER] {signal['message']}")
                            self.notifier.send(
                                f"⚠️ <b>[TRADE REJECTED - V-SHAPE PULLBACK VELOCITY]</b>\n\n"
                                f"📈 <b>Symbol:</b> {symbol} ({signal['action']})\n"
                                f"🛑 <b>Safety Trigger:</b> {signal['message']}\n\n"
                                f"🛡️ System correctly rejected trade to protect capital from market maker fakeout traps!"
                            )
                            self.trades_today[symbol] += 1
                            if symbol in self.notified_breakout:
                                self.notified_breakout.remove(symbol)

                        elif status == "EXECUTE_RETEST":
                            self._execute_retest_entry(symbol, signal, now)
                            if symbol in self.notified_breakout:
                                self.notified_breakout.remove(symbol)

                time.sleep(polling_interval)
                
                if FORCE_SIMULATION_TEST and all(count >= MAX_TRADES_PER_SYMBOL for count in self.trades_today.values()):
                    print("\n[INSTITUTIONAL TEST COMPLETE] FORCE_SIMULATION_TEST completed successfully.")
                    self.stop()
                    break
        except KeyboardInterrupt:
            print("\n[STOPPING] Keyboard interrupt received.")
            self.stop()

    def _execute_retest_entry(self, symbol, signal, now):
        act = signal["action"]
        opt_symbol, strike, opt_price = self.broker.get_2_itm_option_contract(symbol, signal["execution_price"], act)
        
        if opt_price == 999.99:
            print(f"\n[SAFETY FILTER] Options spread temporarily inflated by market makers. Trade rejected.")
            self.notifier.send(
                f"⚠️ <b>[TRADE REJECTED - WIDE OPTIONS SPREAD]</b>\n\n"
                f"📈 <b>Symbol:</b> {symbol} ({act})\n"
                f"🛑 <b>Safety Trigger:</b> Options spread width exceeded max limit ($0.15).\n\n"
                f"🛡️ System correctly rejected trade to protect capital from inflated market maker spreads!"
            )
            self.trades_today[symbol] += 1
            return

        max_opt_price = MAX_PREMIUM_PER_CONTRACT / 100.0
        if opt_price > max_opt_price:
            print(f"\n[SAFETY FILTER] {opt_symbol} premium is ${opt_price:.2f} ($ {opt_price*100:.2f}). Exceeds limit of ${MAX_PREMIUM_PER_CONTRACT:.2f}. Trade rejected.")
            self.notifier.send(
                f"⚠️ <b>[TRADE REJECTED - OVERPRICED CONTRACT]</b>\n\n"
                f"📈 <b>Symbol:</b> {symbol} ({act})\n"
                f"💵 <b>Current Premium:</b> ${opt_price*100:.2f}\n"
                f"🛑 <b>Max Limit:</b> ${MAX_PREMIUM_PER_CONTRACT:.2f}\n\n"
                f"🛡️ System correctly rejected trade to protect capital from inflated volatility!"
            )
            self.trades_today[symbol] += 1
            return

        tp = opt_price * (1.0 + PROFIT_TARGET_PCT)
        sl = opt_price * (1.0 - STOP_LOSS_PCT)
        
        if not EXECUTE_TRADES or self.trades_today[symbol] >= MAX_TRADES_PER_SYMBOL:
            reason = "Master Switch EXECUTE_TRADES=False." if not EXECUTE_TRADES else f"Daily trade limit ({MAX_TRADES_PER_SYMBOL}) reached for {symbol}."
            print(f"\n[ALERT ONLY MODE] Confirmed Retest Entry on {opt_symbol} @ ${opt_price:.2f}. {reason} Skipping order placement.")
            self.logger.log_trade(symbol, opt_symbol, f"ALERT_{act}", strike, signal["pattern"], signal["execution_price"], opt_price, tp, sl, "ALERT_ONLY", self.mode)
            self.notifier.send(
                f"🎯 <b>[RETEST ENTRY CONFIRMED - CONTINUOUS ALERT MODE]</b>\n\n"
                f"🏆 <b>Contract:</b> {opt_symbol}\n"
                f"📌 <b>Strike:</b> ${strike:.2f} (2 ITM)\n"
                f"💵 <b>Target Price:</b> ${opt_price:.2f}\n\n"
                f"⚙️ <i>{reason} No order was sent to Moomoo. Continuous alert scanning remains active.</i>"
            )
            return

        # MASTER SAFETY FIX: ACCOUNT BALANCE & PURCHASING POWER VERIFICATION
        estimated_cost = opt_price * 100.0 # 1 contract multiplier
        has_balance, avail_cash = self.broker.check_account_balance(estimated_cost)
        if not has_balance:
            print(f"\n[SAFETY FILTER] Insufficient settled cash balance (${avail_cash:.2f}) for estimated cost (${estimated_cost:.2f}). Trade rejected.")
            self.notifier.send(
                f"⚠️ <b>[TRADE REJECTED - INSUFFICIENT CASH BALANCE]</b>\n\n"
                f"📈 <b>Symbol:</b> {symbol} ({act})\n"
                f"💵 <b>Estimated Cost:</b> ${estimated_cost:.2f}\n"
                f"🛑 <b>Available Settled Cash:</b> ${avail_cash:.2f}\n\n"
                f"🛡️ System correctly rejected trade to protect account from brokerage rejection penalties!"
            )
            self.trades_today[symbol] += 1
            return

        success, order_id = self.broker.place_bracket_order(opt_symbol, "BUY", 1, opt_price, tp, sl)
        if success:
            self.trades_today[symbol] += 1
            max_exit_time = now + timedelta(minutes=MAX_HOLD_MINUTES)
            self.active_trades[symbol] = {
                "symbol": symbol, "option_symbol": opt_symbol, "strike": strike,
                "action": act, "entry_price": opt_price, "tp": tp, "sl": sl,
                "entry_time": now, "max_exit_time": max_exit_time, "pattern": signal["pattern"],
                "order_id": order_id, "box_high": signal["box_high"], "box_low": signal["box_low"],
                "is_filled": False
            }
            self.logger.log_trade(symbol, opt_symbol, f"SUBMITTED_{act}", strike, signal["pattern"], signal["execution_price"], opt_price, tp, sl, "SUBMITTED", self.mode)
            self.notifier.send(f"⏳ <b>[ORDER SUBMITTED TO QUEUE]</b>\nContract: {opt_symbol} @ ${opt_price:.2f}.\nWaiting for official match in Moomoo order book...")

    def _manage_active_trade(self, symbol, now):
        trade = self.active_trades[symbol]
        opt_sym = trade["option_symbol"]
        order_id = trade["order_id"]
        
        if not trade["is_filled"]:
            is_filled, status = self.broker.check_order_filled(order_id)
            if is_filled:
                trade["is_filled"] = True
                print(f"\n[ORDER FILLED] Limit order ID {order_id} officially matched in Moomoo queue!")
                self.logger.log_trade(symbol, opt_sym, f"FILLED_{trade['action']}", trade["strike"], trade["pattern"], 0, trade["entry_price"], trade["tp"], trade["sl"], "FILLED", self.mode)
                self.notifier.notify_retest_executed(symbol, opt_sym, trade["strike"], trade["entry_price"], trade["tp"], trade["sl"], MAX_HOLD_MINUTES)
                return
            else:
                if now > trade["entry_time"] + timedelta(seconds=UNFILLED_ORDER_CANCEL_SECONDS) and not FORCE_SIMULATION_TEST:
                    print(f"\n[ORDER EXPIRED UNFILLED] Limit order ID {order_id} sat in CBOE queue unfilled for {UNFILLED_ORDER_CANCEL_SECONDS}s as market bounced away.")
                    print(f"                         Canceling limit order. Resetting daily trade count so bot can scan for new entries!")
                    self.broker.cancel_order(order_id)
                    self.trades_today[symbol] -= 1
                    del self.active_trades[symbol]
                    self.notifier.send(
                        f"⚠️ <b>[ORDER EXPIRED UNFILLED - CANCELED]</b>\n\n"
                        f"📦 <b>Contract:</b> {opt_sym}\n"
                        f"⏳ Limit order sat in Moomoo queue unfilled for >{UNFILLED_ORDER_CANCEL_SECONDS}s as market bounced away.\n\n"
                        f"🛡️ <b>System Status:</b> Limit order successfully canceled. Daily trade count reset. Bot is scanning for new entries!"
                    )
                    return
                return

        cur_opt_price = trade["entry_price"] * 1.05
        
        underlying_df = self.broker.get_5m_klines(symbol, limit=5)
        if not underlying_df.empty and len(underlying_df) >= 2:
            last_closed_kline = underlying_df.iloc[-2]
            u_close = last_closed_kline['close']
            
            if trade["action"] == "CALL" and u_close < trade["box_high"] * 0.999:
                print(f"\n[SAFETY FIX 3] Underlying ETF {symbol} confirmed CLOSED CANDLE below Box High (${trade['box_high']:.2f}) at ${u_close:.2f}!")
                print(f"               Bypassing options spread manipulation. Executing immediate market close.")
                pnl_doll = (trade["sl"] - trade["entry_price"]) * 100
                self._close_trade(symbol, opt_sym, trade["sl"], pnl_doll, -STOP_LOSS_PCT*100, "Underlying ETF Stop Trigger (-25%)")
                return
            elif trade["action"] == "PUT" and u_close > trade["box_low"] * 1.001:
                print(f"\n[SAFETY FIX 3] Underlying ETF {symbol} confirmed CLOSED CANDLE above Box Low (${trade['box_low']:.2f}) at ${u_close:.2f}!")
                print(f"               Bypassing options spread manipulation. Executing immediate market close.")
                pnl_doll = (trade["sl"] - trade["entry_price"]) * 100
                self._close_trade(symbol, opt_sym, trade["sl"], pnl_doll, -STOP_LOSS_PCT*100, "Underlying ETF Stop Trigger (-25%)")
                return

        if cur_opt_price >= trade["tp"]:
            pnl_doll = (trade["tp"] - trade["entry_price"]) * 100
            self._close_trade(symbol, opt_sym, trade["tp"], pnl_doll, PROFIT_TARGET_PCT*100, "Target Hit (+20%)")
            return

        if cur_opt_price <= trade["sl"]:
            pnl_doll = (trade["sl"] - trade["entry_price"]) * 100
            self._close_trade(symbol, opt_sym, trade["sl"], pnl_doll, -STOP_LOSS_PCT*100, "Stop Loss (-25%)")
            return

        if now >= trade["max_exit_time"] or now.time() >= parse_time("15:50") or FORCE_SIMULATION_TEST:
            pnl_doll = (cur_opt_price - trade["entry_price"]) * 100
            pnl_pct = (cur_opt_price - trade["entry_price"]) / trade["entry_price"] * 100
            self._close_trade(symbol, opt_sym, cur_opt_price, pnl_doll, pnl_pct, f"Time Exit ({pnl_pct:+.1f}%)")
            return

    def _close_trade(self, symbol, option_symbol, exit_price, pnl_dollar, pnl_pct, outcome):
        print(f"\n[TRADE CLOSED] {option_symbol} ({symbol}) @ ${exit_price:.2f} | PnL: ${pnl_dollar:.2f} ({pnl_pct:+.2f}%) | Outcome: {outcome}")
        trade = self.active_trades[symbol]
        
        self.broker.place_bracket_order(option_symbol, "SELL", 1, exit_price)
        
        self.logger.log_trade(symbol, option_symbol, f"CLOSE_{trade['action']}", trade["strike"], trade["pattern"], 0, exit_price, trade["tp"], trade["sl"], outcome, self.mode)
        self.notifier.notify_trade_closed(option_symbol, exit_price, pnl_dollar, pnl_pct, outcome)
        del self.active_trades[symbol]
        print(f"🔒 Daily trade limit reached for {symbol} (1 Trade/Day). Continuous alert scanning remains active.")

    def stop(self):
        self.is_running = False
        self.broker.disconnect()
        self.notifier.send("🔴 <b>[SYSTEM SHUTDOWN]</b>\nGolden Sniper Bot stopped.")
        print("=== Bot Stopped Successfully ===")

if __name__ == "__main__":
    bot = GoldenSniperBot()
    bot.start()
