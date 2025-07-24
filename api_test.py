#!/usr/bin/env python3
"""
API Connection Test Script
Tests TradingView integration and Telegram bot connectivity
"""

import asyncio
import aiohttp
import os
from tradingview_integration import initialize_tradingview, get_market_data, get_available_pairs

async def test_tradingview_connection():
    """Test TradingView API connection and data retrieval"""
    print("🔧 Testing TradingView Integration...")
    
    # Test initialization
    tv_ready = await initialize_tradingview()
    print(f"✅ TradingView Auth: {'Success' if tv_ready else 'Using Fallback'}")
    
    # Test getting crypto pairs
    pairs = await get_available_pairs()
    print(f"✅ Available Pairs: {len(pairs)} cryptocurrencies")
    
    # Test data retrieval for major coins
    test_symbols = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT']
    
    for symbol in test_symbols:
        try:
            data = await get_market_data(symbol, '4h', 10)
            if data and len(data) > 0:
                latest = data[-1]
                price = latest[4]  # Close price
                volume = latest[5]
                print(f"✅ {symbol}: Price=${price:,.2f}, Volume={volume:,.0f}")
            else:
                print(f"❌ {symbol}: No data received")
        except Exception as e:
            print(f"❌ {symbol}: Error - {e}")
    
    return tv_ready

async def test_telegram_connection():
    """Test Telegram bot connection"""
    print("\n📱 Testing Telegram Bot Connection...")
    
    token = os.getenv('TELEGRAM_TOKEN')
    if not token:
        print("❌ Telegram token not found")
        return False
    
    url = f"https://api.telegram.org/bot{token}/getMe"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    bot_info = await response.json()
                    if bot_info.get('ok'):
                        result = bot_info.get('result', {})
                        username = result.get('username', 'Unknown')
                        print(f"✅ Bot Connected: @{username}")
                        print(f"✅ Bot ID: {result.get('id')}")
                        print(f"✅ Bot Name: {result.get('first_name')}")
                        return True
                    else:
                        print(f"❌ Bot API Error: {bot_info}")
                        return False
                else:
                    print(f"❌ HTTP Error: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return False

async def test_market_analysis():
    """Test market data analysis capabilities"""
    print("\n📊 Testing Market Data Analysis...")
    
    try:
        # Get sample data for analysis
        data = await get_market_data('BTCUSDT', '4h', 100)
        
        if not data or len(data) < 20:
            print("❌ Insufficient data for analysis")
            return False
        
        # Convert to basic analysis format
        prices = [float(candle[4]) for candle in data]  # Close prices
        volumes = [float(candle[5]) for candle in data]  # Volumes
        
        # Basic statistics
        current_price = prices[-1]
        avg_price = sum(prices) / len(prices)
        avg_volume = sum(volumes) / len(volumes)
        current_volume = volumes[-1]
        
        print(f"✅ Data Points: {len(data)} candles")
        print(f"✅ Current Price: ${current_price:,.2f}")
        print(f"✅ Average Price: ${avg_price:,.2f}")
        print(f"✅ Current Volume: {current_volume:,.0f}")
        print(f"✅ Average Volume: {avg_volume:,.0f}")
        
        # Test EMA calculation capability
        try:
            import pandas as pd
            df = pd.DataFrame({'close': prices})
            ema20 = df['close'].ewm(span=20).mean().iloc[-1]
            print(f"✅ EMA20: ${ema20:,.2f}")
            
            # Check if price is above EMA20
            above_ema = current_price > ema20
            print(f"✅ Price vs EMA20: {'Above' if above_ema else 'Below'} (${abs(current_price - ema20):,.2f})")
            
        except Exception as e:
            print(f"⚠️ EMA Calculation: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Analysis Error: {e}")
        return False

async def main():
    """Run all API tests"""
    print("🧪 CRYPTO BOT API CONNECTION TEST")
    print("=" * 50)
    
    # Test all components
    tv_status = await test_tradingview_connection()
    tg_status = await test_telegram_connection()
    analysis_status = await test_market_analysis()
    
    print("\n" + "=" * 50)
    print("📋 FINAL TEST RESULTS:")
    print(f"📊 TradingView: {'✅ Connected' if tv_status else '⚠️ Fallback Mode'}")
    print(f"📱 Telegram: {'✅ Connected' if tg_status else '❌ Failed'}")
    print(f"📈 Analysis: {'✅ Working' if analysis_status else '❌ Failed'}")
    
    overall_status = tg_status and analysis_status
    print(f"\n🎯 Overall Status: {'✅ ALL SYSTEMS OPERATIONAL' if overall_status else '⚠️ SOME ISSUES DETECTED'}")
    
    return overall_status

if __name__ == "__main__":
    asyncio.run(main())