# Crypto EMA20 Breakout Bot - Local Setup Guide

## Prerequisites

1. **Python 3.8+** installed on your machine
2. **Telegram Bot Token** from @BotFather
3. **Your Telegram Chat ID**
4. **TradingView Account** (optional, for enhanced data)

## Installation Steps

### 1. Download the Project Files

Copy these files to your local directory:
- `simple_bot.py` (main bot file)
- `requirements.txt` (dependencies)
- `config.py` (configuration)
- `crypto_analyzer.py` (analysis logic)
- `tradingview_integration.py` (TradingView data)

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install aiohttp pandas python-telegram-bot requests telegram matplotlib numpy pillow
```

### 3. Set Up Environment Variables

Create a `.env` file in your project directory:

```env
TELEGRAM_TOKEN=your_bot_token_here
CHAT_ID=your_chat_id_here
TRADINGVIEW_USERNAME=your_tradingview_username
TRADINGVIEW_PASSWORD=your_tradingview_password
```

**How to get these values:**

#### Telegram Bot Token:
1. Message @BotFather on Telegram
2. Send `/newbot`
3. Follow instructions to create your bot
4. Copy the token provided

#### Your Chat ID:
1. Start a chat with your bot
2. Send any message
3. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Look for `"chat":{"id":123456789}` - that's your chat ID

#### TradingView (Optional):
- Free TradingView account credentials
- Used for enhanced market data

### 4. Run the Bot

```bash
python simple_bot.py
```

## Configuration Options

### Monitoring Settings

Edit these variables in `simple_bot.py`:

```python
# Cryptocurrency pairs to monitor (currently 21 pairs)
symbols = [
    'LDOUSDT', 'EIGENUSDT', 'THETAUSDT', 'DOGEUSDT', 'SOLUSDT',
    'LTCUSDT', 'BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'WLDUSDT',
    'BNBUSDT', 'SUIUSDT', 'SEIUSDT', 'SANDUSDT', 'ARBUSDT',
    'OPUSDT', 'XLMUSDT', 'ADAUSDT', 'UNIUSDT', 'DOTUSDT', 'ATOMUSDT'
]

# Monitoring frequency (in seconds)
wait_time = 900  # 15 minutes between cycles

# Signal cooldown period (in days)
cooldown_period = 2  # 2 days per coin after signal sent
```

### Signal Criteria

The bot uses strict EMA20 breakout criteria:
- **4H timeframe**: Price must break AND close above EMA20 with high volume
- **1D timeframe**: Price must break AND close above EMA20 with high volume
- **Both required**: Signal only triggers when BOTH timeframes confirm

### Volume Requirements

High volume = 1.5x the 20-period average volume

## Bot Features

### Commands Available:
- `/start` - Initialize bot and show main menu
- `/menu` - Show main menu
- `/status` - Check bot status
- `/help` - Show help information

### Signal Format:
```
🚀 STRONG BUY BTC/USDT
💰 Entry: $95,432
🛑 Stop: $93,171 (-2.4%)
🎯 TP1: $97,693 (+2.4%)
🎯 TP2: $99,954 (+4.7%)
🎯 TP3: $102,216 (+7.1%)
```

## Troubleshooting

### Common Issues:

1. **"Bot not responding"**
   - Check your TELEGRAM_TOKEN is correct
   - Verify your CHAT_ID is accurate
   - Make sure bot is added to your chat

2. **"API Rate Limit Errors"**
   - The bot automatically handles rate limits
   - Wait time is set to 15 minutes between cycles
   - CoinGecko fallback has 5-second delays

3. **"No signals generated"**
   - Market conditions must meet strict EMA20 criteria
   - Both 4H and 1D timeframes must confirm breakout
   - High volume (1.5x average) required on both timeframes

4. **"Import errors"**
   - Run: `pip install -r requirements.txt`
   - Check Python version is 3.8+

### Logs and Monitoring:

The bot provides detailed console output:
- API fetch status
- Signal analysis results
- Rate limiting information
- Error messages and recovery

## Security Notes

- Keep your `.env` file private (add to `.gitignore`)
- Never share your Telegram bot token
- TradingView credentials are optional but enhance data quality

## Support

For issues or questions:
- Check console logs for error details
- Verify all environment variables are set correctly
- Ensure Python dependencies are installed

The bot runs continuously, monitoring all configured cryptocurrency pairs and sending signals when strict EMA20 breakout criteria are met on both 4H and 1D timeframes.