# ==========================================
# STEP 2: DATABASE & ENCRYPTION MODULE
# ==========================================

import sqlite3
import json
import os
from datetime import datetime
from cryptography.fernet import Fernet
import config

class DatabaseManager:
    """Manage all database operations for trading bot"""
    
    def __init__(self):
        self.db_name = config.DB_NAME
        self.create_tables()
    
    def create_tables(self):
        """Create all necessary database tables"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Trades History Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_type TEXT NOT NULL,
                asset TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                quantity REAL NOT NULL,
                profit_loss REAL,
                profit_percent REAL,
                entry_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                exit_time TIMESTAMP,
                status TEXT DEFAULT 'OPEN'
            )
        ''')
        
        # Portfolio History Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cash REAL NOT NULL,
                holdings_value REAL NOT NULL,
                total_value REAL NOT NULL,
                daily_profit REAL
            )
        ''')
        
        # Market Data Cache Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                price REAL NOT NULL,
                volume REAL,
                change_24h REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # AI Decisions Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset TEXT NOT NULL,
                decision TEXT NOT NULL,
                confidence REAL NOT NULL,
                reasoning TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Notifications Log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                notification_type TEXT NOT NULL,
                message TEXT NOT NULL,
                sent BOOLEAN DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Database tables created successfully")
    
    def add_trade(self, trade_type, asset, asset_type, entry_price, quantity):
        """Record a trade"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO trades 
            (trade_type, asset, asset_type, entry_price, quantity, status)
            VALUES (?, ?, ?, ?, ?, 'OPEN')
        ''', (trade_type, asset, asset_type, entry_price, quantity))
        
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"✅ Trade recorded: {trade_type} {quantity} {asset} @ ${entry_price}")
        return trade_id
    
    def close_trade(self, trade_id, exit_price):
        """Close an open trade and calculate P&L"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('SELECT entry_price, quantity FROM trades WHERE id = ?', (trade_id,))
        trade = cursor.fetchone()
        
        if trade:
            entry_price, quantity = trade
            profit_loss = (exit_price - entry_price) * quantity
            profit_percent = ((exit_price - entry_price) / entry_price) * 100
            
            cursor.execute('''
                UPDATE trades 
                SET exit_price = ?, profit_loss = ?, profit_percent = ?, 
                    status = 'CLOSED', exit_time = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (exit_price, profit_loss, profit_percent, trade_id))
            
            conn.commit()
            conn.close()
            
            print(f"✅ Trade closed: P&L = ${profit_loss:.2f} ({profit_percent:.2f}%)")
            return profit_loss
        
        conn.close()
        return 0
    
    def save_portfolio_snapshot(self, cash, holdings_value):
        """Save portfolio state at each checkpoint"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        total_value = cash + holdings_value
        
        cursor.execute('''
            INSERT INTO portfolio_history 
            (cash, holdings_value, total_value)
            VALUES (?, ?, ?)
        ''', (cash, holdings_value, total_value))
        
        conn.commit()
        conn.close()
    
    def save_market_data(self, asset, asset_type, price, volume, change_24h):
        """Store market data for analysis"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO market_data 
            (asset, asset_type, price, volume, change_24h)
            VALUES (?, ?, ?, ?, ?)
        ''', (asset, asset_type, price, volume, change_24h))
        
        conn.commit()
        conn.close()
    
    def save_ai_decision(self, asset, decision, confidence, reasoning):
        """Log AI trading decisions"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO ai_decisions 
            (asset, decision, confidence, reasoning)
            VALUES (?, ?, ?, ?)
        ''', (asset, decision, confidence, reasoning))
        
        conn.commit()
        conn.close()
    
    def add_notification(self, notification_type, message):
        """Queue notification to send"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO notifications 
            (notification_type, message)
            VALUES (?, ?)
        ''', (notification_type, message))
        
        conn.commit()
        conn.close()
    
    def get_portfolio_stats(self):
        """Get current portfolio statistics"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM portfolio_history ORDER BY timestamp DESC LIMIT 1
        ''')
        
        latest = cursor.fetchone()
        conn.close()
        
        if latest:
            return {
                'cash': latest[2],
                'holdings_value': latest[3],
                'total_value': latest[4],
                'timestamp': latest[5]
            }
        return None
    
    def get_all_trades(self):
        """Get all trades history"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM trades ORDER BY entry_time DESC')
        trades = cursor.fetchall()
        conn.close()
        
        return trades
    
    def export_data(self, filename="trading_data_export.json"):
        """Export all data for backup"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Get all trades
        cursor.execute('SELECT * FROM trades')
        trades = cursor.fetchall()
        
        # Get portfolio history
        cursor.execute('SELECT * FROM portfolio_history')
        portfolio = cursor.fetchall()
        
        conn.close()
        
        export_data = {
            'exported_at': datetime.now().isoformat(),
            'trades': trades,
            'portfolio_history': portfolio
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        print(f"✅ Data exported to {filename}")
        return filename


class EncryptionManager:
    """Handle end-to-end encryption for sensitive data"""
    
    def __init__(self, key=None):
        if key is None:
            key = config.ENCRYPTION_KEY.encode()
        
        # Generate key if needed
        if len(key) < 32:
            key = Fernet.generate_key()
            print(f"⚠️ Generated new encryption key: {key.decode()}")
        
        self.cipher = Fernet(key)
    
    def encrypt(self, data):
        """Encrypt sensitive data"""
        if isinstance(data, str):
            data = data.encode()
        
        encrypted = self.cipher.encrypt(data)
        return encrypted.decode()
    
    def decrypt(self, encrypted_data):
        """Decrypt sensitive data"""
        if isinstance(encrypted_data, str):
            encrypted_data = encrypted_data.encode()
        
        decrypted = self.cipher.decrypt(encrypted_data)
        return decrypted.decode()
    
    def encrypt_api_key(self, api_key):
        """Safely encrypt API keys"""
        return self.encrypt(api_key)
    
    def decrypt_api_key(self, encrypted_key):
        """Safely decrypt API keys"""
        return self.decrypt(encrypted_key)


# Initialize
if __name__ == "__main__":
    db = DatabaseManager()
    print("✅ Database manager ready")
    
    encryptor = EncryptionManager()
    test_data = "secret_api_key_12345"
    encrypted = encryptor.encrypt(test_data)
    decrypted = encryptor.decrypt(encrypted)
    print(f"🔐 Encryption test: {test_data} -> {encrypted[:20]}... -> {decrypted}")
