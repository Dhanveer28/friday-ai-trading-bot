# ==========================================
# STEP 3: MARKET DATA FETCHER
# ==========================================

import requests
import json
from datetime import datetime, timedelta
import time
import config
from database import DatabaseManager

class MarketDataFetcher:
    """Fetch real-time market data for stocks and crypto"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.alpha_key = config.ALPHA_VANTAGE_API_KEY
        self.crypto_api = config.CRYPTO_API
        self.market_data_cache = {}
        self.last_update = {}
    
    # ==================== CRYPTO FUNCTIONS ====================
    
    def get_crypto_price(self, crypto_id):
        """Fetch real-time crypto price from CoinGecko (FREE - no API key needed)"""
        try:
            url = f"{self.crypto_api}/simple/price"
            params = {
                'ids': crypto_id.lower(),
                'vs_currencies': 'usd',
                'include_market_cap': 'true',
                'include_24hr_vol': 'true',
                'include_24hr_change': 'true'
            }
            
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if crypto_id.lower() in data:
                crypto_data = data[crypto_id.lower()]
                
                price_info = {
                    'asset': crypto_id,
                    'asset_type': 'CRYPTO',
                    'price': crypto_data.get('usd', 0),
                    'market_cap': crypto_data.get('usd_market_cap', 0),
                    'volume_24h': crypto_data.get('usd_24h_vol', 0),
                    'change_24h': crypto_data.get('usd_24h_change', 0),
                    'timestamp': datetime.now().isoformat()
                }
                
                # Cache it
                self.market_data_cache[crypto_id] = price_info
                
                # Save to database
                self.db.save_market_data(
                    crypto_id,
                    'CRYPTO',
                    price_info['price'],
                    price_info['volume_24h'],
                    price_info['change_24h']
                )
                
                return price_info
            else:
                print(f"❌ Crypto {crypto_id} not found")
                return None
        
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching {crypto_id}: {e}")
            return None
    
    def get_all_crypto_prices(self):
        """Fetch prices for all configured cryptos"""
        print("📊 Fetching crypto prices...")
        crypto_prices = {}
        
        for crypto in config.CRYPTO:
            price = self.get_crypto_price(crypto)
            if price:
                crypto_prices[crypto] = price
            time.sleep(0.5)  # Rate limiting
        
        return crypto_prices
    
    # ==================== STOCK FUNCTIONS ====================
    
    def get_stock_price(self, symbol):
        """Fetch stock price (using Alpha Vantage FREE tier)"""
        try:
            # Alpha Vantage endpoint
            url = "https://www.alphavantage.co/query"
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': symbol,
                'apikey': self.alpha_key
            }
            
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if 'Global Quote' in data and data['Global Quote']:
                quote = data['Global Quote']
                
                stock_data = {
                    'asset': symbol,
                    'asset_type': 'STOCK',
                    'price': float(quote.get('05. price', 0)),
                    'open': float(quote.get('02. open', 0)),
                    'high': float(quote.get('03. high', 0)),
                    'low': float(quote.get('04. low', 0)),
                    'volume': float(quote.get('06. volume', 0)),
                    'timestamp': datetime.now().isoformat()
                }
                
                # Calculate 24h change
                if stock_data['open'] > 0:
                    stock_data['change_24h'] = ((stock_data['price'] - stock_data['open']) / stock_data['open']) * 100
                else:
                    stock_data['change_24h'] = 0
                
                # Cache it
                self.market_data_cache[symbol] = stock_data
                
                # Save to database
                self.db.save_market_data(
                    symbol,
                    'STOCK',
                    stock_data['price'],
                    stock_data['volume'],
                    stock_data['change_24h']
                )
                
                return stock_data
            else:
                print(f"❌ Stock {symbol} not found or API limit reached (free tier limit: 5 calls/min)")
                # Return cached data if available
                return self.market_data_cache.get(symbol)
        
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching {symbol}: {e}")
            return self.market_data_cache.get(symbol)
    
    def get_all_stock_prices(self):
        """Fetch prices for all configured stocks"""
        print("📈 Fetching stock prices...")
        stock_prices = {}
        
        for stock in config.STOCKS:
            price = self.get_stock_price(stock)
            if price:
                stock_prices[stock] = price
            time.sleep(1.2)  # Respect Alpha Vantage rate limit (5 calls/min = 1 call every 12 seconds)
        
        return stock_prices
    
    # ==================== COMBINED FUNCTIONS ====================
    
    def get_all_market_data(self):
        """Fetch all stocks and crypto data"""
        print("\n" + "="*60)
        print("🔄 FETCHING ALL MARKET DATA")
        print("="*60)
        
        all_data = {}
        
        # Get crypto prices
        crypto_data = self.get_all_crypto_prices()
        all_data['crypto'] = crypto_data
        
        # Get stock prices
        stock_data = self.get_all_stock_prices()
        all_data['stocks'] = stock_data
        
        print("\n✅ Market data updated successfully")
        return all_data
    
    def get_price_history(self, asset, asset_type, limit=10):
        """Get historical price data for an asset"""
        import sqlite3
        
        conn = sqlite3.connect(config.DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT price, change_24h, timestamp FROM market_data
            WHERE asset = ? AND asset_type = ?
            ORDER BY timestamp DESC LIMIT ?
        ''', (asset, asset_type, limit))
        
        history = cursor.fetchall()
        conn.close()
        
        return history
    
    def is_market_open(self):
        """Check if US stock market is open (basic check)"""
        now = datetime.now()
        
        # Market hours: 9:30 AM - 4:00 PM EST, Monday-Friday
        # This is simplified - doesn't account for holidays
        if now.weekday() >= 5:  # Weekend
            return False
        
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        
        return market_open <= now <= market_close
    
    def format_price_display(self, asset_type, data):
        """Format price data for display"""
        if asset_type == 'CRYPTO':
            return f"""
            💰 {data['asset'].upper()}
            Price: ${data['price']:,.2f}
            24h Change: {data['change_24h']:+.2f}%
            Market Cap: ${data['market_cap']:,.0f}
            Volume 24h: ${data['volume_24h']:,.0f}
            """
        else:  # STOCK
            return f"""
            📈 {data['asset']}
            Price: ${data['price']:,.2f}
            Day Change: {data['change_24h']:+.2f}%
            Day High: ${data['high']:,.2f}
            Day Low: ${data['low']:,.2f}
            Volume: {data['volume']:,.0f}
            """


# Test the data fetcher
if __name__ == "__main__":
    print("🚀 Testing Market Data Fetcher...")
    
    fetcher = MarketDataFetcher()
    
    # Test crypto
    print("\n📊 Testing Crypto Fetcher:")
    btc = fetcher.get_crypto_price('bitcoin')
    if btc:
        print(f"Bitcoin: ${btc['price']:,.2f} ({btc['change_24h']:+.2f}%)")
    
    # Test stock (if API key is valid)
    print("\n📈 Testing Stock Fetcher:")
    aapl = fetcher.get_stock_price('AAPL')
    if aapl:
        print(f"AAPL: ${aapl['price']:,.2f} ({aapl['change_24h']:+.2f}%)")
    else:
        print("⚠️ Stock API not available (use 'demo' key for testing)")
    
    print("\n✅ Market data fetcher ready!")
