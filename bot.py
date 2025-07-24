import asyncio
import aiohttp
import pandas as pd
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TELEGRAM_TOKEN = '8161774951:AAGYBbKajxUakx_NwrIClnf87ziQN5Z1ixo'
CHAT_ID = '@crypto_high_stakes'  # или ID чата, куда отправлять сигналы

BINANCE_API = 'https://api.binance.com/api/v3/klines'
BINANCE_EXCHANGE_INFO = 'https://api.binance.com/api/v3/exchangeInfo'

# --- Функции для работы с Binance API и анализом ---

async def get_all_usdt_pairs(session):
    async with session.get(BINANCE_EXCHANGE_INFO) as resp:
        data = await resp.json()
        symbols = [
            s['symbol'] for s in data['symbols']
            if s['quoteAsset'] == 'USDT' and s['status'] == 'TRADING'
        ]
        return symbols

async def fetch_klines(session, symbol, interval, limit=50):
    params = {
        'symbol': symbol,
        'interval': interval,
        'limit': limit
    }
    async with session.get(BINANCE_API, params=params) as resp:
        data = await resp.json()
        return data

def calculate_ema(prices, period=20):
    return prices.ewm(span=period, adjust=False).mean()

def check_breakout(df):
    if len(df) < 2:
        return False
    today = df.iloc[-1]
    yesterday = df.iloc[-2]
    return today['close'] > today['ema20'] and yesterday['close'] <= yesterday['ema20']

def is_high_volume(df):
    if len(df) < 20:
        return False
    avg_volume = df['volume'].iloc[:-1].mean()
    last_volume = df['volume'].iloc[-1]
    return last_volume > avg_volume

async def check_symbol(session, symbol):
    klines_4h = await fetch_klines(session, symbol, '4h', 50)
    klines_1d = await fetch_klines(session, symbol, '1d', 50)

    df_4h = pd.DataFrame(klines_4h, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'trades',
        'taker_base_vol', 'taker_quote_vol', 'ignore'
    ])
    df_1d = pd.DataFrame(klines_1d, columns=df_4h.columns)

    for df in [df_4h, df_1d]:
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        df['ema20'] = calculate_ema(df['close'], 20)

    breakout_4h = check_breakout(df_4h) and is_high_volume(df_4h)
    breakout_1d = check_breakout(df_1d) and is_high_volume(df_1d)

    return breakout_4h and breakout_1d

# --- Telegram бота с командами и мониторингом ---

class CryptoBot:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.app = ApplicationBuilder().token(self.token).build()
        self.bot: Bot = self.app.bot
        self.sent_signals = set()  # Кэш отправленных сообщений

        # Регистрируем команды
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("ping", self.cmd_ping))

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Привет! Я крипто-бот. Я мониторю прорывы EMA20 с высоким объёмом.")

    async def cmd_ping(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("✅ Бот работает!")

    async def monitor(self):
        async with aiohttp.ClientSession() as session:
            symbols = await get_all_usdt_pairs(session)
            print(f"Monitoring {len(symbols)} USDT pairs.")
            while True:
                print(f"Checking symbols at {pd.Timestamp.now()}")
                for symbol in symbols:
                    try:
                        if await check_symbol(session, symbol):
                            if symbol not in self.sent_signals:
                                msg = f"🚀 {symbol} broke EMA20 on 4H and 1D with high volume!"
                                print(f"Sending signal: {msg}")
                                await self.bot.send_message(chat_id=self.chat_id, text=msg)
                                self.sent_signals.add(symbol)
                        else:
                            # Если сигнал больше не актуален — удалить из кэша
                            if symbol in self.sent_signals:
                                self.sent_signals.remove(symbol)
                    except Exception as e:
                        print(f"Error checking {symbol}: {e}")
                print("Waiting 4 hours until next check...")
                await asyncio.sleep(4 * 3600)  # пауза 4 часа

    async def run(self):
        # Запускаем одновременно бота и мониторинг
        await asyncio.gather(
            self.app.run_polling(),
            self.monitor()
        )

if __name__ == '__main__':
    crypto_bot = CryptoBot(TELEGRAM_TOKEN, CHAT_ID)
    asyncio.run(crypto_bot.run())