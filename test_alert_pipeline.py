import os
import sys
from main import GoldenSniperBot

print("=== STARTING INSTANT PIPELINE & TELEGRAM VERIFICATION TEST ===")
print("Overriding FORCE_SIMULATION_TEST=True to verify alerts and order execution mechanics instantly...\n")

# Override config dynamically for instant test
import config
config.FORCE_SIMULATION_TEST = True

bot = GoldenSniperBot()
bot.start()
