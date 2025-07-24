import asyncio
import aiohttp
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from crypto_analyzer import CryptoAnalyzer
from config import TELEGRAM_TOKEN, CHAT_ID, MONITORING_INTERVAL


class CryptoTelegramBot:
    """Telegram bot for cryptocurrency signal monitoring"""
    
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.analyzer = CryptoAnalyzer()
        self.sent_signals = set()  # Cache for sent signals to prevent duplicates
        self.monitoring_active = False
        
        # Initialize Telegram application
        self.app = ApplicationBuilder().token(self.token).build()
        self.bot: Bot = self.app.bot
        
        # Register command handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all command handlers"""
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("ping", self.cmd_ping))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = (
            "🤖 **Crypto EMA20 Breakout Bot** 🤖\n\n"
            "I monitor cryptocurrency markets for EMA20 breakouts with volume confirmation.\n\n"
            "**Available Commands:**\n"
            "/start - Show this welcome message\n"
            "/ping - Check if bot is responsive\n"
            "/status - Show monitoring status\n"
            "/help - Show help information\n\n"
            "🔍 I'm currently monitoring all USDT pairs on Binance for:\n"
            "• EMA20 breakouts on 4H timeframe\n"
            "• EMA20 breakouts on 1D timeframe\n"
            "• High volume confirmation\n\n"
            "⚠️ Signals are for informational purposes only. Not financial advice!"
        )
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def cmd_ping(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ping command"""
        await update.message.reply_text("✅ Bot is online and responsive!")
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        status_message = (
            f"📊 **Bot Status**\n\n"
            f"🔄 Monitoring Active: {'✅ Yes' if self.monitoring_active else '❌ No'}\n"
            f"📈 Signals Sent Today: {len(self.sent_signals)}\n"
            f"⏱️ Check Interval: {MONITORING_INTERVAL // 3600} hours\n"
            f"🎯 Target Channel: {self.chat_id}\n"
        )
        await update.message.reply_text(status_message, parse_mode='Markdown')
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = (
            "📚 **Help & Information**\n\n"
            "**What I Do:**\n"
            "• Monitor all USDT trading pairs on Binance\n"
            "• Detect EMA20 breakouts on multiple timeframes\n"
            "• Confirm signals with volume analysis\n"
            "• Send alerts to designated channel\n\n"
            "**Signal Criteria:**\n"
            "• Price breaks above EMA20 on 4H chart\n"
            "• Price breaks above EMA20 on 1D chart\n"
            "• Current volume > 1.5x average volume\n"
            "• No duplicate signals for same symbol\n\n"
            "**Commands:**\n"
            "/start - Welcome message\n"
            "/ping - Test bot responsiveness\n"
            "/status - Check monitoring status\n"
            "/help - This help message\n\n"
            "⚠️ **Disclaimer:** These signals are for educational purposes only. "
            "Always conduct your own research before making trading decisions!"
        )
        await update.message.reply_text(help_message, parse_mode='Markdown')
    
    async def send_signal(self, symbol: str):
        """Send trading signal to the designated channel"""
        try:
            message = self.analyzer.get_signal_message(symbol)
            await self.bot.send_message(
                chat_id=self.chat_id, 
                text=message, 
                parse_mode='Markdown'
            )
            print(f"✅ Signal sent for {symbol}")
        except Exception as e:
            print(f"❌ Error sending signal for {symbol}: {e}")
    
    async def monitor_markets(self):
        """Main monitoring loop for cryptocurrency markets"""
        self.monitoring_active = True
        print("🚀 Starting cryptocurrency market monitoring...")
        
        async with aiohttp.ClientSession() as session:
            # Get all USDT trading pairs
            symbols = await self.analyzer.get_all_usdt_pairs(session)
            print(f"📊 Monitoring {len(symbols)} USDT pairs")
            
            if not symbols:
                print("❌ No symbols found. Retrying in next cycle...")
                return
            
            while self.monitoring_active:
                print(f"🔍 Market scan started at {asyncio.get_event_loop().time()}")
                signals_found = 0
                
                # Check each symbol for trading signals
                for symbol in symbols:
                    try:
                        if await self.analyzer.analyze_symbol(session, symbol):
                            if symbol not in self.sent_signals:
                                await self.send_signal(symbol)
                                self.sent_signals.add(symbol)
                                signals_found += 1
                        else:
                            # Remove from cache if signal is no longer valid
                            self.sent_signals.discard(symbol)
                    
                    except Exception as e:
                        print(f"❌ Error analyzing {symbol}: {e}")
                        continue
                
                print(f"✅ Market scan completed. Found {signals_found} new signals.")
                print(f"⏳ Waiting {MONITORING_INTERVAL // 3600} hours until next scan...")
                
                # Wait for next monitoring cycle
                await asyncio.sleep(MONITORING_INTERVAL)
    
    async def run(self):
        """Start the bot and monitoring system"""
        print("🤖 Starting Crypto EMA20 Breakout Bot...")
        
        try:
            # Test bot token
            bot_info = await self.bot.get_me()
            print(f"✅ Bot authenticated: @{bot_info.username}")
            
            # Start both bot polling and market monitoring concurrently
            await asyncio.gather(
                self.app.run_polling(drop_pending_updates=True),
                self.monitor_markets()
            )
        
        except Exception as e:
            print(f"❌ Critical error starting bot: {e}")
            self.monitoring_active = False
            raise
    
    def stop_monitoring(self):
        """Stop the monitoring system"""
        self.monitoring_active = False
        print("🛑 Monitoring stopped")
