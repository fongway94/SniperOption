import pandas as pd
import numpy as np
from datetime import datetime, time
import pytz
from config import BOX_WINDOW_MINUTES, ENTRY_WINDOW_CUTOFF, PROFIT_TARGET_PCT, STOP_LOSS_PCT, STRIKE_OFFSET

def get_us_eastern_time():
    eastern = pytz.timezone("US/Eastern")
    return datetime.now(eastern)

def parse_time(t_str):
    return datetime.strptime(t_str, "%H:%M").time()

def check_candlestick_pattern(curr_row, prev_row, direction):
    op = curr_row['open']; hi = curr_row['high']; lo = curr_row['low']; cl = curr_row['close']
    p_op = prev_row['open']; p_cl = prev_row['close']
    body = abs(cl - op); rng = hi - lo
    if rng == 0: return False, "None"
    
    if direction == 'bullish':
        if p_cl < p_op and cl > op and cl >= p_op and op <= p_cl: return True, "Bullish Engulfing"
        lower_shadow = min(op, cl) - lo; upper_shadow = hi - max(op, cl)
        if lower_shadow >= 2 * body and upper_shadow <= 0.2 * rng and cl > op: return True, "Hammer Pin Bar"
        if cl > op and cl >= hi - 0.15 * rng and body >= 0.5 * rng: return True, "Marubozu Breakout"
    elif direction == 'bearish':
        if p_cl > p_op and cl < op and cl <= p_op and op >= p_cl: return True, "Bearish Engulfing"
        upper_shadow = hi - max(op, cl); lower_shadow = min(op, cl) - lo
        if upper_shadow >= 2 * body and lower_shadow <= 0.2 * rng and cl < op: return True, "Shooting Star Pin Bar"
        if cl < op and cl <= lo + 0.15 * rng and body >= 0.5 * rng: return True, "Bearish Marubozu"
    return False, "None"

def generate_signals(df, symbol):
    if df.empty or len(df) < 6:
        return {"status": "WAITING_FOR_BOX", "message": "Accumulating first 30 mins of candles..."}

    df['dt_parsed'] = pd.to_datetime(df['time_key'])
    df['time_only'] = df['dt_parsed'].dt.time
    
    box_end_time = parse_time("10:00")
    cutoff_time = parse_time(ENTRY_WINDOW_CUTOFF)
    
    setup_df = df[df['time_only'] < box_end_time]
    if setup_df.empty or len(setup_df) < 6:
        return {"status": "WAITING_FOR_BOX", "message": "Building 30-min Opening Range Box..."}
        
    box_high = setup_df['high'].max()
    box_low = setup_df['low'].min()
    
    exec_df = df[(df['time_only'] >= box_end_time) & (df['time_only'] <= cutoff_time)]
    if exec_df.empty:
        return {"status": "BOX_ACTIVE", "box_high": box_high, "box_low": box_low, "message": "Box active. Waiting for initial breakout..."}
        
    prev_row = setup_df.iloc[-1]
    trigger_detected = False; trig_action = None; trig_pat = "None"; trig_price = 0
    
    for idx, row in exec_df.iterrows():
        close = row['close']; vwap = row['VWAP']; t = row['time_only']; high = row['high']; low = row['low']; open_p = row['open']
        
        if not trigger_detected:
            if close > box_high and close > vwap:
                is_pat, pat = check_candlestick_pattern(row, prev_row, 'bullish')
                if is_pat: trigger_detected = True; trig_action = "CALL"; trig_pat = pat; trig_price = close
            elif close < box_low and close < vwap:
                is_pat, pat = check_candlestick_pattern(row, prev_row, 'bearish')
                if is_pat: trigger_detected = True; trig_action = "PUT"; trig_pat = pat; trig_price = close
        else:
            if trig_action == "CALL" and low <= box_high * 1.0005:
                # MASTER SAFETY FIX: MOMENTUM VELOCITY FILTER
                if (open_p - close) / open_p > 0.0025:
                    return {"status": "TRADE_REJECTED", "symbol": symbol, "action": "CALL", "message": "Pullback candle velocity too strong (>0.25% drop). V-shape reversal trap avoided."}
                return {
                    "status": "EXECUTE_RETEST", "action": "CALL", "symbol": symbol,
                    "box_high": box_high, "box_low": box_low, "pattern": trig_pat,
                    "execution_price": box_high, "vwap": vwap
                }
            elif trig_action == "PUT" and high >= box_low * 0.9995:
                # MASTER SAFETY FIX: MOMENTUM VELOCITY FILTER
                if (close - open_p) / open_p > 0.0025:
                    return {"status": "TRADE_REJECTED", "symbol": symbol, "action": "PUT", "message": "Pullback candle velocity too strong (>0.25% surge). V-shape reversal trap avoided."}
                return {
                    "status": "EXECUTE_RETEST", "action": "PUT", "symbol": symbol,
                    "box_high": box_high, "box_low": box_low, "pattern": trig_pat,
                    "execution_price": box_low, "vwap": vwap
                }
        prev_row = row

    if trigger_detected:
        return {
            "status": "WAITING_FOR_RETEST", "action": trig_action, "symbol": symbol,
            "box_high": box_high, "box_low": box_low, "pattern": trig_pat,
            "current_price": trig_price, "message": f"Breakout confirmed ({trig_pat}). Waiting for pullback to box line..."
        }
        
    return {"status": "NO_BREAKOUT", "box_high": box_high, "box_low": box_low, "message": "No confirmed candlestick breakout yet."}

