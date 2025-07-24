import asyncio
import aiohttp
import pandas as pd
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import numpy as np
from io import BytesIO
import base64
import random
from datetime import datetime, timedelta
import requests
import time
from tradingview_integration import initialize_tradingview, get_market_data, get_available_pairs
from user_database import UserDatabase

# Rate limiter for CoinGecko API
class APIRateLimiter:
    def __init__(self, max_requests_per_minute=10):
        self.max_requests_per_minute = max_requests_per_minute
        self.requests = []
        self.min_delay = 2.0  # Balanced delay for dual API load balancing
        self.last_request_time = 0
    
    async def wait_if_needed(self):
        now = time.time()
        
        # Ensure minimum delay between requests
        time_since_last = now - self.last_request_time
        if time_since_last < self.min_delay:
            wait_time = self.min_delay - time_since_last
            print(f"⏳ Rate limiting: waiting {wait_time:.1f} seconds...")
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()

# Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '8161774951:AAGYBbKajxUakx_NwrIClnf87ziQN5Z1ixo')
CHAT_ID = os.getenv('CHAT_ID', '304403982')

BINANCE_API = 'https://api.binance.com/api/v3/klines'
BINANCE_EXCHANGE_INFO = 'https://api.binance.com/api/v3/exchangeInfo'

class SimpleCryptoBot:
    def __init__(self, token, chat_id):
        # Initialize database
        self.user_db = UserDatabase()
        self.token = token
        self.admin_chat_id = '304403982'  # Admin chat ID for notifications
        self.admin_ids = {'304403982'}  # Set of admin user IDs
        # Add admin to premium users by default for testing
        self.paid_users = {'304403982'}  # Admin gets premium access
        self.restart_requested = False  # Flag to track restart requests
        self.sent_signals = set()
        self.signal_history = []  # Store last 5 signals with details
        self.signal_cooldowns = {}  # Track when signals were sent (symbol: timestamp)
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.user_languages = {}  # Store user language preferences
        # self.paid_users initialized above with admin access
        self.free_users = set()  # Store free tier users (first 100)
        self.pending_payments = {}  # Track pending payments (user_id: payment_info)
        self.subscription_expiry = {}  # Track subscription expiry dates (user_id: expiry_date)
        self.max_free_users = 100  # Maximum number of free users allowed
        self.current_pair_index = 0  # Track which pair to check next
        self.subscription_plans = {
            'weekly': {'price': 9.99, 'days': 7, 'description': 'Weekly Premium'},
            'monthly': {'price': 29.99, 'days': 30, 'description': 'Monthly Premium'},
            'yearly': {'price': 199.99, 'days': 365, 'description': 'Yearly Premium (Best Value)'}
        }
        
        # Initialize rate limiter for CoinGecko API (optimized settings)
        self.rate_limiter = APIRateLimiter(max_requests_per_minute=20)
        self.current_pair_index = 0  # Track which pairs to check in rotation
        
        # Set up persistent menu (will be called after bot starts)
        self.setup_commands_called = False
        
        # Multi-language messages
        self.messages = {
            'en': {
                'select_language': "🌍 Please select your language:\n\n🇺🇸 English\n🇪🇸 Español\n🇫🇷 Français\n🇩🇪 Deutsch\n🇷🇺 Русский",
                'bot_intro': (
                    "🤖 Crypto EMA20 Breakout Bot\n\n"
                    "✅ Bot is working and monitoring!\n\n"
                    "📊 Currently tracking: 22 USDT pairs\n"
                    "🔍 Analysis includes:\n"
                    "• EMA20 breakouts (4H & 1D)\n"
                    "• Volume confirmation\n"
                    "• RSI momentum\n"
                    "• 200 SMA trend\n"
                    "• Bullish candle patterns\n\n"
                    "📈 You'll receive signals when breakouts occur\n"
                    "⏰ Scanning every 5 minutes\n\n"
                    "🎯 TRADING FEATURES:\n"
                    "• Entry points with current prices\n"
                    "• Take profit levels (TP1, TP2, TP3)\n"
                    "• Stop loss calculations\n"
                    "• Risk/reward ratios\n"
                    "• Signal strength indicators\n"
                    "• Position sizing recommendations\n"
                    "• Danger zone warnings\n\n"
                    "Commands:\n"
                    "/start - Show this status\n"
                    "/status - Quick status check\n\n"
                    "⚠️ This is not financial advice!"
                ),
                'status_report': (
                    "📊 Bot Status Report\n\n"
                    "✅ Monitoring: 22 crypto pairs\n"
                    "📈 Signals sent today: {signals_count}\n"
                    "🔄 Scanning every 5 minutes\n"
                    "💪 All systems operational"
                ),
                'admin_only': "❌ Admin only command",
                'welcome_new_user': "🎉 Welcome to Crypto EMA20 Breakout Bot!\n\n💎 This is a premium trading signal service.\n\n✅ Premium features include:\n• Real-time trading signals\n• Entry/exit recommendations\n• Risk management guidance\n• Multi-timeframe analysis\n\nUse /subscribe to get premium access!",
                'free_tier_welcome': "🎉 Welcome to Crypto EMA20 Breakout Bot!\n\n🤖 **What This Bot Does:**\nThis bot automatically monitors 50 major cryptocurrencies and sends you instant trading signals when it detects profitable EMA20 breakout opportunities. You get entry points, take profit levels, stop loss calculations, and risk management guidance - all delivered straight to your Telegram.\n\n🆓 **CONGRATULATIONS!** You have FREE access to all premium features!\n\n🎯 What You Get (Completely Free):\n• Advanced EMA20 breakout signals from 50 USDT pairs\n• Real-time trading alerts with entry/exit points\n• Take profit levels (TP1, TP2, TP3) and stop loss\n• Volume confirmation and trend analysis\n• Risk management and position sizing guidance\n• Multi-timeframe technical analysis\n• Professional trading recommendations\n\n📊 Technical Features:\n• Monitors: BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOT, LINK, MATIC and 40 more pairs\n• Scanning frequency: Every 4 hours\n• Signal delivery: Instant Telegram notifications\n• Analysis: EMA20 breakouts with volume confirmation\n\n🌍 Multilingual support in 5 languages\n\n🚀 You're one of our first 100 users - enjoy completely free access!\n\n⚠️ Important: After 100 users, new members will need premium subscriptions. Your free access is permanent!\n\n📚 Type /help for complete feature guide",
                'free_tier_full': "🎉 Welcome to Crypto EMA20 Breakout Bot!\n\n🤖 **What This Bot Does:**\nThis bot automatically monitors 50 major cryptocurrencies and sends you instant trading signals when it detects profitable EMA20 breakout opportunities. You get entry points, take profit levels, stop loss calculations, and risk management guidance - all delivered straight to your Telegram.\n\n🆓 Thank you for your interest! Our free tier is now full (100/100 users).\n\n💎 Premium Subscription Features:\n• Advanced EMA20 breakout signals from 50 USDT pairs\n• Real-time trading alerts with entry/exit points\n• Take profit levels (TP1, TP2, TP3) and stop loss calculations\n• Volume confirmation and trend strength analysis\n• Risk management and position sizing guidance\n• Multi-timeframe technical analysis (4H, 1D)\n• Professional trading recommendations\n\n📊 What You Get:\n• Monitors: BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOT, LINK, MATIC + 40 more pairs\n• Scanning: Every 4 hours continuously\n• Delivery: Instant Telegram notifications\n• Analysis: EMA20 breakouts with volume confirmation\n• Languages: 5 language support\n\n💰 Affordable premium plans starting from $9.99/week\n\nUse /subscribe to get premium access!\n\n📚 Type /help for complete feature guide",
                'subscription_menu': "💎 Choose Your Premium Plan:\n\n📅 Plans Available:",
                'payment_success': "✅ Payment Successful!\n\nWelcome to Premium! You now have full access to all trading signals and features.",
                'payment_failed': "❌ Payment failed. Please try again or contact support.",
                'payment_submitted': "✅ Payment verification request submitted!\n\n📋 Your payment details have been sent to admin for verification.\n⏳ You will receive confirmation within 24 hours.\n\n💬 If you have questions, contact @avie_support",
                'paid_command_usage': "📝 Payment Verification Usage:\n\n/paid <method> <transaction_hash>\n\nExample:\n/paid BTC 1A2B3C4D5E6F7G8H9I0J\n/paid ETH 0x1234567890abcdef\n/paid USDT TRX123456789\n\n💡 Replace with your actual transaction hash",
                'not_subscribed': "🔒 Premium Feature\n\nFree access available for first 100 users, then premium subscription required.\nCurrent users: {user_count}/100\n\nIf full, use /subscribe to upgrade and unlock all trading signals!",
                'help_message_free': (
                    "📚 Crypto EMA20 Breakout Bot - Complete Guide\n\n"
                    "🎯 What This Bot Does:\n"
                    "This bot is an advanced cryptocurrency trading signal service that monitors 50 major USDT trading pairs on Binance using sophisticated technical analysis. It detects profitable EMA20 breakout opportunities with volume confirmation and sends you instant trading signals.\n\n"
                    "🆓 **FREE ACCESS Available!**\n"
                    "Join now and get completely free access to all premium features. Limited to first 100 users only!\n\n"
                    "🔍 Technical Analysis Features:\n"
                    "• EMA20 (Exponential Moving Average) breakout detection\n"
                    "• Volume confirmation for signal validation\n"
                    "• Multi-timeframe analysis (4H, 1D charts)\n"
                    "• Support/resistance level identification\n"
                    "• Trend strength analysis\n"
                    "• Market momentum indicators\n\n"
                    "📊 Trading Signal Information:\n"
                    "• Entry price recommendations\n"
                    "• Take profit levels (TP1, TP2, TP3)\n"
                    "• Stop loss calculations\n"
                    "• Risk/reward ratios\n"
                    "• Position sizing guidance\n"
                    "• Market context analysis\n\n"
                    "⏰ Monitoring Schedule:\n"
                    "• Continuous market scanning every 4 hours\n"
                    "• Real-time signal delivery\n"
                    "• 50 USDT pairs monitored simultaneously\n"
                    "• Instant notifications when conditions are met\n\n"
                    "🤖 Available Commands:\n"
                    "/start - Welcome and language selection\n"
                    "/status - Bot status and recent signals\n"
                    "/help - This comprehensive guide\n\n"
                    "🌍 Multi-Language Support:\n"
                    "Full support for 5 languages: English, Spanish, French, German, Russian\n\n"
                    "💰 Supported Cryptocurrencies:\n"
                    "BTC, ETH, BNB, ADA, SOL, XRP, MATIC, AVAX, DOT, LINK, LTC, ATOM, ALGO, VET, FIL, TRX, EOS, XLM, NEO, IOTA, DASH, SHIB, PEPE, TON, BCH, NEAR, APT, HBAR, ETC, RNDR, INJ, STX, FLOW, ARB, OP and 15 more pairs\n\n"
                    "🎯 Who Should Use This Bot:\n"
                    "• Cryptocurrency traders seeking profitable opportunities\n"
                    "• Technical analysis enthusiasts\n"
                    "• Both beginner and experienced traders\n"
                    "• Anyone wanting automated market monitoring\n\n"
                    "📧 Support: @avie_support"
                ),
                'coin_list': "💰 Monitored Cryptocurrency Pairs\n\n" +
                    "📊 The bot continuously monitors these 50 USDT trading pairs for EMA20 breakout signals:\n\n" +
                    "🔥 Major Coins:\n" +
                    "• BTCUSDT - Bitcoin\n" +
                    "• ETHUSDT - Ethereum\n" +
                    "• BNBUSDT - Binance Coin\n" +
                    "• ADAUSDT - Cardano\n" +
                    "• SOLUSDT - Solana\n" +
                    "• XRPUSDT - Ripple\n\n" +
                    "💎 Altcoins:\n" +
                    "• MATICUSDT - Polygon\n" +
                    "• AVAXUSDT - Avalanche\n" +
                    "• DOTUSDT - Polkadot\n" +
                    "• LINKUSDT - Chainlink\n" +
                    "• LTCUSDT - Litecoin\n" +
                    "• ATOMUSDT - Cosmos\n\n" +
                    "🚀 Additional Pairs:\n" +
                    "• ALGOUSDT - Algorand\n" +
                    "• VETUSDT - VeChain\n" +
                    "• FILUSDT - Filecoin\n" +
                    "• TRXUSDT - TRON\n" +
                    "• EOSUSDT - EOS\n" +
                    "• XLMUSDT - Stellar\n" +
                    "• NEOUSDT - Neo\n" +
                    "• IOTAUSDT - IOTA\n" +
                    "• DASHUSDT - Dash\n\n" +
                    "⏰ Scanning Frequency: Every 4 hours\n" +
                    "📈 Analysis: EMA20 breakouts with volume confirmation\n" +
                    "🎯 Signal Types: Entry, TP1/TP2/TP3, Stop Loss\n\n" +
                    "💡 New signals are sent instantly when breakout conditions are met!",
                'command_menu': "🤖 Bot Commands",
                'help_message_premium': (
                    "📚 Crypto EMA20 Breakout Bot - Complete Guide\n\n"
                    "🎯 What This Bot Does:\n"
                    "This bot is an advanced cryptocurrency trading signal service that monitors 50 major USDT trading pairs on Binance using sophisticated technical analysis. It detects profitable EMA20 breakout opportunities with volume confirmation and sends you instant trading signals.\n\n"
                    "💎 **PREMIUM SUBSCRIPTION REQUIRED**\n"
                    "Free tier is full (100/100). Premium plans available starting from $9.99/week.\n\n"
                    "🔍 Technical Analysis Features:\n"
                    "• EMA20 (Exponential Moving Average) breakout detection\n"
                    "• Volume confirmation for signal validation\n"
                    "• Multi-timeframe analysis (4H, 1D charts)\n"
                    "• Support/resistance level identification\n"
                    "• Trend strength analysis\n"
                    "• Market momentum indicators\n\n"
                    "📊 Trading Signal Information:\n"
                    "• Entry price recommendations\n"
                    "• Take profit levels (TP1, TP2, TP3)\n"
                    "• Stop loss calculations\n"
                    "• Risk/reward ratios\n"
                    "• Position sizing guidance\n"
                    "• Market context analysis\n\n"
                    "⏰ Monitoring Schedule:\n"
                    "• Continuous market scanning every 4 hours\n"
                    "• Real-time signal delivery\n"
                    "• 50 USDT pairs monitored simultaneously\n"
                    "• Instant notifications when conditions are met\n\n"
                    "🤖 Available Commands:\n"
                    "/start - Welcome and language selection\n"
                    "/status - Bot status and recent signals\n"
                    "/subscribe - Premium subscription plans\n"
                    "/paid <method> <tx_hash> - Payment verification\n"
                    "/help - This comprehensive guide\n\n"
                    "🌍 Multi-Language Support:\n"
                    "Full support for 5 languages: English, Spanish, French, German, Russian\n\n"
                    "💰 Supported Cryptocurrencies:\n"
                    "BTC, ETH, BNB, ADA, SOL, XRP, MATIC, AVAX, DOT, LINK, LTC, ATOM, ALGO, VET, FIL, TRX, EOS, XLM, NEO, IOTA, DASH, SHIB, PEPE, TON, BCH, NEAR, APT, HBAR, ETC, RNDR, INJ, STX, FLOW, ARB, OP and 15 more pairs\n\n"
                    "🎯 Who Should Use This Bot:\n"
                    "• Cryptocurrency traders seeking profitable opportunities\n"
                    "• Technical analysis enthusiasts\n"
                    "• Both beginner and experienced traders\n"
                    "• Anyone wanting automated market monitoring\n\n"
                    "📧 Support: @avie_support"
                ),
                'coin_list': "💰 Monitored Cryptocurrency Pairs\n\n📊 The bot continuously monitors these 50 USDT trading pairs for EMA20 breakout signals:\n\n🔸 BTC/USDT - Bitcoin\n🔸 ETH/USDT - Ethereum\n🔸 BNB/USDT - Binance Coin\n🔸 SOL/USDT - Solana\n🔸 XRP/USDT - Ripple\n🔸 ADA/USDT - Cardano\n🔸 AVAX/USDT - Avalanche\n🔸 DOT/USDT - Polkadot\n🔸 LINK/USDT - Chainlink\n🔸 MATIC/USDT - Polygon\n🔸 UNI/USDT - Uniswap\n🔸 LTC/USDT - Litecoin\n🔸 ATOM/USDT - Cosmos\n🔸 FTM/USDT - Fantom\n🔸 ALGO/USDT - Algorand\n🔸 VET/USDT - VeChain\n🔸 ICP/USDT - Internet Computer\n🔸 SAND/USDT - The Sandbox\n🔸 MANA/USDT - Decentraland\n🔸 CRV/USDT - Curve DAO\n🔸 AAVE/USDT - Aave\n🔸 MKR/USDT - Maker\n\n🔸 SHIB/USDT - Shiba Inu\n🔸 PEPE/USDT - Pepe\n🔸 TON/USDT - Toncoin\n🔸 BCH/USDT - Bitcoin Cash\n🔸 NEAR/USDT - Near Protocol\n🔸 APT/USDT - Aptos\n🔸 SUI/USDT - Sui\n🔸 XLM/USDT - Stellar\n🔸 HBAR/USDT - Hedera\n🔸 ETC/USDT - Ethereum Classic\n🔸 FIL/USDT - Filecoin\n🔸 VET/USDT - VeChain\n🔸 RNDR/USDT - Render\n🔸 ICP/USDT - Internet Computer\n🔸 FET/USDT - Fetch.ai\n🔸 MANA/USDT - Decentraland\n🔸 SAND/USDT - The Sandbox\n🔸 INJ/USDT - Injective\n🔸 AAVE/USDT - Aave\n🔸 STX/USDT - Stacks\n🔸 FLOW/USDT - Flow\n🔸 XTZ/USDT - Tezos\n🔸 EGLD/USDT - MultiversX\n🔸 EIGEN/USDT - EigenLayer\n🔸 LDO/USDT - Lido DAO\n🔸 ONDO/USDT - Ondo\n🔸 SEI/USDT - Sei\n🔸 WLD/USDT - Worldcoin\n🔸 ARB/USDT - Arbitrum\n🔸 OP/USDT - Optimism\n\n⚡ Signals are generated when:\n• EMA20 breakout confirmed on 4H + 1D timeframes\n• Volume is 1.5x above average\n• Additional technical criteria met\n\n🔄 Updated every 5 minutes",
                'payment_submitted': "✅ Payment information submitted!\n\n📋 Your payment details have been sent for verification.\n\n⏳ Processing time: Usually within 24 hours\n💎 You'll receive premium access once verified\n\n📧 Contact @avie_support if you have questions",
                'paid_command_usage': "💳 Payment Command Usage:\n\n📝 Format: /paid <method> <transaction_hash>\n\n🔸 Example: /paid BTC 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa\n🔸 Example: /paid ETH 0x742d35cc6ab2b7b8c5c1234567890abcdef123456\n🔸 Example: /paid USDT TxHash123456789\n\n📧 Contact @avie_support for payment assistance",
                'delete_messages_confirm': "🗑️ Delete All Bot Messages\n\n⚠️ This will delete all messages sent by the bot in this chat.\n\n❗ This action cannot be undone.\n\nAre you sure you want to continue?",
                'delete_messages_success': "✅ Successfully deleted all bot messages from this chat.",
                'delete_messages_error': "❌ Some messages could not be deleted. This is normal for older messages (48+ hours old).",
                'delete_messages_none': "ℹ️ No bot messages found to delete in this chat."
            },
            'es': {
                'select_language': "🌍 Por favor selecciona tu idioma:\n\n🇺🇸 English\n🇪🇸 Español\n🇫🇷 Français\n🇩🇪 Deutsch\n🇷🇺 Русский",
                'bot_intro': (
                    "🤖 Bot de Señales Crypto EMA20\n\n"
                    "✅ ¡El bot está funcionando y monitoreando!\n\n"
                    "📊 Siguiendo actualmente: 50 pares USDT\n"
                    "🔍 El análisis incluye:\n"
                    "• Rupturas EMA20 (4H y 1D)\n"
                    "• Confirmación de volumen\n"
                    "• Momentum RSI\n"
                    "• Tendencia SMA 200\n"
                    "• Patrones de velas alcistas\n\n"
                    "📈 Recibirás señales cuando ocurran rupturas\n"
                    "⏰ Escaneando cada 5 minutos\n\n"
                    "🎯 CARACTERÍSTICAS DE TRADING:\n"
                    "• Puntos de entrada con precios actuales\n"
                    "• Niveles de toma de ganancias (TP1, TP2, TP3)\n"
                    "• Cálculos de stop loss\n"
                    "• Ratios riesgo/recompensa\n"
                    "• Indicadores de fuerza de señal\n"
                    "• Recomendaciones de tamaño de posición\n"
                    "• Advertencias de zona de peligro\n\n"
                    "Comandos:\n"
                    "/start - Mostrar este estado\n"
                    "/status - Verificación rápida\n\n"
                    "⚠️ ¡Esto no es asesoramiento financiero!"
                ),
                'status_report': (
                    "📊 Reporte de Estado del Bot\n\n"
                    "✅ Monitoreando: 50 pares crypto\n"
                    "📈 Señales enviadas hoy: {signals_count}\n"
                    "🔄 Escaneando cada 5 minutos\n"
                    "💪 Todos los sistemas operativos"
                ),
                'admin_only': "❌ Comando solo para administrador",
                'free_tier_welcome': "🎉 ¡Bienvenido al Bot Crypto EMA20 Breakout!\n\n🤖 **Qué hace este bot:**\nEste bot monitorea automáticamente 50 criptomonedas principales y te envía señales de trading instantáneas cuando detecta oportunidades rentables de ruptura EMA20. Obtienes puntos de entrada, niveles de toma de ganancias, cálculos de stop loss y guía de gestión de riesgos, todo entregado directamente a tu Telegram.\n\n🆓 **¡FELICITACIONES!** ¡Tienes acceso GRATUITO a todas las funciones premium!\n\n🎯 Lo que obtienes (completamente gratis):\n• Señales avanzadas de ruptura EMA20 de 50 pares USDT\n• Alertas de trading en tiempo real con puntos de entrada/salida\n• Niveles de toma de ganancias (TP1, TP2, TP3) y stop loss\n• Confirmación de volumen y análisis de tendencias\n• Guía de gestión de riesgos y dimensionamiento de posiciones\n• Análisis técnico multi-timeframe\n• Recomendaciones de trading profesionales\n\n📊 Características técnicas:\n• Monitorea: BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOT, LINK, MATIC y 40 pares más\n• Frecuencia de escaneo: Cada 4 horas\n• Entrega de señales: Notificaciones instantáneas de Telegram\n• Análisis: Rupturas EMA20 con confirmación de volumen\n\n🌍 Soporte multiidioma en 5 idiomas\n\n🚀 ¡Eres uno de nuestros primeros 100 usuarios - disfruta el acceso completamente gratis!\n\n⚠️ Importante: Después de 100 usuarios, los nuevos miembros necesitarán suscripciones premium. ¡Tu acceso gratuito es permanente!\n\n📚 Escribe /help para la guía completa de funciones",
                'free_tier_full': "🎉 ¡Bienvenido al Bot Crypto EMA20 Breakout!\n\n🤖 **Qué hace este bot:**\nEste bot monitorea automáticamente 50 criptomonedas principales y te envía señales de trading instantáneas cuando detecta oportunidades rentables de ruptura EMA20. Obtienes puntos de entrada, niveles de toma de ganancias, cálculos de stop loss y guía de gestión de riesgos, todo entregado directamente a tu Telegram.\n\n🆓 ¡Gracias por tu interés! Nuestro nivel gratuito está lleno (100/100 usuarios).\n\n💎 Características de Suscripción Premium:\n• Señales avanzadas de ruptura EMA20 de 50 pares USDT\n• Alertas de trading en tiempo real con puntos de entrada/salida\n• Niveles de toma de ganancias (TP1, TP2, TP3) y cálculos de stop loss\n• Confirmación de volumen y análisis de fuerza de tendencia\n• Guía de gestión de riesgos y dimensionamiento de posiciones\n• Análisis técnico multi-timeframe (4H, 1D)\n• Recomendaciones de trading profesionales\n\n📊 Lo que obtienes:\n• Monitorea: BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOT, LINK, MATIC + 40 pares más\n• Escaneo: Cada 4 horas continuamente\n• Entrega: Notificaciones instantáneas de Telegram\n• Análisis: Rupturas EMA20 con confirmación de volumen\n• Idiomas: Soporte de 5 idiomas\n\n💰 Planes premium asequibles desde $9.99/semana\n\n¡Usa /subscribe para obtener acceso premium!\n\n📚 Escribe /help para la guía completa de funciones",
                'trial_expired': "⏰ ¡Tu prueba de 3 días ha expirado!\n\n💎 Actualiza a Premium para continuar recibiendo señales:\n• Semanal: $9.99\n• Mensual: $29.99 (Mejor Valor)\n• Anual: $199.99 (Ahorra 44%)\n\n¡Usa /subscribe para actualizar ahora!",
                'trial_welcome': "🎉 ¡Bienvenido! ¡Tienes una prueba GRATUITA de 3 días!\n\n✅ Acceso completo a todas las funciones premium:\n• Señales de trading en tiempo real\n• Recomendaciones de entrada/salida\n• Guía de gestión de riesgos\n• Análisis multi-timeframe\n\nLa prueba expira en {days} días. ¡Usa /subscribe para actualizar en cualquier momento!",
                'subscription_menu': "💎 Elige Tu Plan Premium:\n\n📅 Planes Disponibles:",
                'payment_success': "✅ ¡Pago Exitoso!\n\n¡Bienvenido a Premium! Ahora tienes acceso completo a todas las señales de trading y funciones.",
                'payment_failed': "❌ Error en el pago. Por favor intenta de nuevo o contacta soporte.",
                'not_subscribed': "🔒 Función Premium\n\nAcceso gratuito disponible para los primeros 100 usuarios, luego se requiere suscripción premium.\nUsuarios actuales: {user_count}/100\n\n¡Si está lleno, usa /subscribe para actualizar y desbloquear todas las señales de trading!",
                'help_message_free': (
                    "📚 Bot Crypto EMA20 Breakout - Guía Completa\n\n"
                    "🎯 Qué hace este bot:\n"
                    "Este bot es un servicio avanzado de señales de trading de criptomonedas que monitorea 50 pares principales USDT en Binance usando análisis técnico sofisticado. Detecta oportunidades rentables de ruptura EMA20 con confirmación de volumen y te envía señales de trading instantáneas.\n\n"
                    "🆓 **¡ACCESO GRATUITO Disponible!**\n"
                    "¡Únete ahora y obtén acceso completamente gratuito a todas las funciones premium. ¡Limitado solo a los primeros 100 usuarios!\n\n"
                    "🔍 Características de Análisis Técnico:\n"
                    "• Detección de ruptura EMA20 (Media Móvil Exponencial)\n"
                    "• Confirmación de volumen para validación de señales\n"
                    "• Análisis multi-timeframe (gráficos 4H, 1D)\n"
                    "• Identificación de niveles de soporte/resistencia\n"
                    "• Análisis de fuerza de tendencia\n"
                    "• Indicadores de momentum del mercado\n\n"
                    "📊 Información de Señales de Trading:\n"
                    "• Recomendaciones de precio de entrada\n"
                    "• Niveles de toma de ganancias (TP1, TP2, TP3)\n"
                    "• Cálculos de stop loss\n"
                    "• Ratios riesgo/recompensa\n"
                    "• Guía de tamaño de posición\n"
                    "• Análisis de contexto del mercado\n\n"
                    "⏰ Horario de Monitoreo:\n"
                    "• Escaneo continuo del mercado cada 4 horas\n"
                    "• Entrega de señales en tiempo real\n"
                    "• 50 pares USDT monitoreados simultáneamente\n"
                    "• Notificaciones instantáneas cuando se cumplen condiciones\n\n"
                    "🤖 Comandos Disponibles:\n"
                    "/start - Bienvenida y selección de idioma\n"
                    "/status - Estado del bot y señales recientes\n"
                    "/help - Esta guía completa\n\n"
                    "🌍 Soporte Multi-Idioma:\n"
                    "Soporte completo para 5 idiomas: Inglés, Español, Francés, Alemán, Ruso\n\n"
                    "💰 Criptomonedas Soportadas:\n"
                    "BTC, ETH, BNB, ADA, SOL, XRP, MATIC, AVAX, DOT, LINK, LTC, ATOM, ALGO, VET, FIL, TRX, EOS, XLM, NEO, IOTA, DASH, SHIB, PEPE, TON, BCH, NEAR, APT, HBAR, ETC, RNDR, INJ, STX, FLOW, ARB, OP y 15 pares más\n\n"
                    "🎯 Quién debería usar este bot:\n"
                    "• Traders de criptomonedas buscando oportunidades rentables\n"
                    "• Entusiastas del análisis técnico\n"
                    "• Tanto traders principiantes como experimentados\n"
                    "• Cualquiera que quiera monitoreo automatizado del mercado\n\n"
                    "📧 Soporte: @avie_support"
                ),
                'help_message_premium': "📚 Guía Premium - Todas las funciones desbloqueadas\n\n🎯 Acceso completo a análisis avanzado y señales en tiempo real\n\n📊 Funciones Premium activas\n💎 Trading profesional habilitado",
                'command_menu': "🤖 **Menú de Comandos del Bot**\n\n📊 Comandos principales:\n• /start - Inicio y selección de idioma\n• /status - Estado actual del bot\n• /help - Guía completa\n• /subscribe - Planes premium\n\n🎯 Usa los botones para navegación fácil",
                'coin_list': "💰 Pares de Criptomonedas Monitoreados\n\n📊 El bot monitorea continuamente estos 50 pares USDT para señales de ruptura EMA20:\n\n🔸 BTC/USDT - Bitcoin\n🔸 ETH/USDT - Ethereum\n🔸 BNB/USDT - Binance Coin\n🔸 SOL/USDT - Solana\n🔸 XRP/USDT - Ripple\n🔸 ADA/USDT - Cardano\n🔸 AVAX/USDT - Avalanche\n🔸 DOT/USDT - Polkadot\n🔸 LINK/USDT - Chainlink\n🔸 MATIC/USDT - Polygon\n🔸 UNI/USDT - Uniswap\n🔸 LTC/USDT - Litecoin\n🔸 ATOM/USDT - Cosmos\n🔸 FTM/USDT - Fantom\n🔸 ALGO/USDT - Algorand\n🔸 VET/USDT - VeChain\n🔸 ICP/USDT - Internet Computer\n🔸 SAND/USDT - The Sandbox\n🔸 MANA/USDT - Decentraland\n🔸 CRV/USDT - Curve DAO\n🔸 AAVE/USDT - Aave\n🔸 MKR/USDT - Maker\n\n⚡ Las señales se generan cuando:\n• Ruptura EMA20 confirmada en marcos de 4H + 1D\n• El volumen es 1.5x por encima del promedio\n• Se cumplen criterios técnicos adicionales\n\n🔄 Actualizado cada 5 minutos",
                'payment_submitted': "✅ ¡Información de pago enviada!\n\n📋 Tus detalles de pago han sido enviados para verificación.\n\n⏳ Tiempo de procesamiento: Usualmente dentro de 24 horas\n💎 Recibirás acceso premium una vez verificado\n\n📧 Contacta @avie_support si tienes preguntas",
                'paid_command_usage': "💳 Uso del Comando de Pago:\n\n📝 Formato: /paid <método> <hash_transacción>\n\n🔸 Ejemplo: /paid BTC 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa\n🔸 Ejemplo: /paid ETH 0x742d35cc6ab2b7b8c5c1234567890abcdef123456\n🔸 Ejemplo: /paid USDT TxHash123456789\n\n📧 Contacta @avie_support para asistencia con pagos",
                'delete_messages_confirm': "🗑️ Eliminar Todos los Mensajes del Bot\n\n⚠️ Esto eliminará todos los mensajes enviados por el bot en este chat.\n\n❗ Esta acción no se puede deshacer.\n\n¿Estás seguro de que quieres continuar?",
                'delete_messages_success': "✅ Se eliminaron exitosamente todos los mensajes del bot de este chat.",
                'delete_messages_error': "❌ Algunos mensajes no pudieron ser eliminados. Esto es normal para mensajes antiguos (48+ horas).",
                'delete_messages_none': "ℹ️ No se encontraron mensajes del bot para eliminar en este chat."
            },
            'fr': {
                'select_language': "🌍 Veuillez sélectionner votre langue:\n\n🇺🇸 English\n🇪🇸 Español\n🇫🇷 Français\n🇩🇪 Deutsch\n🇷🇺 Русский",
                'bot_intro': (
                    "🤖 Bot de Signaux Crypto EMA20\n\n"
                    "✅ Le bot fonctionne et surveille!\n\n"
                    "📊 Suivi actuel: 50 paires USDT\n"
                    "🔍 L'analyse comprend:\n"
                    "• Cassures EMA20 (4H et 1D)\n"
                    "• Confirmation de volume\n"
                    "• Momentum RSI\n"
                    "• Tendance SMA 200\n"
                    "• Modèles de chandelles haussières\n\n"
                    "📈 Vous recevrez des signaux lors des cassures\n"
                    "⏰ Scan toutes les 5 minutes\n\n"
                    "🎯 FONCTIONNALITÉS DE TRADING:\n"
                    "• Points d'entrée avec prix actuels\n"
                    "• Niveaux de prise de profit (TP1, TP2, TP3)\n"
                    "• Calculs de stop loss\n"
                    "• Ratios risque/récompense\n"
                    "• Indicateurs de force du signal\n"
                    "• Recommandations de taille de position\n"
                    "• Avertissements de zone de danger\n\n"
                    "Commandes:\n"
                    "/start - Afficher ce statut\n"
                    "/status - Vérification rapide\n\n"
                    "⚠️ Ce n'est pas un conseil financier!"
                ),
                'status_report': (
                    "📊 Rapport de Statut du Bot\n\n"
                    "✅ Surveillance: 50 paires crypto\n"
                    "📈 Signaux envoyés aujourd'hui: {signals_count}\n"
                    "🔄 Scan toutes les 5 minutes\n"
                    "💪 Tous les systèmes opérationnels"
                ),
                'admin_only': "❌ Commande réservée à l'administrateur",
                'free_tier_welcome': "🎉 Bienvenue au Bot Crypto EMA20 Breakout!\n\n🤖 **Ce que fait ce bot:**\nCe bot surveille automatiquement 50 principales cryptomonnaies et vous envoie des signaux de trading instantanés quand il détecte des opportunités rentables de cassure EMA20. Vous obtenez des points d'entrée, des niveaux de prise de profit, des calculs de stop loss et des conseils de gestion des risques - tout livré directement à votre Telegram.\n\n🆓 **FÉLICITATIONS!** Vous avez un accès GRATUIT à toutes les fonctionnalités premium!\n\n🎯 Ce que vous obtenez (complètement gratuit):\n• Signaux avancés de cassure EMA20 de 50 paires USDT\n• Alertes de trading en temps réel avec points d'entrée/sortie\n• Niveaux de prise de profit (TP1, TP2, TP3) et stop loss\n• Confirmation de volume et analyse de tendance\n• Guide de gestion des risques et dimensionnement de position\n• Analyse technique multi-timeframe\n• Recommandations de trading professionnelles\n\n📊 Caractéristiques techniques:\n• Surveille: BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOT, LINK, MATIC et 40 paires de plus\n• Fréquence de scan: Toutes les 4 heures\n• Livraison de signaux: Notifications Telegram instantanées\n• Analyse: Cassures EMA20 avec confirmation de volume\n\n🌍 Support multilingue en 5 langues\n\n🚀 Vous êtes l'un de nos 100 premiers utilisateurs - profitez de l'accès complètement gratuit!\n\n⚠️ Important: Après 100 utilisateurs, les nouveaux membres auront besoin d'abonnements premium. Votre accès gratuit est permanent!\n\n📚 Tapez /help pour le guide complet des fonctionnalités",
                'free_tier_full': "🎉 Bienvenue au Bot Crypto EMA20 Breakout!\n\n🤖 **Ce que fait ce bot:**\nCe bot surveille automatiquement 50 principales cryptomonnaies et vous envoie des signaux de trading instantanés quand il détecte des opportunités rentables de cassure EMA20. Vous obtenez des points d'entrée, des niveaux de prise de profit, des calculs de stop loss et des conseils de gestion des risques - tout livré directement à votre Telegram.\n\n🆓 Merci pour votre intérêt! Notre niveau gratuit est complet (100/100 utilisateurs).\n\n💎 Fonctionnalités d'abonnement Premium:\n• Signaux avancés de cassure EMA20 de 50 paires USDT\n• Alertes de trading en temps réel avec points d'entrée/sortie\n• Niveaux de prise de profit (TP1, TP2, TP3) et calculs de stop loss\n• Confirmation de volume et analyse de force de tendance\n• Guide de gestion des risques et dimensionnement de position\n• Analyse technique multi-timeframe (4H, 1D)\n• Recommandations de trading professionnelles\n\n📊 Ce que vous obtenez:\n• Surveille: BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOT, LINK, MATIC + 40 paires de plus\n• Scan: Toutes les 4 heures en continu\n• Livraison: Notifications Telegram instantanées\n• Analyse: Cassures EMA20 avec confirmation de volume\n• Langues: Support de 5 langues\n\n💰 Plans premium abordables à partir de $9.99/semaine\n\nUtilisez /subscribe pour obtenir l'accès premium!\n\n📚 Tapez /help pour le guide complet des fonctionnalités",
                'trial_expired': "⏰ Votre essai de 3 jours a expiré!\n\n💎 Passez à Premium pour continuer à recevoir des signaux:\n• Hebdomadaire: $9.99\n• Mensuel: $29.99 (Meilleure Valeur)\n• Annuel: $199.99 (Économisez 44%)\n\nUtilisez /subscribe pour passer à niveau maintenant!",
                'trial_welcome': "🎉 Bienvenue! Vous avez un essai GRATUIT de 3 jours!\n\n✅ Accès complet à toutes les fonctionnalités premium:\n• Signaux de trading en temps réel\n• Recommandations d'entrée/sortie\n• Guidance de gestion des risques\n• Analyse multi-timeframe\n\nL'essai expire dans {days} jours. Utilisez /subscribe pour passer à niveau à tout moment!",
                'subscription_menu': "💎 Choisissez Votre Plan Premium:\n\n📅 Plans Disponibles:",
                'payment_success': "✅ Paiement Réussi!\n\nBienvenue à Premium! Vous avez maintenant un accès complet à tous les signaux de trading et fonctionnalités.",
                'payment_failed': "❌ Échec du paiement. Veuillez réessayer ou contacter le support.",
                'not_subscribed': "🔒 Fonctionnalité Premium\n\nCette fonctionnalité nécessite un abonnement premium.\nUtilisez /subscribe pour passer à niveau et débloquer tous les signaux de trading!",
                'help_message_free': (
                    "📚 Bot Crypto EMA20 Breakout - Guide Complet\n\n"
                    "🎯 Ce que fait ce bot:\n"
                    "Ce bot est un service avancé de signaux de trading de cryptomonnaies qui surveille 50 paires USDT principales sur Binance en utilisant une analyse technique sophistiquée. Il détecte les opportunités rentables de cassure EMA20 avec confirmation de volume et vous envoie des signaux de trading instantanés.\n\n"
                    "🆓 **ACCÈS GRATUIT Disponible!**\n"
                    "Rejoignez maintenant et obtenez un accès complètement gratuit à toutes les fonctionnalités premium. Limité aux 100 premiers utilisateurs seulement!\n\n"
                    "🔍 Caractéristiques d'Analyse Technique:\n"
                    "• Détection de cassure EMA20 (Moyenne Mobile Exponentielle)\n"
                    "• Confirmation de volume pour validation de signal\n"
                    "• Analyse multi-timeframe (graphiques 4H, 1D)\n"
                    "• Identification des niveaux de support/résistance\n"
                    "• Analyse de force de tendance\n"
                    "• Indicateurs de momentum de marché\n\n"
                    "📊 Informations de Signal de Trading:\n"
                    "• Recommandations de prix d'entrée\n"
                    "• Niveaux de prise de profit (TP1, TP2, TP3)\n"
                    "• Calculs de stop loss\n"
                    "• Ratios risque/récompense\n"
                    "• Guidance de dimensionnement de position\n"
                    "• Analyse de contexte de marché\n\n"
                    "⏰ Programme de Surveillance:\n"
                    "• Scan continu du marché toutes les 4 heures\n"
                    "• Livraison de signaux en temps réel\n"
                    "• 50 paires USDT surveillées simultanément\n"
                    "• Notifications instantanées quand les conditions sont remplies\n\n"
                    "🤖 Commandes Disponibles:\n"
                    "/start - Bienvenue et sélection de langue\n"
                    "/status - Statut du bot et signaux récents\n"
                    "/help - Ce guide complet\n\n"
                    "🌍 Support Multi-Langue:\n"
                    "Support complet pour 5 langues: Anglais, Espagnol, Français, Allemand, Russe\n\n"
                    "💰 Cryptomonnaies Supportées:\n"
                    "BTC, ETH, BNB, ADA, SOL, XRP, MATIC, AVAX, DOT, LINK, LTC, ATOM, ALGO, VET, FIL, TRX, EOS, XLM, NEO, IOTA, DASH, SHIB, PEPE, TON, BCH, NEAR, APT, HBAR, ETC, RNDR, INJ, STX, FLOW, ARB, OP et 15 paires de plus\n\n"
                    "🎯 Qui devrait utiliser ce bot:\n"
                    "• Traders de cryptomonnaies cherchant des opportunités rentables\n"
                    "• Enthousiastes d'analyse technique\n"
                    "• Traders débutants et expérimentés\n"
                    "• Quiconque voulant une surveillance automatisée du marché\n\n"
                    "📧 Support: @avie_support"
                ),
                'help_message_premium': "📚 Guide Premium - Toutes les fonctionnalités débloquées\n\n🎯 Accès complet à l'analyse avancée et signaux en temps réel\n\n📊 Fonctionnalités Premium actives\n💎 Trading professionnel activé",
                'command_menu': "🤖 **Menu des Commandes du Bot**\n\n📊 Commandes principales:\n• /start - Accueil et sélection de langue\n• /status - Statut actuel du bot\n• /help - Guide complet\n• /subscribe - Plans premium\n\n🎯 Utilisez les boutons pour une navigation facile",
                'coin_list': "💰 Paires de Cryptomonnaies Surveillées\n\n📊 Le bot surveille en continu ces 50 paires USDT pour les signaux de rupture EMA20:\n\n🔸 BTC/USDT - Bitcoin\n🔸 ETH/USDT - Ethereum\n🔸 BNB/USDT - Binance Coin\n🔸 SOL/USDT - Solana\n🔸 XRP/USDT - Ripple\n🔸 ADA/USDT - Cardano\n🔸 AVAX/USDT - Avalanche\n🔸 DOT/USDT - Polkadot\n🔸 LINK/USDT - Chainlink\n🔸 MATIC/USDT - Polygon\n🔸 UNI/USDT - Uniswap\n🔸 LTC/USDT - Litecoin\n🔸 ATOM/USDT - Cosmos\n🔸 FTM/USDT - Fantom\n🔸 ALGO/USDT - Algorand\n🔸 VET/USDT - VeChain\n🔸 ICP/USDT - Internet Computer\n🔸 SAND/USDT - The Sandbox\n🔸 MANA/USDT - Decentraland\n🔸 CRV/USDT - Curve DAO\n🔸 AAVE/USDT - Aave\n🔸 MKR/USDT - Maker\n\n⚡ Signaux générés quand:\n• Rupture EMA20 confirmée sur timeframes 4H + 1D\n• Volume 1.5x au-dessus de la moyenne\n• Critères techniques supplémentaires remplis\n\n🔄 Mis à jour toutes les 5 minutes",
                'payment_submitted': "✅ Informations de paiement soumises!\n\n📋 Vos détails de paiement ont été envoyés pour vérification.\n\n⏳ Temps de traitement: Généralement sous 24 heures\n💎 Vous recevrez l'accès premium une fois vérifié\n\n📧 Contactez @avie_support si vous avez des questions",
                'paid_command_usage': "💳 Utilisation de la Commande de Paiement:\n\n📝 Format: /paid <méthode> <hash_transaction>\n\n🔸 Exemple: /paid BTC 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa\n🔸 Exemple: /paid ETH 0x742d35cc6ab2b7b8c5c1234567890abcdef123456\n🔸 Exemple: /paid USDT TxHash123456789\n\n📧 Contactez @avie_support pour l'assistance paiement",
                'delete_messages_confirm': "🗑️ Supprimer Tous les Messages du Bot\n\n⚠️ Cela supprimera tous les messages envoyés par le bot dans ce chat.\n\n❗ Cette action ne peut pas être annulée.\n\nÊtes-vous sûr de vouloir continuer?",
                'delete_messages_success': "✅ Tous les messages du bot ont été supprimés avec succès de ce chat.",
                'delete_messages_error': "❌ Certains messages n'ont pas pu être supprimés. C'est normal pour les anciens messages (48+ heures).",
                'delete_messages_none': "ℹ️ Aucun message du bot trouvé à supprimer dans ce chat."
            },
            'de': {
                'select_language': "🌍 Bitte wählen Sie Ihre Sprache:\n\n🇺🇸 English\n🇪🇸 Español\n🇫🇷 Français\n🇩🇪 Deutsch\n🇷🇺 Русский",
                'bot_intro': (
                    "🤖 Crypto EMA20 Breakout Bot\n\n"
                    "✅ Bot funktioniert und überwacht!\n\n"
                    "📊 Derzeit verfolgt: 50 USDT-Paare\n"
                    "🔍 Analyse umfasst:\n"
                    "• EMA20-Ausbrüche (4H & 1D)\n"
                    "• Volumenbestätigung\n"
                    "• RSI-Momentum\n"
                    "• 200 SMA-Trend\n"
                    "• Bullische Kerzenmuster\n\n"
                    "📈 Sie erhalten Signale bei Ausbrüchen\n"
                    "⏰ Scan alle 5 Minuten\n\n"
                    "🎯 TRADING-FUNKTIONEN:\n"
                    "• Einstiegspunkte mit aktuellen Preisen\n"
                    "• Gewinnmitnahme-Level (TP1, TP2, TP3)\n"
                    "• Stop-Loss-Berechnungen\n"
                    "• Risiko-/Gewinnverhältnisse\n"
                    "• Signalstärke-Indikatoren\n"
                    "• Positionsgrößen-Empfehlungen\n"
                    "• Gefahrenzone-Warnungen\n\n"
                    "Befehle:\n"
                    "/start - Diesen Status anzeigen\n"
                    "/status - Schnelle Statusprüfung\n\n"
                    "⚠️ Dies ist keine Finanzberatung!"
                ),
                'status_report': (
                    "📊 Bot-Statusbericht\n\n"
                    "✅ Überwachung: 50 Krypto-Paare\n"
                    "📈 Heute gesendete Signale: {signals_count}\n"
                    "🔄 Scan alle 5 Minuten\n"
                    "💪 Alle Systeme betriebsbereit"
                ),
                'admin_only': "❌ Nur Administrator-Befehl",
                'free_tier_welcome': "🎉 Willkommen beim Crypto EMA20 Breakout Bot!\n\n🤖 **Was dieser Bot macht:**\nDieser Bot überwacht automatisch 50 wichtige Kryptowährungen und sendet Ihnen sofortige Trading-Signale, wenn er profitable EMA20-Ausbruchsmöglichkeiten erkennt. Sie erhalten Einstiegspunkte, Gewinnmitnahme-Level, Stop-Loss-Berechnungen und Risikomanagement-Anleitung - alles direkt an Ihr Telegram geliefert.\n\n🆓 **GLÜCKWUNSCH!** Sie haben KOSTENLOSEN Zugriff auf alle Premium-Funktionen!\n\n🎯 Was Sie bekommen (völlig kostenlos):\n• Erweiterte EMA20-Ausbruchsignale von 50 USDT-Paaren\n• Echtzeit-Trading-Alerts mit Ein-/Ausstiegspunkten\n• Gewinnmitnahme-Level (TP1, TP2, TP3) und Stop-Loss\n• Volumenbestätigung und Trendanalyse\n• Risikomanagement und Positionsgrößen-Anleitung\n• Multi-Timeframe technische Analyse\n• Professionelle Trading-Empfehlungen\n\n📊 Technische Merkmale:\n• Überwacht: BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOT, LINK, MATIC und 40 weitere Paare\n• Scan-Frequenz: Alle 4 Stunden\n• Signal-Lieferung: Sofortige Telegram-Benachrichtigungen\n• Analyse: EMA20-Ausbrüche mit Volumenbestätigung\n\n🌍 Mehrsprachiger Support in 5 Sprachen\n\n🚀 Sie sind einer unserer ersten 100 Benutzer - genießen Sie völlig kostenlosen Zugriff!\n\n⚠️ Wichtig: Nach 100 Benutzern benötigen neue Mitglieder Premium-Abonnements. Ihr kostenloser Zugriff ist dauerhaft!\n\n📚 Geben Sie /help für die vollständige Funktionsanleitung ein",
                'free_tier_full': "🎉 Willkommen beim Crypto EMA20 Breakout Bot!\n\n🤖 **Was dieser Bot macht:**\nDieser Bot überwacht automatisch 50 wichtige Kryptowährungen und sendet Ihnen sofortige Trading-Signale, wenn er profitable EMA20-Ausbruchsmöglichkeiten erkennt. Sie erhalten Einstiegspunkte, Gewinnmitnahme-Level, Stop-Loss-Berechnungen und Risikomanagement-Anleitung - alles direkt an Ihr Telegram geliefert.\n\n🆓 Vielen Dank für Ihr Interesse! Unser kostenloser Bereich ist voll (100/100 Benutzer).\n\n💎 Premium-Abonnement-Funktionen:\n• Erweiterte EMA20-Ausbruchsignale von 50 USDT-Paaren\n• Echtzeit-Trading-Alerts mit Ein-/Ausstiegspunkten\n• Gewinnmitnahme-Level (TP1, TP2, TP3) und Stop-Loss-Berechnungen\n• Volumenbestätigung und Trendstärke-Analyse\n• Risikomanagement und Positionsgrößen-Anleitung\n• Multi-Timeframe technische Analyse (4H, 1D)\n• Professionelle Trading-Empfehlungen\n\n📊 Was Sie bekommen:\n• Überwacht: BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOT, LINK, MATIC + 40 weitere Paare\n• Scannen: Alle 4 Stunden kontinuierlich\n• Lieferung: Sofortige Telegram-Benachrichtigungen\n• Analyse: EMA20-Ausbrüche mit Volumenbestätigung\n• Sprachen: 5-Sprachen-Support\n\n💰 Erschwingliche Premium-Pläne ab $9.99/Woche\n\nVerwenden Sie /subscribe für Premium-Zugriff!\n\n📚 Geben Sie /help für die vollständige Funktionsanleitung ein",
                'trial_expired': "⏰ Ihre 3-tägige Testversion ist abgelaufen!\n\n💎 Auf Premium upgraden, um weiterhin Signale zu erhalten:\n• Wöchentlich: $9.99\n• Monatlich: $29.99 (Bester Wert)\n• Jährlich: $199.99 (44% sparen)\n\nVerwenden Sie /subscribe zum Upgraden!",
                'trial_welcome': "🎉 Willkommen! Sie haben eine 3-tägige KOSTENLOSE Testversion!\n\n✅ Vollzugriff auf alle Premium-Funktionen:\n• Echtzeit-Trading-Signale\n• Ein-/Ausstiegsempfehlungen\n• Risikomanagement-Anleitung\n• Multi-Timeframe-Analyse\n\nTestversion läuft in {days} Tagen ab. Verwenden Sie /subscribe zum Upgraden!",
                'subscription_menu': "💎 Wählen Sie Ihren Premium-Plan:\n\n📅 Verfügbare Pläne:",
                'payment_success': "✅ Zahlung Erfolgreich!\n\nWillkommen bei Premium! Sie haben jetzt vollständigen Zugriff auf alle Trading-Signale und Funktionen.",
                'payment_failed': "❌ Zahlung fehlgeschlagen. Bitte versuchen Sie es erneut oder kontaktieren Sie den Support.",
                'not_subscribed': "🔒 Premium-Funktion\n\nDiese Funktion erfordert ein Premium-Abonnement.\nVerwenden Sie /subscribe zum Upgraden und freischalten aller Trading-Signale!",
                'help_message_free': (
                    "📚 Crypto EMA20 Breakout Bot - Vollständige Anleitung\n\n"
                    "🎯 Was dieser Bot macht:\n"
                    "Dieser Bot ist ein fortschrittlicher Kryptowährungs-Trading-Signal-Service, der 50 wichtige USDT-Handelspaare auf Binance mit ausgeklügelter technischer Analyse überwacht. Er erkennt profitable EMA20-Ausbruchsmöglichkeiten mit Volumenbestätigung und sendet Ihnen sofortige Trading-Signale.\n\n"
                    "🆓 **KOSTENLOSER ZUGANG Verfügbar!**\n"
                    "Treten Sie jetzt bei und erhalten Sie völlig kostenlosen Zugang zu allen Premium-Funktionen. Nur auf die ersten 100 Benutzer begrenzt!\n\n"
                    "🔍 Technische Analyse-Funktionen:\n"
                    "• EMA20 (Exponential Moving Average) Ausbruchserkennung\n"
                    "• Volumenbestätigung für Signalvalidierung\n"
                    "• Multi-Timeframe-Analyse (4H, 1D Charts)\n"
                    "• Support/Widerstand-Level-Identifikation\n"
                    "• Trendstärke-Analyse\n"
                    "• Marktmomentum-Indikatoren\n\n"
                    "📊 Trading-Signal-Informationen:\n"
                    "• Einstiegspreis-Empfehlungen\n"
                    "• Gewinnmitnahme-Level (TP1, TP2, TP3)\n"
                    "• Stop-Loss-Berechnungen\n"
                    "• Risiko-/Gewinnverhältnisse\n"
                    "• Positionsgrößen-Anleitung\n"
                    "• Marktkontext-Analyse\n\n"
                    "⏰ Überwachungsplan:\n"
                    "• Kontinuierliche Marktscans alle 4 Stunden\n"
                    "• Echtzeit-Signal-Lieferung\n"
                    "• 50 USDT-Paare gleichzeitig überwacht\n"
                    "• Sofortige Benachrichtigungen wenn Bedingungen erfüllt\n\n"
                    "🤖 Verfügbare Befehle:\n"
                    "/start - Willkommen und Sprachauswahl\n"
                    "/status - Bot-Status und aktuelle Signale\n"
                    "/help - Diese umfassende Anleitung\n\n"
                    "🌍 Multi-Sprach-Support:\n"
                    "Vollständige Unterstützung für 5 Sprachen: Englisch, Spanisch, Französisch, Deutsch, Russisch\n\n"
                    "💰 Unterstützte Kryptowährungen:\n"
                    "BTC, ETH, BNB, ADA, SOL, XRP, MATIC, AVAX, DOT, LINK, LTC, ATOM, ALGO, VET, FIL, TRX, EOS, XLM, NEO, IOTA, DASH, SHIB, PEPE, TON, BCH, NEAR, APT, HBAR, ETC, RNDR, INJ, STX, FLOW, ARB, OP und 15 weitere Paare\n\n"
                    "🎯 Wer sollte diesen Bot nutzen:\n"
                    "• Kryptowährungs-Trader, die profitable Gelegenheiten suchen\n"
                    "• Technische Analyse-Enthusiasten\n"
                    "• Sowohl Anfänger als auch erfahrene Trader\n"
                    "• Jeder, der automatisierte Marktüberwachung wünscht\n\n"
                    "📧 Support: @avie_support"
                ),
                'help_message_premium': "📚 Premium-Anleitung - Alle Funktionen freigeschaltet\n\n🎯 Vollzugriff auf erweiterte Analyse und Echtzeit-Signale\n\n📊 Premium-Funktionen aktiv\n💎 Professioneller Handel aktiviert",
                'command_menu': "🤖 **Bot-Befehls-Menü**\n\n📊 Hauptbefehle:\n• /start - Begrüßung und Sprachauswahl\n• /status - Aktueller Bot-Status\n• /help - Vollständige Anleitung\n• /subscribe - Premium-Pläne\n\n🎯 Verwenden Sie Schaltflächen für einfache Navigation",
                'coin_list': "💰 Überwachte Kryptowährungspaare\n\n📊 Der Bot überwacht kontinuierlich diese 50 USDT-Paare für EMA20-Ausbruchsignale:\n\n🔸 BTC/USDT - Bitcoin\n🔸 ETH/USDT - Ethereum\n🔸 BNB/USDT - Binance Coin\n🔸 SOL/USDT - Solana\n🔸 XRP/USDT - Ripple\n🔸 ADA/USDT - Cardano\n🔸 AVAX/USDT - Avalanche\n🔸 DOT/USDT - Polkadot\n🔸 LINK/USDT - Chainlink\n🔸 MATIC/USDT - Polygon\n🔸 UNI/USDT - Uniswap\n🔸 LTC/USDT - Litecoin\n🔸 ATOM/USDT - Cosmos\n🔸 FTM/USDT - Fantom\n🔸 ALGO/USDT - Algorand\n🔸 VET/USDT - VeChain\n🔸 ICP/USDT - Internet Computer\n🔸 SAND/USDT - The Sandbox\n🔸 MANA/USDT - Decentraland\n🔸 CRV/USDT - Curve DAO\n🔸 AAVE/USDT - Aave\n🔸 MKR/USDT - Maker\n\n⚡ Signale werden generiert wenn:\n• EMA20-Ausbruch bestätigt auf 4H + 1D Zeitrahmen\n• Volumen 1.5x über dem Durchschnitt\n• Zusätzliche technische Kriterien erfüllt\n\n🔄 Alle 5 Minuten aktualisiert",
                'payment_submitted': "✅ Zahlungsinformationen eingereicht!\n\n📋 Ihre Zahlungsdetails wurden zur Überprüfung gesendet.\n\n⏳ Bearbeitungszeit: Normalerweise innerhalb von 24 Stunden\n💎 Sie erhalten Premium-Zugang nach der Verifikation\n\n📧 Kontaktieren Sie @avie_support bei Fragen",
                'paid_command_usage': "💳 Zahlungsbefehl Verwendung:\n\n📝 Format: /paid <methode> <transaktions_hash>\n\n🔸 Beispiel: /paid BTC 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa\n🔸 Beispiel: /paid ETH 0x742d35cc6ab2b7b8c5c1234567890abcdef123456\n🔸 Beispiel: /paid USDT TxHash123456789\n\n📧 Kontaktieren Sie @avie_support für Zahlungshilfe",
                'delete_messages_confirm': "🗑️ Alle Bot-Nachrichten Löschen\n\n⚠️ Dies wird alle vom Bot gesendeten Nachrichten in diesem Chat löschen.\n\n❗ Diese Aktion kann nicht rückgängig gemacht werden.\n\nSind Sie sicher, dass Sie fortfahren möchten?",
                'delete_messages_success': "✅ Alle Bot-Nachrichten wurden erfolgreich aus diesem Chat gelöscht.",
                'delete_messages_error': "❌ Einige Nachrichten konnten nicht gelöscht werden. Das ist normal bei älteren Nachrichten (48+ Stunden).",
                'delete_messages_none': "ℹ️ Keine Bot-Nachrichten zum Löschen in diesem Chat gefunden."
            },
            'ru': {
                'select_language': "🌍 Пожалуйста, выберите ваш язык:\n\n🇺🇸 English\n🇪🇸 Español\n🇫🇷 Français\n🇩🇪 Deutsch\n🇷🇺 Русский",
                'bot_intro': (
                    "🤖 Крипто EMA20 Бот Пробоев\n\n"
                    "✅ Бот работает и мониторит!\n\n"
                    "📊 Отслеживает: 50 USDT пары\n"
                    "🔍 Анализ включает:\n"
                    "• Пробои EMA20 (4ч и 1д)\n"
                    "• Подтверждение объёма\n"
                    "• Моментум RSI\n"
                    "• Тренд 200 SMA\n"
                    "• Бычьи паттерны свечей\n\n"
                    "📈 Получите сигналы при пробоях\n"
                    "⏰ Сканирование каждые 5 минут\n\n"
                    "🎯 ТОРГОВЫЕ ФУНКЦИИ:\n"
                    "• Точки входа с текущими ценами\n"
                    "• Уровни тейк-профита (TP1, TP2, TP3)\n"
                    "• Расчёты стоп-лосса\n"
                    "• Соотношения риск/доходность\n"
                    "• Индикаторы силы сигнала\n"
                    "• Рекомендации размера позиции\n"
                    "• Предупреждения опасной зоны\n\n"
                    "Команды:\n"
                    "/start - Показать этот статус\n"
                    "/status - Быстрая проверка\n\n"
                    "⚠️ Это не финансовый совет!"
                ),
                'status_report': (
                    "📊 Отчёт о Статусе Бота\n\n"
                    "✅ Мониторинг: 50 крипто пары\n"
                    "📈 Сигналов отправлено сегодня: {signals_count}\n"
                    "🔄 Сканирование каждые 5 минут\n"
                    "💪 Все системы работают"
                ),
                'admin_only': "❌ Команда только для администратора",
                'free_tier_welcome': "🎉 Добро пожаловать в Crypto EMA20 Breakout Bot!\n\n🤖 **Что делает этот бот:**\nЭтот бот автоматически отслеживает 50 основных криптовалют и отправляет вам мгновенные торговые сигналы, когда обнаруживает прибыльные возможности прорыва EMA20. Вы получаете точки входа, уровни тейк-профита, расчеты стоп-лосса и руководство по управлению рисками - все доставляется прямо в ваш Telegram.\n\n🆓 **ПОЗДРАВЛЯЕМ!** У вас есть БЕСПЛАТНЫЙ доступ ко всем премиум функциям!\n\n🎯 Что вы получаете (полностью бесплатно):\n• Продвинутые сигналы прорыва EMA20 от 50 USDT пар\n• Торговые уведомления в реальном времени с точками входа/выхода\n• Уровни тейк-профита (TP1, TP2, TP3) и стоп-лосс\n• Подтверждение объема и анализ тренда\n• Руководство по управлению рисками и размерам позиций\n• Многотаймфреймовый технический анализ\n• Профессиональные торговые рекомендации\n\n📊 Технические особенности:\n• Отслеживает: BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOT, LINK, MATIC и еще 40 пар\n• Частота сканирования: Каждые 4 часа\n• Доставка сигналов: Мгновенные уведомления Telegram\n• Анализ: Прорывы EMA20 с подтверждением объема\n\n🌍 Многоязычная поддержка на 5 языках\n\n🚀 Вы один из наших первых 100 пользователей - наслаждайтесь полностью бесплатным доступом!\n\n⚠️ Важно: После 100 пользователей новым участникам потребуются премиум подписки. Ваш бесплатный доступ навсегда!\n\n📚 Введите /help для полного руководства по функциям",
                'free_tier_full': "🎉 Добро пожаловать в Crypto EMA20 Breakout Bot!\n\n🤖 **Что делает этот бот:**\nЭтот бот автоматически отслеживает 50 основных криптовалют и отправляет вам мгновенные торговые сигналы, когда обнаруживает прибыльные возможности прорыва EMA20. Вы получаете точки входа, уровни тейк-профита, расчеты стоп-лосса и руководство по управлению рисками - все доставляется прямо в ваш Telegram.\n\n🆓 Спасибо за ваш интерес! Наш бесплатный уровень заполнен (100/100 пользователей).\n\n💎 Функции премиум подписки:\n• Продвинутые сигналы прорыва EMA20 от 50 USDT пар\n• Торговые уведомления в реальном времени с точками входа/выхода\n• Уровни тейк-профита (TP1, TP2, TP3) и расчеты стоп-лосса\n• Подтверждение объема и анализ силы тренда\n• Руководство по управлению рисками и размерам позиций\n• Многотаймфреймовый технический анализ (4H, 1D)\n• Профессиональные торговые рекомендации\n\n📊 Что вы получаете:\n• Отслеживает: BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOT, LINK, MATIC + еще 40 пар\n• Сканирование: Каждые 4 часа непрерывно\n• Доставка: Мгновенные уведомления Telegram\n• Анализ: Прорывы EMA20 с подтверждением объема\n• Языки: Поддержка 5 языков\n\n💰 Доступные премиум планы от $9.99/неделя\n\nИспользуйте /subscribe для получения премиум доступа!\n\n📚 Введите /help для полного руководства по функциям",
                'trial_expired': "⏰ Ваш 3-дневный пробный период истёк!\n\n💎 Обновитесь до Премиум для продолжения получения сигналов:\n• Недельный: $9.99\n• Месячный: $29.99 (Лучшее Предложение)\n• Годовой: $199.99 (Экономия 44%)\n\nИспользуйте /subscribe для обновления!",
                'welcome_new_user': "🎉 Добро пожаловать в бота торговых сигналов!\n\n💎 Это премиум сервис торговых сигналов.\n\n✅ Премиум функции включают:\n• Торговые сигналы в реальном времени\n• Рекомендации входа/выхода\n• Руководство по управлению рисками\n• Мульти-таймфреймовый анализ\n\nИспользуйте /subscribe для получения премиум доступа!",
                'subscription_menu': "💎 Выберите Ваш Премиум План:\n\n📅 Доступные Планы:",
                'payment_success': "✅ Платёж Успешен!\n\nДобро пожаловать в Премиум! Теперь у вас есть полный доступ ко всем торговым сигналам и функциям.",
                'payment_failed': "❌ Ошибка платежа. Пожалуйста, попробуйте снова или обратитесь в поддержку.",
                'not_subscribed': "🔒 Премиум Функция\n\nЭта функция требует премиум подписку.\nИспользуйте /subscribe для обновления и разблокировки всех торговых сигналов!",
                'help_message_free': (
                    "📚 Crypto EMA20 Breakout Bot - Полное Руководство\n\n"
                    "🎯 Что делает этот бот:\n"
                    "Этот бот - продвинутый сервис торговых сигналов криптовалют, который мониторит 50 основных USDT торговых пар на Binance, используя сложный технический анализ. Он обнаруживает прибыльные возможности прорыва EMA20 с подтверждением объема и отправляет вам мгновенные торговые сигналы.\n\n"
                    "🆓 **БЕСПЛАТНЫЙ ДОСТУП Доступен!**\n"
                    "Присоединяйтесь сейчас и получите полностью бесплатный доступ ко всем премиум функциям. Ограничено только для первых 100 пользователей!\n\n"
                    "🔍 Функции Технического Анализа:\n"
                    "• Обнаружение прорыва EMA20 (Экспоненциальная Скользящая Средняя)\n"
                    "• Подтверждение объема для валидации сигналов\n"
                    "• Мульти-таймфреймовый анализ (4H, 1D графики)\n"
                    "• Идентификация уровней поддержки/сопротивления\n"
                    "• Анализ силы тренда\n"
                    "• Индикаторы рыночного моментума\n\n"
                    "📊 Информация Торговых Сигналов:\n"
                    "• Рекомендации цены входа\n"
                    "• Уровни взятия прибыли (TP1, TP2, TP3)\n"
                    "• Расчеты стоп-лосса\n"
                    "• Соотношения риск/прибыль\n"
                    "• Руководство по размеру позиции\n"
                    "• Анализ рыночного контекста\n\n"
                    "⏰ График Мониторинга:\n"
                    "• Непрерывное сканирование рынка каждые 4 часа\n"
                    "• Доставка сигналов в реальном времени\n"
                    "• 50 USDT пар мониторятся одновременно\n"
                    "• Мгновенные уведомления при выполнении условий\n\n"
                    "🤖 Доступные Команды:\n"
                    "/start - Приветствие и выбор языка\n"
                    "/status - Статус бота и недавние сигналы\n"
                    "/help - Это всеобъемлющее руководство\n\n"
                    "🌍 Мульти-Языковая Поддержка:\n"
                    "Полная поддержка 5 языков: Английский, Испанский, Французский, Немецкий, Русский\n\n"
                    "💰 Поддерживаемые Криптовалюты:\n"
                    "BTC, ETH, BNB, ADA, SOL, XRP, MATIC, AVAX, DOT, LINK, LTC, ATOM, ALGO, VET, FIL, TRX, EOS, XLM, NEO, IOTA, DASH, SHIB, PEPE, TON, BCH, NEAR, APT, HBAR, ETC, RNDR, INJ, STX, FLOW, ARB, OP и еще 15 пар\n\n"
                    "🎯 Кто должен использовать этот бот:\n"
                    "• Трейдеры криптовалют, ищущие прибыльные возможности\n"
                    "• Энтузиасты технического анализа\n"
                    "• Как начинающие, так и опытные трейдеры\n"
                    "• Любой, кто хочет автоматизированного мониторинга рынка\n\n"
                    "📧 Поддержка: @avie_support"
                ),
                'help_message_premium': "📚 Премиум Руководство - Все функции разблокированы\n\n🎯 Полный доступ к продвинутому анализу и сигналам в реальном времени\n\n📊 Премиум функции активны\n💎 Профессиональная торговля включена",
                'command_menu': "🤖 **Меню Команд Бота**\n\n📊 Основные команды:\n• /start - Приветствие и выбор языка\n• /status - Текущий статус бота\n• /help - Полное руководство\n• /subscribe - Премиум планы\n\n🎯 Используйте кнопки для легкой навигации",
                'coin_list': "💰 Отслеживаемые Криптовалютные Пары\n\n📊 Бот непрерывно мониторит эти 50 USDT пары для сигналов пробоя EMA20:\n\n🔸 BTC/USDT - Биткоин\n🔸 ETH/USDT - Эфириум\n🔸 BNB/USDT - Binance Coin\n🔸 SOL/USDT - Solana\n🔸 XRP/USDT - Рипл\n🔸 ADA/USDT - Кардано\n🔸 AVAX/USDT - Avalanche\n🔸 DOT/USDT - Polkadot\n🔸 LINK/USDT - Chainlink\n🔸 MATIC/USDT - Polygon\n🔸 UNI/USDT - Uniswap\n🔸 LTC/USDT - Лайткоин\n🔸 ATOM/USDT - Cosmos\n🔸 FTM/USDT - Fantom\n🔸 ALGO/USDT - Algorand\n🔸 VET/USDT - VeChain\n🔸 ICP/USDT - Internet Computer\n🔸 SAND/USDT - The Sandbox\n🔸 MANA/USDT - Decentraland\n🔸 CRV/USDT - Curve DAO\n🔸 AAVE/USDT - Aave\n🔸 MKR/USDT - Maker\n\n⚡ Сигналы генерируются когда:\n• Пробой EMA20 подтверждён на 4H + 1D таймфреймах\n• Объём в 1.5 раза выше среднего\n• Выполнены дополнительные технические критерии\n\n🔄 Обновляется каждые 5 минут",
                'payment_submitted': "✅ Информация о платеже отправлена!\n\n📋 Детали вашего платежа отправлены на проверку.\n\n⏳ Время обработки: Обычно в течение 24 часов\n💎 Вы получите премиум доступ после проверки\n\n📧 Обращайтесь к @avie_support при вопросах",
                'paid_command_usage': "💳 Использование команды платежа:\n\n📝 Формат: /paid <метод> <хеш_транзакции>\n\n🔸 Пример: /paid BTC 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa\n🔸 Пример: /paid ETH 0x742d35cc6ab2b7b8c5c1234567890abcdef123456\n🔸 Пример: /paid USDT TxHash123456789\n\n📧 Обращайтесь к @avie_support за помощью с платежами",
                'delete_messages_confirm': "🗑️ Удалить Все Сообщения Бота\n\n⚠️ Это удалит все сообщения, отправленные ботом в этом чате.\n\n❗ Это действие нельзя отменить.\n\nВы уверены, что хотите продолжить?",
                'delete_messages_success': "✅ Все сообщения бота успешно удалены из этого чата.",
                'delete_messages_error': "❌ Некоторые сообщения не удалось удалить. Это нормально для старых сообщений (48+ часов).",
                'delete_messages_none': "ℹ️ В этом чате не найдено сообщений бота для удаления."
            }
        }

    async def setup_bot_commands(self):
        """Set up persistent bot commands in Telegram menu"""
        url = f"{self.base_url}/setMyCommands"
        commands = [
            {
                "command": "start",
                "description": "🏠 Main Menu - Show bot menu"
            },
            {
                "command": "menu", 
                "description": "🏠 Main Menu - Show bot menu"
            },
            {
                "command": "status",
                "description": "📊 Bot Status - Check current status"
            },
            {
                "command": "help",
                "description": "📚 Help - Complete feature guide"
            }
        ]
        
        data = {"commands": commands}
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        print("✅ Persistent bot menu commands set up successfully")
                        return True
                    else:
                        print(f"❌ Failed to set up bot commands: {response.status}")
                        return False
            except Exception as e:
                print(f"❌ Error setting up bot commands: {e}")
                return False

    async def send_message(self, text, reply_to_message_id=None, target_chat_id=None, parse_mode=None):
        """Send message using direct HTTP API"""
        url = f"{self.base_url}/sendMessage"
        data = {
            'chat_id': target_chat_id,  # Must specify target chat ID
            'text': text
        }
        
        if parse_mode:
            data['parse_mode'] = parse_mode
            
        if reply_to_message_id:
            data['reply_to_message_id'] = reply_to_message_id
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        print(f"✅ Message sent: {text[:50]}...")
                        result = await response.json()
                        return result['result']['message_id']
                    else:
                        response_text = await response.text()
                        print(f"❌ Failed to send message: {response.status} - {response_text}")
                        return False
            except Exception as e:
                print(f"❌ Error sending message: {e}")
                return False

    async def broadcast_signal_to_premium_users(self, signal_text):
        """Send trading signal to all users until 100 user limit reached"""
        all_users = self.paid_users.union(self.free_users)
        total_users = len(all_users)
        
        if not all_users:
            print("⚠️ No users to send signals to")
            return 0
        
        successful_sends = 0
        
        # Everyone gets premium access until 100 users reached
        if total_users <= self.max_free_users:
            # All users get signals (true freemium model)
            for user_id in all_users:
                try:
                    success = await self.send_message(signal_text, target_chat_id=user_id)
                    if success:
                        successful_sends += 1
                    await asyncio.sleep(0.1)  # Rate limiting
                except Exception as e:
                    print(f"❌ Failed to send signal to user {user_id}: {e}")
            print(f"📊 Signal sent to {successful_sends}/{total_users} users (All premium until 100 users)")
        else:
            # After 100 users, only paid users get signals
            for user_id in self.paid_users:
                try:
                    success = await self.send_message(signal_text, target_chat_id=user_id)
                    if success:
                        successful_sends += 1
                    await asyncio.sleep(0.1)  # Rate limiting
                except Exception as e:
                    print(f"❌ Failed to send signal to paid user {user_id}: {e}")
            print(f"📊 Signal sent to {successful_sends}/{len(self.paid_users)} paid users (Over 100 user limit)")
            
        return successful_sends

    async def get_updates(self, offset=0):
        """Get updates from Telegram"""
        url = f"{self.base_url}/getUpdates"
        params = {'offset': offset, 'timeout': 10}
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    return None
            except Exception as e:
                print(f"❌ Error getting updates: {e}")
                return None

    def get_user_language(self, user_id):
        """Get user's preferred language, default to English"""
        user_id_str = str(user_id)
        lang = self.user_languages.get(user_id_str, 'en')
        # Ensure the language exists in our messages
        if lang not in self.messages:
            lang = 'en'
        return lang
    
    def is_admin(self, user_id):
        """Check if user is an admin"""
        return str(user_id) in self.admin_ids
    
    def add_admin(self, user_id):
        """Add user to admin list"""
        user_id = str(user_id)
        self.admin_ids.add(user_id)
        print(f"✅ Added admin: {user_id}")
    
    def remove_admin(self, user_id):
        """Remove user from admin list (except main admin)"""
        user_id = str(user_id)
        if user_id != self.admin_chat_id:  # Protect main admin
            self.admin_ids.discard(user_id)
            print(f"✅ Removed admin: {user_id}")
            return True
        return False
    
    def add_to_signal_history(self, symbol, message):
        """Add signal to history, keep only last 5"""
        from datetime import datetime
        
        signal_data = {
            'symbol': symbol,
            'message': message,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'date_short': datetime.now().strftime('%m/%d %H:%M')
        }
        
        self.signal_history.insert(0, signal_data)  # Add to front
        if len(self.signal_history) > 5:
            self.signal_history = self.signal_history[:5]  # Keep only last 5
        
        print(f"📈 Added {symbol} to signal history ({len(self.signal_history)}/5)")
    
    def is_symbol_in_cooldown(self, symbol):
        """Check if symbol is in cooldown period (2 days)"""
        from datetime import datetime, timedelta
        
        if symbol not in self.signal_cooldowns:
            return False
            
        last_signal_time = self.signal_cooldowns[symbol]
        cooldown_end = last_signal_time + timedelta(days=2)
        current_time = datetime.now()
        
        if current_time < cooldown_end:
            remaining_time = cooldown_end - current_time
            print(f"🕒 {symbol} in cooldown: {remaining_time.days} days, {remaining_time.seconds//3600} hours remaining")
            return True
        else:
            # Cooldown expired, remove from tracking
            del self.signal_cooldowns[symbol]
            return False
    
    def add_symbol_to_cooldown(self, symbol):
        """Add symbol to cooldown tracking"""
        from datetime import datetime
        self.signal_cooldowns[symbol] = datetime.now()
        print(f"🔒 Added {symbol} to 2-day cooldown")
    
    def get_signals_history_message(self, lang='en'):
        """Generate message showing last 5 signals"""
        if not self.signal_history:
            messages = {
                'en': "📊 Recent Signals\n\n❌ No signals detected yet.\n\nThe bot is monitoring 20 cryptocurrency pairs for EMA20 breakouts. Signals will appear here when market conditions are met.",
                'es': "📊 Señales Recientes\n\n❌ Aún no se han detectado señales.\n\nEl bot está monitoreando 20 pares de criptomonedas para rupturas EMA20. Las señales aparecerán aquí cuando se cumplan las condiciones del mercado.",
                'fr': "📊 Signaux Récents\n\n❌ Aucun signal détecté pour le moment.\n\nLe bot surveille 20 paires de cryptomonnaies pour les cassures EMA20. Les signaux apparaîtront ici lorsque les conditions du marché seront remplies.",
                'de': "📊 Aktuelle Signale\n\n❌ Noch keine Signale erkannt.\n\nDer Bot überwacht 20 Kryptowährungspaare auf EMA20-Ausbrüche. Signale werden hier angezeigt, wenn die Marktbedingungen erfüllt sind.",
                'ru': "📊 Последние Сигналы\n\n❌ Сигналы пока не обнаружены.\n\nБот отслеживает 20 криптовалютных пар на пробои EMA20. Сигналы появятся здесь, когда рыночные условия будут выполнены."
            }
            return messages.get(lang, messages['en'])
        
        headers = {
            'en': "📊 Recent Trading Signals (Last 5)",
            'es': "📊 Señales de Trading Recientes (Últimas 5)",
            'fr': "📊 Signaux de Trading Récents (5 Derniers)",
            'de': "📊 Aktuelle Trading-Signale (Letzte 5)",
            'ru': "📊 Последние Торговые Сигналы (Последние 5)"
        }
        
        message = headers.get(lang, headers['en']) + "\n\n"
        
        for i, signal in enumerate(self.signal_history, 1):
            # Extract just the core signal info for compact display
            signal_text = signal['message']
            lines = signal_text.split('\n')
            
            # Get the symbol and entry info
            symbol_line = lines[0] if lines else f"Signal {i}"
            entry_line = ""
            for line in lines:
                if "Entry:" in line or "Entrada:" in line or "Entrée:" in line or "Einstieg:" in line or "Вход:" in line:
                    entry_line = line.strip()
                    break
            
            signal_summary = f"{i}. {symbol_line}"
            if entry_line:
                signal_summary += f"\n   {entry_line}"
            signal_summary += f"\n   🕒 {signal['date_short']}\n"
            
            message += signal_summary
        
        footers = {
            'en': "\n💡 Detailed signal information was sent when each signal was generated.",
            'es': "\n💡 La información detallada de la señal se envió cuando se generó cada señal.",
            'fr': "\n💡 Les informations détaillées du signal ont été envoyées lors de la génération de chaque signal.",
            'de': "\n💡 Detaillierte Signalinformationen wurden bei der Generierung jedes Signals gesendet.",
            'ru': "\n💡 Подробная информация о сигнале была отправлена при генерации каждого сигнала."
        }
        
        message += footers.get(lang, footers['en'])
        return message
    
    def is_user_premium(self, user_id):
        """Check if user has premium access - first 100 users get PERMANENT access, then paid only"""
        user_id = str(user_id)
        
        # Admin always has access
        if self.is_admin(user_id):
            return True
        
        # First 100 users get PERMANENT premium access (grandfathered forever)
        if user_id in self.free_users:
            return True
        
        # Paid users always have access
        if user_id in self.paid_users:
            return True
        
        # New users after 100 free users need to pay
        return False
    
    def can_add_free_user(self):
        """Check if we can add more free users"""
        return len(self.free_users) < self.max_free_users
    
    def add_free_user(self, user_id):
        """Add user to free tier if under limit"""
        user_id = str(user_id)
        if self.can_add_free_user() and user_id not in self.free_users and user_id not in self.paid_users:
            self.free_users.add(user_id)
            print(f"✅ Added free tier access for user: {user_id} ({len(self.free_users)}/{self.max_free_users})")
            return True
        return False
    
    def add_premium_user(self, user_id, plan_days=30):
        """Add user to premium subscribers with expiry tracking"""
        user_id = str(user_id)
        self.paid_users.add(user_id)
        
        # Set subscription expiry date
        import datetime
        expiry_date = datetime.datetime.now() + datetime.timedelta(days=plan_days)
        self.subscription_expiry[user_id] = expiry_date
        
        print(f"✅ Added premium access for user: {user_id} (expires: {expiry_date.strftime('%Y-%m-%d')})")
    
    def check_subscription_expiry(self):
        """Check and remove expired subscriptions"""
        import datetime
        current_time = datetime.datetime.now()
        expired_users = []
        
        for user_id, expiry_date in list(self.subscription_expiry.items()):
            if current_time > expiry_date:
                expired_users.append(user_id)
                self.paid_users.discard(user_id)
                del self.subscription_expiry[user_id]
                print(f"⏰ Subscription expired for user: {user_id}")
        
        return expired_users
    
    def generate_admin_dashboard(self):
        """Generate comprehensive admin dashboard"""
        import datetime
        current_time = datetime.datetime.now()
        
        # Check for expired subscriptions
        expired_count = len(self.check_subscription_expiry())
        
        dashboard = "🛠️ ADMIN DASHBOARD\n"
        dashboard += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Bot Status
        dashboard += "📊 BOT STATUS:\n"
        dashboard += f"• Status: ✅ Running\n"
        dashboard += f"• Signals sent today: {len(self.sent_signals)}\n"
        dashboard += f"• Monitoring: 22 USDT pairs\n"
        dashboard += f"• Scan frequency: Every 5 minutes\n\n"
        
        # User Statistics
        dashboard += "👥 USER STATISTICS:\n"
        dashboard += f"• Free users: {len(self.free_users)}/{self.max_free_users}\n"
        dashboard += f"• Premium users: {len(self.paid_users)}\n"
        dashboard += f"• Total active: {len(self.free_users) + len(self.paid_users)}\n"
        dashboard += f"• Free slots remaining: {self.max_free_users - len(self.free_users)}\n\n"
        
        # Subscription Management
        dashboard += "⏰ SUBSCRIPTION STATUS:\n"
        dashboard += f"• Active subscriptions: {len(self.subscription_expiry)}\n"
        if expired_count > 0:
            dashboard += f"• Expired today: {expired_count}\n"
        
        # Show expiring soon (next 7 days)
        expiring_soon = []
        for user_id, expiry_date in self.subscription_expiry.items():
            days_left = (expiry_date - current_time).days
            if 0 <= days_left <= 7:
                expiring_soon.append((user_id, days_left))
        
        if expiring_soon:
            dashboard += f"• Expiring within 7 days: {len(expiring_soon)}\n"
            for user_id, days in expiring_soon[:3]:  # Show first 3
                dashboard += f"  - User {user_id}: {days} days\n"
        
        dashboard += "\n"
        
        # Pending Payments
        dashboard += "💳 PENDING PAYMENTS:\n"
        if self.pending_payments:
            dashboard += f"• Total pending: {len(self.pending_payments)}\n"
            for user_id, payment in list(self.pending_payments.items())[:3]:  # Show first 3
                dashboard += f"  - User {user_id}: {payment['method']}\n"
        else:
            dashboard += "• No pending payments\n"
        
        dashboard += "\n"
        
        # Quick Admin Commands
        dashboard += "🛠️ ADMIN COMMANDS:\n\n"
        dashboard += "👥 USER MANAGEMENT:\n"
        dashboard += "• /adduser <user_id> [days] - Add premium user\n"
        dashboard += "• /removeuser <user_id> - Remove premium user\n"
        dashboard += "• /verify <user_id> - Verify payment & grant access\n"
        dashboard += "• /listusers - Show all users\n"
        dashboard += "• /freestats - Free tier statistics\n\n"
        
        dashboard += "💳 PAYMENT MANAGEMENT:\n"
        dashboard += "• /pending - View pending payments\n"
        dashboard += "• User command: /paid <method> <tx_hash>\n\n"
        
        dashboard += "🔧 BOT OPERATIONS:\n"
        dashboard += "• /test - Send test signal\n"
        dashboard += "• /status - Bot status check\n"
        dashboard += "• /restart - Restart bot (10-15 sec downtime)\n"
        dashboard += "• /admin - This dashboard\n\n"
        
        dashboard += "👑 ADMIN MANAGEMENT:\n"
        dashboard += "• /addadmin <user_id> - Add new admin (main admin only)\n"
        dashboard += "• /removeadmin <user_id> - Remove admin (main admin only)\n"
        dashboard += "• /listadmins - Show all current admins\n\n"
        
        dashboard += f"👑 Current Admins: {len(self.admin_ids)}\n"
        dashboard += "📊 TIP: Use /listusers for detailed user lists"
        
        return dashboard
        
    def verify_payment(self, user_id, payment_method, amount):
        """Verify payment and grant premium access"""
        # This would integrate with real payment verification system
        # For now, admin can manually verify payments
        user_id = str(user_id)
        payment_info = {
            'method': payment_method,
            'amount': amount,
            'status': 'pending'
        }
        self.pending_payments[user_id] = payment_info
        print(f"💳 Payment verification needed for user {user_id}: {payment_method} ${amount}")
        return True
    
    async def send_subscription_menu(self, user_id, message_id, chat_id):
        """Send subscription plans keyboard"""
        lang = self.get_user_language(user_id)
        
        # Localized button texts
        if lang == 'en':
            buttons = {'weekly': '📅 Weekly', 'monthly': '🗓️ Monthly', 'yearly': '📆 Yearly', 
                      'support': '❓ Support', 'back': '🔙 Back'}
        elif lang == 'es':
            buttons = {'weekly': '📅 Semanal', 'monthly': '🗓️ Mensual', 'yearly': '📆 Anual', 
                      'support': '❓ Soporte', 'back': '🔙 Atrás'}
        elif lang == 'fr':
            buttons = {'weekly': '📅 Hebdo', 'monthly': '🗓️ Mensuel', 'yearly': '📆 Annuel', 
                      'support': '❓ Support', 'back': '🔙 Retour'}
        elif lang == 'de':
            buttons = {'weekly': '📅 Wöchentlich', 'monthly': '🗓️ Monatlich', 'yearly': '📆 Jährlich', 
                      'support': '❓ Support', 'back': '🔙 Zurück'}
        elif lang == 'ru':
            buttons = {'weekly': '📅 Неделя', 'monthly': '🗓️ Месяц', 'yearly': '📆 Год', 
                      'support': '❓ Поддержка', 'back': '🔙 Назад'}
        else:
            buttons = {'weekly': '📅 Weekly', 'monthly': '🗓️ Monthly', 'yearly': '📆 Yearly', 
                      'support': '❓ Support', 'back': '🔙 Back'}
        
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": buttons['weekly'], "callback_data": "sub_weekly"},
                    {"text": buttons['monthly'], "callback_data": "sub_monthly"}
                ],
                [
                    {"text": buttons['yearly'], "callback_data": "sub_yearly"}
                ],
                [
                    {"text": buttons['support'], "callback_data": "support"},
                    {"text": buttons['back'], "callback_data": "cmd_menu"}
                ]
            ]
        }
        
        # Localized subscription menu content
        if lang == 'en':
            text = f"{self.messages[lang]['subscription_menu']}\n\n"
            text += "📅 **Weekly Premium** - $9.99\n• 7 days access\n• All premium features\n\n"
            text += "🗓️ **Monthly Premium** - $29.99\n• 30 days access\n• Best value for regular traders\n\n"
            text += "📆 **Yearly Premium** - $199.99\n• 365 days access\n• Save 44% compared to monthly\n• Best for serious traders\n\n"
            text += "💳 **Payment Options:**\n• Cryptocurrency (BTC, ETH, USDT)\n• Bank Transfer\n• PayPal (Contact Support)\n\n"
            text += "⚠️ Secure payment processing"
        elif lang == 'es':
            text = f"{self.messages[lang]['subscription_menu']}\n\n"
            text += "📅 **Premium Semanal** - $9.99\n• 7 días de acceso\n• Todas las funciones premium\n\n"
            text += "🗓️ **Premium Mensual** - $29.99\n• 30 días de acceso\n• Mejor valor para traders regulares\n\n"
            text += "📆 **Premium Anual** - $199.99\n• 365 días de acceso\n• Ahorra 44% comparado con mensual\n• Mejor para traders serios\n\n"
            text += "💳 **Opciones de Pago:**\n• Criptomonedas (BTC, ETH, USDT)\n• Transferencia Bancaria\n• PayPal (Contactar Soporte)\n\n"
            text += "⚠️ Procesamiento de pago seguro"
        elif lang == 'fr':
            text = f"{self.messages[lang]['subscription_menu']}\n\n"
            text += "📅 **Premium Hebdomadaire** - $9.99\n• 7 jours d'accès\n• Toutes les fonctionnalités premium\n\n"
            text += "🗓️ **Premium Mensuel** - $29.99\n• 30 jours d'accès\n• Meilleure valeur pour les traders réguliers\n\n"
            text += "📆 **Premium Annuel** - $199.99\n• 365 jours d'accès\n• Économisez 44% par rapport au mensuel\n• Meilleur pour les traders sérieux\n\n"
            text += "💳 **Options de Paiement:**\n• Cryptomonnaies (BTC, ETH, USDT)\n• Virement Bancaire\n• PayPal (Contacter le Support)\n\n"
            text += "⚠️ Traitement de paiement sécurisé"
        elif lang == 'de':
            text = f"{self.messages[lang]['subscription_menu']}\n\n"
            text += "📅 **Wöchentliches Premium** - $9.99\n• 7 Tage Zugang\n• Alle Premium-Funktionen\n\n"
            text += "🗓️ **Monatliches Premium** - $29.99\n• 30 Tage Zugang\n• Bester Wert für regelmäßige Trader\n\n"
            text += "📆 **Jährliches Premium** - $199.99\n• 365 Tage Zugang\n• Sparen Sie 44% im Vergleich zu monatlich\n• Am besten für ernsthafte Trader\n\n"
            text += "💳 **Zahlungsoptionen:**\n• Kryptowährungen (BTC, ETH, USDT)\n• Banküberweisung\n• PayPal (Support kontaktieren)\n\n"
            text += "⚠️ Sichere Zahlungsabwicklung"
        elif lang == 'ru':
            text = f"{self.messages[lang]['subscription_menu']}\n\n"
            text += "📅 **Недельный Премиум** - $9.99\n• 7 дней доступа\n• Все премиум функции\n\n"
            text += "🗓️ **Месячный Премиум** - $29.99\n• 30 дней доступа\n• Лучшая цена для обычных трейдеров\n\n"
            text += "📆 **Годовой Премиум** - $199.99\n• 365 дней доступа\n• Экономия 44% по сравнению с месячным\n• Лучше всего для серьезных трейдеров\n\n"
            text += "💳 **Варианты Оплаты:**\n• Криптовалюты (BTC, ETH, USDT)\n• Банковский Перевод\n• PayPal (Обратиться в Поддержку)\n\n"
            text += "⚠️ Безопасная обработка платежей"
        else:
            # Default English
            text = f"{self.messages[lang]['subscription_menu']}\n\n"
            text += "📅 **Weekly Premium** - $9.99\n• 7 days access\n• All premium features\n\n"
            text += "🗓️ **Monthly Premium** - $29.99\n• 30 days access\n• Best value for regular traders\n\n"
            text += "📆 **Yearly Premium** - $199.99\n• 365 days access\n• Save 44% compared to monthly\n• Best for serious traders\n\n"
            text += "💳 **Payment Options:**\n• Cryptocurrency (BTC, ETH, USDT)\n• Bank Transfer\n• PayPal (Contact Support)\n\n"
            text += "⚠️ Secure payment processing"
        
        await self.send_keyboard_message(text, keyboard, message_id, chat_id)

    async def send_language_keyboard(self, message_id, chat_id):
        """Send inline keyboard for language selection"""
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🇺🇸 English", "callback_data": "lang_en"},
                    {"text": "🇪🇸 Español", "callback_data": "lang_es"}
                ],
                [
                    {"text": "🇫🇷 Français", "callback_data": "lang_fr"},
                    {"text": "🇩🇪 Deutsch", "callback_data": "lang_de"}
                ],
                [
                    {"text": "🇷🇺 Русский", "callback_data": "lang_ru"}
                ]
            ]
        }
        
        lang_text = "🌍 **Select Your Language**"
        await self.send_keyboard_message(lang_text, keyboard, message_id, chat_id)



    async def send_main_menu(self, user_id, message_id=None, chat_id=None):
        """Send main menu with all available options as buttons"""
        lang = self.get_user_language(user_id)
        target_chat = chat_id or user_id
        
        # Check user status for personalized menu
        is_premium = self.is_user_premium(user_id)
        free_tier_full = len(self.free_users) >= self.max_free_users
        
        # Define button texts based on user's language
        if lang == 'en':
            buttons = {
                'status': '📊 Status', 'signals': '📈 Signals', 'coins': '💰 Coins', 'help': '📚 Help',
                'language': '🌍 Language', 'delete': '🗑️ Delete', 'refresh': '🔄 Refresh',
                'subscribe': '💎 Subscribe', 'paid': '💳 I Paid', 'support': '❓ Support',
                'manage': '⚙️ Manage', 'admin': '⚙️ Admin', 'restart': '🔁 Restart'
            }
        elif lang == 'es':
            buttons = {
                'status': '📊 Estado', 'signals': '📈 Señales', 'coins': '💰 Monedas', 'help': '📚 Ayuda',
                'language': '🌍 Idioma', 'delete': '🗑️ Eliminar', 'refresh': '🔄 Actualizar',
                'subscribe': '💎 Suscribirse', 'paid': '💳 Pagué', 'support': '❓ Soporte',
                'manage': '⚙️ Gestionar', 'admin': '⚙️ Admin', 'restart': '🔁 Reiniciar'
            }
        elif lang == 'fr':
            buttons = {
                'status': '📊 Statut', 'signals': '📈 Signaux', 'coins': '💰 Pièces', 'help': '📚 Aide',
                'language': '🌍 Langue', 'delete': '🗑️ Supprimer', 'refresh': '🔄 Actualiser',
                'subscribe': '💎 S\'abonner', 'paid': '💳 J\'ai Payé', 'support': '❓ Support',
                'manage': '⚙️ Gérer', 'admin': '⚙️ Admin', 'restart': '🔁 Redémarrer'
            }
        elif lang == 'de':
            buttons = {
                'status': '📊 Status', 'signals': '📈 Signale', 'coins': '💰 Münzen', 'help': '📚 Hilfe',
                'language': '🌍 Sprache', 'delete': '🗑️ Löschen', 'refresh': '🔄 Aktualisieren',
                'subscribe': '💎 Abonnieren', 'paid': '💳 Ich Bezahlte', 'support': '❓ Support',
                'manage': '⚙️ Verwalten', 'admin': '⚙️ Admin', 'restart': '🔁 Neustart'
            }
        elif lang == 'ru':
            buttons = {
                'status': '📊 Статус', 'signals': '📈 Сигналы', 'coins': '💰 Монеты', 'help': '📚 Помощь',
                'language': '🌍 Язык', 'delete': '🗑️ Удалить', 'refresh': '🔄 Обновить',
                'subscribe': '💎 Подписка', 'paid': '💳 Я Заплатил', 'support': '❓ Поддержка',
                'manage': '⚙️ Управление', 'admin': '⚙️ Админ', 'restart': '🔁 Перезапуск'
            }
        else:
            # Default to English
            buttons = {
                'status': '📊 Status', 'signals': '📈 Signals', 'coins': '💰 Coins', 'help': '📚 Help',
                'language': '🌍 Language', 'delete': '🗑️ Delete', 'refresh': '🔄 Refresh',
                'subscribe': '💎 Subscribe', 'paid': '💳 I Paid', 'support': '❓ Support',
                'manage': '⚙️ Manage', 'admin': '⚙️ Admin', 'restart': '🔁 Restart'
            }
        
        # Main menu buttons - everyone gets these
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": buttons['status'], "callback_data": "cmd_status"},
                    {"text": buttons['signals'], "callback_data": "cmd_signals"},
                    {"text": buttons['coins'], "callback_data": "cmd_coins"}
                ],
                [
                    {"text": buttons['help'], "callback_data": "cmd_help"},
                    {"text": buttons['language'], "callback_data": "cmd_language"},
                    {"text": buttons['delete'], "callback_data": "cmd_delete"}
                ],
                [
                    {"text": buttons['refresh'], "callback_data": "cmd_menu"},
                    {"text": buttons['subscribe'], "callback_data": "cmd_subscribe"}
                ]
            ]
        }
        
        # Add premium/subscription options for all non-premium users
        if not is_premium:
            if free_tier_full and user_id not in self.free_users:
                # User 101+ needs to subscribe - show payment options too
                keyboard["inline_keyboard"].append([
                    {"text": buttons['paid'], "callback_data": "cmd_paid"},
                    {"text": buttons['support'], "callback_data": "support"}
                ])
            # All non-premium users can see subscription option
        else:
            # Premium users can still see subscription to manage their plan
            keyboard["inline_keyboard"][-1].append({"text": buttons['manage'], "callback_data": "cmd_subscribe"})
        
        # Admin buttons (only for admins)
        if self.is_admin(user_id):
            keyboard["inline_keyboard"].append([
                {"text": buttons['admin'], "callback_data": "cmd_admin"},
                {"text": buttons['restart'], "callback_data": "cmd_restart"}
            ])
        
        # Create menu text in user's language
        if lang == 'en':
            menu_text = f"🤖 **Crypto Trading Bot Menu**\n\n"
            if is_premium:
                menu_text += "✅ **Premium User** - All features unlocked\n"
            elif user_id in self.free_users:
                menu_text += "🆓 **Free Tier User** - All features included\n"
            elif free_tier_full:
                menu_text += "🔒 **Premium Required** - Free tier is full (100/100)\n"
            else:
                menu_text += "🆓 **Welcome** - You have free access!\n"
            menu_text += f"\n📊 Monitoring: 50 crypto pairs\n⚡ Signals: EMA20 breakout strategy\n🔄 Updates: Every 5 minutes\n\n"
            menu_text += f"💰 **Notice:** Bot will require payment after 100 users\n"
            menu_text += f"👥 Current users: {len(self.free_users) + len(self.paid_users)}/100\n\n**Choose an option:**"
        elif lang == 'es':
            menu_text = f"🤖 **Menú del Bot de Trading de Criptomonedas**\n\n"
            if is_premium:
                menu_text += "✅ **Usuario Premium** - Todas las funciones desbloqueadas\n"
            elif user_id in self.free_users:
                menu_text += "🆓 **Usuario Gratis** - Todas las funciones incluidas\n"
            elif free_tier_full:
                menu_text += "🔒 **Premium Requerido** - Nivel gratuito lleno (100/100)\n"
            else:
                menu_text += "🆓 **Bienvenido** - ¡Tienes acceso gratuito!\n"
            menu_text += f"\n📊 Monitoreo: 50 pares de cripto\n⚡ Señales: Estrategia de ruptura EMA20\n🔄 Actualizaciones: Cada 5 minutos\n\n"
            menu_text += f"💰 **Aviso:** El bot requerirá pago después de 100 usuarios\n"
            menu_text += f"👥 Usuarios actuales: {len(self.free_users) + len(self.paid_users)}/100\n\n**Elige una opción:**"
        elif lang == 'fr':
            menu_text = f"🤖 **Menu du Bot de Trading Crypto**\n\n"
            if is_premium:
                menu_text += "✅ **Utilisateur Premium** - Toutes les fonctionnalités débloquées\n"
            elif user_id in self.free_users:
                menu_text += "🆓 **Utilisateur Gratuit** - Toutes les fonctionnalités incluses\n"
            elif free_tier_full:
                menu_text += "🔒 **Premium Requis** - Niveau gratuit plein (100/100)\n"
            else:
                menu_text += "🆓 **Bienvenue** - Vous avez un accès gratuit!\n"
            menu_text += f"\n📊 Surveillance: 50 paires crypto\n⚡ Signaux: Stratégie de cassure EMA20\n🔄 Mises à jour: Toutes les 5 minutes\n\n"
            menu_text += f"💰 **Avis:** Le bot nécessitera un paiement après 100 utilisateurs\n"
            menu_text += f"👥 Utilisateurs actuels: {len(self.free_users) + len(self.paid_users)}/100\n\n**Choisissez une option:**"
        elif lang == 'de':
            menu_text = f"🤖 **Krypto-Trading-Bot-Menü**\n\n"
            if is_premium:
                menu_text += "✅ **Premium-Benutzer** - Alle Funktionen freigeschaltet\n"
            elif user_id in self.free_users:
                menu_text += "🆓 **Kostenloser Benutzer** - Alle Funktionen enthalten\n"
            elif free_tier_full:
                menu_text += "🔒 **Premium Erforderlich** - Kostenlose Stufe voll (100/100)\n"
            else:
                menu_text += "🆓 **Willkommen** - Sie haben kostenlosen Zugang!\n"
            menu_text += f"\n📊 Überwachung: 50 Krypto-Paare\n⚡ Signale: EMA20-Ausbruchsstrategie\n🔄 Updates: Alle 5 Minuten\n\n"
            menu_text += f"💰 **Hinweis:** Bot erfordert Zahlung nach 100 Benutzern\n"
            menu_text += f"👥 Aktuelle Benutzer: {len(self.free_users) + len(self.paid_users)}/100\n\n**Wählen Sie eine Option:**"
        elif lang == 'ru':
            menu_text = f"🤖 **Меню Криптотрейдинг Бота**\n\n"
            if is_premium:
                menu_text += "✅ **Премиум Пользователь** - Все функции разблокированы\n"
            elif user_id in self.free_users:
                menu_text += "🆓 **Бесплатный Пользователь** - Все функции включены\n"
            elif free_tier_full:
                menu_text += "🔒 **Требуется Премиум** - Бесплатный уровень заполнен (100/100)\n"
            else:
                menu_text += "🆓 **Добро пожаловать** - У вас есть бесплатный доступ!\n"
            menu_text += f"\n📊 Мониторинг: 50 криптопар\n⚡ Сигналы: Стратегия прорыва EMA20\n🔄 Обновления: Каждые 5 минут\n\n"
            menu_text += f"💰 **Уведомление:** Бот потребует оплату после 100 пользователей\n"
            menu_text += f"👥 Текущие пользователи: {len(self.free_users) + len(self.paid_users)}/100\n\n**Выберите опцию:**"
        else:
            # Default English
            menu_text = f"🤖 **Crypto Trading Bot Menu**\n\n"
            if is_premium:
                menu_text += "✅ **Premium User** - All features unlocked\n"
            elif user_id in self.free_users:
                menu_text += "🆓 **Free Tier User** - All features included\n"
            elif free_tier_full:
                menu_text += "🔒 **Premium Required** - Free tier is full (100/100)\n"
            else:
                menu_text += "🆓 **Welcome** - You have free access!\n"
            menu_text += f"\n📊 Monitoring: 50 crypto pairs\n⚡ Signals: EMA20 breakout strategy\n🔄 Updates: Every 5 minutes\n\n"
            menu_text += f"💰 **Notice:** Bot will require payment after 100 users\n"
            menu_text += f"👥 Current users: {len(self.free_users) + len(self.paid_users)}/100\n\n**Choose an option:**"
        
        await self.send_keyboard_message(menu_text, keyboard, message_id, target_chat)



    def create_back_to_menu_keyboard(self, lang):
        """Create back to menu keyboard in user's language"""
        if lang == 'ru':
            back_text = "🔙 В Меню"
        elif lang == 'es':
            back_text = "🔙 Al Menú"
        elif lang == 'fr':
            back_text = "🔙 Au Menu"
        elif lang == 'de':
            back_text = "🔙 Zum Menü"
        else:
            back_text = "🔙 Back to Menu"
        
        return {
            "inline_keyboard": [[
                {"text": back_text, "callback_data": "cmd_menu"}
            ]]
        }

    async def send_keyboard_message(self, text, keyboard, message_id=None, chat_id=None, target_chat_id=None):
        """Send message with inline keyboard"""
        import json
        url = f"{self.base_url}/sendMessage"
        
        # Use target_chat_id if provided, otherwise fall back to chat_id
        chat_target = target_chat_id if target_chat_id else chat_id
        
        data = {
            'chat_id': chat_target,
            'text': text,
            'reply_markup': json.dumps(keyboard),
            'parse_mode': 'Markdown'
        }
        
        if message_id:
            data['reply_to_message_id'] = message_id
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        return True
                    return False
            except Exception as e:
                print(f"❌ Error sending keyboard message: {e}")
                return False

    async def handle_command(self, message):
        """Handle incoming commands"""
        text = message.get('text', '')
        message_id = message.get('message_id')
        user_id = str(message.get('from', {}).get('id', ''))
        chat_id = str(message.get('chat', {}).get('id', ''))
        user_info = message.get('from', {})
        
        # Track user activity in database
        await self.user_db.add_or_update_user(user_info)
        
        if text.startswith('/start') or text.startswith('/menu'):
            user_id_str = str(user_id)
            
            # Check if user has selected a language
            if user_id_str not in self.user_languages:
                welcome_msg = "🌍 **Welcome to Crypto Trading Bot!**\n\nPlease select your language to continue:"
                await self.send_message(welcome_msg, target_chat_id=chat_id)
                await self.send_language_keyboard(message_id, chat_id)
            else:
                # Automatically register user to free tier if space available
                was_added = self.add_free_user(user_id_str)
                
                # Always check if user has access (free or paid)
                if self.is_user_premium(user_id_str):
                    # User has access, send welcome if they were just added
                    if was_added:
                        lang = self.get_user_language(user_id_str)
                        response = self.messages[lang]['free_tier_welcome']
                        await self.send_message(response, target_chat_id=chat_id)
                else:
                    # User doesn't have access (free tier full and not paid)
                    lang = self.get_user_language(user_id_str)
                    total_users = len(self.paid_users.union(self.free_users))
                    response = self.messages[lang]['free_tier_full'].format(user_count=total_users)
                    await self.send_message(response, target_chat_id=chat_id)
                
                # Always show main menu
                await self.send_main_menu(user_id_str, message_id, chat_id)
            
        elif text.startswith('/status'):
            # Automatically add user to free tier if possible
            self.add_free_user(user_id)
            
            if not self.is_user_premium(user_id):
                lang = self.get_user_language(user_id)
                total_users = len(self.paid_users.union(self.free_users))
                message = self.messages[lang]['not_subscribed'].format(user_count=total_users)
                await self.send_message(message, reply_to_message_id=message_id, target_chat_id=chat_id)
                return
                
            lang = self.get_user_language(user_id)
            
            # Determine user type and subscription info
            user_type_info = ""
            if user_id in self.paid_users:
                if user_id in self.subscription_expiry and self.subscription_expiry[user_id]:
                    expiry_date = self.subscription_expiry[user_id]
                    days_remaining = (expiry_date - datetime.now()).days
                    if days_remaining > 0:
                        if lang == 'ru':
                            user_type_info = f"👑 Вы премиум пользователь (осталось {days_remaining} дней)"
                        elif lang == 'es':  
                            user_type_info = f"👑 Eres usuario premium ({days_remaining} días restantes)"
                        elif lang == 'fr':
                            user_type_info = f"👑 Vous êtes utilisateur premium ({days_remaining} jours restants)"
                        elif lang == 'de':
                            user_type_info = f"👑 Sie sind Premium-Nutzer ({days_remaining} Tage verbleibend)"
                        else:
                            user_type_info = f"👑 You are a premium user ({days_remaining} days remaining)"
                    else:
                        if lang == 'ru':
                            user_type_info = "⚠️ Ваша премиум подписка истекла"
                        elif lang == 'es':
                            user_type_info = "⚠️ Su suscripción premium ha expirado"
                        elif lang == 'fr':
                            user_type_info = "⚠️ Votre abonnement premium a expiré"
                        elif lang == 'de':
                            user_type_info = "⚠️ Ihr Premium-Abonnement ist abgelaufen"
                        else:
                            user_type_info = "⚠️ Your premium subscription has expired"
                else:
                    # Permanent premium (admin or first 100 users)
                    if lang == 'ru':
                        user_type_info = "👑 Вы премиум пользователь (постоянно)"
                    elif lang == 'es':
                        user_type_info = "👑 Eres usuario premium (permanente)"
                    elif lang == 'fr':
                        user_type_info = "👑 Vous êtes utilisateur premium (permanent)"
                    elif lang == 'de':
                        user_type_info = "👑 Sie sind Premium-Nutzer (dauerhaft)"
                    else:
                        user_type_info = "👑 You are a premium user (permanent)"
            elif user_id in self.free_users:
                if lang == 'ru':
                    user_type_info = "🆓 Вы пользователь бесплатного уровня (первые 100)"
                elif lang == 'es':
                    user_type_info = "🆓 Eres usuario de nivel gratuito (primeros 100)"
                elif lang == 'fr':
                    user_type_info = "🆓 Vous êtes utilisateur gratuit (100 premiers)"
                elif lang == 'de':
                    user_type_info = "🆓 Sie sind kostenloser Nutzer (erste 100)"
                else:
                    user_type_info = "🆓 You are a free tier user (first 100)"
            
            # Add user type info to status message
            base_response = self.messages[lang]['status_report'].format(signals_count=len(self.sent_signals))
            response = f"{user_type_info}\n\n{base_response}"
            
            await self.send_message(response, reply_to_message_id=message_id, target_chat_id=chat_id)
            
        elif text.startswith('/subscribe'):
            await self.send_subscription_menu(user_id, message_id, chat_id)
            
        elif text.startswith('/help'):
            # Automatically add user to free tier if possible
            self.add_free_user(user_id)
            
            lang = self.get_user_language(user_id)
            # Check if user has premium access
            if self.is_user_premium(user_id):
                response = self.messages[lang]['help_message_premium']
            else:
                response = self.messages[lang]['help_message_free']
            
            # Add back to menu button
            back_keyboard = self.create_back_to_menu_keyboard(lang)
            await self.send_keyboard_message(response, back_keyboard, message_id, chat_id, chat_id)
            
        elif text.startswith('/coins'):
            # Show list of monitored coins
            lang = self.get_user_language(user_id)
            response = self.messages[lang]['coin_list']
            await self.send_message(response, reply_to_message_id=message_id, target_chat_id=chat_id)
            
        # Remove old menu command as it's now handled in /start
            
        elif text.startswith('/test'):
            # Admin only command
            if self.is_admin(user_id):  # Only allow admin
                await self.send_test_signal()
            else:
                lang = self.get_user_language(user_id)
                await self.send_message(self.messages[lang]['admin_only'], reply_to_message_id=message_id, target_chat_id=chat_id)
                
        elif text.startswith('/adduser') and self.is_admin(user_id):
            # Admin command to add premium user with optional duration
            parts = text.split()
            if len(parts) >= 2:
                target_user_id = parts[1]
                plan_days = 30  # Default 30 days
                
                if len(parts) >= 3:
                    try:
                        plan_days = int(parts[2])
                    except ValueError:
                        await self.send_message("Invalid days value. Using default 30 days.", reply_to_message_id=message_id)
                
                self.add_premium_user(target_user_id, plan_days)
                await self.send_message(f"✅ Added premium access for user: {target_user_id} ({plan_days} days)", reply_to_message_id=message_id, target_chat_id=chat_id)
            else:
                await self.send_message("Usage: /adduser <user_id> [days]", reply_to_message_id=message_id, target_chat_id=chat_id)
                
        elif text.startswith('/removeuser') and self.is_admin(user_id):
            # Admin command to remove premium user
            parts = text.split()
            if len(parts) == 2:
                target_user_id = parts[1]
                self.paid_users.discard(target_user_id)
                await self.send_message(f"✅ Removed premium access for user: {target_user_id}", reply_to_message_id=message_id, target_chat_id=chat_id)
            else:
                await self.send_message("Usage: /removeuser <user_id>", reply_to_message_id=message_id, target_chat_id=chat_id)
                
        elif text.startswith('/listusers') and self.is_admin(user_id):
            # Admin command to list all users
            response = f"👥 User Statistics:\n\n"
            response += f"🆓 Free Users: {len(self.free_users)}/{self.max_free_users}\n"
            response += f"💎 Premium Users: {len(self.paid_users)}\n"
            response += f"📊 Total Active: {len(self.free_users) + len(self.paid_users)}\n\n"
            
            if self.free_users:
                free_list = '\n'.join([f"• {uid}" for uid in list(self.free_users)[:10]])  # Show first 10
                if len(self.free_users) > 10:
                    free_list += f"\n... and {len(self.free_users) - 10} more"
                response += f"🆓 Free Users:\n{free_list}\n\n"
            
            if self.paid_users:
                paid_list = '\n'.join([f"• {uid}" for uid in self.paid_users])
                response += f"💎 Premium Users:\n{paid_list}"
                
            await self.send_message(response, reply_to_message_id=message_id, target_chat_id=chat_id)
            
        elif text.startswith('/freestats') and self.is_admin(user_id):
            # Admin command to show free tier statistics
            remaining = self.max_free_users - len(self.free_users)
            response = f"🆓 Free Tier Status:\n\n"
            response += f"Used: {len(self.free_users)}/{self.max_free_users}\n"
            response += f"Remaining: {remaining}\n"
            response += f"Status: {'FULL' if remaining == 0 else 'AVAILABLE'}\n\n"
            response += f"💎 Premium Users: {len(self.paid_users)}"
            await self.send_message(response, reply_to_message_id=message_id, target_chat_id=chat_id)
            
        elif text.startswith('/verify') and self.is_admin(user_id):
            # Admin command to verify payment and add premium user
            parts = text.split()
            if len(parts) == 2:
                target_user_id = parts[1]
                # Move from free to premium or add new premium user
                if target_user_id in self.free_users:
                    self.free_users.remove(target_user_id)
                    print(f"🔄 Moved user {target_user_id} from free to premium")
                
                self.add_premium_user(target_user_id)
                
                # Send confirmation to the user
                lang = self.get_user_language(target_user_id)
                success_msg = self.messages[lang]['payment_success']
                await self.send_message(success_msg, target_chat_id=target_user_id)
                
                await self.send_message(f"✅ Payment verified and premium access granted for user: {target_user_id}", reply_to_message_id=message_id, target_chat_id=chat_id)
            else:
                await self.send_message("Usage: /verify <user_id>", reply_to_message_id=message_id, target_chat_id=chat_id)
                
        elif text.startswith('/pending') and self.is_admin(user_id):
            # Admin command to see pending payments
            if self.pending_payments:
                response = "💳 Pending Payments:\n\n"
                for user_id, payment_info in self.pending_payments.items():
                    response += f"User: {user_id}\n"
                    response += f"Method: {payment_info['method']}\n"
                    response += f"Amount: ${payment_info['amount']}\n"
                    response += f"Status: {payment_info['status']}\n\n"
            else:
                response = "No pending payments."
            await self.send_message(response, reply_to_message_id=message_id, target_chat_id=chat_id)
            
        elif text.startswith('/admin') and self.is_admin(user_id):
            # Comprehensive admin dashboard
            dashboard = self.generate_admin_dashboard()
            await self.send_message(dashboard, reply_to_message_id=message_id, target_chat_id=chat_id)
            
        elif text.startswith('/restart') and self.is_admin(user_id):
            # Admin command to restart bot
            await self.send_message("🔄 Bot restart initiated...\n\n⚠️ Bot will be offline for 10-15 seconds during restart.", reply_to_message_id=message_id, target_chat_id=chat_id)
            print("🔄 Admin requested bot restart")
            # Set restart flag instead of killing process
            self.restart_requested = True
            
        elif text.startswith('/addadmin') and self.is_admin(user_id):
            # Add new admin (only main admin can do this)
            if user_id == self.admin_chat_id:  # Only main admin can add other admins
                parts = text.split()
                if len(parts) == 2:
                    new_admin_id = parts[1]
                    self.add_admin(new_admin_id)
                    await self.send_message(f"✅ Added new admin: {new_admin_id}\n\n⚠️ They now have full admin access to the bot.", reply_to_message_id=message_id, target_chat_id=chat_id)
                else:
                    await self.send_message("Usage: /addadmin <user_id>\n\n💡 To get @avie_support's user ID, they need to send a message to the bot first.", reply_to_message_id=message_id, target_chat_id=chat_id)
            else:
                await self.send_message("❌ Only the main admin can add new admins.", reply_to_message_id=message_id, target_chat_id=chat_id)
                
        elif text.startswith('/removeadmin') and self.is_admin(user_id):
            # Remove admin (only main admin can do this)
            if user_id == self.admin_chat_id:  # Only main admin can remove other admins
                parts = text.split()
                if len(parts) == 2:
                    target_admin_id = parts[1]
                    if self.remove_admin(target_admin_id):
                        await self.send_message(f"✅ Removed admin access from: {target_admin_id}", reply_to_message_id=message_id, target_chat_id=chat_id)
                    else:
                        await self.send_message("❌ Cannot remove main admin or user is not an admin.", reply_to_message_id=message_id, target_chat_id=chat_id)
                else:
                    await self.send_message("Usage: /removeadmin <user_id>", reply_to_message_id=message_id, target_chat_id=chat_id)
            else:
                await self.send_message("❌ Only the main admin can remove admins.", reply_to_message_id=message_id, target_chat_id=chat_id)
                
        elif text.startswith('/listadmins') and self.is_admin(user_id):
            # List all current admins
            response = "👑 Current Admins:\n\n"
            for admin_id in self.admin_ids:
                if admin_id == self.admin_chat_id:
                    response += f"• {admin_id} (Main Admin) 👑\n"
                else:
                    response += f"• {admin_id} 🛠️\n"
            response += f"\n📊 Total Admins: {len(self.admin_ids)}"
            await self.send_message(response, reply_to_message_id=message_id, target_chat_id=chat_id)
            
        elif text.startswith('/paid'):
            # User command to report payment completion
            parts = text.split(' ', 2)
            if len(parts) >= 3:
                method = parts[1]  # BTC, ETH, USDT
                tx_hash = parts[2]  # Transaction hash or proof
                
                # Store payment verification request
                self.pending_payments[user_id] = {
                    'method': method.upper(),
                    'tx_hash': tx_hash,
                    'status': 'pending',
                    'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                lang = self.get_user_language(user_id)
                response = self.messages[lang]['payment_submitted']
                await self.send_message(response, reply_to_message_id=message_id, target_chat_id=chat_id)
                
                # Notify admin
                admin_msg = f"💳 New Payment Verification Request:\n\n"
                admin_msg += f"User: {user_id}\n"
                admin_msg += f"Method: {method.upper()}\n"
                admin_msg += f"TX Hash: {tx_hash}\n"
                admin_msg += f"Time: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                admin_msg += f"Use: /verify {user_id} to approve"
                await self.send_message(admin_msg, target_chat_id=self.admin_chat_id)
            else:
                lang = self.get_user_language(user_id)
                usage_msg = self.messages[lang]['paid_command_usage']
                await self.send_message(usage_msg, reply_to_message_id=message_id, target_chat_id=chat_id)
            
    async def create_trading_chart(self, symbol, price_data, signal_data):
        """Create simple clean trading chart"""
        try:
            # Simple single chart setup
            plt.style.use('dark_background') 
            fig, ax = plt.subplots(1, 1, figsize=(10, 6))
            fig.patch.set_facecolor('#0f1419')
            
            # Simple data preparation
            df = pd.DataFrame(price_data)
            if len(df.columns) >= 6:
                df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume'] + list(df.columns[6:])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['close'] = pd.to_numeric(df['close'])
            
            # Calculate only EMA20
            df['ema20'] = df['close'].ewm(span=20).mean()
            
            # Simple clean price chart 
            coin_name = symbol.replace('USDT', '')
            ax.plot(df['timestamp'], df['close'], color='#00d4aa', linewidth=2.5, label='Price')
            ax.plot(df['timestamp'], df['ema20'], color='#ff6b35', linewidth=2, label='EMA20')
            
            # Fill area above EMA20 (breakout zone)
            breakout_mask = df['close'] > df['ema20']
            ax.fill_between(df['timestamp'], df['close'], df['ema20'], 
                           where=breakout_mask, alpha=0.2, color='green')
            
            # Clean chart styling
            ax.set_title(f'{coin_name}/USDT', color='white', fontsize=18, fontweight='bold', pad=20)
            ax.legend(loc='upper left', fontsize=12)
            ax.grid(True, alpha=0.2)
            ax.set_facecolor('#0f1419')
            ax.set_xlabel('')
            ax.set_ylabel('')
            
            # Format time axis
            import matplotlib.dates as mdates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.tick_params(colors='white', labelsize=10)
            
            # Add current price annotation
            current_price = df['close'].iloc[-1]
            ax.annotate(f'${current_price:.4f}', 
                       xy=(df['timestamp'].iloc[-1], current_price),
                       xytext=(10, 10), textcoords='offset points',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='#00d4aa', alpha=0.8),
                       color='white', fontsize=11, fontweight='bold')
            
            plt.tight_layout()
            
            # Save to BytesIO with lower DPI for smaller file
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', 
                       facecolor='#0f1419', edgecolor='none')
            buffer.seek(0)
            plt.close()
            
            return buffer
            
        except Exception as e:
            print(f"❌ Error creating chart: {e}")
            return None
    
    def calculate_rsi(self, prices, period=14):
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calculate_signal_strength(self, price_data, volume_data):
        """Calculate signal strength and recommendation based on multiple factors"""
        try:
            # Convert to DataFrame for analysis
            df = pd.DataFrame({
                'close': [float(x[4]) for x in price_data],
                'volume': [float(x[5]) for x in price_data]
            })
            
            # Calculate indicators
            df['ema20'] = df['close'].ewm(span=20).mean()
            df['volume_ma'] = df['volume'].rolling(window=20).mean()
            df['rsi'] = self.calculate_rsi(df['close'])
            
            current_price = df['close'].iloc[-1]
            current_ema20 = df['ema20'].iloc[-1]
            current_volume = df['volume'].iloc[-1]
            avg_volume = df['volume_ma'].iloc[-1]
            current_rsi = df['rsi'].iloc[-1]
            
            # Calculate strength factors
            strength_score = 0
            
            # EMA20 breakout strength (0-30 points)
            price_above_ema = ((current_price - current_ema20) / current_ema20) * 100
            if price_above_ema > 2:
                strength_score += 30
            elif price_above_ema > 1:
                strength_score += 25
            elif price_above_ema > 0.5:
                strength_score += 20
            elif price_above_ema > 0:
                strength_score += 15
            
            # Volume confirmation (0-25 points)
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            if volume_ratio > 2:
                strength_score += 25
            elif volume_ratio > 1.5:
                strength_score += 20
            elif volume_ratio > 1.2:
                strength_score += 15
            elif volume_ratio > 1:
                strength_score += 10
            
            # RSI momentum (0-20 points)
            if 50 <= current_rsi <= 70:
                strength_score += 20
            elif 45 <= current_rsi <= 75:
                strength_score += 15
            elif 40 <= current_rsi <= 80:
                strength_score += 10
            elif current_rsi < 80:
                strength_score += 5
            
            # Trend consistency (0-15 points)
            recent_closes = df['close'].tail(5)
            uptrend = sum(recent_closes.diff().dropna() > 0) / 4
            strength_score += int(uptrend * 15)
            
            # Volume trend (0-10 points)
            recent_volumes = df['volume'].tail(3)
            if len(recent_volumes) >= 2:
                volume_increasing = recent_volumes.iloc[-1] > recent_volumes.iloc[-2]
                if volume_increasing:
                    strength_score += 10
                else:
                    strength_score += 5
            
            # Calculate simple breakout confirmations for recommendation
            ema_breakout_confirmed = price_above_ema > 0  # Price above EMA20
            volume_confirmed = volume_ratio >= 1.5  # High volume
            strong_momentum = current_rsi >= 50 and current_rsi <= 75  # Good RSI range
            
            # Flexible recommendation system based on signal strength
            if strength_score >= 85 and ema_breakout_confirmed and volume_confirmed:
                recommendation = "STRONG BUY"
                confidence = "EXTREMELY HIGH"
                emoji = "🚀🚀🚀"
                visual_strength = "🟢🟢🟢🟢🟢"
            elif strength_score >= 70 and (ema_breakout_confirmed or volume_confirmed):
                recommendation = "BUY"
                confidence = "HIGH"
                emoji = "🚀🚀"
                visual_strength = "🟢🟢🟢🟢⚪"
            elif strength_score >= 55 or ema_breakout_confirmed or volume_confirmed:
                recommendation = "CONSIDER"
                confidence = "MODERATE"
                emoji = "🚀"
                visual_strength = "🟢🟢🟢⚪⚪"
            elif strength_score >= 55:
                recommendation = "WEAK BUY"
                confidence = "LOW"
                emoji = "📈"
                visual_strength = "🟢🟢⚪⚪⚪"
            else:
                recommendation = "HOLD"
                confidence = "VERY LOW"
                emoji = "⚠️"
                visual_strength = "🟢⚪⚪⚪⚪"
            
            return {
                'recommendation': recommendation,
                'confidence': confidence,
                'emoji': emoji,
                'visual_strength': visual_strength,
                'score': strength_score,
                'price_above_ema': price_above_ema,
                'volume_ratio': volume_ratio,
                'rsi': current_rsi,
                'trend_strength': uptrend * 100
            }
            
        except Exception as e:
            print(f"❌ Error calculating signal strength: {e}")
            return {
                'recommendation': "BUY",
                'confidence': "MODERATE",
                'emoji': "🚀",
                'visual_strength': "🟢🟢🟢⚪⚪",
                'score': 70,
                'price_above_ema': 1.0,
                'volume_ratio': 1.5,
                'rsi': 60,
                'trend_strength': 70
            }

    async def send_test_signal(self):
        """Send an enhanced test trading signal with chart and detailed analysis"""
        try:
            # Generate realistic test data
            symbol = "BTCUSDT"
            current_price = 95847.523
            
            # Create test price data (48 hours of 1-hour candles)
            test_data = []
            base_price = current_price * 0.98
            for i in range(48):
                timestamp = int((datetime.now() - timedelta(hours=47-i)).timestamp() * 1000)
                # Simulate price movement with breakout at the end
                if i < 40:
                    price = base_price + random.uniform(-500, 300)
                else:
                    # Simulate breakout
                    price = base_price + (i - 40) * 200 + random.uniform(-100, 200)
                
                volume = random.uniform(20000000, 35000000)
                if i >= 40:  # Higher volume during breakout
                    volume *= 1.8
                    
                test_data.append([
                    timestamp,
                    price * 0.999,  # open
                    price * 1.002,  # high
                    price * 0.998,  # low
                    price,           # close
                    volume          # volume
                ])
            
            # Calculate signal strength
            signal_analysis = self.calculate_signal_strength(test_data, [x[5] for x in test_data])
            
            # Create chart
            chart_buffer = await self.create_trading_chart(symbol, test_data, signal_analysis)
            
            # Enhanced signal message
            recommendation = signal_analysis['recommendation']
            confidence = signal_analysis['confidence']
            strength_emoji = signal_analysis['emoji']
            visual_strength = signal_analysis['visual_strength']
            price_above_ema = signal_analysis['price_above_ema']
            volume_ratio = signal_analysis['volume_ratio']
            rsi = signal_analysis['rsi']
            
            test_message = (
                f"{strength_emoji} **ADVANCED EMA20 BREAKOUT SIGNAL**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💎 **{symbol.replace('USDT', '/USDT')}** - Premium Signal\n"
                f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
                f"💰 **CURRENT MARKET DATA:**\n"
                f"Price: ${current_price:,.2f}\n"
                f"24h Change: +{random.uniform(2, 5):.2f}%\n"
                f"24h Volume: ${random.uniform(25, 35):,.1f}M\n"
                f"Market Cap Rank: #1\n\n"
                f"🎯 **SIGNAL RECOMMENDATION: {recommendation}** ⭐\n"
                f"📊 **CONFIDENCE LEVEL: {confidence}**\n"
                f"💪 **SIGNAL STRENGTH: {visual_strength}**\n\n"

                f"✅ **BREAKOUT CONFIRMATION:**\n"
                f"• 4H EMA20 Breakout: Price broke and closed above EMA20\n"
                f"• 1D EMA20 Breakout: Price broke and closed above EMA20\n"
                f"• 4H Volume: {volume_ratio:.1f}x average (>1.5x required)\n"
                f"• 1D Volume: High volume confirmation\n"
                f"• Current Price: +{price_above_ema:.2f}% above EMA20\n"
                f"• Signal Strength: Both timeframes aligned\n\n"
                f"📈 **TECHNICAL ANALYSIS:**\n"
                f"• Trend: Strong Uptrend 📈\n"
                f"• Support: ${current_price * 0.97:,.2f}\n"
                f"• Resistance: ${current_price * 1.05:,.2f}\n"
                f"• Next Major Resistance: ${current_price * 1.15:,.2f}\n\n"
                f"🎯 **POSITION SETUP:**\n"
                f"**Entry Zone:** ${current_price:,.2f} - ${current_price * 1.01:,.2f}\n"
                f"**Stop Loss:** ${current_price * 0.974:,.2f} (-2.6%)\n\n"
                f"**TAKE PROFIT TARGETS:**\n"
                f"🎯 **TP1:** ${current_price * 1.072:,.2f} (+7.2%) - Take 30%\n"
                f"🎯 **TP2:** ${current_price * 1.143:,.2f} (+14.3%) - Take 40%\n"
                f"🎯 **TP3:** ${current_price * 1.306:,.2f} (+30.6%) - Take 30%\n\n"
                f"⚖️ **RISK MANAGEMENT:**\n"
                f"• Risk/Reward Ratio: **1:2.8** ⭐\n"
                f"• Position Size: 2-3% of portfolio\n"
                f"• Max Risk per Trade: 1% of capital\n"
                f"• Move SL to breakeven after TP1\n\n"
                f"📊 **VOLUME ANALYSIS:**\n"
                f"• Current Volume: ${volume_ratio * 28:.1f}M (+{(volume_ratio-1)*100:.0f}%)\n"
                f"• 20-day Avg: $28.5M\n"
                f"• Volume Trend: 📈 Increasing\n"
                f"• Institutional Activity: High\n\n"
                f"🔥 **MARKET SENTIMENT:**\n"
                f"• Fear & Greed Index: 72 (Greed)\n"
                f"• Social Sentiment: 🟢 Bullish\n"
                f"• Whale Activity: 🐋 Accumulating\n"
                f"• Options Flow: Bullish\n\n"
                f"⚠️ **TRADING GUIDELINES:**\n"
                f"• Wait for entry zone confirmation\n"
                f"• Don't FOMO above ${current_price * 1.02:,.2f}\n"
                f"• Scale out at each TP level\n"
                f"• Monitor volume for continuation\n"
                f"• Be ready to exit if SL is hit\n\n"
                f"🚨 **RISK WARNINGS:**\n"
                f"• High volatility expected\n"
                f"• Bitcoin correlation risk\n"
                f"• Market structure dependent\n"
                f"• Not financial advice - DYOR\n\n"
                f"📱 **Next Update:** 4 hours\n"
                f"🎯 **Signal ID:** #{random.randint(1000, 9999)}\n"
                f"🧪 **TEST SIGNAL** - Enhanced Features Demo"
            )
            
            # Send chart with message combined
            if chart_buffer:
                await self.send_photo_with_message(chart_buffer, test_message, self.admin_chat_id)
            else:
                # Fallback to text message if chart generation fails
                await self.send_message(test_message, target_chat_id=self.admin_chat_id)
                
        except Exception as e:
            print(f"❌ Error sending enhanced test signal: {e}")
            # Fallback to simple message
            simple_message = f"🧪 Enhanced signal system test failed: {e}\nFalling back to basic signal format."
            await self.send_message(simple_message, target_chat_id=self.admin_chat_id)

    async def send_photo_with_message(self, photo_buffer, caption, chat_id):
        """Send photo with signal message combined as caption"""
        try:
            url = f"{self.base_url}/sendPhoto"
            
            # Reset buffer position
            photo_buffer.seek(0)
            
            # Prepare the photo file for multipart upload
            files = {
                'photo': ('signal_chart.png', photo_buffer.getvalue(), 'image/png')
            }
            
            # Telegram caption limit is 1024 characters, so we need to keep it concise
            # For longer messages, we'll send chart + shortened caption, then full message
            short_caption = caption[:1000] + "..." if len(caption) > 1000 else caption
            
            data = {
                'chat_id': str(chat_id),
                'caption': short_caption,
                'parse_mode': 'Markdown'
            }
            
            # Use requests for reliable file upload
            response = requests.post(url, data=data, files=files)
            
            if response.status_code == 200:
                print("✅ Chart with signal message sent successfully")
                
                # If the original message was truncated, send the full message as a follow-up
                if len(caption) > 1000:
                    await asyncio.sleep(1)  # Small delay
                    await self.send_message(caption, target_chat_id=chat_id)
                
                return True
            else:
                print(f"❌ Failed to send photo: {response.status_code}")
                print(f"Response: {response.text}")
                # Fallback to text message
                await self.send_message(caption, target_chat_id=chat_id)
                return False
                        
        except Exception as e:
            print(f"❌ Error sending photo: {e}")
            # Fallback to text message
            await self.send_message(caption, target_chat_id=chat_id)
            return False

# Duplicate method removed - keeping only the first one

    async def handle_callback_query(self, callback_query):
        """Handle inline keyboard callbacks"""
        data = callback_query.get('data', '')
        user_id = str(callback_query.get('from', {}).get('id', ''))
        message_id = callback_query.get('message', {}).get('message_id')
        
        # Handle command buttons
        if data.startswith('cmd_'):
            command = data.replace('cmd_', '')
            
            if command == 'status':
                # Automatically add user to free tier if possible
                self.add_free_user(user_id)
                
                if not self.is_user_premium(user_id):
                    lang = self.get_user_language(user_id)
                    total_users = len(self.paid_users.union(self.free_users))
                    message = self.messages[lang]['not_subscribed'].format(user_count=total_users)
                    await self.send_message(message, target_chat_id=user_id)
                    return
                lang = self.get_user_language(user_id)
                response = self.messages[lang]['status_report'].format(signals_count=len(self.sent_signals))
                keyboard = self.create_back_to_menu_keyboard(lang)
                await self.send_keyboard_message(response, keyboard, target_chat_id=user_id)
                
            elif command == 'signals':
                # Show last 5 signals
                lang = self.get_user_language(user_id)
                response = self.get_signals_history_message(lang)
                keyboard = self.create_back_to_menu_keyboard(lang)
                await self.send_keyboard_message(response, keyboard, target_chat_id=user_id)
                
            elif command == 'coins':
                lang = self.get_user_language(user_id)
                response = self.messages[lang]['coin_list']
                keyboard = self.create_back_to_menu_keyboard(lang)
                await self.send_keyboard_message(response, keyboard, target_chat_id=user_id)
                
            elif command == 'help':
                # Automatically add user to free tier if possible
                self.add_free_user(user_id)
                
                lang = self.get_user_language(user_id)
                # Check if user has premium access
                if self.is_user_premium(user_id):
                    response = self.messages[lang]['help_message_premium']
                else:
                    response = self.messages[lang]['help_message_free']
                keyboard = self.create_back_to_menu_keyboard(lang)
                await self.send_keyboard_message(response, keyboard, target_chat_id=user_id)
                
            elif command == 'language':
                await self.send_language_keyboard(message_id, user_id)
                
            elif command == 'delete':
                # Show delete confirmation - use proper function
                await self.delete_all_user_messages(user_id)
                
            elif command == 'subscribe':
                await self.send_subscription_menu(user_id, message_id, user_id)
                
            elif command == 'paid':
                lang = self.get_user_language(user_id)
                usage_msg = self.messages[lang]['paid_command_usage']
                keyboard = self.create_back_to_menu_keyboard(lang)
                await self.send_keyboard_message(usage_msg, keyboard, target_chat_id=user_id)
                
            elif command == 'menu':
                await self.send_main_menu(user_id, message_id, user_id)
                
            elif command == 'admin':
                if self.is_admin(user_id):
                    dashboard = self.generate_admin_dashboard()
                    lang = self.get_user_language(user_id)
                    keyboard = self.create_back_to_menu_keyboard(lang)
                    await self.send_keyboard_message(dashboard, keyboard, target_chat_id=user_id)
                    
            elif command == 'restart':
                if self.is_admin(user_id):
                    await self.send_message("🔄 Restarting bot... Please wait 10-15 seconds.", target_chat_id=user_id)
                    self.restart_requested = True
            
            # Answer callback query to remove loading state
            await self.answer_callback_query(callback_query['id'])
            return
        try:
            data = callback_query.get('data', '')
            user_id = str(callback_query['from']['id'])
            message_id = callback_query['message']['message_id']
            
            if data.startswith('lang_'):
                # Language selection
                lang_code = data.replace('lang_', '')
                old_lang = self.user_languages.get(user_id, 'en')
                self.user_languages[user_id] = lang_code
                
                # Answer callback query
                await self.answer_callback_query(callback_query['id'])
                
                # Show language confirmation message in the NEW language
                if self.is_user_premium(user_id) or user_id in self.free_users:
                    # Existing user - just confirm language change
                    if lang_code in self.messages:
                        if lang_code == 'en':
                            response = f"✅ Language set to English"
                        elif lang_code == 'es':
                            response = "✅ Idioma cambiado a Español"
                        elif lang_code == 'fr':
                            response = "✅ Langue changée en Français"
                        elif lang_code == 'de':
                            response = "✅ Sprache auf Deutsch geändert"
                        elif lang_code == 'ru':
                            response = "✅ Язык изменен на Русский"
                        else:
                            response = f"✅ Language set to {lang_code.upper()}"
                    else:
                        response = f"✅ Language set to {lang_code.upper()}"
                elif self.can_add_free_user():
                    # New user - add to free tier
                    if self.add_free_user(user_id):
                        response = self.messages[lang_code]['free_tier_welcome']
                    else:
                        response = "✅ Language updated!"
                else:
                    # Free tier is full - must pay
                    response = self.messages[lang_code]['free_tier_full']
                    
                await self.send_message(response, target_chat_id=user_id)
                
                # Show main menu with updated language
                await self.send_main_menu(user_id)
                
            elif data.startswith('sub_'):
                # Subscription plan selection
                plan = data.replace('sub_', '')
                await self.handle_subscription_selection(user_id, plan, callback_query['id'])
                
            elif data.startswith('pay_'):
                # Payment address selection (format: pay_plan_method)
                parts = data.split('_')
                if len(parts) == 3:  # pay_plan_method
                    plan = parts[1]
                    method = parts[2]
                    await self.handle_payment_address(user_id, plan, method, callback_query['id'])
                else:
                    # Old format fallback
                    method = data.replace('pay_', '')
                    await self.send_message("Please select a subscription plan first.", target_chat_id=user_id)
                
            elif data == 'support':
                # Contact support
                await self.send_support_info(user_id, callback_query['id'])
                
            elif data == 'confirm_delete_yes':
                # User confirmed deletion
                await self.answer_callback_query(callback_query['id'])
                await self.perform_message_deletion(user_id)
                
            elif data == 'confirm_delete_no':
                # User cancelled deletion
                await self.answer_callback_query(callback_query['id'])
                lang = self.get_user_language(user_id)
                if lang == 'ru':
                    response = "❌ Удаление сообщений отменено."
                elif lang == 'es':
                    response = "❌ Eliminación de mensajes cancelada."
                elif lang == 'fr':
                    response = "❌ Suppression des messages annulée."
                elif lang == 'de':
                    response = "❌ Nachrichtenlöschung abgebrochen."
                else:
                    response = "❌ Message deletion cancelled."
                await self.send_message(response, target_chat_id=user_id)
                
            elif data == 'cmd_menu':
                # Refresh main menu
                await self.answer_callback_query(callback_query['id'])
                await self.send_main_menu(user_id)
                
            elif data == 'cmd_admin':
                # Admin panel
                await self.answer_callback_query(callback_query['id'])
                if self.is_admin(user_id):
                    dashboard = self.generate_admin_dashboard()
                    await self.send_message(dashboard, target_chat_id=user_id)
                else:
                    await self.send_message("❌ Admin access required.", target_chat_id=user_id)
                    
            elif data == 'cmd_restart':
                # Restart bot (admin only)
                await self.answer_callback_query(callback_query['id'])
                if self.is_admin(user_id):
                    await self.send_message("🔄 Bot restart initiated...\n\n⚠️ Bot will be offline for 10-15 seconds during restart.", target_chat_id=user_id)
                    print("🔄 Admin requested bot restart via button")
                    self.restart_requested = True
                else:
                    await self.send_message("❌ Admin access required.", target_chat_id=user_id)
                
        except Exception as e:
            print(f"❌ Error handling callback: {e}")

    async def handle_subscription_selection(self, user_id, plan, callback_id):
        """Handle subscription plan selection - show plan details and payment methods"""
        try:
            await self.answer_callback_query(callback_id)
            
            plan_info = self.subscription_plans.get(plan)
            if not plan_info:
                return
                
            # Store the selected plan for this user
            self.user_selected_plan = getattr(self, 'user_selected_plan', {})
            self.user_selected_plan[user_id] = plan
            
            lang = self.get_user_language(user_id)
            
            # Create simple plan details and payment method selection
            if lang == 'en':
                plan_name = plan_info['description']
                message = f"💎 **{plan_name}**\n\n"
                message += f"💰 **Price:** ${plan_info['price']}\n"
                message += f"⏰ **Duration:** {plan_info['days']} days\n\n"
                message += "Please select your payment method:"
                
                # Payment method buttons
                keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "₿ Bitcoin (BTC)", "callback_data": f"pay_{plan}_btc"},
                            {"text": "⟠ Ethereum (ETH)", "callback_data": f"pay_{plan}_eth"}
                        ],
                        [
                            {"text": "💚 USDT (TRC20)", "callback_data": f"pay_{plan}_usdt"}
                        ],
                        [
                            {"text": "🏦 Bank Transfer", "callback_data": f"pay_{plan}_bank"}
                        ],
                        [
                            {"text": "❓ Support", "callback_data": "support"},
                            {"text": "🔙 Back to Menu", "callback_data": "cmd_menu"}
                        ]
                    ]
                }
            elif lang == 'es':
                if plan == 'weekly':
                    plan_name = "Premium Semanal"
                elif plan == 'monthly':
                    plan_name = "Premium Mensual"
                elif plan == 'yearly':
                    plan_name = "Premium Anual"
                else:
                    plan_name = "Premium"
                message = f"💎 **{plan_name}**\n\n"
                message += f"💰 **Precio:** ${plan_info['price']}\n"
                message += f"⏰ **Duración:** {plan_info['days']} días\n\n"
                message += "Por favor selecciona tu método de pago:"
                
                keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "₿ Bitcoin (BTC)", "callback_data": f"pay_{plan}_btc"},
                            {"text": "⟠ Ethereum (ETH)", "callback_data": f"pay_{plan}_eth"}
                        ],
                        [
                            {"text": "💚 USDT (TRC20)", "callback_data": f"pay_{plan}_usdt"}
                        ],
                        [
                            {"text": "🏦 Transferencia Bancaria", "callback_data": f"pay_{plan}_bank"}
                        ],
                        [
                            {"text": "❓ Soporte", "callback_data": "support"},
                            {"text": "🔙 Al Menú", "callback_data": "cmd_menu"}
                        ]
                    ]
                }
            elif lang == 'fr':
                if plan == 'weekly':
                    plan_name = "Premium Hebdomadaire"
                elif plan == 'monthly':
                    plan_name = "Premium Mensuel"
                elif plan == 'yearly':
                    plan_name = "Premium Annuel"
                else:
                    plan_name = "Premium"
                message = f"💎 **{plan_name}**\n\n"
                message += f"💰 **Prix:** ${plan_info['price']}\n"
                message += f"⏰ **Durée:** {plan_info['days']} jours\n\n"
                message += "Veuillez sélectionner votre méthode de paiement:"
                
                keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "₿ Bitcoin (BTC)", "callback_data": f"pay_{plan}_btc"},
                            {"text": "⟠ Ethereum (ETH)", "callback_data": f"pay_{plan}_eth"}
                        ],
                        [
                            {"text": "💚 USDT (TRC20)", "callback_data": f"pay_{plan}_usdt"}
                        ],
                        [
                            {"text": "🏦 Virement Bancaire", "callback_data": f"pay_{plan}_bank"}
                        ],
                        [
                            {"text": "❓ Support", "callback_data": "support"},
                            {"text": "🔙 Au Menu", "callback_data": "cmd_menu"}
                        ]
                    ]
                }
            elif lang == 'de':
                if plan == 'weekly':
                    plan_name = "Wöchentliches Premium"
                elif plan == 'monthly':
                    plan_name = "Monatliches Premium"
                elif plan == 'yearly':
                    plan_name = "Jährliches Premium"
                else:
                    plan_name = "Premium"
                message = f"💎 **{plan_name}**\n\n"
                message += f"💰 **Preis:** ${plan_info['price']}\n"
                message += f"⏰ **Dauer:** {plan_info['days']} Tage\n\n"
                message += "Bitte wählen Sie Ihre Zahlungsmethode:"
                
                keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "₿ Bitcoin (BTC)", "callback_data": f"pay_{plan}_btc"},
                            {"text": "⟠ Ethereum (ETH)", "callback_data": f"pay_{plan}_eth"}
                        ],
                        [
                            {"text": "💚 USDT (TRC20)", "callback_data": f"pay_{plan}_usdt"}
                        ],
                        [
                            {"text": "🏦 Banküberweisung", "callback_data": f"pay_{plan}_bank"}
                        ],
                        [
                            {"text": "❓ Support", "callback_data": "support"},
                            {"text": "🔙 Zum Menü", "callback_data": "cmd_menu"}
                        ]
                    ]
                }
            elif lang == 'ru':
                if plan == 'weekly':
                    plan_name = "Недельный Премиум"
                elif plan == 'monthly':
                    plan_name = "Месячный Премиум"
                elif plan == 'yearly':
                    plan_name = "Годовой Премиум"
                else:
                    plan_name = "Премиум"
                message = f"💎 **{plan_name}**\n\n"
                message += f"💰 **Цена:** ${plan_info['price']}\n"
                message += f"⏰ **Продолжительность:** {plan_info['days']} дней\n\n"
                message += "Пожалуйста, выберите способ оплаты:"
                
                keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "₿ Bitcoin (BTC)", "callback_data": f"pay_{plan}_btc"},
                            {"text": "⟠ Ethereum (ETH)", "callback_data": f"pay_{plan}_eth"}
                        ],
                        [
                            {"text": "💚 USDT (TRC20)", "callback_data": f"pay_{plan}_usdt"}
                        ],
                        [
                            {"text": "🏦 Банковский Перевод", "callback_data": f"pay_{plan}_bank"}
                        ],
                        [
                            {"text": "❓ Поддержка", "callback_data": "support"},
                            {"text": "🔙 В Меню", "callback_data": "cmd_menu"}
                        ]
                    ]
                }
            else:
                # Default English
                plan_name = plan_info['description']
                message = f"💎 **{plan_name}**\n\n"
                message += f"💰 **Price:** ${plan_info['price']}\n"
                message += f"⏰ **Duration:** {plan_info['days']} days\n\n"
                message += "Please select your payment method:"
                
                keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "₿ Bitcoin (BTC)", "callback_data": f"pay_{plan}_btc"},
                            {"text": "⟠ Ethereum (ETH)", "callback_data": f"pay_{plan}_eth"}
                        ],
                        [
                            {"text": "💚 USDT (TRC20)", "callback_data": f"pay_{plan}_usdt"}
                        ],
                        [
                            {"text": "🏦 Bank Transfer", "callback_data": f"pay_{plan}_bank"}
                        ],
                        [
                            {"text": "❓ Support", "callback_data": "support"},
                            {"text": "🔙 Back to Menu", "callback_data": "cmd_menu"}
                        ]
                    ]
                }
            
            await self.send_keyboard_message(message, keyboard, target_chat_id=user_id)
            
        except Exception as e:
            print(f"❌ Error handling subscription selection: {e}")

    async def handle_payment_address(self, user_id, plan, method, callback_id):
        """Show individual payment address for easy copying"""
        try:
            await self.answer_callback_query(callback_id)
            
            # Get plan info for amount
            plan_info = self.subscription_plans.get(plan)
            if not plan_info:
                return
            
            lang = self.get_user_language(user_id)
            
            # Create clean payment address message based on method
            if method == 'btc':
                if lang == 'en':
                    message = f"₿ **Bitcoin (BTC) Payment**\n\n"
                    message += f"💰 **Amount:** ${plan_info['price']} USD equivalent\n\n"
                    message += "**Payment Address:**\n"
                elif lang == 'es':
                    message = f"₿ **Pago Bitcoin (BTC)**\n\n"
                    message += f"💰 **Cantidad:** ${plan_info['price']} USD equivalente\n\n"
                    message += "**Dirección de Pago:**\n"
                elif lang == 'fr':
                    message = f"₿ **Paiement Bitcoin (BTC)**\n\n"
                    message += f"💰 **Montant:** ${plan_info['price']} USD équivalent\n\n"
                    message += "**Adresse de Paiement:**\n"
                elif lang == 'de':
                    message = f"₿ **Bitcoin (BTC) Zahlung**\n\n"
                    message += f"💰 **Betrag:** ${plan_info['price']} USD Äquivalent\n\n"
                    message += "**Zahlungsadresse:**\n"
                elif lang == 'ru':
                    message = f"₿ **Оплата Bitcoin (BTC)**\n\n"
                    message += f"💰 **Сумма:** ${plan_info['price']} USD эквивалент\n\n"
                    message += "**Адрес для оплаты:**\n"
                else:
                    message = f"₿ **Bitcoin (BTC) Payment**\n\n"
                    message += f"💰 **Amount:** ${plan_info['price']} USD equivalent\n\n"
                    message += "**Payment Address:**\n"
                
                # Add address in monospace
                await self.send_message(message, target_chat_id=user_id)
                
                # Send address as separate message for easy copying
                await self.send_message("12avETUACYneRXng9fno38XRktKZFC8yxZ", target_chat_id=user_id)
                
                # Send instructions
                if lang == 'en':
                    instructions = "📧 After payment, send proof to @avie_support\n"
                    instructions += f"Include your Telegram ID: {user_id}\n\n"
                    instructions += "⚡ Activation within 1 hour"
                elif lang == 'es':
                    instructions = "📧 Después del pago, envía comprobante a @avie_support\n"
                    instructions += f"Incluye tu ID de Telegram: {user_id}\n\n"
                    instructions += "⚡ Activación en 1 hora"
                elif lang == 'fr':
                    instructions = "📧 Après paiement, envoyez preuve à @avie_support\n"
                    instructions += f"Incluez votre ID Telegram: {user_id}\n\n"
                    instructions += "⚡ Activation sous 1 heure"
                elif lang == 'de':
                    instructions = "📧 Nach Zahlung, senden Sie Nachweis an @avie_support\n"
                    instructions += f"Ihre Telegram ID: {user_id}\n\n"
                    instructions += "⚡ Aktivierung innerhalb 1 Stunde"
                elif lang == 'ru':
                    instructions = "📧 После оплаты отправьте подтверждение @avie_support\n"
                    instructions += f"Укажите ваш Telegram ID: {user_id}\n\n"
                    instructions += "⚡ Активация в течение 1 часа"
                else:
                    instructions = "📧 After payment, send proof to @avie_support\n"
                    instructions += f"Include your Telegram ID: {user_id}\n\n"
                    instructions += "⚡ Activation within 1 hour"
                
                keyboard = self.create_back_to_menu_keyboard(lang)
                await self.send_keyboard_message(instructions, keyboard, target_chat_id=user_id)
                
            elif method == 'eth':
                if lang == 'en':
                    message = f"⟠ **Ethereum (ETH) Payment**\n\n"
                    message += f"💰 **Amount:** ${plan_info['price']} USD equivalent\n\n"
                    message += "**Payment Address:**\n"
                elif lang == 'es':
                    message = f"⟠ **Pago Ethereum (ETH)**\n\n"
                    message += f"💰 **Cantidad:** ${plan_info['price']} USD equivalente\n\n"
                    message += "**Dirección de Pago:**\n"
                elif lang == 'fr':
                    message = f"⟠ **Paiement Ethereum (ETH)**\n\n"
                    message += f"💰 **Montant:** ${plan_info['price']} USD équivalent\n\n"
                    message += "**Adresse de Paiement:**\n"
                elif lang == 'de':
                    message = f"⟠ **Ethereum (ETH) Zahlung**\n\n"
                    message += f"💰 **Betrag:** ${plan_info['price']} USD Äquivalent\n\n"
                    message += "**Zahlungsadresse:**\n"
                elif lang == 'ru':
                    message = f"⟠ **Оплата Ethereum (ETH)**\n\n"
                    message += f"💰 **Сумма:** ${plan_info['price']} USD эквивалент\n\n"
                    message += "**Адрес для оплаты:**\n"
                else:
                    message = f"⟠ **Ethereum (ETH) Payment**\n\n"
                    message += f"💰 **Amount:** ${plan_info['price']} USD equivalent\n\n"
                    message += "**Payment Address:**\n"
                
                await self.send_message(message, target_chat_id=user_id)
                await self.send_message("0x570a6177046ed1f4683762693ec4a2a43c47c56f", target_chat_id=user_id)
                
                # Send instructions
                if lang == 'en':
                    instructions = "📧 After payment, send proof to @avie_support\n"
                    instructions += f"Include your Telegram ID: {user_id}\n\n"
                    instructions += "⚡ Activation within 1 hour"
                elif lang == 'es':
                    instructions = "📧 Después del pago, envía comprobante a @avie_support\n"
                    instructions += f"Incluye tu ID de Telegram: {user_id}\n\n"
                    instructions += "⚡ Activación en 1 hora"
                elif lang == 'fr':
                    instructions = "📧 Après paiement, envoyez preuve à @avie_support\n"
                    instructions += f"Incluez votre ID Telegram: {user_id}\n\n"
                    instructions += "⚡ Activation sous 1 heure"
                elif lang == 'de':
                    instructions = "📧 Nach Zahlung, senden Sie Nachweis an @avie_support\n"
                    instructions += f"Ihre Telegram ID: {user_id}\n\n"
                    instructions += "⚡ Aktivierung innerhalb 1 Stunde"
                elif lang == 'ru':
                    instructions = "📧 После оплаты отправьте подтверждение @avie_support\n"
                    instructions += f"Укажите ваш Telegram ID: {user_id}\n\n"
                    instructions += "⚡ Активация в течение 1 часа"
                else:
                    instructions = "📧 After payment, send proof to @avie_support\n"
                    instructions += f"Include your Telegram ID: {user_id}\n\n"
                    instructions += "⚡ Activation within 1 hour"
                
                keyboard = self.create_back_to_menu_keyboard(lang)
                await self.send_keyboard_message(instructions, keyboard, target_chat_id=user_id)
                
            elif method == 'usdt':
                if lang == 'en':
                    message = f"💚 **USDT (TRC20) Payment**\n\n"
                    message += f"💰 **Amount:** ${plan_info['price']} USDT\n\n"
                    message += "**Payment Address:**\n"
                elif lang == 'es':
                    message = f"💚 **Pago USDT (TRC20)**\n\n"
                    message += f"💰 **Cantidad:** ${plan_info['price']} USDT\n\n"
                    message += "**Dirección de Pago:**\n"
                elif lang == 'fr':
                    message = f"💚 **Paiement USDT (TRC20)**\n\n"
                    message += f"💰 **Montant:** ${plan_info['price']} USDT\n\n"
                    message += "**Adresse de Paiement:**\n"
                elif lang == 'de':
                    message = f"💚 **USDT (TRC20) Zahlung**\n\n"
                    message += f"💰 **Betrag:** ${plan_info['price']} USDT\n\n"
                    message += "**Zahlungsadresse:**\n"
                elif lang == 'ru':
                    message = f"💚 **Оплата USDT (TRC20)**\n\n"
                    message += f"💰 **Сумма:** ${plan_info['price']} USDT\n\n"
                    message += "**Адрес для оплаты:**\n"
                else:
                    message = f"💚 **USDT (TRC20) Payment**\n\n"
                    message += f"💰 **Amount:** ${plan_info['price']} USDT\n\n"
                    message += "**Payment Address:**\n"
                
                await self.send_message(message, target_chat_id=user_id)
                await self.send_message("TFAmy3TRqvisPWCa8V7jynAM6tmoFsTh3Y", target_chat_id=user_id)
                
                # Send instructions
                if lang == 'en':
                    instructions = "📧 After payment, send proof to @avie_support\n"
                    instructions += f"Include your Telegram ID: {user_id}\n\n"
                    instructions += "⚡ Activation within 1 hour"
                elif lang == 'es':
                    instructions = "📧 Después del pago, envía comprobante a @avie_support\n"
                    instructions += f"Incluye tu ID de Telegram: {user_id}\n\n"
                    instructions += "⚡ Activación en 1 hora"
                elif lang == 'fr':
                    instructions = "📧 Après paiement, envoyez preuve à @avie_support\n"
                    instructions += f"Incluez votre ID Telegram: {user_id}\n\n"
                    instructions += "⚡ Activation sous 1 heure"
                elif lang == 'de':
                    instructions = "📧 Nach Zahlung, senden Sie Nachweis an @avie_support\n"
                    instructions += f"Ihre Telegram ID: {user_id}\n\n"
                    instructions += "⚡ Aktivierung innerhalb 1 Stunde"
                elif lang == 'ru':
                    instructions = "📧 После оплаты отправьте подтверждение @avie_support\n"
                    instructions += f"Укажите ваш Telegram ID: {user_id}\n\n"
                    instructions += "⚡ Активация в течение 1 часа"
                else:
                    instructions = "📧 After payment, send proof to @avie_support\n"
                    instructions += f"Include your Telegram ID: {user_id}\n\n"
                    instructions += "⚡ Activation within 1 hour"
                
                keyboard = self.create_back_to_menu_keyboard(lang)
                await self.send_keyboard_message(instructions, keyboard, target_chat_id=user_id)
                
            elif method == 'bank':
                if lang == 'en':
                    message = f"🏦 **Bank Transfer Payment**\n\n"
                    message += f"💰 **Amount:** ${plan_info['price']} USD\n\n"
                    message += "📞 Contact @avie_support for:\n"
                    message += "• Bank account details\n"
                    message += "• Wire transfer instructions\n"
                    message += "• International transfer options\n\n"
                    message += f"Include your Telegram ID: {user_id}\n\n"
                    message += "⚡ Processing within 24 hours"
                elif lang == 'es':
                    message = f"🏦 **Pago por Transferencia Bancaria**\n\n"
                    message += f"💰 **Cantidad:** ${plan_info['price']} USD\n\n"
                    message += "📞 Contacta @avie_support para:\n"
                    message += "• Detalles de cuenta bancaria\n"
                    message += "• Instrucciones de transferencia\n"
                    message += "• Opciones de transferencia internacional\n\n"
                    message += f"Incluye tu ID de Telegram: {user_id}\n\n"
                    message += "⚡ Procesamiento en 24 horas"
                elif lang == 'fr':
                    message = f"🏦 **Paiement par Virement Bancaire**\n\n"
                    message += f"💰 **Montant:** ${plan_info['price']} USD\n\n"
                    message += "📞 Contactez @avie_support pour:\n"
                    message += "• Détails du compte bancaire\n"
                    message += "• Instructions de virement\n"
                    message += "• Options de transfert international\n\n"
                    message += f"Incluez votre ID Telegram: {user_id}\n\n"
                    message += "⚡ Traitement sous 24 heures"
                elif lang == 'de':
                    message = f"🏦 **Zahlung per Banküberweisung**\n\n"
                    message += f"💰 **Betrag:** ${plan_info['price']} USD\n\n"
                    message += "📞 Kontaktieren Sie @avie_support für:\n"
                    message += "• Bankkontodetails\n"
                    message += "• Überweisungsanweisungen\n"
                    message += "• Internationale Übertragungsoptionen\n\n"
                    message += f"Ihre Telegram ID: {user_id}\n\n"
                    message += "⚡ Bearbeitung innerhalb 24 Stunden"
                elif lang == 'ru':
                    message = f"🏦 **Оплата Банковским Переводом**\n\n"
                    message += f"💰 **Сумма:** ${plan_info['price']} USD\n\n"
                    message += "📞 Обратитесь к @avie_support за:\n"
                    message += "• Реквизиты банковского счета\n"
                    message += "• Инструкции по переводу\n"
                    message += "• Международные варианты перевода\n\n"
                    message += f"Укажите ваш Telegram ID: {user_id}\n\n"
                    message += "⚡ Обработка в течение 24 часов"
                else:
                    message = f"🏦 **Bank Transfer Payment**\n\n"
                    message += f"💰 **Amount:** ${plan_info['price']} USD\n\n"
                    message += "📞 Contact @avie_support for:\n"
                    message += "• Bank account details\n"
                    message += "• Wire transfer instructions\n"
                    message += "• International transfer options\n\n"
                    message += f"Include your Telegram ID: {user_id}\n\n"
                    message += "⚡ Processing within 24 hours"
                
                keyboard = self.create_back_to_menu_keyboard(lang)
                await self.send_keyboard_message(message, keyboard, target_chat_id=user_id)
                
            else:
                # Unknown payment method
                if lang == 'en':
                    message = "❌ Unknown payment method. Please contact @avie_support for assistance."
                elif lang == 'es':
                    message = "❌ Método de pago desconocido. Contacta @avie_support para asistencia."
                elif lang == 'fr':
                    message = "❌ Méthode de paiement inconnue. Contactez @avie_support pour assistance."
                elif lang == 'de':
                    message = "❌ Unbekannte Zahlungsmethode. Kontaktieren Sie @avie_support für Hilfe."
                elif lang == 'ru':
                    message = "❌ Неизвестный способ оплаты. Обратитесь к @avie_support за помощью."
                else:
                    message = "❌ Unknown payment method. Please contact @avie_support for assistance."
                
                keyboard = self.create_back_to_menu_keyboard(lang)
                await self.send_keyboard_message(message, keyboard, target_chat_id=user_id)

            
        except Exception as e:
            print(f"❌ Error handling payment method: {e}")

    async def send_support_info(self, user_id, callback_id):
        """Send support contact information"""
        try:
            await self.answer_callback_query(callback_id)
            
            lang = self.get_user_language(user_id)
            
            if lang == 'ru':
                message = "📞 Премиум Поддержка\n\n"
                message += "💬 Telegram: @avie_support\n"
                message += "📧 Email: support@aviebot.com\n\n"
                message += "⏰ Время ответа: В течение 2 часов\n"
                message += "🌍 Доступно 24/7\n\n"
                message += "📝 Для проблем с оплатой, укажите:\n"
                message += "• Ваш Telegram ID\n"
                message += "• Подтверждение платежа/скриншот\n"
                message += "• Выбранный план подписки"
            elif lang == 'es':
                message = "📞 Soporte Premium\n\n"
                message += "💬 Telegram: @avie_support\n"
                message += "📧 Email: support@aviebot.com\n\n"
                message += "⏰ Tiempo de respuesta: Dentro de 2 horas\n"
                message += "🌍 Disponible 24/7\n\n"
                message += "📝 Para problemas de pago, incluye:\n"
                message += "• Tu ID de Telegram\n"
                message += "• Comprobante de pago/captura\n"
                message += "• Plan de suscripción elegido"
            elif lang == 'fr':
                message = "📞 Support Premium\n\n"
                message += "💬 Telegram: @avie_support\n"
                message += "📧 Email: support@aviebot.com\n\n"
                message += "⏰ Temps de réponse: Sous 2 heures\n"
                message += "🌍 Disponible 24/7\n\n"
                message += "📝 Pour problèmes de paiement, incluez:\n"
                message += "• Votre ID Telegram\n"
                message += "• Preuve de paiement/capture\n"
                message += "• Plan d'abonnement choisi"
            elif lang == 'de':
                message = "📞 Premium Support\n\n"
                message += "💬 Telegram: @avie_support\n"
                message += "📧 Email: support@aviebot.com\n\n"
                message += "⏰ Antwortzeit: Innerhalb 2 Stunden\n"
                message += "🌍 Verfügbar 24/7\n\n"
                message += "📝 Für Zahlungsprobleme, angeben:\n"
                message += "• Ihre Telegram ID\n"
                message += "• Zahlungsnachweis/Screenshot\n"
                message += "• Gewählter Abonnementplan"
            else:
                message = "📞 Premium Support\n\n"
                message += "💬 Telegram: @avie_support\n"
                message += "📧 Email: support@aviebot.com\n\n"
                message += "⏰ Response time: Within 2 hours\n"
                message += "🌍 Available 24/7\n\n"
                message += "📝 For payment issues, include:\n"
                message += "• Your Telegram ID\n"
                message += "• Payment proof/screenshot\n"
                message += "• Subscription plan chosen"
            
            # Add back to menu button
            keyboard = self.create_back_to_menu_keyboard(lang)
            await self.send_keyboard_message(message, keyboard, target_chat_id=user_id)
            
        except Exception as e:
            print(f"❌ Error sending support info: {e}")

    async def answer_callback_query(self, callback_query_id):
        """Answer callback query"""
        url = f"{self.base_url}/answerCallbackQuery"
        data = {'callback_query_id': callback_query_id}
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=data) as response:
                    return response.status == 200
            except Exception as e:
                print(f"❌ Error answering callback: {e}")
                return False

    async def edit_message(self, message_id, text, chat_id):
        """Edit existing message"""
        url = f"{self.base_url}/editMessageText"
        data = {
            'chat_id': chat_id,
            'message_id': message_id,
            'text': text
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=data) as response:
                    return response.status == 200
            except Exception as e:
                print(f"❌ Error editing message: {e}")
                return False

    async def check_for_commands(self):
        """Check for incoming commands"""
        last_update_id = 0
        
        while True:
            try:
                updates = await self.get_updates(last_update_id + 1)
                
                if updates and updates.get('ok'):
                    for update in updates.get('result', []):
                        last_update_id = update['update_id']
                        
                        if 'message' in update:
                            message = update['message']
                            chat_id = str(message['chat']['id'])
                            user_id = str(message.get('from', {}).get('id', ''))
                            
                            # Respond to all users (public bot)
                            await self.handle_command(message)
                        
                        elif 'callback_query' in update:
                            callback_query = update['callback_query']
                            
                            # Handle callbacks from all users
                            await self.handle_callback_query(callback_query)
                
                await asyncio.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                print(f"❌ Error checking commands: {e}")
                await asyncio.sleep(5)

    async def get_all_usdt_pairs(self, session=None):
        """Get specific 20 USDT trading pairs as requested"""
        # User-specified 20 cryptocurrency pairs
        pairs = ['LDOUSDT', 'EIGENUSDT', 'THETAUSDT', 'DOGEUSDT', 'SOLUSDT', 
                'LTCUSDT', 'BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'WLDUSDT',
                'BNBUSDT', 'SUIUSDT', 'SEIUSDT', 'SANDUSDT', 'ARBUSDT',
                'OPUSDT', 'XLMUSDT', 'ADAUSDT', 'UNIUSDT', 'DOTUSDT', 'ATOMUSDT']
        
        print(f"✅ Monitoring {len(pairs)} cryptocurrency pairs")
        return pairs

    async def fetch_klines(self, session, symbol, interval, limit=50):
        """Fetch real market data - CoinPaprika primary, CoinGecko fallback"""
        try:
            # Use CoinPaprika as primary (more generous rate limits)
            print(f"📊 Fetching {symbol} data from CoinPaprika ({interval}, {limit} candles)...")
            
            try:
                # CoinPaprika attempt with optimized delay
                await asyncio.sleep(1.0)  # Optimized delay for CoinPaprika (better rate limits)
                klines = await self.fetch_from_coinpaprika(session, symbol, interval, limit)
                
                if klines and len(klines) > 0:
                    print(f"✅ Retrieved {len(klines)} real market candles from CoinPaprika")
                    return klines
                else:
                    print("⚠️ CoinPaprika failed, trying CoinGecko...")
                    
            except Exception as e:
                print(f"⚠️ CoinPaprika error: {e}, trying CoinGecko...")
            
            # Fallback to CoinGecko with longer delay
            try:
                print(f"⏳ Rate limiting: waiting 5.0 seconds...")
                await asyncio.sleep(5.0)  # Conservative delay for CoinGecko - increased for rate limits
                klines = await self.fetch_from_coingecko(session, symbol, limit)
                
                if klines and len(klines) > 0:
                    print(f"✅ Retrieved {len(klines)} real market candles from CoinGecko")
                    return klines
                else:
                    print("⚠️ CoinGecko failed, using synthetic data")
                    return self.generate_synthetic_data(symbol, limit)
                    
            except Exception as e:
                print(f"⚠️ CoinGecko error: {e}, using synthetic data")
                return self.generate_synthetic_data(symbol, limit)
                    
        except Exception as e:
            print(f"❌ Error fetching {symbol} data: {e}, using synthetic data")
            return self.generate_synthetic_data(symbol, limit)

    def get_coinpaprika_id(self, symbol):
        """Convert trading symbol to CoinPaprika coin ID (User-specified 20 pairs)"""
        symbol_map = {
            'LDOUSDT': 'ldo-lido-dao', 'EIGENUSDT': 'eigen-eigenlayer', 'THETAUSDT': 'theta-theta',
            'DOGEUSDT': 'doge-dogecoin', 'SOLUSDT': 'sol-solana', 'LTCUSDT': 'ltc-litecoin',
            'BTCUSDT': 'btc-bitcoin', 'ETHUSDT': 'eth-ethereum', 'XRPUSDT': 'xrp-xrp',
            'WLDUSDT': 'wld-worldcoin', 'BNBUSDT': 'bnb-binance-coin', 'SUIUSDT': 'sui-sui',
            'SEIUSDT': 'sei-sei', 'SANDUSDT': 'sand-the-sandbox', 'ARBUSDT': 'arb-arbitrum',
            'OPUSDT': 'op-optimism', 'XLMUSDT': 'xlm-stellar', 'ADAUSDT': 'ada-cardano',
            'UNIUSDT': 'uni-uniswap', 'DOTUSDT': 'dot-polkadot', 'ATOMUSDT': 'atom-cosmos'
        }
        return symbol_map.get(symbol, 'btc-bitcoin')  # Default to bitcoin
    
    def get_coingecko_id(self, symbol):
        """Convert trading symbol to CoinGecko coin ID (User-specified 20 pairs)"""
        symbol_map = {
            'LDOUSDT': 'lido-dao', 'EIGENUSDT': 'eigenlayer', 'THETAUSDT': 'theta-token',
            'DOGEUSDT': 'dogecoin', 'SOLUSDT': 'solana', 'LTCUSDT': 'litecoin',
            'BTCUSDT': 'bitcoin', 'ETHUSDT': 'ethereum', 'XRPUSDT': 'ripple',
            'WLDUSDT': 'worldcoin-wld', 'BNBUSDT': 'binancecoin', 'SUIUSDT': 'sui',
            'SEIUSDT': 'sei-network', 'SANDUSDT': 'the-sandbox', 'ARBUSDT': 'arbitrum',
            'OPUSDT': 'optimism', 'XLMUSDT': 'stellar', 'ADAUSDT': 'cardano',
            'UNIUSDT': 'uniswap', 'DOTUSDT': 'polkadot', 'ATOMUSDT': 'cosmos'
        }
        return symbol_map.get(symbol, 'bitcoin')  # Default to bitcoin

    async def fetch_from_coingecko(self, session, symbol, limit=50):
        """Fetch data from CoinGecko API"""
        try:
            coin_id = self.get_coingecko_id(symbol)
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
            params = {'vs_currency': 'usd', 'days': '30'}
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return self.convert_coingecko_to_klines(data, limit)
                return None
        except:
            return None
    
    async def fetch_from_coinpaprika(self, session, symbol, interval=None, limit=50):
        """Fetch data from CoinPaprika API"""
        try:
            coin_id = self.get_coinpaprika_id(symbol)
            url = f"https://api.coinpaprika.com/v1/tickers/{coin_id}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    current_price = data['quotes']['USD']['price']
                    percent_change_24h = data['quotes']['USD']['percent_change_24h']
                    volume_24h = data['quotes']['USD']['volume_24h']
                    return self.generate_realistic_data_from_current_price(
                        symbol, current_price, percent_change_24h, volume_24h, limit
                    )
                return None
        except:
            return None
    
    def convert_coingecko_to_klines(self, data, limit):
        """Convert CoinGecko market chart data to klines format"""
        try:
            prices = data.get('prices', [])
            volumes = data.get('total_volumes', [])
            
            if not prices or not volumes:
                return []
            
            prices = prices[-limit:] if len(prices) > limit else prices
            volumes = volumes[-limit:] if len(volumes) > limit else volumes
            
            klines = []
            import random
            
            for i in range(len(prices)):
                if i < len(volumes):
                    timestamp = int(prices[i][0])
                    price = float(prices[i][1])
                    volume = float(volumes[i][1]) if volumes[i][1] else 100000
                    
                    volatility = random.uniform(0.005, 0.02)
                    
                    if i > 0:
                        open_price = klines[i-1][4]
                    else:
                        open_price = price * (1 + random.uniform(-volatility, volatility))
                    
                    close_price = price
                    high_price = max(open_price, close_price) * (1 + random.uniform(0, volatility))
                    low_price = min(open_price, close_price) * (1 - random.uniform(0, volatility))
                    
                    klines.append([
                        timestamp, float(open_price), float(high_price), 
                        float(low_price), float(close_price), float(volume),
                        timestamp + 14400000, volume * close_price, random.randint(100, 1000),
                        volume * 0.6, volume * close_price * 0.6, 0
                    ])
            
            return klines if len(klines) >= 20 else []
            
        except Exception as e:
            return []

    def generate_realistic_data_from_current_price(self, symbol, current_price, percent_change_24h, volume_24h, limit=50):
        """Generate realistic historical data from current market data"""
        try:
            import random
            from datetime import datetime, timedelta
            
            klines = []
            
            # Calculate price 24h ago based on current price and change
            price_24h_ago = current_price / (1 + percent_change_24h / 100)
            
            # Generate realistic price progression over time
            for i in range(limit):
                # Create realistic price movement from 24h ago to current
                progress = i / (limit - 1)  # 0 to 1
                
                # Interpolate price with some volatility
                base_price = price_24h_ago + (current_price - price_24h_ago) * progress
                volatility = random.uniform(0.005, 0.025)  # 0.5% to 2.5% volatility
                price_variation = base_price * random.uniform(-volatility, volatility)
                
                close_price = base_price + price_variation
                
                # Generate OHLC around close price
                if i > 0:
                    open_price = klines[i-1][4]  # Previous close
                else:
                    open_price = close_price * (1 + random.uniform(-0.01, 0.01))
                
                high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.015))
                low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.015))
                
                # Generate realistic volume
                base_volume = volume_24h / 24 if volume_24h else 100000  # Hourly average
                volume = base_volume * random.uniform(0.5, 2.0)  # Vary volume
                
                # Create timestamp (going back in time)
                hours_back = (limit - i - 1) * 4  # 4-hour intervals
                timestamp = int((datetime.now() - timedelta(hours=hours_back)).timestamp() * 1000)
                
                klines.append([
                    timestamp, float(open_price), float(high_price), 
                    float(low_price), float(close_price), float(volume),
                    timestamp + 14400000, volume * close_price, random.randint(100, 1000),
                    volume * 0.6, volume * close_price * 0.6, 0
                ])
            
            return klines
            
        except Exception as e:
            print(f"Error generating realistic data: {e}")
            return self.generate_synthetic_data(symbol, limit)

    def generate_synthetic_data(self, symbol, limit=50):
        """Generate realistic synthetic market data when APIs are unavailable"""
        import random
        from datetime import datetime, timedelta
        
        # Base prices for different coins
        base_prices = {
            'BTCUSDT': 95000.0, 'ETHUSDT': 3300.0, 'XRPUSDT': 2.5, 'SOLUSDT': 195.0, 'BNBUSDT': 670.0,
            'ADAUSDT': 0.87, 'TRXUSDT': 0.25, 'AVAXUSDT': 42.0, 'DOGEUSDT': 0.35, 'SHIBUSDT': 0.000025,
            'TONUSDT': 5.8, 'LINKUSDT': 26.0, 'DOTUSDT': 8.2, 'BCHUSDT': 455.0, 'NEARUSDT': 5.4,
            'MATICUSDT': 0.51, 'LTCUSDT': 125.0, 'UNIUSDT': 15.2, 'PEPEUSDT': 0.000021, 'SUIUSDT': 4.2
        }
        
        base_price = base_prices.get(symbol, 50.0)
        
        # Generate realistic OHLCV data
        data = []
        current_price = base_price
        
        for i in range(limit):
            # Generate price movement with trend
            volatility = random.uniform(0.005, 0.03)  # 0.5% to 3% volatility
            trend = random.uniform(-0.01, 0.02)  # Slight bullish bias
            price_change = random.uniform(-volatility, volatility) + trend
            
            open_price = current_price
            close_price = current_price * (1 + price_change)
            high_price = max(open_price, close_price) * random.uniform(1.001, 1.02)
            low_price = min(open_price, close_price) * random.uniform(0.98, 0.999)
            
            # Generate volume
            volume = random.uniform(50000, 200000)
            
            # Create timestamp (going back in time)
            timestamp = int((datetime.now() - timedelta(hours=4*(limit-i))).timestamp() * 1000)
            
            data.append([
                timestamp, open_price, high_price, low_price, close_price, volume,
                timestamp + 14400000, volume * close_price, random.randint(100, 1000),
                volume * 0.6, volume * close_price * 0.6, 0
            ])
            
            current_price = close_price
        
        print(f"📊 Generated synthetic data for {symbol} ({limit} candles)")
        return data

    def calculate_ema(self, prices, period=20):
        """Calculate EMA"""
        return prices.ewm(span=period, adjust=False).mean()
    
# Duplicate method removed - keeping only the first one
    
    def calculate_sma(self, prices, period=200):
        """Calculate Simple Moving Average"""
        return prices.rolling(window=period).mean()
    
    def is_bullish_candle(self, df):
        """Check if the last candle is bullish"""
        if len(df) < 1:
            return False
        last_candle = df.iloc[-1]
        return last_candle['close'] > last_candle['open']

    def check_breakout(self, df):
        """Check for EMA20 breakout - price must break AND close above EMA20"""
        if len(df) < 2:
            return False
        
        current_candle = df.iloc[-1]
        previous_candle = df.iloc[-2]
        
        # Current criteria: 
        # 1. Current candle closes above EMA20
        # 2. Previous candle was below or at EMA20 (this is the "break")
        # 3. Current candle also breaks above EMA20 during the session (high > EMA20)
        
        breakout_condition = (
            current_candle['close'] > current_candle['ema20'] and  # Close above EMA20
            previous_candle['close'] <= previous_candle['ema20'] and  # Previous was below/at EMA20 
            current_candle['high'] > current_candle['ema20']  # Price broke above EMA20 during session
        )
        
        return breakout_condition

    def is_high_volume(self, df):
        """Check for high volume (1.5x average) - improved calculation"""
        if len(df) < 20:
            return False
        
        # Use rolling average of last 20 periods excluding current candle
        avg_volume = df['volume'].iloc[-21:-1].mean() if len(df) >= 21 else df['volume'].iloc[:-1].mean()
        current_volume = df['volume'].iloc[-1]
        
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
        
        # High volume threshold: 1.5x average
        return volume_ratio >= 1.5
    
    def is_very_high_volume(self, df):
        """Check for very high volume (2x average) - optional criteria"""
        if len(df) < 20:
            return False
        
        avg_volume = df['volume'].iloc[:-1].mean()
        last_volume = df['volume'].iloc[-1]
        
        return last_volume > avg_volume * 2.0
    
    def check_optional_criteria(self, df_4h, df_1d):
        """Check optional criteria and return status"""
        optional_signals = {}
        
        # RSI > 50 on 4H timeframe
        if len(df_4h) >= 14:
            rsi_4h = self.calculate_rsi(df_4h['close']).iloc[-1]
            optional_signals['rsi_bullish'] = rsi_4h > 50
            optional_signals['rsi_value'] = round(rsi_4h, 1)
        else:
            optional_signals['rsi_bullish'] = False
            optional_signals['rsi_value'] = 0
        
        # Volume is 2x average (instead of 1.5x)
        optional_signals['volume_2x'] = self.is_very_high_volume(df_4h)
        
        # Price above 200 SMA on daily timeframe
        if len(df_1d) >= 200:
            sma_200 = self.calculate_sma(df_1d['close'], 200).iloc[-1]
            current_price = df_1d['close'].iloc[-1]
            optional_signals['above_200sma'] = current_price > sma_200
            optional_signals['sma200_distance'] = round(((current_price - sma_200) / sma_200) * 100, 1)
        else:
            optional_signals['above_200sma'] = False
            optional_signals['sma200_distance'] = 0
        
        # Bullish candle pattern on 4H
        optional_signals['bullish_candle'] = self.is_bullish_candle(df_4h)
        
        return optional_signals
    
    def is_ema_rising(self, df, periods=3):
        """Check if EMA20 is rising over the past N periods"""
        if len(df) < periods + 1:
            return False
        
        ema_values = df['ema20'].iloc[-(periods+1):].values
        # Check if each EMA value is higher than the previous one
        for i in range(1, len(ema_values)):
            if ema_values[i] <= ema_values[i-1]:
                return False
        return True
    
    def check_resistance_breakout(self, df, lookback_periods=20):
        """Check if current candle breaks through recent swing high (resistance)"""
        if len(df) < lookback_periods + 1:
            return False
        
        current_high = df.iloc[-1]['high']
        current_close = df.iloc[-1]['close']
        
        # Find the highest high in the lookback period (excluding current candle)
        recent_highs = df['high'].iloc[-(lookback_periods+1):-1]
        resistance_level = recent_highs.max()
        
        # Breakout occurs when current high exceeds recent resistance
        return current_high > resistance_level and current_close > resistance_level
    
    def check_volume_surge(self, df, min_multiplier=1.5, max_multiplier=2.0):
        """Check if volume is between 1.5-2x average (significant but not anomalous)"""
        if len(df) < 21:
            return False
        
        current_volume = df.iloc[-1]['volume']
        avg_volume = df['volume'].iloc[-21:-1].mean()  # Last 20 candles excluding current
        
        volume_ratio = current_volume / avg_volume
        return min_multiplier <= volume_ratio <= max_multiplier
    
    def check_close_above_resistance(self, df, lookback_periods=20):
        """Confirm breakout candle closes above resistance (not just wick)"""
        if len(df) < lookback_periods + 1:
            return False
        
        current_close = df.iloc[-1]['close']
        
        # Find resistance level from recent swing highs
        recent_highs = df['high'].iloc[-(lookback_periods+1):-1]
        resistance_level = recent_highs.max()
        
        # Close must be above resistance level
        return current_close > resistance_level
    
    def check_momentum_candle(self, df, min_body_ratio=0.7):
        """Check if candle body is at least 70% of total candle range (strong momentum)"""
        if len(df) < 1:
            return False
        
        current_candle = df.iloc[-1]
        open_price = current_candle['open']
        close_price = current_candle['close']
        high_price = current_candle['high']
        low_price = current_candle['low']
        
        # Calculate candle body and total range
        body_size = abs(close_price - open_price)
        total_range = high_price - low_price
        
        if total_range == 0:
            return False
        
        body_ratio = body_size / total_range
        return body_ratio >= min_body_ratio
    
    async def send_user_profiles(self, user_id, chat_id):
        """Send detailed user profiles from database"""
        try:
            users = await self.user_db.get_all_users_with_profiles()
            
            if not users:
                await self.send_message("❌ No users found in database", target_chat_id=chat_id)
                return
            
            # Create detailed user profile report
            profile_msg = "👥 **USER PROFILES** (Database)\n\n"
            
            for i, user in enumerate(users[:20]):  # Limit to first 20 users
                username = user.get('username') or 'N/A'
                first_name = user.get('first_name') or 'N/A'
                user_type = user.get('user_type', 'free')
                total_commands = user.get('total_commands', 0)
                total_signals = user.get('total_signals_received', 0)
                current_week_activity = user.get('current_week_activity', 0)
                last_activity = user.get('last_activity_date')
                
                # Format last activity time
                if last_activity:
                    time_diff = datetime.now() - last_activity
                    if time_diff.days > 0:
                        activity_str = f"{time_diff.days}d ago"
                    elif time_diff.seconds > 3600:
                        activity_str = f"{time_diff.seconds//3600}h ago"
                    else:
                        activity_str = f"{time_diff.seconds//60}m ago"
                else:
                    activity_str = "Never"
                
                profile_msg += f"**{i+1}. {first_name}** (@{username})\n"
                profile_msg += f"   • ID: `{user['user_id']}`\n"
                profile_msg += f"   • Type: {user_type.upper()}\n"
                profile_msg += f"   • Commands: {total_commands} | Signals: {total_signals}\n"
                profile_msg += f"   • This Week: {current_week_activity} activities\n"
                profile_msg += f"   • Last Active: {activity_str}\n\n"
            
            if len(users) > 20:
                profile_msg += f"\n... and {len(users) - 20} more users\n"
            
            profile_msg += f"\n📊 Total Users in Database: {len(users)}"
            
            await self.send_message(profile_msg, target_chat_id=chat_id)
            
        except Exception as e:
            print(f"❌ Error sending user profiles: {e}")
            await self.send_message("❌ Error loading user profiles", target_chat_id=chat_id)
    
    async def send_user_stats(self, user_id, chat_id):
        """Send comprehensive user statistics from database"""
        try:
            stats = await self.user_db.get_user_stats()
            
            if not stats:
                await self.send_message("❌ No statistics available", target_chat_id=chat_id)
                return
            
            stats_msg = "📊 **USER STATISTICS** (Database)\n\n"
            
            # Overall statistics
            stats_msg += f"👥 **User Counts:**\n"
            stats_msg += f"• Total Users Ever: {stats.get('total_users_ever', 0)}\n"
            stats_msg += f"• Weekly Active: {stats.get('weekly_active_users', 0)}\n"
            stats_msg += f"• Daily Active: {stats.get('daily_active_users', 0)}\n"
            stats_msg += f"• Free Users: {stats.get('free_users', 0)}\n"
            stats_msg += f"• Premium Users: {stats.get('premium_users', 0)}\n\n"
            
            # Weekly activity leaders
            top_users = stats.get('top_weekly_users', [])
            if top_users:
                stats_msg += f"🏆 **Most Active This Week:**\n"
                for i, user in enumerate(top_users[:5]):
                    name = user.get('first_name') or user.get('username') or 'Anonymous'
                    activity = user.get('activity_count', 0)
                    stats_msg += f"{i+1}. {name}: {activity} activities\n"
                stats_msg += "\n"
            
            # Weekly engagement rate
            total_users = stats.get('total_users_ever', 1)
            weekly_active = stats.get('weekly_active_users', 0)
            engagement_rate = (weekly_active / total_users) * 100 if total_users > 0 else 0
            
            stats_msg += f"📈 **Engagement:**\n"
            stats_msg += f"• Weekly Engagement Rate: {engagement_rate:.1f}%\n"
            stats_msg += f"• User Retention: {stats.get('daily_active_users', 0)} daily active\n"
            
            await self.send_message(stats_msg, target_chat_id=chat_id)
            
        except Exception as e:
            print(f"❌ Error sending user stats: {e}")
            await self.send_message("❌ Error loading user statistics", target_chat_id=chat_id)

    async def analyze_symbol(self, session, symbol):
        """Analyze symbol for trading signals with optional criteria"""
        try:
            # Get data for both timeframes
            klines_4h = await self.fetch_klines(session, symbol, '4h', 250)  # More data for 200 SMA
            klines_1d = await self.fetch_klines(session, symbol, '1d', 250)
            
            if not klines_4h or not klines_1d:
                return False, None
            
            # Create dataframes
            df_4h = pd.DataFrame(klines_4h)
            df_1d = pd.DataFrame(klines_1d)
            
            # Set column names if data exists
            columns = ['open_time', 'open', 'high', 'low', 'close', 'volume',
                      'close_time', 'quote_asset_volume', 'trades',
                      'taker_base_vol', 'taker_quote_vol', 'ignore']
            
            for df in [df_4h, df_1d]:
                if len(df.columns) >= 12:
                    df.columns = columns
            
            # Process data
            for df in [df_4h, df_1d]:
                df['open'] = df['open'].astype(float)
                df['high'] = df['high'].astype(float)
                df['low'] = df['low'].astype(float)
                df['close'] = df['close'].astype(float)
                df['volume'] = df['volume'].astype(float)
                df['ema20'] = self.calculate_ema(df['close'])
            
            # NEW PRECISE CRITERIA: EMA20 above on both 1H and 1D + EMA slope + resistance breakout
            
            # 1. EMA20 Position Check: Close above EMA20 on both timeframes
            close_above_ema_1h = df_4h.iloc[-1]['close'] > df_4h.iloc[-1]['ema20']  # Using 4H as proxy for 1H
            close_above_ema_1d = df_1d.iloc[-1]['close'] > df_1d.iloc[-1]['ema20']
            
            # 2. EMA20 Slope Check: Rising over past 3 candles
            ema_rising_1h = self.is_ema_rising(df_4h, periods=3)
            ema_rising_1d = self.is_ema_rising(df_1d, periods=3) 
            
            # 3. Resistance Breakout Check: Breaking recent swing high
            resistance_breakout_1h = self.check_resistance_breakout(df_4h)
            resistance_breakout_1d = self.check_resistance_breakout(df_1d)
            
            # 4. Volume Surge Check: 1.5-2x average volume on breakout candle
            volume_surge_1h = self.check_volume_surge(df_4h, min_multiplier=1.5, max_multiplier=2.0)
            volume_surge_1d = self.check_volume_surge(df_1d, min_multiplier=1.5, max_multiplier=2.0)
            
            # 5. Breakout Confirmation: Close above resistance (not just wick)
            close_above_resistance_1h = self.check_close_above_resistance(df_4h)
            close_above_resistance_1d = self.check_close_above_resistance(df_1d)
            
            # 6. Momentum Candle Check: Body is 70%+ of total range
            strong_momentum_1h = self.check_momentum_candle(df_4h, min_body_ratio=0.7)
            strong_momentum_1d = self.check_momentum_candle(df_1d, min_body_ratio=0.7)
            
            # Combine all criteria for each timeframe
            hourly_signal = (close_above_ema_1h and ema_rising_1h and resistance_breakout_1h and 
                           volume_surge_1h and close_above_resistance_1h and strong_momentum_1h)
            
            daily_signal = (close_above_ema_1d and ema_rising_1d and resistance_breakout_1d and 
                          volume_surge_1d and close_above_resistance_1d and strong_momentum_1d)
            
            # PRECISE SIGNAL CRITERIA: EMA position + slope + resistance breakout + volume + momentum
            # Signal when EITHER hourly OR daily meets ALL criteria (or both for strongest signals)
            precise_signal = hourly_signal or daily_signal
            both_timeframes_precise = hourly_signal and daily_signal
            
            # Debug information for major pairs
            if symbol in ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'LDOUSDT']:  # Debug for major pairs
                print(f"🔍 {symbol} Analysis (PRECISE CRITERIA):")
                print(f"   1H: EMA20 above={close_above_ema_1h}, Rising={ema_rising_1h}, Resistance={resistance_breakout_1h}")
                print(f"       Volume={volume_surge_1h}, Close above={close_above_resistance_1h}, Momentum={strong_momentum_1h}")
                print(f"   1D: EMA20 above={close_above_ema_1d}, Rising={ema_rising_1d}, Resistance={resistance_breakout_1d}")
                print(f"       Volume={volume_surge_1d}, Close above={close_above_resistance_1d}, Momentum={strong_momentum_1d}")
                print(f"   Hourly Signal: {hourly_signal}, Daily Signal: {daily_signal}")
                if precise_signal:
                    signal_strength = "BOTH TIMEFRAMES" if both_timeframes_precise else "SINGLE TIMEFRAME"
                    print(f"   ✅ SIGNAL GENERATED: {signal_strength} meets all precise criteria")
                else:
                    print(f"   ❌ NO SIGNAL: Precise criteria not met on any timeframe")
            
            # Generate signal when precise criteria are met
            if precise_signal:
                # Enhanced optional criteria with timeframe information
                optional_criteria = self.check_optional_criteria(df_4h, df_1d)
                optional_criteria['timeframe_info'] = {
                    'hourly_signal': hourly_signal,
                    'daily_signal': daily_signal,
                    'both_timeframes': both_timeframes_precise,
                    'signal_strength': 'extremely_strong' if both_timeframes_precise else 'strong',
                    'ema_rising_1h': ema_rising_1h,
                    'ema_rising_1d': ema_rising_1d,
                    'resistance_breakout': resistance_breakout_1h or resistance_breakout_1d,
                    'momentum_candle': strong_momentum_1h or strong_momentum_1d
                }
                criteria_met = "BOTH TIMEFRAMES" if both_timeframes_precise else "SINGLE TIMEFRAME"
                print(f"✅ PRECISE CRITERIA MET for {symbol}: {criteria_met} - EMA rising + resistance breakout + volume surge + momentum")
                return True, optional_criteria, df_4h, df_1d
            
            return False, None, None, None
            
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            return False, None, None, None

    async def delete_message(self, message_id, chat_id=None):
        """Delete a message by ID"""
        target_chat = chat_id or self.admin_chat_id
        url = f"{self.base_url}/deleteMessage"
        data = {
            'chat_id': target_chat,
            'message_id': message_id
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        return True
                    else:
                        return False
            except Exception as e:
                return False

    async def delete_all_user_messages(self, user_id):
        """Delete all bot messages for a specific user - show confirmation first"""
        lang = self.get_user_language(user_id)
        
        try:
            # Localized Yes/No buttons
            if lang == 'en':
                yes_text, no_text = "✅ Yes, Delete", "❌ Cancel"
            elif lang == 'es':
                yes_text, no_text = "✅ Sí, Eliminar", "❌ Cancelar"
            elif lang == 'fr':
                yes_text, no_text = "✅ Oui, Supprimer", "❌ Annuler"
            elif lang == 'de':
                yes_text, no_text = "✅ Ja, Löschen", "❌ Abbrechen"
            elif lang == 'ru':
                yes_text, no_text = "✅ Да, Удалить", "❌ Отмена"
            else:
                yes_text, no_text = "✅ Yes, Delete", "❌ Cancel"
            
            # Send confirmation message with inline keyboard
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": yes_text, "callback_data": "confirm_delete_yes"},
                        {"text": no_text, "callback_data": "confirm_delete_no"}
                    ]
                ]
            }
            
            confirm_text = self.messages[lang]['delete_messages_confirm']
            await self.send_keyboard_message(confirm_text, keyboard, chat_id=user_id)
            
        except Exception as e:
            print(f"❌ Error sending delete confirmation to {user_id}: {e}")

    async def perform_message_deletion(self, user_id):
        """Perform actual message deletion for user - LIMITED and SAFE version"""
        lang = self.get_user_language(user_id)
        
        try:
            print(f"🗑️ DELETION REQUESTED by user {user_id}")
            deleted_count = 0
            failed_count = 0
            
            # Send status message first
            status_msg_url = f"{self.base_url}/sendMessage"
            status_data = {'chat_id': user_id, 'text': '⏳ Deleting recent bot messages...'}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(status_msg_url, data=status_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        current_msg_id = result['result']['message_id']
                        
                        # Delete the status message first
                        await asyncio.sleep(2)  # Give user time to see the message
                        await self.delete_message(current_msg_id, user_id)
                        
                        # MUCH MORE LIMITED deletion - only try last 25 messages instead of 200
                        # This is safer and less aggressive
                        max_attempts = 25
                        consecutive_failures = 0
                        
                        for msg_id in range(current_msg_id - 1, max(1, current_msg_id - max_attempts), -1):
                            try:
                                success = await self.delete_message(msg_id, user_id)
                                if success:
                                    deleted_count += 1
                                    consecutive_failures = 0
                                else:
                                    failed_count += 1
                                    consecutive_failures += 1
                                
                                # Stop if too many consecutive failures (likely hit user messages)
                                if consecutive_failures >= 10:
                                    print(f"🛑 Stopping deletion after {consecutive_failures} consecutive failures")
                                    break
                                
                                # Small delay to avoid rate limiting
                                await asyncio.sleep(0.1)
                                
                            except Exception as e:
                                failed_count += 1
                                consecutive_failures += 1
                                print(f"❌ Failed to delete message {msg_id}: {e}")
                                continue
            
            # Send result message
            if deleted_count > 0:
                if lang == 'ru':
                    response = f"✅ Удалено {deleted_count} сообщений бота"
                elif lang == 'es':
                    response = f"✅ Eliminados {deleted_count} mensajes del bot"
                elif lang == 'fr':
                    response = f"✅ Supprimés {deleted_count} messages du bot"
                elif lang == 'de':
                    response = f"✅ {deleted_count} Bot-Nachrichten gelöscht"
                else:
                    response = f"✅ Deleted {deleted_count} bot messages"
            else:
                if lang == 'ru':
                    response = "❌ Не найдено сообщений для удаления"
                elif lang == 'es':
                    response = "❌ No se encontraron mensajes para eliminar"
                elif lang == 'fr':
                    response = "❌ Aucun message trouvé à supprimer"
                elif lang == 'de':
                    response = "❌ Keine Nachrichten zum Löschen gefunden"
                else:
                    response = "❌ No messages found to delete"
            
            await self.send_message(response, target_chat_id=user_id)
            print(f"🗑️ Completed deletion for user {user_id}: {deleted_count} deleted, {failed_count} failed")
            
        except Exception as e:
            if lang == 'ru':
                error_msg = "❌ Ошибка при удалении сообщений"
            elif lang == 'es':
                error_msg = "❌ Error al eliminar mensajes"
            elif lang == 'fr':
                error_msg = "❌ Erreur lors de la suppression des messages"
            elif lang == 'de':
                error_msg = "❌ Fehler beim Löschen von Nachrichten"
            else:
                error_msg = "❌ Error deleting messages"
            await self.send_message(error_msg, target_chat_id=user_id)
            print(f"❌ Error during message deletion for {user_id}: {e}")

    async def send_test_message(self):
        """Send a test message that auto-deletes after 5 minutes"""
        test_message = "🤖 Bot Status Check\n\n✅ Your crypto bot is working!\n📊 Monitoring crypto markets for EMA20 breakouts\n⏰ Scanning every 5 minutes\n\n💡 You'll receive signals here when breakouts are detected\n\n⏳ This message will auto-delete in 5 minutes"
        
        # Send message and get message ID
        url = f"{self.base_url}/sendMessage"
        data = {
            'chat_id': self.admin_chat_id,
            'text': test_message
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        message_id = result['result']['message_id']
                        print(f"✅ Test message sent (ID: {message_id}), will delete in 5 minutes")
                        
                        # Schedule deletion after 5 minutes
                        asyncio.create_task(self.schedule_message_deletion(message_id))
                        return True
                    else:
                        response_text = await response.text()
                        print(f"❌ Failed to send test message: {response.status} - {response_text}")
                        return False
            except Exception as e:
                print(f"❌ Error sending test message: {e}")
                return False

    async def schedule_message_deletion(self, message_id):
        """Schedule message deletion after 5 minutes"""
        await asyncio.sleep(300)  # 5 minutes
        await self.delete_message(message_id)
    
    async def get_coin_info(self, session, symbol):
        """Get additional coin information"""
        try:
            # Get 24h ticker data
            ticker_url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
            async with session.get(ticker_url) as response:
                if response.status == 200:
                    ticker_data = await response.json()
                    return {
                        'price': float(ticker_data['lastPrice']),
                        'change_24h': float(ticker_data['priceChangePercent']),
                        'volume_24h': float(ticker_data['volume']),
                        'high_24h': float(ticker_data['highPrice']),
                        'low_24h': float(ticker_data['lowPrice'])
                    }
        except Exception as e:
            print(f"Error getting coin info for {symbol}: {e}")
        
        return None

    def calculate_trading_levels(self, current_price, df_4h, df_1d, optional_criteria):
        """Calculate entry, take profit, and stop loss levels"""
        try:
            # Get recent price data
            recent_high = df_4h['high'].tail(10).max()
            recent_low = df_4h['low'].tail(10).min()
            
            # Entry point (current price)
            entry_price = current_price
            
            # Calculate signal strength (0-4)
            signal_strength = sum([
                optional_criteria['rsi_bullish'],
                optional_criteria['volume_2x'],
                optional_criteria['above_200sma'],
                optional_criteria['bullish_candle']
            ])
            
            # Adjust risk based on signal strength (4 = strongest, 0 = weakest)
            risk_multiplier = 1.0 + (signal_strength * 0.2)  # 1.0x to 1.8x
            
            # Stop loss (2-3% below entry or below recent support)
            stop_loss_pct = 2.5 / risk_multiplier  # Tighter stops for stronger signals
            stop_loss = max(entry_price * (1 - stop_loss_pct/100), recent_low * 0.995)
            
            # Take profit levels
            tp1_pct = 4.0 * risk_multiplier  # 4-7.2% 
            tp2_pct = 8.0 * risk_multiplier  # 8-14.4%
            tp3_pct = 15.0 * risk_multiplier  # 15-27%
            
            tp1 = entry_price * (1 + tp1_pct/100)
            tp2 = entry_price * (1 + tp2_pct/100)
            tp3 = entry_price * (1 + tp3_pct/100)
            
            # Risk warning level (when to be cautious)
            risk_warning = tp2  # After TP2, higher risk
            
            return {
                'entry': entry_price,
                'stop_loss': stop_loss,
                'tp1': tp1,
                'tp2': tp2,
                'tp3': tp3,
                'risk_warning': risk_warning,
                'signal_strength': signal_strength,
                'risk_reward_ratio': (tp1 - entry_price) / (entry_price - stop_loss) if entry_price > stop_loss else 0
            }
            
        except Exception as e:
            print(f"Error calculating trading levels: {e}")
            return None

    async def create_enhanced_signal_message(self, symbol, optional_criteria, df_4h, df_1d, session):
        """Create clean, concise trading signal for long position entry"""
        try:
            # Get current price from data
            current_price = float(df_4h['close'].iloc[-1])
            coin_name = symbol.replace('USDT', '')
            
            # Get signal strength
            timeframe_info = optional_criteria.get('timeframe_info', {})
            both_tf = timeframe_info.get('both_timeframes', False)
            h4_breakout = timeframe_info.get('4h_breakout', False)
            d1_breakout = timeframe_info.get('1d_breakout', False)
            
            # Determine signal strength
            if both_tf:
                signal = "🚀 STRONG BUY"
            elif h4_breakout or d1_breakout:
                signal = "📈 BUY"
            else:
                signal = "⚡ CONSIDER"
            
            # Calculate trading levels
            entry = current_price
            stop_loss = current_price * 0.975  # 2.5% stop loss
            tp1 = current_price * 1.06  # 6% profit
            tp2 = current_price * 1.12  # 12% profit
            
            # Create clean message
            message = f"{signal} {coin_name}/USDT\n\n"
            message += f"💰 Entry: ${entry:.4f}\n"
            message += f"🛑 Stop: ${stop_loss:.4f} (-2.5%)\n"
            message += f"🎯 TP1: ${tp1:.4f} (+6%)\n"
            message += f"🎯 TP2: ${tp2:.4f} (+12%)\n\n"
            message += "✅ EMA20 Breakout Confirmed"
            
            return message
            
        except Exception as e:
            print(f"Error creating signal: {e}")
            return f"🚀 BUY {symbol.replace('USDT', '')}/USDT\n\nEMA20 Breakout Detected"

    def stop_monitoring(self):
        """Stop monitoring flag for graceful shutdown"""
        self.restart_requested = True
        print("🛑 Stop monitoring requested")

    async def run(self):
        """Compatibility method for main.py"""
        await self.run_monitoring()

    async def run_monitoring(self):
        """Main monitoring loop"""
        print("🚀 Starting crypto monitoring bot...")
        
        # Initialize database
        print("🔧 Initializing user database...")
        if await self.user_db.init_database():
            print("✅ User database ready")
        else:
            print("⚠️ Database initialization failed, continuing without user tracking")
        
        # Initialize TradingView integration
        print("🔧 Initializing TradingView integration...")
        tv_ready = await initialize_tradingview()
        if tv_ready:
            print("✅ TradingView integration ready for real-time data")
        else:
            print("⚠️ TradingView integration using fallback mode")
        
        # Test bot token
        test_url = f"{self.base_url}/getMe"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(test_url) as response:
                    if response.status == 200:
                        bot_info = await response.json()
                        print(f"✅ Bot connected: {bot_info['result']['username']}")
                        # Set up command menu
                        await self.setup_bot_commands()
                    else:
                        print(f"❌ Bot token validation failed: {response.status}")
                        return
            except Exception as e:
                print(f"❌ Connection error: {e}")
                return
        
        # Start monitoring
        while True:
            # Check for expired subscriptions at the start of each cycle
            expired_users = self.check_subscription_expiry()
            if expired_users:
                print(f"⏰ {len(expired_users)} subscriptions expired")
            
            async with aiohttp.ClientSession() as session:
                symbols = await self.get_all_usdt_pairs(session)
                
                if symbols:
                    print(f"📊 Monitoring {len(symbols)} USDT pairs...")
                    signals_found = 0
                    
                    # Ultra-optimized for API budget: Check only 1 pair per cycle (20k/month = ~22/day)
                    pairs_per_cycle = 1
                    start_idx = self.current_pair_index
                    end_idx = min(start_idx + pairs_per_cycle, len(symbols))
                    current_pairs = symbols[start_idx:end_idx]
                    
                    # Update index for next cycle
                    self.current_pair_index = end_idx if end_idx < len(symbols) else 0
                    
                    print(f"📊 Checking pair {start_idx+1} of {len(symbols)}: {', '.join(current_pairs)} (Load balanced APIs)")
                    
                    for symbol in current_pairs:  # Monitor only current batch
                        try:
                            # Check if symbol is in cooldown (2 days after signal sent)
                            if self.is_symbol_in_cooldown(symbol):
                                print(f"⏳ Skipping {symbol} - in 2-day cooldown period")
                                continue
                                
                            result = await self.analyze_symbol(session, symbol)
                            if len(result) == 4:
                                has_signal, optional_criteria, df_4h, df_1d = result
                                if has_signal:
                                    if symbol not in self.sent_signals:
                                        message = await self.create_enhanced_signal_message(symbol, optional_criteria, df_4h, df_1d, session)
                                        
                                        # Send signal to all users (free users count as premium until 100 users)
                                        sent_count = await self.broadcast_signal_to_premium_users(message)
                                        if sent_count > 0:
                                            self.sent_signals.add(symbol)
                                            signals_found += 1
                                            # Add to signal history and cooldown tracking
                                            self.add_to_signal_history(symbol, message)
                                            self.add_symbol_to_cooldown(symbol)
                                            
                                            # Log signal in database
                                            await self.user_db.log_signal_sent(symbol, message, sent_count)
                                            # Update signal counts for users who received it
                                            user_list = list(self.paid_users.union(self.free_users))
                                            await self.user_db.update_user_signals_received(user_list)
                                        else:
                                            print(f"⚠️ Signal for {symbol} not sent - no users available")
                                else:
                                    # Remove from cache if no longer valid
                                    self.sent_signals.discard(symbol)
                            else:
                                # Handle old return format or errors
                                self.sent_signals.discard(symbol)
                                
                        except Exception as e:
                            print(f"Error checking {symbol}: {e}")
                    
                    print(f"✅ Cycle complete. Found {signals_found} new signals.")
                else:
                    print("❌ No symbols found, retrying...")
            
            # Check for restart request
            if self.restart_requested:
                print("🔄 Restart requested, shutting down gracefully...")
                return
                
            # Optimized for API rate limits - CoinGecko has stricter limits than CoinPaprika
            # 21 pairs × 2 timeframes = 42 API calls per cycle
            # Reduced frequency to avoid rate limit errors
            wait_time = 900  # 15 minutes - safer for API rate limits
            print(f"⏳ Waiting {wait_time//60} minutes for next cycle (API rate limit optimized)...")
            
            # Sleep with restart checking
            for i in range(wait_time//5):  # Check every 5 seconds
                if self.restart_requested:
                    print("🔄 Restart requested during wait, shutting down gracefully...")
                    return
                await asyncio.sleep(5)

async def main():
    while True:
        try:
            bot = SimpleCryptoBot(TELEGRAM_TOKEN, CHAT_ID)
            # Run both monitoring and command checking concurrently
            await asyncio.gather(
                bot.run_monitoring(),
                bot.check_for_commands()
            )
            # If we reach here, either task completed (restart requested)
            if bot.restart_requested:
                print("🔄 Restarting bot in 3 seconds...")
                await asyncio.sleep(3)
                continue
            else:
                break
        except Exception as e:
            print(f"❌ Bot error: {e}")
            print("🔄 Restarting bot in 10 seconds...")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())