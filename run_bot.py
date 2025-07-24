#!/usr/bin/env python3
"""
Simple script to run the crypto bot with environment variable loading
"""

import os
import sys
from pathlib import Path

def load_env_file():
    """Load environment variables from .env file if it exists"""
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        print("✅ Loaded environment variables from .env file")
    else:
        print("⚠️ No .env file found. Please create one with your bot credentials.")
        return False
    return True

def check_requirements():
    """Check if required environment variables are set"""
    required_vars = ['TELEGRAM_TOKEN', 'CHAT_ID']
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("\nPlease add them to your .env file:")
        print("TELEGRAM_TOKEN=your_bot_token_here")
        print("CHAT_ID=your_chat_id_here")
        print("TRADINGVIEW_USERNAME=your_username (optional)")
        print("TRADINGVIEW_PASSWORD=your_password (optional)")
        return False
    
    print("✅ All required environment variables are set")
    return True

def main():
    print("🚀 Starting Crypto EMA20 Breakout Bot...")
    
    # Load environment variables
    if not load_env_file():
        return
    
    # Check requirements
    if not check_requirements():
        return
    
    # Import and run the bot
    try:
        print("📦 Importing bot modules...")
        from simple_bot import main as bot_main
        import asyncio
        
        print("🤖 Starting bot monitoring...")
        asyncio.run(bot_main())
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please install required packages: pip install aiohttp pandas python-telegram-bot requests matplotlib numpy pillow")
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()