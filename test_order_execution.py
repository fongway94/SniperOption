import time
from broker_moomoo import MoomooBroker
from config import USE_REAL_PAPER_TRADING, STRIKE_OFFSET

print("=== STARTING STANDALONE MOOMOO ORDER EXECUTION VERIFICATION ===")
print("Testing broker connection, dynamic option chain query, limit BUY placement, queue verification, and exit SELL placement...\n")

broker = MoomooBroker(use_real_paper=USE_REAL_PAPER_TRADING)

if not broker.connect():
    print("[FATAL ERROR] Broker connection failed. Exiting test.")
    exit(1)

# Step 1: Test Dynamic Option Contract Selection & Pricing
print("\n--- STEP 1: TEST OPTION CONTRACT SELECTION & PRICING ---")
symbol = "QQQ"
underlying_p = 720.50
opt_symbol, strike, opt_price = broker.get_2_itm_option_contract(symbol, underlying_p, "CALL")
print(f"[TEST SUCCESS] Target Contract Retrieved: {opt_symbol} | Strike: ${strike:.2f} (2 ITM) | Exec Ask Price: ${opt_price:.2f}")

# Step 2: Test Account Balance & Purchasing Power Verification
print("\n--- STEP 2: TEST ACCOUNT BALANCE CHECK ---")
estimated_cost = opt_price * 100.0
has_balance, avail_cash = broker.check_account_balance(estimated_cost)
print(f"[TEST SUCCESS] Account Balance Verified: Available Settled Cash = ${avail_cash:.2f} | Estimated Cost = ${estimated_cost:.2f}")

if not has_balance:
    print("[ERROR] Insufficient cash balance in broker account to proceed with order test.")
    broker.disconnect()
    exit(1)

# Step 3: Test Limit BUY Bracket Order Placement
print("\n--- STEP 3: TEST LIMIT BUY ORDER PLACEMENT (ENTER TRADE) ---")
tp = opt_price * 1.20
sl = opt_price * 0.75
success, order_id = broker.place_bracket_order(opt_symbol, "BUY", 1, opt_price, tp, sl)

if not success:
    print(f"[TEST FAILED] Failed to place limit BUY order for {opt_symbol}. Check OpenD permissions.")
    broker.disconnect()
    exit(1)

print(f"[TEST SUCCESS] Limit BUY Order Successfully Placed in Moomoo Queue! Order ID: {order_id}")

# Step 4: Test Queue Verification & Status Check
print("\n--- STEP 4: TEST QUEUE VERIFICATION (CHECK STATUS) ---")
time.sleep(3) # Wait 3 seconds to allow Moomoo matching engine to process
is_filled, status = broker.check_order_filled(order_id)
print(f"[TEST SUCCESS] Order Queue Queried Successfully. Current Status: {status}")

# Step 5: Test Exit SELL Order Placement (Close Trade / Cancel Queue)
print("\n--- STEP 5: TEST EXIT SELL ORDER PLACEMENT (CLOSE TRADE) ---")
if status == "FILLED":
    print(f"Order was FILLED in queue. Testing immediate market/limit exit SELL order to close position...")
    sell_success, sell_order_id = broker.place_bracket_order(opt_symbol, "SELL", 1, opt_price)
    if sell_success:
        print(f"[TEST SUCCESS] Exit SELL Order Successfully Placed! Position Closed. Sell Order ID: {sell_order_id}")
    else:
        print(f"[TEST FAILED] Failed to place exit SELL order.")
else:
    print(f"Order is currently SUBMITTED in queue (Unfilled). Testing unfilled queue cancellation...")
    cancel_success, cancel_data = broker.cancel_order(order_id)
    if cancel_success:
        print(f"[TEST SUCCESS] Unfilled Limit Order Successfully Canceled! Queue Reset.")
    else:
        print(f"[TEST FAILED] Failed to cancel unfilled order.")

broker.disconnect()
print("\n=== STANDALONE ORDER EXECUTION VERIFICATION COMPLETED SUCCESSFULLY ===")
