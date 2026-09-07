# ==========================================
# STEP 4: AI BRAIN - TRADING INTELLIGENCE
# ==========================================

import numpy as np
from datetime import datetime, timedelta
import config
from database import DatabaseManager
from market_data import MarketDataFetcher
import json

class AITradingBrain:
    """AI engine that learns, analyzes, and makes trading decisions"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.fetcher = MarketDataFetcher()
        self.learning_rate = config.LEARNING_RATE
        self.prediction_threshold = config.PREDICTION_THRESHOLD
        
        # AI Memory - learns from past trades
        self.trade_history = []
        self.performance_metrics = {
            'win_rate': 0.5,
            'avg_profit': 0,
            'confidence_level': 0.5
        }
        
        self.load_learning_data()
    
    def load_learning_data(self):
        """Load historical trades to learn from"""
        trades = self.db.get_all_trades()
        self.trade_history = trades
        
        if trades:
            # Calculate win rate
            closed_trades = [t for t in trades if t[10] == 'CLOSED']  # status
            if closed_trades:
                wins = sum(1 for t in closed_trades if t[8] and t[8] > 0)  # profit_loss > 0
                self.performance_metrics['win_rate'] = wins / len(closed_trades)
                
                # Calculate average profit
                profits = [t[8] for t in closed_trades if t[8]]
                self.performance_metrics['avg_profit'] = np.mean(profits) if profits else 0
                
                # Adjust confidence based on performance
                self.performance_metrics['confidence_level'] = min(0.9, 0.5 + (self.performance_metrics['win_rate'] * 0.4))
                
                print(f"📚 AI Learning: Win Rate={self.performance_metrics['win_rate']:.2%}, Confidence={self.performance_metrics['confidence_level']:.2%}")
    
    # ==================== TECHNICAL ANALYSIS ====================
    
    def calculate_sma(self, prices, period=20):
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        return np.mean(prices[-period:])
    
    def calculate_ema(self, prices, period=12):
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        
        ema = [prices[0]]
        multiplier = 2 / (period + 1)
        
        for price in prices[1:]:
            ema.append(price * multiplier + ema[-1] * (1 - multiplier))
        
        return ema[-1]
    
    def calculate_rsi(self, prices, period=14):
        """Calculate Relative Strength Index (momentum indicator)"""
        if len(prices) < period:
            return 50
        
        deltas = np.diff(prices[-period-1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100 if avg_gain > 0 else 50
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_macd(self, prices):
        """Calculate MACD (Moving Average Convergence Divergence)"""
        if len(prices) < 26:
            return 0, 0
        
        ema12 = self.calculate_ema(prices, 12)
        ema26 = self.calculate_ema(prices, 26)
        macd_line = ema12 - ema26
        
        return macd_line, ema12 - ema26  # Simplified
    
    def calculate_bollinger_bands(self, prices, period=20):
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            current = prices[-1] if prices else 0
            return current, current, current
        
        sma = self.calculate_sma(prices, period)
        std_dev = np.std(prices[-period:])
        
        upper_band = sma + (std_dev * 2)
        lower_band = sma - (std_dev * 2)
        
        return upper_band, sma, lower_band
    
    # ==================== SENTIMENT ANALYSIS ====================
    
    def analyze_price_sentiment(self, current_price, change_24h, volume_trend):
        """Determine market sentiment from price action"""
        sentiment_score = 0.5  # Neutral (0-1 scale, 0.5 = neutral)
        
        # Price momentum
        if change_24h > 5:
            sentiment_score += 0.2  # Strong bullish
        elif change_24h > 2:
            sentiment_score += 0.1  # Mildly bullish
        elif change_24h < -5:
            sentiment_score -= 0.2  # Strong bearish
        elif change_24h < -2:
            sentiment_score -= 0.1  # Mildly bearish
        
        # Volume trend
        if volume_trend > 1.2:
            sentiment_score += 0.1  # High volume bullish
        elif volume_trend < 0.8:
            sentiment_score -= 0.1  # Low volume bearish
        
        # Ensure score stays in range
        return max(0, min(1, sentiment_score))
    
    # ==================== DECISION ENGINE ====================
    
    def analyze_asset(self, asset, asset_type, current_data):
        """Comprehensive analysis of an asset"""
        try:
            # Get price history
            history = self.fetcher.get_price_history(asset, asset_type, limit=30)
            
            if not history or len(history) < 5:
                return None
            
            prices = [h[0] for h in history]
            prices.reverse()  # Oldest first
            
            # Calculate indicators
            sma_20 = self.calculate_sma(prices, 20)
            ema_12 = self.calculate_ema(prices, 12)
            rsi = self.calculate_rsi(prices)
            upper_band, middle_band, lower_band = self.calculate_bollinger_bands(prices)
            
            current_price = prices[-1]
            change_24h = current_data.get('change_24h', 0)
            
            # Build analysis report
            analysis = {
                'asset': asset,
                'asset_type': asset_type,
                'current_price': current_price,
                'sma_20': sma_20,
                'ema_12': ema_12,
                'rsi': rsi,
                'upper_band': upper_band,
                'lower_band': lower_band,
                'change_24h': change_24h,
                'indicators': {}
            }
            
            # Evaluate indicators
            analysis['indicators']['price_trend'] = "UP" if current_price > sma_20 else "DOWN"
            analysis['indicators']['momentum'] = "STRONG" if rsi > 70 or rsi < 30 else "NORMAL"
            analysis['indicators']['oversold'] = rsi < 30
            analysis['indicators']['overbought'] = rsi > 70
            
            return analysis
        
        except Exception as e:
            print(f"❌ Error analyzing {asset}: {e}")
            return None
    
    def generate_signal(self, analysis):
        """Generate BUY/SELL/HOLD signal from analysis"""
        if not analysis:
            return None
        
        signal_score = 0.5  # Neutral
        confidence = 0.5
        reasoning = []
        
        # Price position analysis
        current_price = analysis['current_price']
        sma_20 = analysis['sma_20']
        ema_12 = analysis['ema_12']
        rsi = analysis['rsi']
        change_24h = analysis['change_24h']
        
        # RSI signals
        if rsi < 30:
            signal_score += 0.3
            confidence += 0.2
            reasoning.append("RSI oversold - buying opportunity")
        elif rsi > 70:
            signal_score -= 0.3
            confidence += 0.2
            reasoning.append("RSI overbought - selling opportunity")
        
        # Moving average signals
        if current_price > sma_20 and current_price > ema_12:
            signal_score += 0.2
            reasoning.append("Price above moving averages - bullish")
        elif current_price < sma_20 and current_price < ema_12:
            signal_score -= 0.2
            reasoning.append("Price below moving averages - bearish")
        
        # Momentum signals
        if change_24h > 3:
            signal_score += 0.15
            reasoning.append("Strong positive momentum")
        elif change_24h < -3:
            signal_score -= 0.15
            reasoning.append("Strong negative momentum")
        
        # Apply AI learning
        signal_score += (self.performance_metrics['win_rate'] - 0.5) * 0.1
        confidence = self.performance_metrics['confidence_level']
        
        # Normalize score
        signal_score = max(0, min(1, signal_score))
        
        # Generate decision
        if signal_score > 0.65:
            decision = "BUY"
        elif signal_score < 0.35:
            decision = "SELL"
        else:
            decision = "HOLD"
        
        return {
            'decision': decision,
            'confidence': confidence,
            'signal_score': signal_score,
            'reasoning': " | ".join(reasoning),
            'timestamp': datetime.now().isoformat()
        }
    
    def make_trading_decision(self, market_data):
        """Make trading decision for all assets"""
        print("\n" + "="*60)
        print("🧠 AI DECISION ENGINE ACTIVATED")
        print("="*60)
        
        decisions = {}
        
        # Analyze stocks
        if 'stocks' in market_data:
            for stock, data in market_data['stocks'].items():
                analysis = self.analyze_asset(stock, 'STOCK', data)
                if analysis:
                    signal = self.generate_signal(analysis)
                    decisions[stock] = signal
                    
                    # Save to database
                    self.db.save_ai_decision(
                        stock,
                        signal['decision'],
                        signal['confidence'],
                        signal['reasoning']
                    )
                    
                    print(f"\n📈 {stock}")
                    print(f"   Decision: {signal['decision']} (Confidence: {signal['confidence']:.2%})")
                    print(f"   Reasoning: {signal['reasoning']}")
        
        # Analyze crypto
        if 'crypto' in market_data:
            for crypto, data in market_data['crypto'].items():
                analysis = self.analyze_asset(crypto, 'CRYPTO', data)
                if analysis:
                    signal = self.generate_signal(analysis)
                    decisions[crypto] = signal
                    
                    # Save to database
                    self.db.save_ai_decision(
                        crypto,
                        signal['decision'],
                        signal['confidence'],
                        signal['reasoning']
                    )
                    
                    print(f"\n💰 {crypto.upper()}")
                    print(f"   Decision: {signal['decision']} (Confidence: {signal['confidence']:.2%})")
                    print(f"   Reasoning: {signal['reasoning']}")
        
        print("\n" + "="*60)
        return decisions


# Test the AI brain
if __name__ == "__main__":
    print("🚀 Testing AI Trading Brain...")
    
    brain = AITradingBrain()
    
    # Simulate with sample data
    sample_data = {
        'crypto': {
            'bitcoin': {
                'price': 45000,
                'change_24h': 2.5,
                'market_cap': 900000000000
            }
        },
        'stocks': {}
    }
    
    decisions = brain.make_trading_decision(sample_data)
    print("\n✅ AI Brain ready!")
