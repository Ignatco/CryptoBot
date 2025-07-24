import pandas as pd
import aiohttp
from typing import List, Dict, Any
from config import BINANCE_KLINES_ENDPOINT, BINANCE_EXCHANGE_INFO_ENDPOINT, EMA_PERIOD, KLINES_LIMIT


class CryptoAnalyzer:
    """Handles cryptocurrency market analysis and signal detection"""
    
    def __init__(self):
        self.session = None
    
    async def get_all_usdt_pairs(self, session: aiohttp.ClientSession) -> List[str]:
        """Fetch all active USDT trading pairs from Binance"""
        try:
            async with session.get(BINANCE_EXCHANGE_INFO_ENDPOINT) as response:
                if response.status != 200:
                    print(f"Error fetching exchange info: {response.status}")
                    return []
                
                data = await response.json()
                symbols = [
                    symbol['symbol'] for symbol in data['symbols']
                    if (symbol['quoteAsset'] == 'USDT' and 
                        symbol['status'] == 'TRADING' and
                        symbol['permissions'] and 'SPOT' in symbol['permissions'])
                ]
                return symbols
        except Exception as e:
            print(f"Error getting USDT pairs: {e}")
            return []
    
    async def fetch_klines(self, session: aiohttp.ClientSession, symbol: str, 
                          interval: str, limit: int = KLINES_LIMIT) -> List[List]:
        """Fetch candlestick data for a given symbol and timeframe"""
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        try:
            async with session.get(BINANCE_KLINES_ENDPOINT, params=params) as response:
                if response.status != 200:
                    print(f"Error fetching klines for {symbol}: {response.status}")
                    return []
                
                data = await response.json()
                return data
        except Exception as e:
            print(f"Error fetching klines for {symbol}: {e}")
            return []
    
    def calculate_ema(self, prices: pd.Series, period: int = EMA_PERIOD) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return prices.ewm(span=period, adjust=False).mean()
    
    def prepare_dataframe(self, klines: List[List]) -> pd.DataFrame:
        """Convert klines data to pandas DataFrame with proper types"""
        if not klines:
            return pd.DataFrame()
        
        df = pd.DataFrame(klines, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'trades',
            'taker_base_vol', 'taker_quote_vol', 'ignore'
        ])
        
        # Convert to proper data types
        numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'quote_asset_volume']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Calculate EMA20
        df['ema20'] = self.calculate_ema(df['close'], EMA_PERIOD)
        
        return df
    
    def check_ema_breakout(self, df: pd.DataFrame) -> bool:
        """Check if price broke above EMA20"""
        if len(df) < 2:
            return False
        
        current_candle = df.iloc[-1]
        previous_candle = df.iloc[-2]
        
        # Current close is above EMA20 and previous close was below or at EMA20
        breakout_condition = (
            current_candle['close'] > current_candle['ema20'] and
            previous_candle['close'] <= previous_candle['ema20']
        )
        
        return breakout_condition
    
    def check_high_volume(self, df: pd.DataFrame) -> bool:
        """Check if current volume is significantly higher than average"""
        if len(df) < 20:
            return False
        
        # Calculate average volume excluding the last candle
        avg_volume = df['volume'].iloc[:-1].mean()
        current_volume = df['volume'].iloc[-1]
        
        # Current volume should be at least 1.5x the average
        return current_volume > (avg_volume * 1.5)
    
    async def analyze_symbol(self, session: aiohttp.ClientSession, symbol: str) -> bool:
        """Analyze a symbol for EMA20 breakout with volume confirmation"""
        try:
            # Fetch data for both timeframes
            klines_4h = await self.fetch_klines(session, symbol, '4h')
            klines_1d = await self.fetch_klines(session, symbol, '1d')
            
            if not klines_4h or not klines_1d:
                return False
            
            # Prepare dataframes
            df_4h = self.prepare_dataframe(klines_4h)
            df_1d = self.prepare_dataframe(klines_1d)
            
            if df_4h.empty or df_1d.empty:
                return False
            
            # Check conditions for both timeframes
            breakout_4h = self.check_ema_breakout(df_4h) and self.check_high_volume(df_4h)
            breakout_1d = self.check_ema_breakout(df_1d) and self.check_high_volume(df_1d)
            
            # Both timeframes must show breakout with high volume
            return breakout_4h and breakout_1d
            
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            return False
    
    def get_signal_message(self, symbol: str, df_4h: pd.DataFrame = None, df_1d: pd.DataFrame = None) -> str:
        """Generate formatted signal message"""
        message = f"🚀 **BREAKOUT SIGNAL** 🚀\n\n"
        message += f"📈 Symbol: {symbol}\n"
        message += f"🎯 EMA20 breakout detected on both 4H and 1D timeframes\n"
        message += f"📊 High volume confirmation\n"
        message += f"⏰ Signal Time: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
        message += f"⚠️ This is not financial advice. Always DYOR!"
        
        return message
