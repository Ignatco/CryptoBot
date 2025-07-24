#!/usr/bin/env python3
"""
Crypto EMA20 Breakout Bot

A Telegram bot that monitors cryptocurrency markets and sends trading signals
based on EMA20 breakouts with volume confirmation on multiple timeframes.

Author: Crypto Trading Bot
Version: 1.0.0
"""

import asyncio
import sys
import signal
from simple_bot import SimpleCryptoBot
from config import TELEGRAM_TOKEN, CHAT_ID


class BotManager:
    """Manages the bot lifecycle and graceful shutdown"""
    
    def __init__(self):
        self.bot = None
        self.running = False
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            print(f"\n🛑 Received signal {signum}. Shutting down gracefully...")
            self.running = False
            if self.bot:
                self.bot.stop_monitoring()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start_bot(self):
        """Initialize and start the bot"""
        try:
            # Validate configuration
            if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == 'your_bot_token_here':
                raise ValueError("Please set a valid TELEGRAM_TOKEN in environment variables")
            
            if not CHAT_ID:
                raise ValueError("Please set CHAT_ID in environment variables")
            
            # Initialize bot
            self.bot = SimpleCryptoBot(TELEGRAM_TOKEN, CHAT_ID)
            self.running = True
            
            print("=" * 60)
            print("🚀 CRYPTO EMA20 BREAKOUT BOT")
            print("=" * 60)
            print(f"📱 Chat ID: {CHAT_ID}")
            print(f"🔑 Token: {TELEGRAM_TOKEN[:10]}...")
            print("=" * 60)
            
            # Start the bot
            await self.bot.run()
            
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user")
        except Exception as e:
            print(f"❌ Fatal error: {e}")
            sys.exit(1)
        finally:
            if self.bot:
                self.bot.stop_monitoring()
            print("👋 Bot shutdown complete")


def main():
    """Main entry point"""
    manager = BotManager()
    manager.setup_signal_handlers()
    
    try:
        # Run the bot
        asyncio.run(manager.start_bot())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
