import os

# Telegram Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '8161774951:AAGYBbKajxUakx_NwrIClnf87ziQN5Z1ixo')
CHAT_ID = os.getenv('CHAT_ID', '@crypto_high_stakes')

# Binance API Configuration
BINANCE_API_BASE = 'https://api.binance.com/api/v3'
BINANCE_KLINES_ENDPOINT = f'{BINANCE_API_BASE}/klines'
BINANCE_EXCHANGE_INFO_ENDPOINT = f'{BINANCE_API_BASE}/exchangeInfo'

# Trading Parameters
EMA_PERIOD = 20
MONITORING_INTERVAL = 4 * 3600  # 4 hours in seconds
KLINES_LIMIT = 50

# Timeframes
TIMEFRAMES = ['4h', '1d']
