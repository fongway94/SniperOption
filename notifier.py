import telegram
from telegram import Bot
import asyncio
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

class TelegramNotifier:
    def __init__(self, token=TELEGRAM_BOT_TOKEN, chat_id=TELEGRAM_CHAT_ID):
        self.token = token
        self.chat_id = chat_id
        self.bot = Bot(token=self.token) if self.token else None

    async def _send_message_async(self, message):
        if not self.bot or not self.chat_id:
            print(f"[TELEGRAM SIMULATION - TOKEN/CHAT_ID NOT SET]\n{message}\n")
            return
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message, parse_mode='HTML')
            print(f"[TELEGRAM] Alert sent to chat {self.chat_id}")
        except Exception as e:
            print(f"[TELEGRAM ERROR] Failed to send message: {e}")

    def send(self, message):
        """Send message synchronously by wrapping asyncio loop."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            # If running inside an existing event loop
            asyncio.create_task(self._send_message_async(message))
        else:
            loop.run_until_complete(self._send_message_async(message))

    def notify_breakout_trigger(self, symbol, box_high, box_low, pattern, current_price, action):
        direction = "🟢 BULLISH BREAKOUT" if action == "CALL" else "🔴 BEARISH BREAKOUT"
        msg = (
            f"🚨 <b>[GOLDEN SNIPER ALERT] {direction}</b>\n\n"
            f"📈 <b>Symbol:</b> {symbol}\n"
            f"📦 <b>30-Min Box Range:</b> ${box_low:.2f} - ${box_high:.2f}\n"
            f"🕯️ <b>Confirmed Pattern:</b> {pattern}\n"
            f"💰 <b>Current Price:</b> ${current_price:.2f}\n\n"
            f"⚠️ <b>RULE OF ENGAGEMENT: DO NOT CHASE!</b>\n"
            f"⏳ Waiting for pullback to Box Line at <b>${box_high if action=='CALL' else box_low:.2f}</b> to execute 2 ITM order..."
        )
        self.send(msg)

    def notify_retest_executed(self, symbol, option_symbol, strike, opt_price, tp, sl, max_hold_mins):
        msg = (
            f"🎯 <b>[RETEST ENTRY EXECUTED]</b>\n\n"
            f"🏆 <b>Contract:</b> {option_symbol}\n"
            f"📌 <b>Strike:</b> ${strike:.2f} (2 ITM)\n"
            f"💵 <b>Fill Price:</b> ${opt_price:.2f}\n\n"
            f"⚖️ <b>Bracket Orders Attached:</b>\n"
            f"✅ <b>Take Profit (+20%):</b> ${tp:.2f}\n"
            f"❌ <b>Stop Loss (-25%):</b> ${sl:.2f}\n\n"
            f"⏱️ <b>{max_hold_mins}-Minute Timer Started!</b>"
        )
        self.send(msg)

    def notify_trade_closed(self, option_symbol, exit_price, pnl_dollar, pnl_pct, outcome):
        icon = "🏁"
        if "Target Hit" in outcome: icon = "🏆 WIN"
        elif "Stop Loss" in outcome: icon = "⚠️ LOSS"
        msg = (
            f"{icon} <b>[TRADE CLOSED - {outcome}]</b>\n\n"
            f"📦 <b>Contract:</b> {option_symbol}\n"
            f"💵 <b>Exit Price:</b> ${exit_price:.2f}\n"
            f"📊 <b>Net PnL:</b> ${pnl_dollar:.2f} ({pnl_pct:+.2f}%)\n\n"
            f"🔒 Daily trade limit reached. Terminal shutting down."
        )
        self.send(msg)

    def notify_cutoff_reached(self):
        msg = (
            f"🛑 <b>[11:00 AM CUTOFF REACHED]</b>\n\n"
            f"No confirmed candlestick pattern retested our box lines today.\n"
            f"🛡️ <b>System Status:</b> Shutting down for the day.\n"
            f"Enjoy your clean $0 day and perfectly protected capital!"
        )
        self.send(msg)
