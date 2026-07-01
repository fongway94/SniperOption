import time
import pandas as pd
import numpy as np
from datetime import datetime
from config import MOOMOO_HOST, MOOMOO_PORT, MOOMOO_TRADING_PASSWORD, USE_REAL_PAPER_TRADING, STRIKE_OFFSET, FORCE_SIMULATION_TEST, MAX_BID_ASK_SPREAD

try:
    from moomoo import *
    FUTU_SDK_AVAILABLE = True
except ImportError:
    try:
        from futu import *
        FUTU_SDK_AVAILABLE = True
    except ImportError:
        FUTU_SDK_AVAILABLE = False
        class TrdSide: BUY = "BUY"; SELL = "SELL"
        class OrderType: NORMAL = "NORMAL"
        class TrdEnv: REAL = "REAL"; SIMULATE = "SIMULATE"
        class OrderStatus: FILLED = "FILLED"; SUBMITTED = "SUBMITTED"; WAITING_TO_MATCH = "WAITING_TO_MATCH"; CANCELLED = "CANCELLED"; FAILED = "FAILED"
        class ModifyOrderOp: CANCEL = "CANCEL"
        class TrdMarket: US = "US"
        class SecurityFirm: FUTUINC = "FUTUINC"
        class KLType: K_5M = "K_5M"
        class SubType: K_5M = "K_5M"; QUOTE = "QUOTE"
        class OptionType: CALL = "CALL"; PUT = "PUT"
        class OptionCondType: ALL = "ALL"
        RET_OK = 0

class MoomooBroker:
    def __init__(self, host=MOOMOO_HOST, port=MOOMOO_PORT, use_real_paper=USE_REAL_PAPER_TRADING):
        self.host = host
        self.port = port
        self.use_real_paper = use_real_paper
        self.quote_ctx = None
        self.trade_ctx = None
        self.acc_id = None
        self.acc_index = 1 if use_real_paper else 0
        self.connected = False
        self.is_simulation = not FUTU_SDK_AVAILABLE or FORCE_SIMULATION_TEST
        self.subscribed_klines = set()

    def connect(self):
        if self.is_simulation:
            mode_str = "PAPER MARGIN (acc_index=1)" if self.use_real_paper else "LIVE CASH ACCOUNT (acc_index=0 - PDT Bypass)"
            print(f"[SIMULATION MODE] Running in active simulation mode. Target Broker Account: {mode_str}.")
            self.connected = True
            return True

        try:
            self.quote_ctx = OpenQuoteContext(host=self.host, port=self.port)
            self.trade_ctx = OpenSecTradeContext(
                filter_trdmarket=TrdMarket.US, host=self.host, port=self.port, security_firm=SecurityFirm.FUTUINC
            )
            ret, data = self.trade_ctx.get_acc_list()
            if ret == RET_OK and not data.empty:
                if self.use_real_paper:
                    sim_accounts = data[data['trd_env'] == TrdEnv.SIMULATE] if 'trd_env' in data.columns else data
                    if len(sim_accounts) > 1:
                        self.acc_id = sim_accounts['acc_id'].iloc[1]
                    else:
                        self.acc_id = sim_accounts['acc_id'].iloc[0]
                    self.acc_index = 1
                    print(f"[MOOMOO] Connected successfully. Using Paper Options Margin Account ID: {self.acc_id}")
                else:
                    real_accounts = data[data['trd_env'] == TrdEnv.REAL] if 'trd_env' in data.columns else data
                    cash_accs = real_accounts[real_accounts['acc_type'].astype(str).str.contains('CASH', case=False)] if 'acc_type' in real_accounts.columns else real_accounts
                    if not cash_accs.empty:
                        self.acc_id = cash_accs['acc_id'].iloc[0]
                    else:
                        self.acc_id = real_accounts['acc_id'].iloc[0]
                    self.acc_index = 0
                    print(f"[MOOMOO] Connected successfully. Using Live CASH ACCOUNT ID (PDT Bypass): {self.acc_id}")
            else:
                print(f"[MOOMOO WARNING] Could not retrieve account list: {data}")
            self.connected = True
            return True
        except Exception as e:
            mode_str = "PAPER MARGIN" if self.use_real_paper else "LIVE CASH ACCOUNT"
            print(f"[MOOMOO CONNECTION FAILED] OpenD gateway unreachable: {e}. Switching to active {mode_str} simulation mode.")
            self.is_simulation = True
            self.connected = True
            return True

    def disconnect(self):
        if self.quote_ctx and not self.is_simulation: self.quote_ctx.close()
        if self.trade_ctx and not self.is_simulation: self.trade_ctx.close()
        print("[MOOMOO] Disconnected from OpenD.")

    def check_account_balance(self, estimated_cost):
        if self.is_simulation:
            print(f"[ACCOUNT CHECK] Simulation balance $25,000.00 sufficient for estimated cost ${estimated_cost:.2f}.")
            return True, 25000.0

        ret, data = self.trade_ctx.accinfo_query(
            trd_env=TrdEnv.SIMULATE if self.use_real_paper else TrdEnv.REAL,
            acc_id=self.acc_id, acc_index=self.acc_index
        )
        if ret == RET_OK and not data.empty:
            cash = data['cash'][0] if 'cash' in data.columns else data['power'][0]
            if cash < estimated_cost:
                print(f"[MOOMOO ERROR] Insufficient cash balance! Available: ${cash:.2f} | Estimated Cost: ${estimated_cost:.2f}")
                return False, cash
            print(f"[ACCOUNT CHECK] Available cash balance (${cash:.2f}) sufficient for estimated cost (${estimated_cost:.2f}).")
            return True, cash
        else:
            print(f"[MOOMOO WARNING] Failed to query account balance: {data}. Proceeding with order attempt.")
            return True, 3000.0

    def get_5m_klines(self, symbol, limit=100):
        if self.is_simulation:
            now = datetime.now()
            base_p = 720.0 if symbol == "QQQ" else 735.0
            dt_list = [datetime.combine(now.date(), datetime.strptime("09:30", "%H:%M").time()) + pd.Timedelta(minutes=5*i) for i in range(20)]
            m_data = []
            for i, dt in enumerate(dt_list):
                op = base_p + i*0.2
                hi = op + 1.5 if i == 7 else op + 0.5
                lo = op - 0.5
                cl = hi - 0.1 if i == 7 else op + 0.2
                m_data.append({'time_key': dt.strftime("%Y-%m-%d %H:%M:%S"), 'open': op, 'high': hi, 'low': lo, 'close': cl, 'volume': 50000 + i*1000})
            df = pd.DataFrame(m_data)
            df['Typical_Price'] = (df['high'] + df['low'] + df['close']) / 3.0
            df['Cum_Vol'] = df['volume'].cumsum()
            df['Cum_PV'] = (df['Typical_Price'] * df['volume']).cumsum()
            df['VWAP'] = df['Cum_PV'] / df['Cum_Vol']
            return df

        futu_symbol = f"US.{symbol}" if not symbol.startswith("US.") else symbol
        if futu_symbol not in self.subscribed_klines:
            ret_sub, err_sub = self.quote_ctx.subscribe([futu_symbol], [SubType.K_5M], subscribe_push=False)
            if ret_sub == RET_OK:
                self.subscribed_klines.add(futu_symbol)
            else:
                print(f"[MOOMOO WARNING] Subscription failed for {futu_symbol}: {err_sub}")

        # MASTER API VALIDATION FIX: EXACT 2 RETURN VALUES (ret, data)
        ret, data = self.quote_ctx.get_cur_kline(futu_symbol, num=limit, ktype=KLType.K_5M)
        if ret == RET_OK:
            df = data.copy()
            df['Typical_Price'] = (df['high'] + df['low'] + df['close']) / 3.0
            df['Cum_Vol'] = df['volume'].cumsum()
            df['Cum_PV'] = (df['Typical_Price'] * df['volume']).cumsum()
            df['VWAP'] = df['Cum_PV'] / df['Cum_Vol']
            return df
        else:
            print(f"[MOOMOO ERROR] Failed to fetch K-lines for {futu_symbol}: {data}")
            return pd.DataFrame()

    def get_2_itm_option_contract(self, symbol, underlying_price, option_type="CALL"):
        strike_target = round(underlying_price) + (STRIKE_OFFSET if option_type == "CALL" else -STRIKE_OFFSET)
        
        if self.is_simulation:
            exp_date = datetime.now().strftime("%y%m%d")
            opt_symbol = f"US.{symbol}{exp_date}{option_type[0]}{int(strike_target*1000):08d}"
            raw_bid = 3.45 if symbol == "QQQ" else 3.15
            raw_ask = 3.50 if symbol == "QQQ" else 3.20
            spread = raw_ask - raw_bid
            exec_price = round(raw_ask + 0.01, 2)
            return opt_symbol, strike_target, exec_price

        futu_symbol = f"US.{symbol}" if not symbol.startswith("US.") else symbol
        opt_type_futu = OptionType.CALL if option_type == "CALL" else OptionType.PUT

        ret_exp, exp_data = self.quote_ctx.get_option_expiration_date(code=futu_symbol)
        if ret_exp != RET_OK or exp_data.empty:
            exp_date = datetime.now().strftime("%y%m%d")
            return f"US.{symbol}{exp_date}{option_type[0]}{int(strike_target*1000):08d}", strike_target, 3.51

        zero_dte_date = exp_data.iloc[0]['strike_time']

        ret_chain, chain_data = self.quote_ctx.get_option_chain(
            code=futu_symbol, start=zero_dte_date, end=zero_dte_date, option_type=opt_type_futu
        )
        if ret_chain != RET_OK or chain_data.empty:
            exp_date = datetime.now().strftime("%y%m%d")
            return f"US.{symbol}{exp_date}{option_type[0]}{int(strike_target*1000):08d}", strike_target, 3.51

        df_chain = chain_data.copy()
        df_chain['strike_diff'] = abs(df_chain['strike_price'] - strike_target)
        df_chain = df_chain.sort_values('strike_diff')
        best_contract = df_chain.iloc[0]
        opt_symbol = best_contract['code']
        actual_strike = best_contract['strike_price']

        self.quote_ctx.subscribe([opt_symbol], [SubType.QUOTE], subscribe_push=False)
        ret_snap, snap_data = self.quote_ctx.get_market_snapshot([opt_symbol])
        
        if ret_snap == RET_OK and not snap_data.empty:
            raw_bid = snap_data['bid_price'][0]
            raw_ask = snap_data['ask_price'][0]
            if raw_ask == 0 or np.isnan(raw_ask):
                raw_ask = snap_data['last_price'][0]
                raw_bid = raw_ask - 0.05
                
            spread = raw_ask - raw_bid
            if spread > MAX_BID_ASK_SPREAD:
                print(f"[SPREAD WARNING] Bid ${raw_bid:.2f} / Ask ${raw_ask:.2f} (Spread ${spread:.2f}). Exceeds MAX_SPREAD (${MAX_BID_ASK_SPREAD:.2f}).")
                return opt_symbol, actual_strike, 999.99
                
            exec_price = round(raw_ask + 0.01, 2)
            return opt_symbol, actual_strike, exec_price
        else:
            return opt_symbol, actual_strike, 3.51

    def place_bracket_order(self, option_symbol, action, quantity, limit_price, tp_price=None, sl_price=None):
        order_side = TrdSide.BUY if action == "BUY" else TrdSide.SELL
        
        if action == "BUY":
            sl_limit_price = round(sl_price - 0.05, 2)
            print(f"[MOOMOO ORDER] Placing LIMIT {action} for {quantity}x {option_symbol} @ ${limit_price:.2f}")
            print(f"             Attached Bracket -> Take Profit Limit: ${tp_price:.2f} | Stop Trigger: ${sl_price:.2f} (Stop-Limit @ ${sl_limit_price:.2f})")
        else:
            print(f"[MOOMOO ORDER] Placing EXIT {action} for {quantity}x {option_symbol} @ ${limit_price:.2f} to close position.")

        if self.is_simulation:
            return True, f"SIM_ORDER_{int(time.time())}"
            
        order_params = {
            'price': limit_price, 'qty': quantity, 'code': option_symbol, 'trd_side': order_side,
            'order_type': OrderType.NORMAL,
            'trd_env': TrdEnv.SIMULATE if self.use_real_paper else TrdEnv.REAL,
            'acc_id': self.acc_id,
            'acc_index': self.acc_index
        }
        
        if action == "BUY" and sl_price:
            order_params['aux_price'] = sl_price
            
        ret, data = self.trade_ctx.place_order(**order_params)
        
        if ret == RET_OK:
            order_id = data['order_id'][0]
            print(f"[MOOMOO OPTIONS] Order successfully placed: ID {order_id}")
            return True, order_id
        else:
            print(f"[MOOMOO OPTIONS ERROR] Order placement failed for {option_symbol}: {data}")
            return False, str(data)

    def check_order_filled(self, order_id):
        if self.is_simulation:
            return True, "FILLED"
            
        ret, data = self.trade_ctx.order_list_query(
            order_id=order_id, trd_env=TrdEnv.SIMULATE if self.use_real_paper else TrdEnv.REAL,
            acc_id=self.acc_id, acc_index=self.acc_index
        )
        if ret == RET_OK and not data.empty:
            status = data['order_status'][0]
            if status in [OrderStatus.FILLED]:
                return True, "FILLED"
            elif status in [OrderStatus.SUBMITTED, OrderStatus.WAITING_TO_MATCH]:
                return False, "SUBMITTED"
            elif status in [OrderStatus.CANCELLED, OrderStatus.FAILED]:
                return False, "CANCELLED"
            return False, str(status)
        else:
            print(f"[MOOMOO WARNING] Order status query failed for ID {order_id}: {data}")
            return False, "UNKNOWN"

    def cancel_order(self, order_id):
        print(f"[MOOMOO ORDER] Canceling unfilled limit order ID {order_id}.")
        if self.is_simulation:
            return True, "SIM_CANCEL_OK"
            
        ret, data = self.trade_ctx.modify_order(
            modify_order_op=ModifyOrderOp.CANCEL, order_id=order_id,
            trd_env=TrdEnv.SIMULATE if self.use_real_paper else TrdEnv.REAL,
            acc_id=self.acc_id, acc_index=self.acc_index
        )
        if ret == RET_OK:
            print(f"[MOOMOO] Order ID {order_id} successfully cancelled.")
            return True, data
        else:
            print(f"[MOOMOO ERROR] Failed to cancel order ID {order_id}: {data}")
            return False, str(data)

