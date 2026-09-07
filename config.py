# ==========================================
# FRIDAY AI TRADING BOT - CONFIGURATION
# ==========================================

import os
from datetime import datetime

# API KEYS (Get free at: https://www.alphavantage.co/ and https://www.coingecko.com/)
ALPHA_VANTAGE_API_KEY = "demo"  # Replace with your free key
CRYPTO_API = "https://api.coingecko.com/api/v3"

# PAPER TRADING CONFIG
PAPER_TRADING_ENABLED = True
INITIAL_PORTFOLIO = 10000  # Starting with $10,000 for testing
MAX_TRADE_RISK_PERCENT = 5  # Risk only 5% per trade

# STOCKS TO MONITOR
STOCKS = ["AAPL", "GOOGL", "MSFT", "TESLA"]  # Add more as needed

# CRYPTO TO MONITOR
CRYPTO = ["bitcoin", "ethereum", "ripple", "cardano"]

# TRADING RULES
PROFIT_TARGET = 2  # Sell when 2% profit
STOP_LOSS = -1  # Stop if -1% loss
MIN_DATA_POINTS = 5  # Need 5 data points before trading

# NOTIFICATION SETTINGS
NOTIFICATIONS_ENABLED = True
ALERT_EMAIL = "your-email@gmail.com"  # Optional
ALERT_PHONE = "+1234567890"  # Optional for SMS

# DATABASE
DB_NAME = "trading_bot.db"
LOG_FILE = "trading_logs.txt"
DATA_FOLDER = "market_data"

# AI SETTINGS
LEARNING_RATE = 0.1
PREDICTION_THRESHOLD = 0.6
MODEL_UPDATE_INTERVAL = 3600  # Update model every hour

# ENCRYPTION KEY (Generate one: python -c "import secrets; print(secrets.token_hex(32))")
ENCRYPTION_KEY = "your-secret-key-here-change-this"

# TIMESTAMPS
BOT_START_TIME = datetime.now()
print("✅ Configuration loaded successfully")
